#!/usr/bin/env python3
"""One command per job: specs (+ hand canonical JSON) -> job.json -> canonical DXF -> reopen + verify -> report.

    python tools/run_job.py spec_26-061247.yaml spec_26-061248.yaml box.job.json OUT/ [--work WORKDIR] [--individual-dxf]
    (files in page-1 order; the last argument is the output folder)

* builds the canonical job with tools/build_canonical.py (spec: tools/BUILD_CANONICAL_SPEC.md);
* exports with tools/export_canonical_dxf.py (all saved-file gates, XDATA read-back);
* reopens the saved DXF and checks per code: closed outline chain, hole count, entity count;
* prints the rules/OUTPUT.md §8 table (Vietnamese) with every FLAG and the run time.

OUT receives only the DXF deliverable; job.json and report.md go to WORKDIR (default: the job's .work/ dir).
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

import geom  # noqa: E402

from build_canonical import BuildError, build_from_files, summary  # noqa: E402
from canonical_contract import CanonicalContractError  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
import job as job_state  # noqa: E402
import ledger  # noqa: E402


def default_work(job_id: str) -> Path:
    """The current job's work dir when it is this job (tools/job.py), else .work/<job_id> (git-ignored)."""
    try:
        d = job_state.work_dir(None)
        if json.loads((d / "job_state.json").read_text(encoding="utf-8-sig")).get("job") == job_id:
            return d
    except (SystemExit, OSError, ValueError):
        pass
    return job_state.WORK_ROOT / job_id


def _ends(e):
    if e.dxftype() in ("SPLINE", "ELLIPSE"):
        import curves
        return curves.saved_ends(e)
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
    base = [i.split(":S")[0] for i in ids]
    for part in job["parts"]:
        code = part["code"]
        own = {e["entity_id"] for e in part["entities"]}
        mine = [(e, b) for e, b in zip(geo, base) if b in own]
        closed = True
        for loop in (e["entity_id"] for e in part["entities"] if e.get("role") in ("outer", "split_flange")):
            deg = Counter()
            if any(b == loop and e.dxftype() == "CIRCLE" for e, b in mine):
                continue            # a round blank is one CIRCLE: closed by definition
            for e, b in mine:
                if b == loop and e.dxftype() in ("LINE", "ARC", "SPLINE", "ELLIPSE"):
                    for p in _ends(e):
                        deg[(round(p[0], 4), round(p[1], 4))] += 1
            closed = closed and bool(deg) and all(v == 2 for v in deg.values())
        pieces = sum(1 for e, b in mine if any(b == x["entity_id"] and x.get("role") == "outer" for x in part["entities"]))
        holes = sum(1 for e, _ in mine if e.dxftype() == "CIRCLE")
        want = sum(1 for e in part["entities"] if e["type"] == "CIRCLE" or
                   (e["type"] == "LWPOLYLINE" and geom.full_circle(e["vertices"], bool(e.get("closed")))))
        bends = sum(1 for e, _ in mine if e.dxftype() == "LINE" and e.dxf.get("linetype", "").upper() == "DASHED")
        want_b = sum(1 for e in part["entities"] if e.get("role") == "bend")
        if not closed or holes != want or bends != want_b:
            raise SystemExit(f"VERIFY_FAIL {code}: closed={closed} holes={holes}/{want} bend lines={bends}/{want_b}")
        rows[code] = {"outline_pieces": pieces, "closed": closed, "holes": holes, "bend_lines": bends}
    return {"audit_errors": doc.audit().has_errors, "parts": rows}


def report(job, manifest, verify, seconds):
    lines = ["| Mã | Vật liệu / t | Phôi (mm) | Trạng thái | Ghi chú |", "|---|---|---|---|---|"]
    parts = {p["code"]: p for p in job["parts"]}
    for row in summary(job):
        p = parts[row["code"]]
        notes = []
        if row["auto_r"]:
            notes.append(f"Laser R tự động ×{row['auto_r']} ({p.get('laser_r_lookup', {}).get('laser_r', '?')})")
        if row["called"]:
            notes.append(f"R/C theo callout ×{row['called']}")
        if row["holes"]:
            notes.append(f"lỗ ×{row['holes']}")
        if p.get("split_flange"):
            notes.append("tách bích 10 mm: " + ", ".join(s["bend"] for s in p["split_flange"]))
        if p.get("unfold"):
            bs = p["unfold"]["bends"]
            notes.append("uốn ×{}: ".format(len(bs)) + ", ".join(
                f"{b['id']} {b['angle']:g}° N{b['nobi']:g} ({'tay' if b['nobi_source'] == 'HANDWRITTEN' else 'bảng'})"
                for b in bs))
        if row["rotation_deg"]:
            notes.append("xoay 180° để J/LJ nằm trên cạnh thẳng")
        if row["blank_mm"] is None:
            lines.append(f"| {row['code']} | {p['material']} / {p['thickness_mm']:g} | - | {row['status']} | "
                         f"{'; '.join(notes) or '-'} |")
            continue
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
    ap.add_argument("paths", nargs="+", type=Path, help="spec/job files in page-1 order, then the output folder")
    ap.add_argument("--work", type=Path)
    ap.add_argument("--individual-dxf", action="store_true")
    ap.add_argument("--allow-nonslip-codes", action="store_true", help="synthetic/test jobs only")
    a = ap.parse_args(argv)
    if len(a.paths) < 2:
        ap.error("give at least one spec/job file and the output folder")
    *inputs, a.out_dir = a.paths
    t0 = time.monotonic()
    try:
        job = build_from_files(inputs)
    except BuildError as exc:
        print(f"BUILD_FAIL: {exc}", file=sys.stderr)
        return 2
    work = a.work or default_work(job["job_id"])
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
    for part in job["parts"]:  # the spec is the ledger: one readable file per code
        (work / f"ledger_{part['code']}.md").write_text(ledger.render(part["code"], ledger.ledger(part), part),
                                                         encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
