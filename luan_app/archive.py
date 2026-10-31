"""Per-run archive in the app data dir: transcript, out/, a copy of .work/<JOB>/, meta.json; zip and CSV exports."""
from __future__ import annotations

import csv
import io
import json
import shutil
import zipfile
from pathlib import Path

MAX_FILE = 50 * 1024 * 1024
SKIP_WORK = {"CURRENT", "render"}
CSV_COLS = [("id", "id"), ("kind", "kind"), ("job", "job"), ("path", "path"), ("user", "user_name"),
            ("status", "status"), ("summary", "summary"), ("queued_at", "queued_at"), ("started_at", "started_at"),
            ("ended_at", "ended_at"), ("commit", "commit")]


def run_dir(paths, run_id: int) -> Path:
    d = paths.runs_dir / f"{int(run_id):06d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir(paths, run_id: int) -> Path:
    d = run_dir(paths, run_id) / "out"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for f in src.rglob("*"):
        if f.is_file() and f.stat().st_size <= MAX_FILE:
            t = dst / f.relative_to(src)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)
            n += 1
    return n


def archive_work(slot_dir: Path, job: str | None, dest: Path) -> int:
    work = Path(slot_dir) / ".work"
    if not work.is_dir():
        return 0
    target = Path(dest) / "work"
    if job and (work / job).is_dir():
        return _copy_tree(work / job, target / job)
    n = 0
    for d in work.iterdir():
        if d.name in SKIP_WORK:
            continue
        if d.is_dir():
            n += _copy_tree(d, target / d.name)
    return n


def resumable(paths, run: dict) -> bool:
    """An E2E run that broke (Lỗi / Hủy / Quá giờ) and left its job_state.json in the archive."""
    if run.get("kind") != "RUN" or run.get("status") not in ("ERROR", "CANCELLED") or not run.get("job"):
        return False
    return (paths.runs_dir / f"{int(run['id']):06d}" / "work" / run["job"] / "job_state.json").is_file()


def restore_work(src_run_dir: Path, slot_dir: Path, job: str) -> int:
    """Put an archived .work/<JOB> back into a slot (paths in job_state are slot-relative); the source copy is
    staged fresh from the share, so the archived one is left out."""
    src, dst, n = Path(src_run_dir) / "work" / job, Path(slot_dir) / ".work" / job, 0
    for f in src.rglob("*"):
        rel = f.relative_to(src)
        if f.is_file() and rel.parts[0] != "source":
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / rel)
            n += 1
    return n


def write_meta(dest: Path, run: dict, extra: dict) -> None:
    meta = {k: v for k, v in run.items() if not isinstance(v, bytes)}
    meta.update(extra)
    (Path(dest) / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def bundle_zip(dest: Path) -> Path:
    dest = Path(dest)
    z = dest.parent / f"{dest.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in dest.rglob("*"):
            if f.is_file():
                zf.write(f, f"{dest.name}/{f.relative_to(dest).as_posix()}")
    return z


def _cell(v):
    """Excel runs a text cell starting with = + - @ (or tab/CR) as a formula; a leading ' keeps it text."""
    if v is None:
        return ""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def runs_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow([c for c, _ in CSV_COLS])
    for r in rows:
        w.writerow([_cell(r.get(k)) for _, k in CSV_COLS])
    return "﻿" + buf.getvalue()
