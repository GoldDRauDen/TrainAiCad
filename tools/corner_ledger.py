#!/usr/bin/env python3
"""Corner / bend-end ledger: one row per corner and per bend end of every part (Vietnamese output).

Usage: python tools/corner_ledger.py job.json [--out ledger.md]

Reads ``corner_inventory`` (tools/corner_guard.py) and ``bend_end_junctions``
(tools/bend_end_guard.py).  Prints every sharp convex outer corner that has no inventory row as
``THIẾU``.  Exit code 1 when any row is FLAG/THIẾU or any guard error remains, else 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bend_end_guard import bend_end_errors  # noqa: E402
from corner_guard import POINT_TOL, _finite_point, corner_errors, draft_inventory, outer_sharp_corners  # noqa: E402

import math  # noqa: E402


def ledger(part):
    """Return {"corners": [...], "bend_ends": [...], "errors": [...]} for one canonical part."""
    inv = part.get("corner_inventory") or []
    points = [(_finite_point(r.get("point")), r) for r in inv if isinstance(r, dict)]
    corners = []
    for p, row in points:
        corners.append({"id": row.get("corner_id"), "point": p, "drawn": row.get("drawn_shape"),
                        "decision": row.get("decision"), "member": row.get("canonical_member_id"),
                        "evidence": row.get("evidence_ref")})
    for c in outer_sharp_corners(part):
        if not any(p and math.dist(c, p) <= POINT_TOL for p, _ in points):
            corners.append({"id": None, "point": c, "drawn": "SHARP", "decision": "THIẾU", "member": None,
                            "evidence": None})
    ends = []
    for site in part.get("bend_end_junctions", []) or []:
        ends.append({"id": site.get("site_id"), "bends": site.get("bend_ids"), "S": site.get("S_mm"),
                     "mechanism": site.get("mechanism"), "decision": site.get("decision"),
                     "status": site.get("status"), "relief": site.get("relief_member_ids"),
                     "corner_retreat": (site.get("corner_retreat") or {}).get("retreated_flange_id")})
    errors = corner_errors(part) + bend_end_errors(part)
    return {"corners": corners, "bend_ends": ends, "errors": errors}


def render(code, led):
    out = [f"## {code}", "", "### Góc", "", "| id | điểm | hình vẽ | quyết định | member |", "|---|---|---|---|---|"]
    for c in led["corners"]:
        pt = "" if c["point"] is None else f"({c['point'][0]:.3f}, {c['point'][1]:.3f})"
        out.append(f"| {c['id'] or '—'} | {pt} | {c['drawn']} | {c['decision']} | {c['member'] or ''} |")
    out += ["", "### Đầu nếp", "", "| site | nếp | S | cơ chế | quyết định | cánh lùi |", "|---|---|---|---|---|---|"]
    for e in led["bend_ends"]:
        out.append(f"| {e['id']} | {', '.join(e['bends'] or [])} | {e['S']} | {e['mechanism']} | {e['decision']} | {e['corner_retreat'] or ''} |")
    if led["errors"]:
        out += ["", "### Lỗi guard", ""] + [f"- {x}" for x in led["errors"]]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--out")
    ap.add_argument("--draft", action="store_true",
                    help="print a corner_inventory skeleton (all FLAG / UNKNOWN) for each part instead of the ledger")
    args = ap.parse_args(argv)
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    job = job.get("job", job)
    if args.draft:
        drafts = {part.get("code", "?"): draft_inventory(part) for part in job.get("parts", [])}
        text = json.dumps(drafts, indent=1, ensure_ascii=False)
        Path(args.out).write_text(text, encoding="utf-8") if args.out else print(text)
        return 0
    text, bad = "", False
    for part in job.get("parts", []):
        led = ledger(part)
        text += render(part.get("code", "?"), led)
        bad = bad or bool(led["errors"]) or any(c["decision"] in {"FLAG", "THIẾU"} for c in led["corners"])
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
