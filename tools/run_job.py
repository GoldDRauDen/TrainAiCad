#!/usr/bin/env python3
"""One command for a FLAT job: spec -> job.json -> canonical DXF -> reopen + verify -> report.

    python tools/run_job.py spec.yaml OUT/ [--work WORKDIR] [--individual-dxf]

* builds the canonical job with tools/build_canonical.py (spec: tools/BUILD_CANONICAL_SPEC.md);
* exports with tools/export_canonical_dxf.py (all saved-file gates, XDATA read-back);
* reopens the saved DXF and checks per code: closed outline chain, hole count, entity count;
* prints the CAD_OUTPUT.md section-11 table (Vietnamese) with every FLAG and the run time.

OUT receives only the DXF deliverable; job.json and report.md go to WORKDIR (default: spec folder).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ezdxf  # noqa: E402

from build_canonical import BuildError, build_job, load_spec, summary  # noqa: E402
from canonical_contract import CanonicalContractError  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402


def _ends(e):
    if e.dxftype() == "LINE":
        return (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)
    c, r = e.dxf.center, e.dxf.radius
    f = lambda a: (c.x + r * math.cos(math.radians(a)), c.y + r * math.sin(math.radians(a)))  # noqa: E731
    return f(e.dxf.start_angle), f(e.dxf.end_angle)


def verify_saved(path, job, manifest):
    doc = ezdxf.readfile(path)
    geo = [e for e in doc.modelspace() if e.dxf.layer == "0"]
    ids = manifest["entity_map"]
    if len(geo) != len(ids):
        raise SystemExit(f"VERIFY_FAIL entity count saved={len(geo)} expected={len(ids)}")
    rows = {}
    for part in job["parts"]:
        code = part["code"]
        outer = f"E_{code}_OUT:"
        pieces = [e for e, i in zip(geo, ids) if i.startswith(outer) and e.dxftype() in ("LINE", "ARC")]
        deg = Counter()
        for e in pieces:
            for p in _ends(e):
                deg[(round(p[0], 4), round(p[1], 4))] += 1
        holes = sum(1 for e, i in zip(geo, ids) if i.startswith(f"E_{code}_") and e.dxftype() == "CIRCLE")
        want = sum(1 for e in part["entities"] if e["type"] == "CIRCLE")
        closed = bool(pieces) and all(v == 2 for v in deg.values())
        if not closed or holes != want:
            raise SystemExit(f"VERIFY_FAIL {code}: closed={closed} holes={holes}/{want}")
        rows[code] = {"outline_pieces": len(pieces), "closed": closed, "holes": holes}
    return {"audit_errors": doc.audit().has_errors, "parts": rows}


def report(job, manifest, verify, seconds):
    lines = ["| Mã | Vật liệu / t | Phôi (mm) | Trạng thái | Ghi chú |", "|---|---|---|---|---|"]
    parts = {p["code"]: p for p in job["parts"]}
    for row in summary(job):
        p = parts[row["code"]]
        notes = []
        if row["auto_r"]:
            notes.append(f"Laser R tự động ×{row['auto_r']} ({p['laser_r_lookup']['laser_r']})")
        if row["called"]:
            notes.append(f"R/C theo callout ×{row['called']}")
        if row["holes"]:
            notes.append(f"lỗ ×{row['holes']}")
        if row["rotation_deg"]:
            notes.append("xoay 180° để J/LJ nằm trên cạnh thẳng")
        blank = f"{row['blank_mm'][0]:g} × {row['blank_mm'][1]:g}"
        env = p.get("envelope_mm")
        if env and (abs(env[0] - row["blank_mm"][0]) > 0.01 or abs(env[1] - row["blank_mm"][1]) > 0.01):
            blank += f" (bao {env[0]:g} × {env[1]:g})"
        lines.append(f"| {row['code']} | {p['material']} / {p['thickness_mm']:g} | {blank} | {row['status']} | "
                     f"{'; '.join(notes) or '-'} |")
    flags = [(p["code"], f) for p in job["parts"] for f in p.get("flags", [])]
    out = [f"File: {manifest['filename']} (mở lại: audit lỗi={verify['audit_errors']}, mọi contour kín)", "", *lines]
    if flags:
        out += ["", "FLAG:"] + [f"- {c}: {f}" for c, f in flags]
    out += ["", f"Thời gian chạy tool: {seconds:.1f} s"]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--individual-dxf", action="store_true")
    ap.add_argument("--allow-nonslip-codes", action="store_true", help="synthetic/test jobs only")
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        job = build_job(load_spec(a.spec))
    except BuildError as exc:
        print(f"BUILD_FAIL: {exc}", file=sys.stderr)
        return 2
    work = a.work or a.spec.parent
    work.mkdir(parents=True, exist_ok=True)
    job_path = work / f"{job['job_id']}_job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:
        manifest = export_canonical_job(job, a.out_dir, require_slip_codes=not a.allow_nonslip_codes,
                                        individual_dxf=a.individual_dxf)
    except (CanonicalContractError, ValueError) as exc:
        print(f"EXPORT_FAIL: {exc}", file=sys.stderr)
        return 3
    verify = verify_saved(a.out_dir / manifest["filename"], job, manifest)
    text = report(job, manifest, verify, time.monotonic() - t0)
    (work / f"{job['job_id']}_report.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
