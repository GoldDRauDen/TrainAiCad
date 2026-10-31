"""Run one headless `claude -p` session and follow its stream-json output.

The prompt goes on stdin (no quoting or length limits of the Windows command line).
Permission flags were checked on Claude Code 2.1.301 (docs/superpowers/specs/2026-10-30-luan-app-cli-probe.md).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

# Without Git Bash on PATH the CLI offers PowerShell instead of Bash, so every shell rule exists for both.
SHELLS = ("Bash", "PowerShell")
ALLOWED = ["Read", "Glob", "Grep", "Write", "Edit", "TodoWrite"] + [f"{s}({c}:*)" for s in SHELLS for c in ("python", "ls", "dir")]
PROTECTED = ("rules", "tools", "data", "templates", "tests", "examples", "regression", "luan_app", ".claude", ".github")
DENIED = [f"{s}(git:*)" for s in SHELLS] + [f"{t}({d}/**)" for t in ("Edit", "Write") for d in PROTECTED]
NOT_LOGGED_IN = "Claude CLI trên máy Admin chưa đăng nhập: mở cmd chạy `claude auth login` rồi chạy lại job."

LIMIT_RE = re.compile(r"(usage|rate)[ _-]?limit|limit (reached|exceeded)|out of (extra )?usage", re.I)
RESET_RE = re.compile(r"resets? (at|in)? ?[^.\n|]+|\b\d{1,2}(:\d{2})?\s?(am|pm)\b", re.I)


class RunnerError(Exception):
    pass


def claude_executable(override: str | None) -> list[str]:
    if override:
        parts = shlex.split(override, posix=False) if os.name == "nt" or '"' in override else shlex.split(override)
        return [p.strip('"') for p in parts]
    exe = shutil.which("claude")
    if not exe:
        raise RunnerError("Không tìm thấy Claude CLI.")
    return [exe]


def build_command(exe: list[str], out_dir: Path, job_dir: str, model: str) -> list[str]:
    cmd = list(exe) + ["-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "dontAsk",
                       "--allowedTools", *ALLOWED, "--disallowedTools", *DENIED,
                       "--add-dir", str(out_dir), "--add-dir", str(job_dir)]
    return cmd + (["--model", model] if model else [])


def detect_usage_limit(text: str) -> tuple[bool, str | None]:
    if not text or not LIMIT_RE.search(text):
        return False, None
    m = RESET_RE.search(text)
    return True, (m.group(0).strip() if m else None)


def _activity(tool: dict) -> str:
    name, inp = tool.get("name") or "?", tool.get("input") or {}
    if name == "Bash":
        s = f"Bash: {inp.get('command', '')}"
    elif "file_path" in inp:
        s = f"{name}: {inp['file_path']}"
    elif "pattern" in inp:
        s = f"{name}: {inp['pattern']}"
    else:
        s = name
    s = " ".join(s.split())
    return s if len(s) <= 140 else s[:139] + "…"


class ClaudeProcess:
    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.activity, self.activity_at = "", 0.0
        self.result: dict | None = None
        self.usage_limit, self.reset_at, self.reset_hint = False, None, None
        self.utilization: float | None = None
        self.usage: dict = {}
        self.auth_failed = False
        self._reader: threading.Thread | None = None
        self._stderr_path: Path | None = None

    @property
    def pid(self) -> int | None:
        return self.proc.pid if self.proc else None

    def start(self, cmd: list[str], cwd, env: dict, prompt: str, transcript: Path, stderr_log: Path) -> None:
        transcript.parent.mkdir(parents=True, exist_ok=True)
        self._stderr_path = stderr_log
        err = open(stderr_log, "wb")
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kw["start_new_session"] = True
        try:
            self.proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=err, **kw)
        except OSError as e:
            err.close()
            raise RunnerError(f"Không chạy được Claude CLI: {e}") from e
        err.close()
        self.activity_at = time.time()
        try:
            self.proc.stdin.write(prompt.encode("utf-8"))
            self.proc.stdin.close()
        except OSError:
            pass
        self._reader = threading.Thread(target=self._read, args=(transcript,), daemon=True)
        self._reader.start()

    def _read(self, transcript: Path) -> None:
        with open(transcript, "a", encoding="utf-8") as tf:
            for raw in self.proc.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if not isinstance(ev, dict):
                        raise ValueError
                except ValueError:
                    tf.write(json.dumps({"type": "raw", "text": line[:2000]}, ensure_ascii=False) + "\n")
                    continue
                tf.write(line + "\n")
                tf.flush()
                self._event(ev)

    def _event(self, ev: dict) -> None:
        t = ev.get("type")
        if ev.get("error") == "authentication_failed":
            self.auth_failed = True
        if t == "assistant":
            for c in (ev.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    self.activity, self.activity_at = _activity(c), time.time()
        elif t == "rate_limit_event":
            info = ev.get("rate_limit_info") or {}
            five = ((info.get("unifiedWindows") or {}).get("five_hour") or {}).get("utilization")
            if five is not None:
                self.utilization = float(five)
            status = str(info.get("status") or "")
            if status and not status.startswith("allowed"):
                self.usage_limit = True
                self.reset_at = info.get("resetsAt")
        elif t == "result":
            self.result = ev
            self.usage = ev.get("usage") or {}
            if ev.get("is_error"):
                text = str(ev.get("result") or "")
                hit, hint = detect_usage_limit(text)
                if hit:
                    self.usage_limit, self.reset_hint = True, hint
                if "not logged in" in text.lower():
                    self.auth_failed = True

    @property
    def error_text(self) -> str:
        """The CLI's own message when it ended with an error result ("Not logged in · Please run /login")."""
        r = self.result or {}
        return str(r.get("result") or "").strip() if r.get("is_error") else ""

    def poll(self) -> int | None:
        return self.proc.poll() if self.proc else None

    def wait(self, timeout: float) -> int | None:
        try:
            code = self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        if self._reader:
            self._reader.join(timeout=5)
        return code

    def kill(self) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        kill_tree(self.proc.pid)

    def stderr_tail(self, n: int = 20) -> str:
        try:
            lines = self._stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except (OSError, AttributeError):
            return ""
        return "\n".join(lines[-n:])


def kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def process_name(pid: int | None) -> str | None:
    """Image name of a live process (`claude.exe`, `python.exe`), or None."""
    if not pid:
        return None
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
        if not out.startswith('"'):
            return None
        return out.split('","')[0].strip('"')
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return None


def same_program(pid: int | None, name: str | None) -> bool:
    """True when `pid` is still the program we started (guards against pid reuse after a reboot)."""
    actual = process_name(pid)
    if not actual or not name:
        return False
    a, n = actual.lower(), Path(name).name.lower()
    return a == n or Path(a).stem == Path(n).stem or a.startswith(Path(n).stem[:15])


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
