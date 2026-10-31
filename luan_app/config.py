"""Paths and default settings of the AI CAD app (luan_app)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SETTINGS = {
    "slots": 3,                 # runs at the same time (1-6)
    "timeout_min": 120,
    "allowed_roots": [],        # job folders must live under one of these
    "model": "sonnet",          # default for every run (empty in an old database = this default)
    "effort": "high",           # claude --effort: low, medium, high, xhigh, max
    "git_ref": "origin/main",   # what every slot checks out before a run
    "queue_paused_until": None,  # ISO time; set when Claude's usage limit is hit
    "claude_cmd": None,         # override for the Claude CLI (tests: fake_claude)
}
SLOTS_MIN, SLOTS_MAX = 1, 6
USAGE_PAUSE_MIN = 30
ADMIN_SESSION_S = 12 * 3600
USER_COOKIE_S = 365 * 24 * 3600
LOCKOUT_FAILS, LOCKOUT_S = 5, 300
BOARD_CACHE_S = 1.0
PORT = 8765


@dataclass(frozen=True)
class Paths:
    data_dir: Path
    runs_dir: Path
    attachments_dir: Path
    db_path: Path
    log_path: Path
    lock_path: Path
    slots_root: Path
    repo_root: Path


def _default_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "LuanApp"


def _default_slots_root() -> Path:
    return Path("C:/TrainAiCad-slots") if os.name == "nt" else Path.home() / "TrainAiCad-slots"


def load_paths(data_dir=None, slots_root=None, repo_root=None) -> Paths:
    data = Path(data_dir or os.environ.get("LUAN_DATA_DIR") or _default_data_dir())
    slots = Path(slots_root or os.environ.get("LUAN_SLOTS_ROOT") or _default_slots_root())
    p = Paths(data_dir=data, runs_dir=data / "runs", attachments_dir=data / "attachments",
              db_path=data / "state.sqlite", log_path=data / "app.log", lock_path=data / "app.lock",
              slots_root=slots, repo_root=Path(repo_root or REPO_ROOT))
    for d in (p.data_dir, p.runs_dir, p.attachments_dir):
        d.mkdir(parents=True, exist_ok=True)
    return p
