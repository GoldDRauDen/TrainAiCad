"""Claude Code refuses UNC paths (\\\\server\\...) in dontAsk mode, even with --add-dir or allow rules.
So a run works on a copy of the job folder in the slot's `.work/<JOB>/source/`; the copy is archived with the run
(data stays on the Admin machine), and new AI_L deliveries are copied back to the share without overwriting —
during the run too, so an urgent job's per-code DXFs reach the share as soon as each one is drawn."""
from __future__ import annotations

import filecmp
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

AI_L = "AI_L"
QA_MARK = "_AI_QA"   # QA writes <JOB>_AI_QA.txt (+ <JOB>_AI_QA.dxf) into AI_L
SKIP_NAMES = {"thumbs.db", "desktop.ini"}
SKIP_EXT = {".bak", ".dwl", ".dwl2", ".tmp", ".sv$"}


class StagingError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class Staged:
    share_dir: str           # job folder on the share, as the OS opens it
    local_dir: Path          # its copy: <slot>/.work/<JOB>/source
    local_target: str        # what Claude is told to work on (the copy of the folder, or of the given .dxf)
    baseline: dict[str, tuple] = field(default_factory=dict)  # AI_L files copied in: name -> (size, mtime_ns)
    seen: dict[str, tuple] = field(default_factory=dict)      # last look at a file still being written
    sent: dict[str, tuple] = field(default_factory=dict)      # files already handled: name -> (size, mtime_ns)
    copied: list[str] = field(default_factory=list)           # share paths written by this run


def _skip(name: str) -> bool:
    n = name.lower()
    return n in SKIP_NAMES or n.startswith("~$") or os.path.splitext(n)[1] in SKIP_EXT


def stage_in(share_dir: str, target: str, slot_dir: Path, job: str) -> Staged:
    local = Path(slot_dir) / ".work" / job / "source"
    if local.exists():
        shutil.rmtree(local)
    try:
        for root, dirs, files in os.walk(share_dir):
            rel = os.path.relpath(root, share_dir)
            dst = local if rel == "." else local / rel
            dst.mkdir(parents=True, exist_ok=True)
            for f in files:
                if not _skip(f):
                    shutil.copy2(os.path.join(root, f), dst / f)
    except OSError as e:
        raise StagingError(f"Không chép được thư mục job về máy: {e}") from e
    rel_target = os.path.relpath(target, share_dir)
    local_target = str(local) if rel_target == "." else str(local / rel_target)
    ai_l = local / AI_L
    baseline = {f.name: _sig(f) for f in ai_l.iterdir() if f.is_file()} if ai_l.is_dir() else {}
    return Staged(share_dir, local, local_target, baseline)


def _sig(f: Path) -> tuple:
    s = f.stat()
    return s.st_size, s.st_mtime_ns


def _wanted(name: str, kind: str) -> bool:
    n = name.lower()
    if kind == "QA":
        return QA_MARK.lower() in n and n.endswith((".txt", ".dxf"))
    return n.endswith(".dxf")


def _free_name(target_dir: Path, name: str) -> Path:
    stem, ext = os.path.splitext(name)
    base = re.sub(r"_v\d+$", "", stem)
    out, n = target_dir / name, 1
    while out.exists():
        n += 1
        out = target_dir / f"{base}_v{n}{ext}"
    return out


def stage_out(st: Staged, kind: str = "RUN", final: bool = True) -> list[str]:
    """Copy files that appeared in the copy's AI_L to the share's AI_L: never overwrite, never repeat identical content.
    During the run (final=False) a file goes once it is unchanged between two calls (not caught half-written)."""
    src_dir = st.local_dir / AI_L
    if not src_dir.is_dir():
        return []
    dst_dir = Path(st.share_dir) / AI_L
    out = []
    for f in sorted(src_dir.iterdir()):
        if not f.is_file() or not _wanted(f.name, kind):
            continue
        sig = _sig(f)
        if st.baseline.get(f.name) == sig or st.sent.get(f.name) == sig:
            continue
        if not final and st.seen.get(f.name) != sig:
            st.seen[f.name] = sig
            continue
        st.sent[f.name] = sig
        dst_dir.mkdir(exist_ok=True)
        if any(g.is_file() and filecmp.cmp(f, g, shallow=False) for g in dst_dir.glob(f"*{f.suffix}")):
            continue
        dst = _free_name(dst_dir, f.name)
        shutil.copyfile(f, dst)   # not copy2: a fresh mtime marks it as delivered by this run
        out.append(str(dst))
    st.copied += out
    return out
