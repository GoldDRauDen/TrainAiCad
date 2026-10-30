import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from luan_app import runner
from luan_app.runner import ClaudeProcess, build_command, detect_usage_limit

FAKE = Path(__file__).with_name("fake_claude.py")


def fake_cmd(out_dir, job_dir):
    return build_command([sys.executable, str(FAKE)], out_dir, str(job_dir), model="")


def start(tmp_path, mode, **env):
    out, job = tmp_path / "out", tmp_path / "job"
    job.mkdir(exist_ok=True)
    e = dict(os.environ, FAKE_MODE=mode, **env)
    p = ClaudeProcess()
    p.start(fake_cmd(out, job), cwd=tmp_path, env=e, prompt="E2E x\n",
            transcript=tmp_path / "transcript.jsonl", stderr_log=tmp_path / "stderr.log")
    return p


def test_build_command_shape():
    cmd = build_command(["claude"], Path("/o"), "/j", model="")
    i = cmd.index("--permission-mode")
    assert cmd[i + 1] == "dontAsk" and "-p" in cmd and "--model" not in cmd
    for d in runner.DENIED:
        assert d in cmd
    assert cmd.count("--add-dir") == 2
    assert build_command(["claude"], Path("/o"), "/j", model="sonnet")[-2:] == ["--model", "sonnet"]


def test_run_ok_parses_activity_and_result(tmp_path):
    p = start(tmp_path, "ok")
    assert p.wait(30) == 0
    assert p.result["is_error"] is False
    assert p.activity.startswith("Edit: ") or p.activity.startswith("Bash: python tools/")
    assert p.utilization == pytest.approx(0.42)
    assert len((tmp_path / "transcript.jsonl").read_text(encoding="utf-8").splitlines()) >= 4
    assert not p.usage_limit


def test_garbage_lines_tolerated(tmp_path):
    p = start(tmp_path, "garbage")
    assert p.wait(30) == 0 and p.result is not None
    assert '"type": "raw"' in (tmp_path / "transcript.jsonl").read_text(encoding="utf-8")


def test_usage_limit_detected(tmp_path):
    p = start(tmp_path, "limit")
    assert p.wait(30) == 1
    assert p.usage_limit and p.reset_at and p.reset_at > time.time()


def test_crash_stderr_kept(tmp_path):
    p = start(tmp_path, "crash")
    assert p.wait(30) == 3
    assert "fake crash" in p.stderr_tail()


def _alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:  # a zombie still answers kill(0); reaped children are gone
        with open(f"/proc/{pid}/status") as f:
            return "zombie" not in f.read()
    except OSError:
        return False


def test_kill_tree_stops_hang(tmp_path):
    pid_file = tmp_path / "child.pid"
    p = start(tmp_path, "hang", FAKE_CHILD_PID_FILE=str(pid_file))
    for _ in range(100):
        if pid_file.exists() and pid_file.read_text():
            break
        time.sleep(0.1)
    child = int(pid_file.read_text())
    assert _alive(child)
    p.kill()
    assert p.wait(10) is not None
    for _ in range(50):
        if not _alive(child):
            break
        time.sleep(0.1)
    assert not _alive(child)


@pytest.mark.parametrize("text,hit", [
    ("Claude AI usage limit reached|1793400000", True),
    ("You've hit your usage limit · resets 3pm", True),
    ("Rate limit exceeded", True),
    ("5-hour limit reached ∙ resets 7pm", True),
    ("rate of 5 limit switches", False),
    ("all codes PASS", False),
])
def test_detect_usage_limit_patterns(text, hit):
    assert detect_usage_limit(text)[0] is hit


def test_claude_executable_override():
    assert runner.claude_executable('"C:\\Py\\python.exe" C:\\x\\fake.py') == ["C:\\Py\\python.exe", "C:\\x\\fake.py"]
