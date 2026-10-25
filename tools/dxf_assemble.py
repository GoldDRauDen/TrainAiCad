#!/usr/bin/env python3
"""Assemble canonical entities from customer-DATA pieces picked by id (tools/dxf_digest.py). No number is retyped.

    python tools/dxf_assemble.py digest.json plan.json --out assembled.json

plan.json
    {"source_sha256": "<optional, must equal the digest>",
     "transform": {"scale": 2, "rotate_deg": 0, "mirror_x": false, "translate": [0, 0], "evidence": "p1 view 1:2"},
     "members": [{"id": "OUT", "role": "outer", "pieces": ["P0007", ...]},     # one closed LINE/ARC chain
                 {"id": "H1",  "role": "hole",  "pieces": ["P0120"]},          # CIRCLE(s)
                 {"id": "BL1", "role": "bend",  "pieces": ["P0200"]}],         # LINE(s) -> DASHED
     "excluded": [{"reason": "FRAME_OR_TITLE_BLOCK", "view": "V01"},
                  {"reason": "EXPLODED_TEXT_OR_DIM_NOISE", "bucket": "B_NOISE"},
                  {"reason": "TAP_NOMINAL_RING", "pieces": ["P0121"]},
                  {"reason": "DIMENSION_GRAPHIC", "rest_of": "V03"}]}          # rest_of = pieces of V03 not used/excluded elsewhere

Roles: outer (closed, CCW), cutout / slot (closed, CW), hole (CIRCLE), bend (LINE, DASHED), kegaki (LINE, Red 1),
point (POINT, ByLayer). Only layer/colour/linetype and the declared rigid transform (scale>0, rotation, mirror,
translation; scale/rotation/mirror need `evidence`) differ from DATA. Every piece must end up used or excluded with a
reason code (exact duplicates ride on their original); anything else blocks. The result is re-decoded and compared
with the source pieces in both directions (rules/DATA_DXF.md §4) before it is returned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_dxf import signed_poly_area  # noqa: E402

REASONS = {
    "FRAME_OR_TITLE_BLOCK", "EXPLODED_TEXT_OR_DIM_NOISE", "DIMENSION_GRAPHIC", "VIEW_NOT_USED", "ISO_VIEW",
    "HIDDEN_OR_PROJECTION_ONLY", "THICKNESS_REPRESENTATION", "DUPLICATE_COINCIDENT", "TAP_NOMINAL_RING",
    "UNSUPPORTED_CURVE_FLAG", "CENTRE_OR_CONSTRUCTION", "OTHER",
}
CHAIN_ROLES = {"outer": 1, "cutout": -1, "slot": -1}          # required winding sign
SINGLE_ROLES = {"hole": "CIRCLE", "bend": "LINE", "kegaki": "LINE", "point": "POINT"}
ROLE_ATTRS = {"bend": {"linetype": "DASHED"}, "kegaki": {"color": 1}}
ENTITY_ROLE = {"point": "ordinary_point"}
JOIN_TOL = 1e-4          # source endpoints closer than this are the same chain node (closure noise only)
INV_TOL = 2e-4           # invariance gate: not a redraw tolerance, only the chain-closure noise above


class AssembleError(ValueError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _transform(plan_tr: dict, errors: list):
    tr = plan_tr or {}
    scale = tr.get("scale", 1)
    rot = tr.get("rotate_deg", 0)
    mirror = bool(tr.get("mirror_x", False))
    t = tr.get("translate", [0, 0])
    ok = (isinstance(scale, (int, float)) and scale > 0 and isinstance(rot, (int, float))
          and isinstance(t, (list, tuple)) and len(t) == 2 and all(isinstance(v, (int, float)) for v in t))
    if not ok:
        errors.append("TRANSFORM_INVALID: scale>0, numeric rotate_deg, translate [x, y]")
        return None
    if (scale != 1 or rot != 0 or mirror) and not str(tr.get("evidence", "")).strip():
        errors.append("TRANSFORM_NEEDS_EVIDENCE: scale/rotation/mirror must cite where the PDF proves them")
        return None
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def fwd(p):
        x, y = (-p[0] if mirror else p[0]) * scale, p[1] * scale
        return [x * c - y * s_ + t[0], x * s_ + y * c + t[1]]
    return {"scale": float(scale), "rotate_deg": float(rot), "mirror_x": mirror, "translate": [float(t[0]), float(t[1])],
            "evidence": str(tr.get("evidence", "")), "fwd": fwd}


def _account(digest, plan, errors):
    pieces = {p["id"]: p for p in digest["pieces"]}
    unsupported = {u["id"] for u in digest["unsupported"]}
    views = {v["id"]: v["piece_ids"] for v in digest["views"]}
    everything = set(pieces) | unsupported
    owner, used, excluded, detail = {}, [], {}, []

    def claim(pid, who):
        if pid not in everything:
            errors.append(f"UNKNOWN_PIECE: {pid}")
        elif pid in owner:
            errors.append(f"PIECE_USED_TWICE: {pid} ({owner[pid]} and {who})")
        else:
            owner[pid] = who
            return True
        return False
    for m in plan.get("members", []):
        for pid in m.get("pieces", []):
            if pid in unsupported:
                errors.append(f"UNSUPPORTED_PIECE_USED: {pid} ({m.get('id')}): ELLIPSE/SPLINE stay UNKNOWN/FLAG, never flattened")
            elif pid in pieces and pieces[pid].get("duplicate_of"):
                errors.append(f"DUPLICATE_PIECE_USED: {pid} duplicates {pieces[pid]['duplicate_of']}; use the original")
            elif claim(pid, f"member {m.get('id')}"):
                used.append(pid)
    deferred = []
    for ex in plan.get("excluded", []):
        reason = ex.get("reason")
        if reason not in REASONS:
            errors.append(f"UNKNOWN_REASON: {reason!r}; allowed: {', '.join(sorted(REASONS))}")
            continue
        if reason == "OTHER" and not str(ex.get("note", "")).strip():
            errors.append("OTHER_NEEDS_NOTE: reason OTHER must say why in `note`")
            continue
        if "rest_of" in ex:
            deferred.append(ex)
            continue
        ids = list(ex.get("pieces", []))
        for key in ("view", "bucket"):
            if key in ex:
                if ex[key] not in views:
                    errors.append(f"UNKNOWN_VIEW: {ex[key]}")
                ids += views.get(ex[key], [])
        n = 0
        for pid in ids:
            if claim(pid, f"exclusion {reason}"):
                excluded[pid] = reason
                n += 1
        detail.append({"reason": reason, "note": ex.get("note", ""), "pieces": n})
    for ex in deferred:
        if ex["rest_of"] not in views:
            errors.append(f"UNKNOWN_VIEW: {ex['rest_of']}")
            continue
        n = 0
        for pid in views[ex["rest_of"]]:
            if pid not in owner and not pieces.get(pid, {}).get("duplicate_of") and claim(pid, f"exclusion {ex['reason']}"):
                excluded[pid] = ex["reason"]
                n += 1
        detail.append({"reason": ex["reason"], "note": ex.get("note", ""), "pieces": n, "rest_of": ex["rest_of"]})
    auto_dup = 0
    for pid, p in pieces.items():
        if pid not in owner and p.get("duplicate_of") in owner:
            owner[pid] = "duplicate of an accounted piece"
            auto_dup += 1
    merged: dict = {}
    for row in detail:
        key = (row["reason"], row["note"])
        merged.setdefault(key, {"reason": row["reason"], "note": row["note"], "pieces": 0})["pieces"] += row["pieces"]
    detail = list(merged.values())
    missing = sorted(everything - set(owner))
    if missing:
        errors.append(f"UNACCOUNTED_PIECES: {len(missing)} not used or excluded (first: {', '.join(missing[:10])})")
    return pieces, used, excluded, detail, auto_dup, len(missing)


def _nodes(segs):
    """Cluster segment endpoints into nodes (within JOIN_TOL)."""
    nodes = []

    def node_of(pt):
        for k, q in enumerate(nodes):
            if abs(q[0] - pt[0]) <= JOIN_TOL and abs(q[1] - pt[1]) <= JOIN_TOL:
                return k
        nodes.append(pt)
        return len(nodes) - 1
    return [(node_of(s["start"]), node_of(s["end"])) for s in segs]


def _chain(recs, errors, who):
    """Order LINE/ARC pieces into one closed loop; returns [(rec, forward)] or None."""
    segs = [r for r in recs if r["type"] in ("LINE", "ARC")]
    if len(segs) != len(recs) or len(segs) < 2:
        errors.append(f"CHAIN_INVALID: {who} needs >=2 LINE/ARC pieces")
        return None
    ends = _nodes(segs)
    deg = Counter(n for e in ends for n in e)
    if any(d == 1 for d in deg.values()):
        errors.append(f"CHAIN_NOT_CLOSED: {who} has a free end")
        return None
    if any(d != 2 for d in deg.values()):
        errors.append(f"CHAIN_BRANCHED: {who} has a node with more than two pieces")
        return None
    order, here, used = [], ends[0][0], set()
    for _ in segs:
        nxt = next((i for i, (a, b) in enumerate(ends) if i not in used and here in (a, b)), None)
        if nxt is None:
            break
        a, b = ends[nxt]
        forward = a == here
        order.append((segs[nxt], forward))
        used.add(nxt)
        here = b if forward else a
    if len(order) != len(segs) or here != ends[0][0]:
        errors.append(f"CHAIN_NOT_CLOSED: {who} is not one closed loop")
        return None
    return order


def _vertices(order, tr, who):
    mirror = tr["mirror_x"]
    pts, segs = [], []
    for rec, fwd in order:
        a, b = (rec["start"], rec["end"]) if fwd else (rec["end"], rec["start"])
        bulge = 0.0
        if rec["type"] == "ARC":
            sweep = (rec["end_angle"] - rec["start_angle"]) % 360 or 360.0
            bulge = math.tan(math.radians(sweep) / 4) * (1 if fwd != mirror else -1)
        segs.append((tr["fwd"](a), tr["fwd"](b), bulge))
    verts = [[s[0][0], s[0][1], s[2]] for s in segs]
    return verts, segs


def _flip(segs):
    n = len(segs)
    return [[segs[n - 1 - j][1][0], segs[n - 1 - j][1][1], -segs[n - 1 - j][2]] for j in range(n)]


def _build(pieces, plan, tr, errors):
    ents = []
    for m in plan.get("members", []):
        mid, role = str(m.get("id", "")), m.get("role")
        recs = [pieces[i] for i in m.get("pieces", []) if i in pieces and not pieces[i].get("duplicate_of")]
        if not recs:
            continue
        attrs = [{"layer": r["layer"], "color": r["color"], "linetype": r["linetype"]} for r in recs]
        src = [dict(t) for t in {tuple(sorted(a.items())) for a in attrs}]
        base = {"layer": "0", "role": ENTITY_ROLE.get(role, role), "source_piece_ids": [r["id"] for r in recs],
                "source_attrs": sorted(src, key=lambda a: json.dumps(a, sort_keys=True))}
        if role in CHAIN_ROLES:
            order = _chain(recs, errors, f"member {mid}")
            if order is None:
                continue
            verts, segs = _vertices(order, tr, mid)
            if signed_poly_area(verts) * CHAIN_ROLES[role] < 0:
                verts = _flip(segs)
            ents.append({"entity_id": f"E_{mid}", "type": "LWPOLYLINE", "closed": True, "vertices": verts, **base})
        elif role in SINGLE_ROLES:
            want = SINGLE_ROLES[role]
            for k, r in enumerate(recs, 1):
                if r["type"] != want:
                    errors.append(f"ROLE_GEOMETRY_MISMATCH: member {mid} role {role} needs {want}, got {r['type']} {r['id']}")
                    continue
                eid = f"E_{mid}" if len(recs) == 1 else f"E_{mid}_{k}"
                e = {"entity_id": eid, **{**base, "source_piece_ids": [r["id"]]}, **ROLE_ATTRS.get(role, {})}
                if want == "CIRCLE":
                    e.update(type="CIRCLE", center=tr["fwd"](r["center"]), radius=r["radius"] * tr["scale"])
                elif want == "LINE":
                    e.update(type="LINE", start=tr["fwd"](r["start"]), end=tr["fwd"](r["end"]))
                else:
                    e.update(type="POINT", point=tr["fwd"](r["point"]))
                ents.append(e)
        else:
            errors.append(f"UNKNOWN_ROLE: member {mid} role {role!r}; allowed: {', '.join(sorted(set(CHAIN_ROLES) | set(SINGLE_ROLES)))}")
    return ents


# ---- independent decode of the output, compared with the source pieces (both directions) -------------------------

def _arc_from_bulge(p0, p1, b):
    chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    theta = 4 * math.atan(b)
    r = chord / (2 * abs(math.sin(theta / 2)))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    h = r * math.cos(theta / 2)
    ux, uy = (p1[0] - p0[0]) / chord, (p1[1] - p0[1]) / chord
    sgn = 1 if b > 0 else -1
    # centre lies to the left of p0->p1 for a ccw arc (b>0) when the arc is minor; sign of cos handles major arcs
    return [mx - uy * h * sgn, my + ux * h * sgn], r, abs(theta)


def _decode_out(ents):
    prims = []
    for e in ents:
        t = e["type"]
        if t == "LWPOLYLINE":
            v = e["vertices"]
            for a, b in zip(v, v[1:] + v[:1]):
                if a[2] == 0:
                    prims.append(("LINE", tuple(sorted((tuple(a[:2]), tuple(b[:2])))), None, None, None))
                else:
                    c, r, sw = _arc_from_bulge(a[:2], b[:2], a[2])
                    prims.append(("ARC", tuple(sorted((tuple(a[:2]), tuple(b[:2])))), tuple(c), r, sw))
        elif t == "CIRCLE":
            prims.append(("CIRCLE", (tuple(e["center"]),), None, e["radius"], None))
        elif t == "LINE":
            prims.append(("LINE", tuple(sorted((tuple(e["start"]), tuple(e["end"])))), None, None, None))
        elif t == "POINT":
            prims.append(("POINT", (tuple(e["point"]),), None, None, None))
    return prims


def _src_prims(recs, tr):
    prims = []
    for r in recs:
        t, f = r["type"], tr["fwd"]
        if t == "LINE":
            prims.append(("LINE", tuple(sorted((tuple(f(r["start"])), tuple(f(r["end"]))))), None, None, None))
        elif t == "ARC":
            sw = math.radians((r["end_angle"] - r["start_angle"]) % 360 or 360)
            prims.append(("ARC", tuple(sorted((tuple(f(r["start"])), tuple(f(r["end"]))))), tuple(f(r["center"])),
                          r["radius"] * tr["scale"], sw))
        elif t == "CIRCLE":
            prims.append(("CIRCLE", (tuple(f(r["center"])),), None, r["radius"] * tr["scale"], None))
        else:
            prims.append(("POINT", (tuple(f(r["point"])),), None, None, None))
    return prims


def _dist(a, b):
    if a[0] != b[0] or len(a[1]) != len(b[1]):
        return math.inf
    d = max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(a[1], b[1]))
    if a[2] is not None:
        d = max(d, abs(a[2][0] - b[2][0]) + abs(a[2][1] - b[2][1]))
    for i in (3, 4):
        if a[i] is not None:
            d = max(d, abs(a[i] - b[i]))
    return d


def verify_invariance(digest: dict, plan: dict, result: dict) -> dict:
    """Re-decode the output and match it against the source pieces named by the plan, both directions."""
    errs = []
    tr = _transform(plan.get("transform"), errs)
    if tr is None:
        return {"ok": False, "max_dev": None, "errors": errs}
    pieces = {p["id"]: p for p in digest["pieces"]}
    used = [pieces[i] for m in plan.get("members", []) for i in m.get("pieces", []) if i in pieces]
    src = _src_prims(used, tr)
    out = _decode_out(result["entities"])
    tol = INV_TOL * max(1.0, tr["scale"])
    left, worst = list(range(len(src))), 0.0
    for prim in out:
        best, bd = None, math.inf
        for k in left:
            d = _dist(prim, src[k])
            if d < bd:
                best, bd = k, d
        if best is None or bd > tol:
            errs.append(f"OUTPUT_WITHOUT_SOURCE: {prim[0]} {prim[1][0]} nearest source differs by {bd:.6g} mm")
        else:
            left.remove(best)
            worst = max(worst, bd)
    for k in left:
        errs.append(f"SOURCE_MISSING_IN_OUTPUT: {src[k][0]} {src[k][1][0]}")
    return {"ok": not errs, "max_dev": worst, "tolerance_mm": tol, "source_prims": len(src), "output_prims": len(out),
            "errors": errs[:20]}


def assemble(digest: dict, plan: dict) -> dict:
    errors: list[str] = []
    want = plan.get("source_sha256")
    if want and want != digest["source"]["sha256"]:
        raise AssembleError(["DIGEST_HASH_MISMATCH: plan was written for a different DXF"])
    tr = _transform(plan.get("transform"), errors)
    pieces, used, excluded, detail, auto_dup, missing = _account(digest, plan, errors)
    if errors or tr is None:
        raise AssembleError(errors)
    ents = _build(pieces, plan, tr, errors)
    if errors:
        raise AssembleError(errors)
    result = {"entities": ents,
              "transform": {k: v for k, v in tr.items() if k != "fwd"},
              "source": digest["source"],
              "ledger": {"pieces": len(pieces), "unsupported": len(digest["unsupported"]), "used": len(used),
                         "excluded": len(excluded), "duplicates_auto": auto_dup, "unaccounted": missing,
                         "excluded_by_reason": dict(Counter(excluded.values())), "excluded_detail": detail}}
    result["invariance"] = verify_invariance(digest, plan, result)
    if not result["invariance"]["ok"]:
        raise AssembleError(["INVARIANCE_FAILED: " + "; ".join(result["invariance"]["errors"][:5])])
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("digest")
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    digest = json.loads(Path(a.digest).read_text(encoding="utf-8"))
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    src = Path(digest["source"]["file"])
    if src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest() != digest["source"]["sha256"]:
        print("DIGEST_STALE: the DXF changed after the digest was made; digest it again", file=sys.stderr)
        return 2
    try:
        res = assemble(digest, plan)
    except AssembleError as e:
        for line in e.errors:
            print(line, file=sys.stderr)
        return 2
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"entities": len(res["entities"]), "ledger": res["ledger"],
                      "invariance": {k: res["invariance"][k] for k in ("ok", "max_dev")}}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
