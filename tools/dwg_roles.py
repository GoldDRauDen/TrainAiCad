#!/usr/bin/env python3
"""Who made a job's DWG and which one is the checked sample (the reference) or the file to QA.

    python tools/dwg_roles.py "<job folder>"          # lists every DWG with creator / checker / role

Name = <JOB>[-_ ]<creator>[-_ ]<checker>.dwg, separator usually "-" (also "_" or a space). The first token is who drew it, the
second who checked it ("t" = Thanh, "h" = Hiếu; "hcheck" = h checked); no token at all = Thanh drew it. Only the order
matters, not who the people are.
  * a checker token present  -> SAMPLE (checked, usable as the reference);
  * no checker token         -> QA_TARGET (what `QA` audits; with a sample present, audit it against the sample and the PDF).
Ignored: .bak/.dwl/.dwl2/lock files and version-like tokens (v2, 2, copy). One sample per job is used (the newest).
Examples (30-10-2026): 521030-10-LUAN - hcheck.dwg = LUAN drew, h checked -> SAMPLE; 521030-10-LUAN.dwg -> QA_TARGET;
521030-05-Toan -T.dwg -> SAMPLE, 521030-05-Toan.dwg -> QA_TARGET; 521030-07.dwg (no name) -> QA_TARGET drawn by Thanh.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

INITIALS = {"t": "Thanh", "h": "Hiếu"}
DEFAULT_CREATOR = "Thanh"
_NOISE = re.compile(r"^(v?\d+|copy|bak|old|new)$", re.I)


def parse_name(path, job: str | None = None) -> dict:
    stem = Path(path).stem
    m = re.match(r"\d{6}-\d{2}", stem)
    job = job or (m.group(0) if m else None)
    rest = stem[len(job):] if job and stem.startswith(job) else stem
    tokens = [t for t in re.split(r"[-_\s]+", rest) if t and not _NOISE.match(t)]
    creator = tokens[0] if tokens else None
    checker_raw = tokens[1] if len(tokens) > 1 else None
    checker = None
    if checker_raw:
        checker = re.sub(r"check", "", checker_raw, flags=re.I) or "?"
    return {"job": job, "creator": creator or DEFAULT_CREATOR, "creator_named": creator is not None,
            "checker": checker, "checker_name": INITIALS.get((checker or "").lower(), checker), "tokens": tokens}


def classify(files, job: str | None = None) -> dict:
    """roles for the DWG files of one job: {files: [...], sample, qa_target, other_samples}."""
    items = []
    for f in map(Path, files):
        if f.suffix.lower() != ".dwg" or f.name.startswith("~$"):
            continue
        info = parse_name(f, job)
        info.update(file=str(f), role="SAMPLE" if info["checker"] else "QA_TARGET",
                    mtime=f.stat().st_mtime if f.exists() else 0.0)
        items.append(info)
    samples = sorted((i for i in items if i["role"] == "SAMPLE"), key=lambda i: i["mtime"], reverse=True)
    targets = [i for i in items if i["role"] == "QA_TARGET"]
    sample = samples[0] if samples else None
    target = None
    if targets:
        same = [t for t in targets if sample and t["creator"].lower() == sample["creator"].lower()]
        target = max(same or targets, key=lambda i: i["mtime"])
    return {"files": items, "sample": sample["file"] if sample else None, "qa_target": target["file"] if target else None,
            "other_samples": [s["file"] for s in samples[1:]]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    folder = Path(str(a.folder).replace("\\", "/") if str(a.folder).startswith("\\\\") else a.folder)
    res = classify(sorted(folder.glob("*.dwg")) + sorted(folder.glob("*.DWG")))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for i in res["files"]:
            who = f"{i['creator']}" + ("" if i["creator_named"] else " (không ghi tên)") + (f" -> check: {i['checker_name']}" if i["checker"] else "")
            print(f"{i['role']:9} {Path(i['file']).name}  [{who}]")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
