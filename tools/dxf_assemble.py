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
point (POINT, ByLayer), datum (LINE or ARC: a source edge kept only as a coordinate reference, e.g. a view's end or plane
line, a corner R or a chamfer line; an ARC becomes an open one-segment LWPOLYLINE; never drawn - `data_views` in tools/data_part.py reads outline corners and face ranges from it). Only layer/colour/linetype and the declared rigid transform (scale>0, rotation, mirror,
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
from geom import bulge_circle  # noqa: E402

REASONS = {
    "FRAME_OR_TITLE_BLOCK", "EXPLODED_TEXT_OR_DIM_NOISE", "DIMENSION_GRAPHIC", "VIEW_NOT_USED", "ISO_VIEW",
    "HIDDEN_OR_PROJECTION_ONLY", "THICKNESS_REPRESENTATION", "DUPLICATE_COINCIDENT", "TAP_NOMINAL_RING",
    "UNSUPPORTED_CURVE_FLAG", "CENTRE_OR_CONSTRUCTION", "OTHER",
}
CHAIN_ROLES = {"outer": 1, "cutout": -1, "slot": -1}          # required winding sign
SINGLE_ROLES = {"hole": "CIRCLE", "bend": "LINE", "kegaki": "LINE", "point": "POINT"}
ROLE_ATTRS = {"bend": {"linetype": "DASHED"}, "kegaki": {"color": 1}}
ENTITY_ROLE = {"point": "ordinary_point"}
JOIN_TOL = 1e-3          # source endpoints closer than this are the same chain node (closure noise only; each gap is a ledger row)
INV_TOL = 2e-4           # invariance gate: not a redraw tolerance, only the chain-closure noise above
NOISE_ROW_MM = 1e-6      # a node whose endpoints differ by more than this gets a CLOSURE_NOISE ledger row


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


def _t_split(segs, notes, who):
    """A LINE piece whose interior holds the endpoint of another piece of the same member (T-junction, e.g. a bar end drawn
    over the neighbouring plate's edge) is cut there into collinear sub-lines: same geometry, one ledger row."""
    ends = [pt for s in segs for pt in (s["start"], s["end"])]
    out = []
    for s in segs:
        if s["type"] != "LINE":
            out.append(s)
            continue
        a, b = s["start"], s["end"]
        length = math.dist(a, b)
        cuts = []
        for q in ends:
            if q is a or q is b or length <= 2 * JOIN_TOL:
                continue
            t = ((q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])) / length ** 2
            off = abs((q[0] - a[0]) * (b[1] - a[1]) - (q[1] - a[1]) * (b[0] - a[0])) / length
            if JOIN_TOL < t * length < length - JOIN_TOL and off <= JOIN_TOL:
                cuts.append(t)
        if not cuts:
            out.append(s)
            continue
        ts = sorted(set(round(t, 12) for t in cuts))
        pts = [list(a)] + [[a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])] for t in ts] + [list(b)]
        for k in range(len(pts) - 1):
            out.append({**s, "start": pts[k], "end": pts[k + 1], "_parent": s["id"]})
        notes.append({"rule": "T_SPLIT", "member": who, "piece": s["id"], "at": [p[:] for p in pts[1:-1]],
                      "note": "collinear cut at the endpoint of another piece; geometry unchanged"})
    return out


def _prune_spurs(segs, notes, who):
    """After a T split, a sub-line that ends in the air (degree 1) is the overhang of the same piece beyond the contour:
    it is not part of the closed loop and is dropped with a ledger row. Original pieces are never pruned."""
    while True:
        ends = _nodes(segs)
        deg = Counter(n for e in ends for n in e)
        spur = next((i for i, (a, b) in enumerate(ends) if segs[i].get("_parent") and (deg[a] == 1 or deg[b] == 1)), None)
        if spur is None:
            return segs
        s = segs[spur]
        notes.append({"rule": "T_SPUR", "member": who, "piece": s["id"], "dropped": [list(s["start"]), list(s["end"])],
                      "note": "overhang of the piece beyond the T-junction, outside the closed contour"})
        segs = segs[:spur] + segs[spur + 1:]


def _noise_rows(segs, notes, who):
    """CLOSURE_NOISE ledger rows: nodes whose joined endpoints are not bit-identical in the source."""
    ends = _nodes(segs)
    at = {}
    for s, (a, b) in zip(segs, ends):
        at.setdefault(a, []).append((s["id"], s["start"]))
        at.setdefault(b, []).append((s["id"], s["end"]))
    for n, items in at.items():
        gap = max(math.dist(p[1], q[1]) for p in items for q in items)
        if gap > NOISE_ROW_MM:
            notes.append({"rule": "CLOSURE_NOISE", "member": who, "gap_mm": gap, "pieces": sorted({i for i, _ in items}),
                          "at": [round(v, 6) for v in items[0][1]]})


def _chain(recs, errors, who, notes=None):
    """Order LINE/ARC pieces into one closed loop; returns [(rec, forward)] or None."""
    notes = [] if notes is None else notes
    segs = [r for r in recs if r["type"] in ("LINE", "ARC")]
    if len(segs) != len(recs) or len(segs) < 2:
        errors.append(f"CHAIN_INVALID: {who} needs >=2 LINE/ARC pieces")
        return None
    segs = _prune_spurs(_t_split(segs, notes, who), notes, who)
    _noise_rows(segs, notes, who)
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


