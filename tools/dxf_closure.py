#!/usr/bin/env python3
"""Census closure of a whole customer DXF over all its assemble plans (rules/DATA_DXF.md §3).

    python tools/dxf_closure.py digest.json plan_web.json plan_top.json ... [--suggest]

Every plan already accounts for every piece (tools/dxf_assemble.py), but a piece that is only `VIEW_NOT_USED` in each
plan was never harvested nor judged: the file is NOT closed. A piece is closed when some plan uses it, or some plan
excludes it with a real reason (anything but VIEW_NOT_USED). `--suggest` prints the light fix: the reason a
view/linetype/layer suggests, to be copied into the plan's `excluded` (OTHER always needs a human note).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dxf_assemble  # noqa: E402

WEAK = "VIEW_NOT_USED"


def suggest_reason(piece, view_kind):
    lt = piece["linetype"].upper()
    if view_kind == "FRAME_CANDIDATE" or piece["layer"].upper().startswith(("WAKU", "DEFPOINTS")):
        return "FRAME_OR_TITLE_BLOCK"
    if piece["type"] == "POINT":
        return "EXPLODED_TEXT_OR_DIM_NOISE"
    if "CENT" in lt or piece["color"] == 1:
        return "CENTRE_OR_CONSTRUCTION"
    if "DASH" in lt:
        return "HIDDEN_OR_PROJECTION_ONLY"
    if view_kind == "DUPLICATE_COINCIDENT":
        return "DUPLICATE_COINCIDENT"
    return "OTHER"


def closure(digest: dict, plans: list[dict]) -> dict:
    used, strong, weak = set(), {}, set()
    for plan in plans:
        errors: list[str] = []
        _, plan_used, excluded, _, _, _ = dxf_assemble._account(digest, plan, errors)
        if errors:
            raise dxf_assemble.AssembleError(errors)
        used |= set(plan_used)
        for pid, reason in excluded.items():
            (weak.add(pid) if reason == WEAK else strong.setdefault(pid, reason))
    kinds = {v["id"]: v["kind"] for v in digest["views"]}
    home = {pid: v["id"] for v in digest["views"] for pid in v["piece_ids"]}
    unclosed, reasons = [], Counter()
    for p in digest["pieces"]:
        pid = p["id"]
        if pid in used:
            reasons["USED"] += 1
        elif pid in strong:
            reasons[strong[pid]] += 1
        elif p.get("duplicate_of"):
            reasons["DUPLICATE_COINCIDENT"] += 1
        else:
            unclosed.append({"id": pid, "view": home.get(pid), "suggest": suggest_reason(p, kinds.get(home.get(pid)))})
    unsupported = [u["id"] for u in digest["unsupported"] if u["id"] not in used and u["id"] not in strong]
    for pid in unsupported:
        unclosed.append({"id": pid, "view": None, "suggest": "EXPLODED_TEXT_OR_DIM_NOISE"})
    return {"closed": not unclosed, "pieces": len(digest["pieces"]) + len(digest["unsupported"]), "by_reason": dict(reasons),
            "unclosed": unclosed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("digest")
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--suggest", action="store_true", help="print the suggested reason per unclosed piece group")
    a = ap.parse_args(argv)
    digest = json.loads(Path(a.digest).read_text(encoding="utf-8-sig"))
    plans = [json.loads(Path(p).read_text(encoding="utf-8-sig")) for p in a.plans]
    try:
        res = closure(digest, plans)
    except dxf_assemble.AssembleError as exc:
        print("\n".join(exc.errors), file=sys.stderr)
        return 2
    groups = Counter((u["view"], u["suggest"]) for u in res["unclosed"])
    print(json.dumps({"closed": res["closed"], "pieces": res["pieces"], "by_reason": res["by_reason"],
                      "unclosed_count": len(res["unclosed"]),
                      **({"unclosed_groups": [{"view": v, "suggest": s, "pieces": n} for (v, s), n in sorted(groups.items(), key=str)]}
                         if a.suggest or not res["closed"] else {})}, ensure_ascii=False, indent=1))
    return 0 if res["closed"] else 2


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
