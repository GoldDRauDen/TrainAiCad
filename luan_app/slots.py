"""One git worktree per run slot, so parallel jobs never share `.work/CURRENT` and never touch the Admin's checkout."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

FETCH_WARNING = "Không fetch được origin, dùng bản đã có."


class SlotError(Exception):
    pass


def _rmtree(p: Path) -> None:
    def onerror(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    if p.exists():
        shutil.rmtree(p, onerror=onerror)


class Slots:
    def __init__(self, repo_root: Path, slots_root: Path):
        self.repo_root, self.slots_root = Path(repo_root), Path(slots_root)

    def _git(self, *args, cwd: Path | None = None, check=True) -> subprocess.CompletedProcess:
        cmd = ["git", "-c", "core.longpaths=true", *args]
        p = subprocess.run(cmd, cwd=str(cwd or self.repo_root), capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if check and p.returncode != 0:
            raise SlotError(f"git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
        return p

    def path(self, k: int) -> Path:
        return self.slots_root / f"slot{k}"

    def ensure(self, k: int) -> Path:
        p = self.path(k)
        if (p / ".git").exists():
            return p
        self.slots_root.mkdir(parents=True, exist_ok=True)
        self._git("worktree", "prune")
        if p.exists():
            _rmtree(p)
        self._git("worktree", "add", "--detach", str(p), "HEAD")
        return p

    def prepare(self, k: int, ref: str) -> tuple[str, list[str]]:
        p = self.ensure(k)
        warnings = []
        if ref.startswith("origin/") and self._git("fetch", "origin", "--quiet", cwd=p, check=False).returncode != 0:
            warnings.append(FETCH_WARNING)
        self._git("checkout", "--detach", "-f", ref, cwd=p)
        self._git("clean", "-fdx", "-q", cwd=p)
        _rmtree(p / ".work")
        sha = self._git("rev-parse", "HEAD", cwd=p).stdout.strip()
        return sha, warnings

    def touched(self, k: int) -> list[str]:
        out = self._git("status", "--porcelain", "--untracked-files=all", cwd=self.path(k)).stdout
        return [line for line in out.splitlines() if line.strip() and not line[3:].lstrip('"').startswith(".work/")]

    def reset(self, k: int) -> None:
        p = self.path(k)
        if not (p / ".git").exists():
            return
        self._git("checkout", "-f", "HEAD", cwd=p)
        self._git("clean", "-fdx", "-q", "-e", ".work", cwd=p)
