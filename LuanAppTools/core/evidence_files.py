"""Per-code JSON kept beside the published DXF as evidence.

The DXF is the deliverable; the JSON each code ended with is the record of what the model decided and what the
repository's gates accepted. It goes to `evidence/<code>.json` next to the combined DXF (never into a path the
publisher owns), written atomically, and a failure here never fails a run that already published.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _write(path: Path, payload) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=".evidence-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return hashlib.sha256(data).hexdigest()


def write_evidence(root, job_name, run, rows, *, salvage=None, canonical_path=None):
    """Write evidence/<code>.json and evidence/_run.json under `root`; returns the written relative names."""
    base = Path(root) / "evidence"
    written, index = [], []
    for row in sorted(rows, key=lambda r: r["code"]):
        name = SAFE.sub("_", row["code"]) + ".json"
        digest = _write(base / name, {
            "job": job_name, "code": row["code"], "status": row["status"], "attempts": row.get("attempts"),
            "run_id": run["id"], "repo_commit": run["repo_commit"], "source_hash": run["source_hash"],
            **row["data"]})
        written.append(f"evidence/{name}")
        index.append({"code": row["code"], "status": row["status"], "file": name, "sha256": digest})
    if canonical_path and Path(canonical_path).is_file():
        job_json = json.loads(Path(canonical_path).read_text(encoding="utf-8"))
        _write(base / "_job_canonical.json", job_json)
        written.append("evidence/_job_canonical.json")
    _write(base / "_run.json", {
        "job": job_name, "run_id": run["id"], "repo_commit": run["repo_commit"], "source_hash": run["source_hash"],
        "written_at": time.time(), "parts": index, **({"salvage": salvage} if salvage else {})})
    written.append("evidence/_run.json")
    return written