def _build(pieces, plan, tr, errors, notes=None):
    notes = [] if notes is None else notes
    ents = []
    for m in plan.get("members", []):
        mid, role = str(m.get("id", "")), m.get("role")
        recs = [pieces[i] for i in m.get("pieces", []) if i in pieces and not pieces[i].get("duplicate_of")]
        if not recs:
            continue
        attrs = [{"layer": r["layer"], "color": r["color"], "linetype": r["linetype"]} for r in recs]
        src = [dict(t) for t in {tuple(sorted(a.items())) for a in attrs}]
        base = {"layer": "0", "role": ENTITY_ROLE.get(role, role), "member_id": mid,
                "source_piece_ids": [r["id"] for r in recs],
                "source_attrs": sorted(src, key=lambda a: json.dumps(a, sort_keys=True))}
        if role in CHAIN_ROLES:
            order = _chain(recs, errors, f"member {mid}", notes)
            if order is None:
                continue
            verts, segs = _vertices(order, tr, mid)
            if signed_poly_area(verts) * CHAIN_ROLES[role] < 0:
                verts = _flip(segs)
            ents.append({"entity_id": f"E_{mid}", "type": "LWPOLYLINE", "closed": True, "vertices": verts, **base})
        elif role == "datum":
            for k, r in enumerate(recs, 1):
                eid = f"E_{mid}" if len(recs) == 1 else f"E_{mid}_{k}"
                e = {"entity_id": eid, **{**base, "source_piece_ids": [r["id"]]}}
                if r["type"] == "LINE":
                    e.update(type="LINE", start=tr["fwd"](r["start"]), end=tr["fwd"](r["end"]))
                elif r["type"] == "ARC":
                    verts, segs = _vertices([(r, True)], tr, mid)
                    e.update(type="LWPOLYLINE", closed=False, vertices=verts + [[segs[0][1][0], segs[0][1][1], 0.0]])
                else:
                    errors.append(f"ROLE_GEOMETRY_MISMATCH: member {mid} role datum needs LINE or ARC, got {r['type']} {r['id']}")
                    continue
                ents.append(e)
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
            errors.append(f"UNKNOWN_ROLE: member {mid} role {role!r}; allowed: {', '.join(sorted(set(CHAIN_ROLES) | set(SINGLE_ROLES) | {'datum'}))}")
    return ents


# ---- independent decode of the output, compared with the source pieces (both directions) -------------------------

def _arc_from_bulge(p0, p1, b):
    cx, cy, r, theta = bulge_circle(p0, p1, b)
    return [cx, cy], r, abs(theta)


def _decode_out(ents):
    prims = []
    for e in ents:
        t = e["type"]
        if t == "LWPOLYLINE":
            v = e["vertices"]
            for a, b in zip(v, v[1:] + v[:1] if e.get("closed", True) else v[1:]):
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


def _kept_lines(piece, cuts, dropped):
    """The sub-lines of a T-split LINE piece that stay in the contour (the dropped overhang removed)."""
    a, b = piece["start"], piece["end"]
    length = math.dist(a, b)
    pts = sorted([list(a), list(b)] + [list(c) for c in cuts],
                 key=lambda p: ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / length)
    gone = [{tuple(round(v, 9) for v in d[0]), tuple(round(v, 9) for v in d[1])} for d in dropped]
    return [(p, q) for p, q in zip(pts, pts[1:])
            if {tuple(round(v, 9) for v in p), tuple(round(v, 9) for v in q)} not in gone]


def _src_prims(recs, tr, kept=None):
    prims = []
    kept = kept or {}
    for r in recs:
        t, f = r["type"], tr["fwd"]
        if t == "LINE" and r["id"] in kept:
            for p, q in kept[r["id"]]:
                prims.append(("LINE", tuple(sorted((tuple(f(p)), tuple(f(q))))), None, None, None))
        elif t == "LINE":
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
    rows = result.get("changes", [])
    kept = {}
    for r in rows:
        if r["rule"] == "T_SPUR" and r["piece"] in pieces:
            cuts = [c for x in rows if x["rule"] == "T_SPLIT" and x["piece"] == r["piece"] for c in x["at"]]
            drops = [x["dropped"] for x in rows if x["rule"] == "T_SPUR" and x["piece"] == r["piece"]]
            kept[r["piece"]] = _kept_lines(pieces[r["piece"]], cuts, drops)
    src = _src_prims(used, tr, kept)
    out = _decode_out(result["entities"])
    noise = max([x["gap_mm"] for x in rows if x["rule"] == "CLOSURE_NOISE"], default=0.0)
    tol = max(INV_TOL * max(1.0, tr["scale"]), 4 * noise * max(1.0, tr["scale"]))
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
    from dxf_digest import pieces_sha256
    if digest.get("pieces_sha256") != pieces_sha256(digest):
        raise AssembleError(["DIGEST_PIECES_ALTERED: the decoded pieces are not what tools/dxf_digest.py wrote "
                             "(customer DATA is copied 100%: never add, merge, split or edit a piece; rules/DATA_DXF.md)"])
    tr = _transform(plan.get("transform"), errors)
    pieces, used, excluded, detail, auto_dup, missing = _account(digest, plan, errors)
    if errors or tr is None:
        raise AssembleError(errors)
    notes: list = []
    ents = _build(pieces, plan, tr, errors, notes)
    if errors:
        raise AssembleError(errors)
    result = {"entities": ents, "changes": notes,
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
    digest = json.loads(Path(a.digest).read_text(encoding="utf-8-sig"))
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8-sig"))
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
