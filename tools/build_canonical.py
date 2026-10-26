#!/usr/bin/env python3
"""Compact FLAT or single-axis BENT part spec -> complete canonical job.json (tools/canonical_contract.py).

The reader states only what the drawing says: outline corners with their R/C callouts,
repeated notch patterns, holes/slots with their dimension chains, and the overall envelope.
This tool derives the rest deterministically and runs the checks it reports as PASS:

* Laser R from ``lookup.laser_r`` on every uncalled convex corner <=90 deg (AUTO), tangent fillets;
* source_groups / canonical_members / corner_inventory (CALLED / AUTO_R / SHARP / FLAG);
* typed witness graph for every hole/slot (center derived from the chain when ``at`` is omitted);
* closed CCW, non-self-intersecting outline, full containment, envelope match;
* J/LJ marks on the long straight edge: when the max-Y edge is notched/sloped and the
  min-Y edge is straight, the whole part is rotated 180 deg (rules/OUTPUT.md J/LJ line).

Bent parts (L/U/Z/multi-bend chain along one axis): tools/bend_flat.py, `bend:` block in the spec.
Spec format and examples: tools/BUILD_CANONICAL_SPEC.md, examples/flat_minimal.yaml, examples/bend_minimal.yaml.
Never writes DXF; export with tools/export_canonical_dxf.py (or tools/run_job.py).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bend_flat  # noqa: E402
import bend_corner  # noqa: E402
import lookup  # noqa: E402
from dimension_witness import validate_graph  # noqa: E402
from export_dxf import (CHECKS, JLJ_INSET_MM, signed_poly_area)  # noqa: E402
from geometry_containment import _intersects, _loop, part_containment_errors  # noqa: E402
from canonical_contract import CONTRACT  # noqa: E402

EPS = 1e-9
ANGLE_TOL_DEG = 1e-6


class BuildError(ValueError):
    pass


def fail(msg):
    raise BuildError(msg)


def _num(v, where):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        fail(f"{where}: finite number required")
    return float(v)


def _pt(v, where):
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        fail(f"{where}: expected [x, y]")
    return (_num(v[0], where), _num(v[1], where))


def _r6(v):
    r = round(float(v), 6)
    return 0.0 if r == 0 else r


def _unit(v):
    n = math.hypot(*v)
    if n <= EPS:
        fail("zero-length outline edge (duplicate point)")
    return (v[0] / n, v[1] / n)


def auto_corner(material, t, customer=None):
    """Automatic outside-corner treatment: None | ("R"|"C", size) | ("FLAG", vi) for a customer confirm."""
    res = lookup.laser_r(material, t, customer)
    if res.get("status") != "OK":
        if str(res.get("reason", "")).startswith("CUSTOMER_CORNER"):
            return ("FLAG", res["flag_vi"]), res
        fail(f"LASER_R_LOOKUP_FLAG: {res.get('flag_vi') or res}")
    if res.get("rule") and res.get("laser_r") == "NONE":
        return ("SHARP", f"{res['rule']}: góc ngoài để nhọn theo quy định khách hàng"), res
    m = re.fullmatch(r"([RC])(\d+(?:\.\d+)?)", str(res.get("laser_r")))
    return ((m.group(1), float(m.group(2))) if m else None), res


# ------------------------------------------------------------------ outline expansion
def _corner_from_item(item, where):
    """Point item -> dict(at, kind, size, group, ev, reason, flag, bulge)."""
    if isinstance(item, (list, tuple)) and len(item) in (2, 3) and not isinstance(item[0], (list, dict)):
        at = _pt(list(item[:2]), where)
        opts = item[2] if len(item) == 3 else {}
    elif isinstance(item, dict) and "at" in item:
        at = _pt(item["at"], where)
        opts = item
    else:
        fail(f"{where}: point must be [x,y], [x,y,{{...}}] or {{at:[x,y],...}}")
    if not isinstance(opts, dict):
        fail(f"{where}: corner options must be a mapping")
    c = {"at": at, "kind": "AUTO", "size": None, "group": opts.get("group"), "ev": opts.get("ev"),
         "qty": opts.get("qty"), "reason": None, "flag": None, "bulge": 0.0}
    keys = [k for k in ("R", "C", "SHARP", "FLAG") if k in opts]
    if len(keys) > 1 and not (set(keys) == {"FLAG", "R"} or set(keys) == {"FLAG", "C"}):
        fail(f"{where}: use one of R / C / SHARP / FLAG")
    if "R" in opts:
        c.update(kind="R", size=_num(opts["R"], where + ".R"))
    if "C" in opts:
        c.update(kind="C", size=_num(opts["C"], where + ".C"))
    if "SHARP" in opts:
        c.update(kind="SHARP", reason=str(opts["SHARP"]))
    if "FLAG" in opts:
        c["flag"] = str(opts["FLAG"])
    if "bulge" in opts:
        c["bulge"] = _num(opts["bulge"], where + ".bulge")
    if c["kind"] in ("R", "C") and c["size"] <= 0:
        fail(f"{where}: R/C must be positive")
    if c["kind"] in ("R", "C") and not c["flag"] and not c["ev"]:
        fail(f"{where}: called R/C needs ev (callout evidence, e.g. 'p2 R3-3')")
    return c


def _expand_vnotch(spec, where):
    xs = spec.get("x")
    if xs is None:
        start, pitch, count = spec.get("start"), spec.get("pitch"), spec.get("count")
        if None in (start, pitch, count):
            fail(f"{where}: vnotch needs x:[...] or start/pitch/count")
        xs = [float(start) + i * float(pitch) for i in range(int(count))]
    xs = [_num(x, where + ".x") for x in xs]
    axis = spec.get("axis", "X")
    level = _num(spec["level"], where + ".level")
    depth = _num(spec["depth"], where + ".depth")
    angle = _num(spec.get("angle", 90), where + ".angle")
    inward = int(spec.get("inward", -1))  # -1: notch cut toward lower coordinate (top edge); +1 bottom edge
    if inward not in (-1, 1) or depth <= 0 or not 0 < angle < 180:
        fail(f"{where}: invalid vnotch inward/depth/angle")
    half = depth * math.tan(math.radians(angle / 2))
    travel = spec.get("travel")
    if travel is None:
        if len(xs) < 2:
            fail(f"{where}: single vnotch needs travel +1/-1")
        travel = 1 if xs[-1] > xs[0] else -1
    out, members = [], []
    for k, x in enumerate(xs):
        a, b = x - travel * half, x + travel * half
        pts = [(a, level), (x, level + inward * depth), (b, level)]
        if axis == "Y":  # notch on a vertical edge: x-list runs along Y, level is the edge X
            pts = [(q[1], q[0]) for q in pts]
        for p in pts:
            out.append({"at": p, "kind": "AUTO", "size": None, "group": None, "ev": None, "qty": None,
                        "reason": None, "flag": None, "bulge": 0.0, "pattern": True})
        members.append(k)
    grp = {"group": spec.get("group", "V_NOTCH"), "family": "V_NOTCH", "qty": spec.get("qty", len(xs)),
           "count": len(xs), "ev": spec.get("ev") or fail(f"{where}: vnotch needs ev")}
    return out, grp


def _expand_unotch(spec, where):
    ats = spec["at"]
    if ats and not isinstance(ats[0], (list, tuple)):
        ats = [ats]
    inward = _unit(_pt(spec["inward"], where + ".inward"))
    width = _num(spec["width"], where + ".width")
    depth = _num(spec["depth"], where + ".depth")  # mouth -> semicircle center
    if width <= 0 or depth < 0:
        fail(f"{where}: invalid unotch width/depth")
    t = (inward[1], -inward[0])  # travel direction: material (inward) on the left of a CCW outline
    half = width / 2
    mouth = spec.get("mouth", {})
    out = []
    for at in ats:
        mc = _pt(at, where + ".at")
        m1 = (mc[0] - t[0] * half, mc[1] - t[1] * half)
        m2 = (mc[0] + t[0] * half, mc[1] + t[1] * half)
        a1 = (m1[0] + inward[0] * depth, m1[1] + inward[1] * depth)
        a2 = (m2[0] + inward[0] * depth, m2[1] + inward[1] * depth)
        for p, kind, bulge in ((m1, "MOUTH", 0.0), (a1, None, -1.0), (a2, None, 0.0), (m2, "MOUTH", 0.0)):
            c = {"at": p, "kind": "AUTO", "size": None, "group": None, "ev": None, "qty": None,
                 "reason": None, "flag": None, "bulge": bulge, "pattern": True}
            if kind == "MOUTH" and mouth:
                c = _corner_from_item({"at": list(p), **mouth}, where + ".mouth")
                c["pattern"] = True
            out.append(c)
    grp = {"group": spec.get("group", "U_NOTCH"), "family": "OPEN_NOTCH", "qty": spec.get("qty", len(ats)),
           "count": len(ats), "ev": spec.get("ev") or fail(f"{where}: unotch needs ev"),
           "radius": half}
    return out, grp


def expand_outline(items, where):
    corners, patterns = [], []
    for i, item in enumerate(items):
        w = f"{where}.outline[{i}]"
        if isinstance(item, dict) and "vnotch" in item:
            pts, grp = _expand_vnotch(item["vnotch"], w + ".vnotch")
        elif isinstance(item, dict) and "unotch" in item:
            pts, grp = _expand_unotch(item["unotch"], w + ".unotch")
        else:
            corners.append(_corner_from_item(item, w))
            continue
        patterns.append(grp)
        corners.extend(pts)
    # merge consecutive duplicates (a notch mouth that coincides with an explicit corner keeps the explicit one)
    merged = []
    for c in corners:
        if merged and math.dist(merged[-1]["at"], c["at"]) <= 1e-9:
            if merged[-1].get("pattern") and not c.get("pattern"):
                merged[-1] = c
            continue
        merged.append(c)
    if len(merged) > 1 and math.dist(merged[0]["at"], merged[-1]["at"]) <= 1e-9:
        if merged[0].get("pattern") and not merged[-1].get("pattern"):
            merged[0] = merged[-1]
        merged.pop()
    if len(merged) < 3:
        fail(f"{where}: outline needs at least 3 corners")
    return merged, patterns


def _corner_geometry(prev, p, nxt):
    a, b = _unit((prev[0] - p[0], prev[1] - p[1])), _unit((nxt[0] - p[0], nxt[1] - p[1]))
    alpha = math.acos(max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1])))
    cross = (p[0] - prev[0]) * (nxt[1] - p[1]) - (p[1] - prev[1]) * (nxt[0] - p[0])
    return a, b, alpha, cross


def build_outline(corners, auto, where):
    """Return LWPOLYLINE vertices and per-corner decisions (convexity, angle, applied treatment)."""
    n = len(corners)
    area2 = sum(corners[i]["at"][0] * corners[(i + 1) % n]["at"][1] -
                corners[(i + 1) % n]["at"][0] * corners[i]["at"][1] for i in range(n))
    if area2 <= 0:
        fail(f"{where}: outline must be listed counter-clockwise (material on the left)")
    verts, decisions = [], []
    for i, c in enumerate(corners):
        prev, nxt = corners[i - 1], corners[(i + 1) % n]
        p = c["at"]
        a, b, alpha, cross = _corner_geometry(prev["at"], p, nxt["at"])
        convex = cross > EPS
        deg = math.degrees(alpha)
        eligible = convex and deg <= 90 + ANGLE_TOL_DEG and not prev["bulge"] and not c["bulge"]
        kind, size = c["kind"], c["size"]
        decision = None
        if c["flag"] and kind in ("AUTO", "SHARP"):
            kind, decision = "NONE", "FLAG"  # unresolved corner: keep the drawn sharp vertex, no automatic R
        elif kind == "AUTO":
            if eligible and auto and auto[0] == "FLAG":
                c = dict(c, flag=auto[1])
                kind, decision = "NONE", "FLAG"
            elif eligible and auto and auto[0] == "SHARP":
                c = dict(c, reason=auto[1])
                kind, decision = "SHARP", "SHARP"
            elif eligible and auto:
                (kind, size), decision = auto, "AUTO_R"
            elif eligible:
                kind, decision = "SHARP", "SHARP"
                c = dict(c, reason="bảng Laser R: không có R tự động cho vật liệu/độ dày này")
            else:
                kind = "NONE"
        elif kind == "SHARP":
            decision = "SHARP"
        else:
            decision = "FLAG" if c["flag"] else "CALLED"
        if kind in ("R", "C") and (c["bulge"] or prev["bulge"]):
            fail(f"{where}: corner {p} touches an arc; R/C only between straight edges")
        if kind == "R":
            d = size / math.tan(alpha / 2)
            t1 = (p[0] + a[0] * d, p[1] + a[1] * d)
            t2 = (p[0] + b[0] * d, p[1] + b[1] * d)
            bulge = (1.0 if convex else -1.0) * math.tan((math.pi - alpha) / 4)
            verts += [[t1[0], t1[1], bulge], [t2[0], t2[1], 0.0]]
        elif kind == "C":
            d = size
            verts += [[p[0] + a[0] * d, p[1] + a[1] * d, 0.0], [p[0] + b[0] * d, p[1] + b[1] * d, 0.0]]
        else:
            verts.append([p[0], p[1], c["bulge"]])
        decisions.append({"corner": c, "convex": convex, "angle_deg": deg, "eligible": eligible,
                          "kind": kind, "size": size, "decision": decision})
    # trimming must not overrun the edges
    for i in range(len(verts)):
        if math.dist(verts[i][:2], verts[(i + 1) % len(verts)][:2]) <= 1e-7:
            fail(f"{where}: R/C larger than the adjacent edge near {verts[i][:2]}")
    verts = [[_r6(v[0]), _r6(v[1]), round(v[2], 12) if v[2] else 0] for v in verts]
    return verts, decisions


def _self_intersects(verts):
    pts = _loop(verts)
    segs = list(zip(pts, pts[1:] + pts[:1]))
    n = len(segs)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if _intersects(*segs[i], *segs[j]):
                return True
    return False


# ------------------------------------------------------------------ witness chains
def _chain(fid, axis, steps, datum, page, nodes, edges, start_type="OUTER_EDGE", end_type="HOLE_CENTER"):
    if not isinstance(steps, list) or not steps:
        fail(f"{fid}: witness {axis} needs at least one step [value, type, evidence]")
    prev = f"{fid}_{axis}_D"
    nodes[prev] = start_type
    total = 0.0
    for k, step in enumerate(steps):
        if not isinstance(step, (list, tuple)) or len(step) not in (3, 4):
            fail(f"{fid}: witness step must be [value, to_type, evidence] or [value, to_type, evidence, kind]")
        value, to_type, ev = _num(step[0], f"{fid} {axis}[{k}]"), str(step[1]), str(step[2])
        kind = str(step[3]) if len(step) == 4 else ("LOCAL" if k == 0 else "CHAIN")
        node = f"{fid}_{axis}_{k}"
        nodes[node] = to_type
        edges.append({"from_node": prev, "to_node": node, "axis": axis, "kind": kind, "value_mm": value,
                      "proof": {"pdf_page": page, "evidence_ref": ev, "endpoint_verified": True,
                                "from_type": nodes[prev], "to_type": to_type}})
        prev, total = node, total + value
    if nodes[prev] != end_type:
        fail(f"{fid}: witness {axis} must end on a {end_type} node")
    return prev, total


# ------------------------------------------------------------------ face chains (one or two axes)
def _load_chains(bend_spec, material, t, customer, code):
    if bend_spec.get("bends") is not None and "chains" in bend_spec:
        fail(f"{code}: bend block has both bends and chains")
    specs = bend_spec["chains"] if "chains" in bend_spec else [bend_spec]
    shared = {k: v for k, v in bend_spec.items() if k not in ("chains", "faces", "bends", "axis", "origin")}
    chains = [bend_flat.unfold_chain({**shared, **cs}, material, t, customer, code) for cs in specs]
    if len(chains) > 2 or (len(chains) == 2 and chains[0]["axis"] == chains[1]["axis"]):
        fail(f"{code}: chains: one per axis (X and Y)")
    bend_ids = [b["id"] for c in chains for b in c["bends"]]
    if len(bend_ids) != len(set(bend_ids)):
        fail(f"{code}: bend ids must be unique across chains")
    return chains


def _chain_key(item):
    """Which chain a face-relative item sits on in a two-axis part: `chain: X|Y`, or a string `axis` (older specs).
    A slot's own `axis` is its direction vector in the flat and never selects a chain."""
    if item.get("chain") is not None:
        return item["chain"]
    return item["axis"] if isinstance(item.get("axis"), str) else None


def _face_chain(chains, face, axis, where):
    owners = [c for c in chains if face in c["faces"]]
    if axis:
        owners = [c for c in owners if c["axis"] == str(axis).upper()]
    if not owners:
        fail(f"{where}: unknown face {face}" + (f" on axis {axis}" if axis else ""))
    if len(owners) > 1:
        fail(f"{where}: face {face} is in both chains: add axis: X|Y")
    return owners[0]


def _resolve_outline(items, chains, code):
    out = []
    for item in items:
        if isinstance(item, dict) and "face" in item:
            ch = _face_chain(chains, item["face"], _chain_key(item), code)
            res = bend_flat.resolve_outline([{k: v for k, v in item.items() if k not in ("axis", "chain")}], ch, code)
            out += res
        else:
            out.append(item)
    return out


# ------------------------------------------------------------------ part
def _cutout_vertices(c, chains, where):
    """Rectangular opening (optionally R-cornered) -> CW closed LWPOLYLINE vertices [x, y, bulge].

    `rect: [x0, y0, x1, y1]` in flat coordinates, or `face/from/u/v` like a hole on a bent face.
    """
    if not c.get("ev"):
        fail(f"{where}: cutout needs ev")
    if "vertices" in c:  # exact closed polygon, e.g. customer DATA (tools/data_part.py): kept as given
        verts = [[_num(v[0], where), _num(v[1], where), _num(v[2] if len(v) > 2 else 0, where)] for v in c["vertices"]]
        if len(verts) < 2 or (len(verts) == 2 and not any(v[2] for v in verts)) or signed_poly_area(verts) >= 0:
            fail(f"{where}: cutout vertices must be a closed clockwise loop")
        return [[_r6(x), _r6(y), g] for x, y, g in verts]
    if "face" in c:
        if not chains:
            fail(f"{where}: face needs a bend block")
        chain = _face_chain(chains, c["face"], _chain_key(c), where)
        try:
            d, _, sgn, _ = bend_flat.face_datum(chain, c["face"], c.get("from"), where)
        except bend_flat.BendError as exc:
            fail(str(exc))
        u0, u1 = (_num(x, where + ".u") for x in c["u"])
        v0, v1 = (_num(x, where + ".v") for x in c["v"])
        (a0, b0), (a1, b1) = bend_flat.to_flat(chain, d + sgn * u0, v0), bend_flat.to_flat(chain, d + sgn * u1, v1)
        x0, y0, x1, y1 = min(a0, a1), min(b0, b1), max(a0, a1), max(b0, b1)
    else:
        rect = c.get("rect")
        if not isinstance(rect, (list, tuple)) or len(rect) != 4:
            fail(f"{where}: cutout needs rect [x0, y0, x1, y1] or face/u/v")
        x0, y0, x1, y1 = (_num(v, where + ".rect") for v in rect)
        if not (x0 < x1 and y0 < y1):
            fail(f"{where}: rect needs x0<x1 and y0<y1, got {list(rect)}")
    r = _num(c.get("R", 0), where + ".R")
    if r < 0 or 2 * r > min(x1 - x0, y1 - y0) + EPS:
        fail(f"{where}: R {r:g} larger than half of the {x1 - x0:g} x {y1 - y0:g} opening")
    if r <= EPS:
        pts = [[x0, y1, 0], [x1, y1, 0], [x1, y0, 0], [x0, y0, 0]]
    else:
        b = -math.tan(math.pi / 8)
        pts = [[x0 + r, y1, 0], [x1 - r, y1, b], [x1, y1 - r, 0], [x1, y0 + r, b],
               [x1 - r, y0, 0], [x0 + r, y0, b], [x0, y0 + r, 0], [x0, y1 - r, b]]
    return [[_r6(x), _r6(y), round(g, 12) if g else 0] for x, y, g in pts]


def build_part(spec, customer=None):
    if spec.get("data") is not None or spec.get("data_views") is not None:
        import data_part
        try:
            spec, extra = data_part.to_spec(spec, customer)
        except data_part.DataPartError as exc:
            fail(str(exc))
        part = build_part(spec, customer)
        return data_part.finish(part, extra)
    code = str(spec.get("code") or fail("part: code required"))
    where = code
    material = str(spec.get("material") or fail(f"{code}: material required"))
    t = _num(spec.get("t"), f"{code}.t")
    page = int(spec.get("page", 1))
    if spec.get("bends"):
        fail(f"{code}: use a `bend:` block (faces + bends), see tools/BUILD_CANONICAL_SPEC.md")
    if spec.get("bend") and "chains" not in spec["bend"]:
        plan = bend_flat.split_plan(spec["bend"], material, t, customer, code)
        if plan:
            return _build_split(spec, plan, customer)
    chains = []
    try:
        if spec.get("bend"):
            chains = _load_chains(spec["bend"], material, t, customer, code)
        outline = spec.get("outline") or fail(f"{code}: outline required")
        if chains:
            if outline == "auto":
                if len(chains) != 1:
                    fail(f"{code}: outline auto is for one chain only; list the two-axis outline")
                outline = bend_flat.auto_outline(spec["bend"], chains[0], code)
            else:
                outline = _resolve_outline(outline, chains, code)
    except bend_flat.BendError as exc:
        fail(str(exc))
    auto, laser = auto_corner(material, t, customer)
    corners, patterns = expand_outline(outline, where)
    verts, decisions = build_outline(corners, auto, where)
    b_ents, b_groups, bend_graph, bend_ledger, corner_rec = [], [], None, None, None
    if chains:
        try:
            corner_rec = bend_corner.records(verts, chains, code, page, material, t)
        except (bend_corner.CornerError, bend_flat.BendError, ValueError) as exc:
            fail(str(exc))
        verts = corner_rec["verts"]
        b_ents, b_groups, bend_ledger = corner_rec["entities"], corner_rec["groups"], corner_rec["ledger"]
        faces, seen = [], set()
        for ch in chains:
            for f in bend_flat.face_records(ch, page):
                if f["face_id"] not in seen:
                    seen.add(f["face_id"])
                    faces.append(f)
        bend_graph = {"faces": faces, "bends": corner_rec["graph_bends"]}

    def bend_line_entity(bid, which):
        return next(e["entity_id"] for e in b_ents
                    if e["entity_id"].startswith(f"E_{code}_{bid}") and e["entity_id"].endswith(f"_{which}"))
    if signed_poly_area(verts) <= 0 or _self_intersects(verts):
        fail(f"{code}: CONTOUR_TOPOLOGY outline is not a simple CCW loop")
    xs, ys = [c["at"][0] for c in corners], [c["at"][1] for c in corners]
    env = spec.get("envelope") or fail(f"{code}: envelope [Ox, Oy] required (overall drawing/slip size)")
    nominal = (max(xs) - min(xs), max(ys) - min(ys))
    tol = float(spec.get("envelope_tol", 0.5))
    if abs(nominal[0] - float(env[0])) > tol or abs(nominal[1] - float(env[1])) > tol:
        fail(f"{code}: ENVELOPE_MISMATCH nominal {nominal[0]:.3f} x {nominal[1]:.3f} != envelope {env}")

    p = code
    eo = f"E_{p}_OUT"
    ents = [{"entity_id": eo, "type": "LWPOLYLINE", "role": "outer", "closed": True, "vertices": verts}]
    groups, members, inventory, flags = [], [], [], list(spec.get("flags") or [])
    groups.append({"group_id": f"{p}_G_OUTER", "family": "OUTER", "status": "PROVED", "source_quantity": 1,
                   "evidence": "closed outer profile", "members": [{"member_id": f"{p}_OUTER", "status": "PROVED"}]})
    members.append({"canonical_member_id": f"CM_{p}_OUTER", "origin": "SOURCE", "source_member_id": f"{p}_OUTER",
                    "group_id": f"{p}_G_OUTER", "status": "PROVED", "entity_ids": [eo]})

    def add_group(name, family, ids, evidence, statuses, owners, qty=None):
        gid = f"{p}_G_{name}"
        if any(g["group_id"] == gid for g in groups):
            fail(f"{code}: duplicate group {name}")
        if qty is not None and int(qty) != len(ids):
            fail(f"{code}: GROUP_COUNT_CLOSURE group {name} callout qty={qty} but {len(ids)} member(s) found")
        gstatus = "FLAGGED" if "FLAGGED" in statuses else "PROVED"
        groups.append({"group_id": gid, "family": family, "status": gstatus, "source_quantity": len(ids),
                       "evidence": evidence,
                       "members": [{"member_id": f"{p}_{m}", "status": s} for m, s in zip(ids, statuses)]})
        for m, s, own in zip(ids, statuses, owners):
            members.append({"canonical_member_id": f"CM_{p}_{m}", "origin": "SOURCE", "source_member_id": f"{p}_{m}",
                            "group_id": gid, "status": "PREVIEW" if s == "FLAGGED" else "PROVED",
                            "entity_ids": own})

    for g in patterns:
        ids = [f"{g['group']}{k}" for k in range(1, g["count"] + 1)]
        add_group(g["group"], g["family"], ids, g["ev"], ["PROVED"] * len(ids), [[eo]] * len(ids), g["qty"])

    # corners: called groups, auto R, sharp, flags
    called = {}
    auto_k = 0
    for k, d in enumerate(decisions, 1):
        c = d["corner"]
        pt = [_r6(c["at"][0]), _r6(c["at"][1])]
        if d["decision"] == "AUTO_R":
            auto_k += 1
            mid = f"CM_{p}_AR{auto_k}"
            members.append({"canonical_member_id": mid, "origin": "DERIVED_RULE", "status": "PROVED",
                            "controlling_rule": "MATERIAL_AUTO_R", "source_member_ids": [f"{p}_OUTER"],
                            "entity_ids": [eo], "laser_r": laser.get("laser_r"), "excel_row": laser.get("excel_row"),
                            **({"customer_rule": laser["rule"]} if laser.get("rule") else {})})
            inventory.append({"corner_id": f"A{auto_k}", "point": pt, "drawn_shape": "SHARP", "decision": "AUTO_R",
                              "canonical_member_id": mid,
                              "evidence_ref": f"góc ngoài {d['angle_deg']:.2f}° vẽ sắc, không callout R/C"})
        elif d["decision"] == "SHARP":
            if d["eligible"]:
                inventory.append({"corner_id": f"S{k}", "point": pt, "drawn_shape": "SHARP", "decision": "SHARP",
                                  "evidence_ref": c.get("ev") or "góc vẽ sắc",
                                  "no_auto_r_reason": c.get("reason") or "SHARP theo bản vẽ"})
        elif d["decision"] in ("CALLED", "FLAG"):
            if d["kind"] in ("R", "C"):
                name = c["group"] or f"{d['kind']}{d['size']:g}".replace(".", "_")
                called.setdefault(name, []).append((k, d, pt))
            else:  # FLAG without drawable treatment: inventory only
                inventory.append({"corner_id": f"F{k}", "point": pt, "drawn_shape": "UNKNOWN", "decision": "FLAG",
                                  "evidence_ref": c.get("ev") or c["flag"]})
            if c["flag"]:
                flags.append(c["flag"])
    for name, rows in called.items():
        ids = [f"{name}_{i}" for i in range(1, len(rows) + 1)]
        statuses = ["FLAGGED" if r[1]["corner"]["flag"] else "PROVED" for r in rows]
        qtys = {r[1]["corner"].get("qty") for r in rows} - {None}
        if len(qtys) > 1:
            fail(f"{code}: corner group {name} has conflicting qty {sorted(qtys)}")
        ev = next((r[1]["corner"]["ev"] for r in rows if r[1]["corner"]["ev"]), name)
        add_group(name, "CHAMFER_FILLET", ids, ev, statuses, [[eo]] * len(ids), qtys.pop() if qtys else None)
        for mid, (k, d, pt), s in zip(ids, rows, statuses):
            inventory.append({"corner_id": f"K{k}", "point": pt,
                              "drawn_shape": "ROUNDED" if d["kind"] == "R" else "CHAMFERED",
                              "decision": "FLAG" if s == "FLAGGED" else "CALLED",
                              "canonical_member_id": f"CM_{p}_{mid}",
                              "evidence_ref": d["corner"]["ev"] or d["corner"]["flag"]})

    # holes and slots with witness chains (face-relative ones mapped onto the flat first)
    nodes, edges, targets, required, slot_records, authorizations = {}, [], [], [], [], []
    start_types, datum_entities = {}, {}
    for kind in ("holes", "slots"):
        for i, h in enumerate(spec.get(kind) or []):
            if "face" not in h:
                continue
            if not chains:
                fail(f"{code}: {kind}[{i}] uses face but the part has no bend block")
            chain = _face_chain(chains, h["face"], _chain_key(h), f"{code}: {kind}[{i}]")
            try:
                d, st, sgn, dline = bend_flat.face_datum(chain, h["face"], h.get("from"), code)
            except bend_flat.BendError as exc:
                fail(str(exc))
            wu = h.get("wu") or fail(f"{code}: {kind}[{i}] needs wu (along the face from its datum)")
            along = [[sgn * float(stp[0])] + list(stp[1:]) for stp in wu]
            across = h.get("wv") or fail(f"{code}: {kind}[{i}] needs wv (across, from the flat edge)")
            key = str(h.get("id") or (f"H{i + 1}" if kind == "holes" else f"SL{i + 1}"))
            along_axis = chain["axis"]
            if along_axis == "X":
                h.update(wx=along, wy=across, datum_x=d, datum_y=float(h.get("datum_v", 0.0)))
                start_types[(kind, key)] = (st, "OUTER_EDGE")
            else:
                h.update(wy=along, wx=across, datum_y=d, datum_x=float(h.get("datum_v", 0.0)))
                start_types[(kind, key)] = ("OUTER_EDGE", st)
            if dline:
                datum_entities[(kind, key, along_axis)] = bend_line_entity(*dline)
    by_group = {}
    for i, h in enumerate(spec.get("holes") or []):
        hid = str(h.get("id") or f"H{i + 1}")
        fid = f"{p}_{hid}"
        dx0, dy0 = float(h.get("datum_x", 0.0)), float(h.get("datum_y", 0.0))
        stx, sty = start_types.get(("holes", hid), (h.get("datum_type", "OUTER_EDGE"),) * 2)
        nx, sx = _chain(fid, "X", h.get("wx"), dx0, page, nodes, edges, start_type=stx)
        ny, sy = _chain(fid, "Y", h.get("wy"), dy0, page, nodes, edges, start_type=sty)
        center = (dx0 + sx, dy0 + sy)
        if "at" in h and math.dist(_pt(h["at"], fid), center) > 1e-6:
            fail(f"{code}: DIMENSION_CHAIN_MISMATCH hole {hid}: at {h['at']} but chain gives {center}")
        if h.get("thread"):  # tap: the pilot from the table (rules/HOLE_TAP.md §1), quantity/datum unchanged
            pl = lookup.pilot(str(h["thread"]))
            if pl.get("status") != "OK":
                fail(f"{code}: hole {hid}: {pl.get('flag_vi')}")
            h["d"] = pl["pilot_dia"]
        dia = _num(h.get("d"), f"{fid}.d")
        piercing, through, stamp = bool(h.get("piercing")), bool(h.get("through")), str(h.get("stamp") or "")
        if through and not piercing:
            fail(f"{code}: hole {hid}: through needs piercing (rules/HOLE_TAP.md §2)")
        if through and not ("PIERCING" in stamp.upper() and "THROUGH HOLE" in stamp.upper()):
            fail(f"{code}: hole {hid}: THROUGH_PIERCING_STAMP needs `stamp` quoting the scoped PIERCING + THROUGH HOLE text")
        hl = lookup.hole(material, t, dia, piercing=piercing, through=through, customer=customer)
        if hl.get("status") != "OK":
            fail(f"{code}: hole {hid} Ø{dia:g}: {hl.get('flag_vi') or hl.get('entity')} - "
                 "draw it by hand as a Magenta feature + FLAG (rules/HOLE_TAP.md §3)")
        eid = f"E_{p}_{hid}"
        at = [_r6(center[0]), _r6(center[1])]
        if hl["entity"] == "POINT":
            green = hl.get("color") == 3
            ents.append({"entity_id": eid, "type": "POINT", "point": at,
                         "role": "through_piercing" if green else "ordinary_point", **({"color": 3} if green else {})})
            if green:
                authorizations.append({"member_id": fid, "entity_id": eid, "source_pdf_page": page,
                                       "evidence_ref": str(h.get("ev") or stamp), "stamp_text": stamp})
        else:
            ents.append({"entity_id": eid, "type": "CIRCLE", "role": "hole", "center": at, "radius": dia / 2})
        by_group.setdefault(h.get("group", f"D{dia:g}".replace(".", "_")), []).append((hid, eid, h))
        for axis, datum, node, total in (("X", dx0, nx, sx), ("Y", dy0, ny, sy)):
            targets.append({"feature_id": fid, "datum_node": f"{fid}_{axis}_D", "feature_node": node, "axis": axis,
                            "coordinate_mm": total, "datum_coordinate_mm": datum,
                            "datum_entity_id": datum_entities.get(("holes", hid, axis), eo), "entity_id": eid})
        required.append(fid)
    for name, items in by_group.items():
        qty = next((it[2].get("qty") for it in items if it[2].get("qty") is not None), None)
        ev = next((it[2].get("ev") for it in items if it[2].get("ev")), None) or fail(f"{code}: hole group {name} needs ev")
        add_group(name, "HOLE", [it[0] for it in items], ev, ["PROVED"] * len(items), [[it[1]] for it in items], qty)
        # member ids must equal witness feature ids: rename members to the hole ids
    slots_by_group = {}
    for i, s in enumerate(spec.get("slots") or []):
        sid = str(s.get("id") or f"SL{i + 1}")
        fid = f"{p}_{sid}"
        dx0, dy0 = float(s.get("datum_x", 0.0)), float(s.get("datum_y", 0.0))
        stx, sty = start_types.get(("slots", sid), (s.get("datum_type", "OUTER_EDGE"),) * 2)
        nx, sx = _chain(fid, "X", s.get("wx"), dx0, page, nodes, edges, start_type=stx, end_type="SLOT_MIDPOINT")
        ny, sy = _chain(fid, "Y", s.get("wy"), dy0, page, nodes, edges, start_type=sty, end_type="SLOT_MIDPOINT")
        mid = (dx0 + sx, dy0 + sy)
        u = _unit(_pt(s.get("axis", [1, 0]), fid + ".axis"))
        nrm = (-u[1], u[0])
        w, cd = _num(s.get("w"), fid + ".w"), _num(s.get("cd"), fid + ".cd")
        r = w / 2
        c1 = (mid[0] - u[0] * cd / 2, mid[1] - u[1] * cd / 2)
        c2 = (mid[0] + u[0] * cd / 2, mid[1] + u[1] * cd / 2)
        sv = [[c1[0] + nrm[0] * r, c1[1] + nrm[1] * r, 0], [c2[0] + nrm[0] * r, c2[1] + nrm[1] * r, -1],
              [c2[0] - nrm[0] * r, c2[1] - nrm[1] * r, 0], [c1[0] - nrm[0] * r, c1[1] - nrm[1] * r, -1]]
        eid = f"E_{p}_{sid}"
        ents.append({"entity_id": eid, "type": "LWPOLYLINE", "role": "slot", "closed": True,
                     "vertices": [[_r6(v[0]), _r6(v[1]), v[2]] for v in sv]})
        slot_records.append({"slot_id": fid, "entity_id": eid, "source_pdf_page": page,
                             "evidence_ref": s.get("ev") or fail(f"{fid}: slot needs ev"), "witness_verified": True,
                             "anchor_point": [_r6(mid[0]), _r6(mid[1])], "anchor_type": "SLOT_MIDPOINT",
                             "axis_unit": [u[0], u[1]], "width_mm": w, "center_distance_mm": cd,
                             "overall_length_mm": w + cd, "canonical_midpoint": [_r6(mid[0]), _r6(mid[1])]})
        slots_by_group.setdefault(s.get("group", "SLOT"), []).append((sid, eid, s))
        for axis, datum, node, total in (("X", dx0, nx, sx), ("Y", dy0, ny, sy)):
            targets.append({"feature_id": fid, "datum_node": f"{fid}_{axis}_D", "feature_node": node, "axis": axis,
                            "coordinate_mm": total, "datum_coordinate_mm": datum, "datum_entity_id": datum_entities.get(("slots", sid, axis), eo),
                            "entity_id": eid})
        required.append(fid)
    for name, items in slots_by_group.items():
        qty = next((it[2].get("qty") for it in items if it[2].get("qty") is not None), None)
        ev = next((it[2].get("ev") for it in items if it[2].get("ev")), name)
        add_group(name, "SLOT", [it[0] for it in items], ev, ["PROVED"] * len(items), [[it[1]] for it in items], qty)

    cuts_by_group = {}
    for i, c in enumerate(spec.get("cutouts") or []):
        cid = str(c.get("id") or f"CUT{i + 1}")
        eid = f"E_{p}_{cid}"
        ents.append({"entity_id": eid, "type": "LWPOLYLINE", "role": "cutout", "closed": True,
                     "vertices": _cutout_vertices(c, chains, f"{code}: cutout {cid}")})
        cuts_by_group.setdefault(c.get("group", "CUTOUT"), []).append((cid, eid, c))
    for name, items in cuts_by_group.items():
        qty = next((it[2].get("qty") for it in items if it[2].get("qty") is not None), None)
        ev = next((it[2].get("ev") for it in items if it[2].get("ev")), name)
        add_group(name, "CUTOUT", [it[0] for it in items], ev, ["PROVED"] * len(items), [[it[1]] for it in items], qty)

    marks_by_group = {}
    for i, k in enumerate(spec.get("kegaki") or []):
        kid = str(k.get("id") or f"K{i + 1}")
        lines = k.get("lines") or fail(f"{code}: kegaki {kid} needs lines [[x0, y0, x1, y1], ...]")
        owned = []
        for n, ln in enumerate(lines, 1):
            if not isinstance(ln, (list, tuple)) or len(ln) != 4:
                fail(f"{code}: kegaki {kid} line {n} must be [x0, y0, x1, y1]")
            eid = f"E_{p}_{kid}" if len(lines) == 1 else f"E_{p}_{kid}_{n}"
            ents.append({"entity_id": eid, "type": "LINE", "role": "kegaki", "color": 1,
                         "start": [_r6(_num(ln[0], kid)), _r6(_num(ln[1], kid))],
                         "end": [_r6(_num(ln[2], kid)), _r6(_num(ln[3], kid))]})
            owned.append(eid)
        marks_by_group.setdefault(k.get("group", "KEGAKI"), []).append((kid, owned, k))
    for name, items in marks_by_group.items():
        qty = next((it[2].get("qty") for it in items if it[2].get("qty") is not None), None)
        ev = next((it[2].get("ev") for it in items if it[2].get("ev")), None) or fail(f"{code}: kegaki {name} needs ev")
        add_group(name, "KEGAKI", [it[0] for it in items], ev, ["PROVED"] * len(items), [it[1] for it in items], qty)

    if chains:
        try:
            bend_corner.check_features(ents, corner_rec["bends"], code)
        except bend_corner.CornerError as exc:
            fail(str(exc))
        ents.extend(b_ents)
        for name, ids, ev, owners in b_groups:
            add_group(name, "BEND", ids, ev, ["PROVED"] * len(ids), owners)
        ents.extend(corner_rec["relief_entities"])
        for m in corner_rec["relief_members"]:
            members.append({**m, "entity_ids": [eo if x == "__OUTER__" else x for x in m["entity_ids"]]})
        flags += corner_rec["flags"]

    status = "PREVIEW" if flags else "PASS"
    flags = list(dict.fromkeys(flags))  # one line per distinct FLAG
    part = {"code": code, "material": material, "thickness_mm": t, "status": status, "flags": flags,
            "entities": ents, "source_groups": groups, "canonical_members": members, "corner_inventory": inventory,
            "laser_r_lookup": {k: laser.get(k) for k in ("laser_r", "group", "excel_row", "rule")},
            "envelope_mm": [float(env[0]), float(env[1])]}
    if required:
        part["witness_required_feature_ids"] = required
        part["feature_witness_graph"] = {"nodes": nodes, "edges": edges, "targets": targets}
        validate_graph(part["feature_witness_graph"])
    if slot_records:
        part["slot_anchor_records"] = slot_records
    if authorizations:
        part["piercing_authorizations"] = authorizations
    if spec.get("dx_label"):
        part["dx_label"] = True
    if chains:
        part["face_graph"] = bend_graph
        part["per_bend_witness_ledger"] = bend_ledger
        part["unfold"] = {"chains": [{"axis": ch["axis"], "origin": ch["origin"], "flat_length_mm": ch["total"],
                                      "faces": {f: {"od": r["od"], "start": r["start"], "end": r["end"]}
                                                for f, r in ch["faces"].items()}} for ch in chains],
                          "bends": [{k: b[k] for k in ("id", "angle", "sign", "nobi", "nobi_source", "line1", "line2",
                                                       "fold")} for ch in chains for b in ch["bends"]]}
        if len(chains) == 1:
            part["unfold"].update(axis=chains[0]["axis"], flat_length_mm=chains[0]["total"],
                                  faces=part["unfold"]["chains"][0]["faces"])
        part["source_bend_end_site_ids"] = [x["site_id"] for x in corner_rec["sites"]]
        part["bend_end_junctions"] = corner_rec["sites"]
        part["bend_end_source_edges"] = corner_rec["edges"]

    # orientation for J/LJ, then marks
    rot = _jlj_rotation(part, spec.get("jlj_edge", "auto"))
    if rot and chains and (len(chains) > 1 or part["bend_end_junctions"]):
        fail(f"{code}: J/LJ would need a 180° turn of a part with bend-end junctions: set jlj_edge or build by hand")
    if rot:
        x0r, y0r, x1r, y1r = _blank(part)
        _rotate_180(part)
        if chains:
            bend_flat.mirror_ledger(part, (x0r + x1r) if chains[0]["axis"] == "X" else (y0r + y1r))
        part["canonical_rotation_deg"] = 180
        part["canonical_rotation_reason"] = "J/LJ trên cạnh dài thẳng (cạnh max-Y gốc có rãnh/nghiêng)"
    _add_jlj_marks(part)

    errors = part_containment_errors(part)
    if errors:
        fail(f"{code}: CONTAINMENT {errors}")
    checks = {k: "N/A" for k in CHECKS}
    checks.update(contour_topology="PASS", datum="PASS", feature_count="PASS", containment="PASS",
                  material_rules="PASS")
    if chains:
        checks.update(unfold="PASS", bend_domain="PASS")
    if slot_records:
        checks["slot_semantics"] = "PASS"
    part["checks"] = checks
    if status == "PREVIEW":
        part["preview_reason"] = "numeric_only_known_topology"
        part["entities"][0]["color"] = 6
        xs2 = [v[0] for v in part["entities"][0]["vertices"]]
        ys2 = [v[1] for v in part["entities"][0]["vertices"]]
        part["entities"].append({"entity_id": f"E_{p}_NOTE", "type": "TEXT", "role": "estimated_note", "color": 6,
                                 "text": "Ước lượng - kiểm tra bản vẽ (xem FLAG)", "height": 5.0,
                                 "insert": [_r6(min(xs2)), _r6(max(ys2) + 6)]})
    return part


# ------------------------------------------------------------------ SPLIT_FLANGE_10MM (rules/BEND.md §6)
SPLIT_GAP_MM = 10.0
_FEATURE_KEYS = ("holes", "slots", "cutouts")


def _translate_part(part, dx, dy):
    """Move every coordinate of a built (sub)part; per-bend ledgers stay in their own piece frame."""
    def mv(pt):
        return [_r6(pt[0] + dx), _r6(pt[1] + dy)]
    for e in part["entities"]:
        if e["type"] == "LWPOLYLINE":
            e["vertices"] = [[_r6(v[0] + dx), _r6(v[1] + dy), v[2]] for v in e["vertices"]]
        for k in ("center", "point", "start", "end", "insert"):
            if k in e:
                e[k] = mv(e[k])
    for tg in part.get("feature_witness_graph", {}).get("targets", []):
        tg["datum_coordinate_mm"] = _r6(tg["datum_coordinate_mm"] + (dx if tg["axis"] == "X" else dy))
    for rec in part.get("slot_anchor_records", []):
        rec["anchor_point"], rec["canonical_midpoint"] = mv(rec["anchor_point"]), mv(rec["canonical_midpoint"])
    for row in part.get("corner_inventory", []):
        if row.get("point") is not None:
            row["point"] = mv(row["point"])
    for face in part.get("face_graph", {}).get("faces", []):
        face["local_origin"] = mv(face["local_origin"])


def _face_ids(faces):
    return [str(f.get("id") or f"F{k + 1}") for k, f in enumerate(faces)]


def _build_split(spec, plan, customer):
    """SPLIT_FLANGE_10MM: each segment between Nobi-less bends is built by build_part at its proved ODs.

    The body (largest ΣOD) stays in place; every other segment becomes a Magenta closed piece placed 10 mm
    away along the unfold axis, in unfold order. No bend line is drawn for a split bend; the part is PREVIEW."""
    code = spec["code"]
    bend = spec["bend"]
    axis = str(bend.get("axis", "X")).upper()
    if spec.get("outline") != "auto":
        fail(f"{code}: SPLIT_FLANGE_10MM is automatic only with `outline: auto`; for a shaped outline build "
             "the body and the split flange by hand (rules/BEND.md §6)")
    all_ids = _face_ids(bend["faces"])
    face_seg, k = {}, 0
    for i, seg in enumerate(plan):
        for _ in seg["faces"]:
            face_seg[all_ids[k]] = i
            k += 1
    sizes = [sum(float(f["od"]) for f in seg["faces"]) for seg in plan]
    body = max(range(len(plan)), key=lambda i: (sizes[i], -i))
    subs = []
    for i, seg in enumerate(plan):
        sub = {key: v for key, v in spec.items() if key not in _FEATURE_KEYS + ("bend", "envelope", "flags")}
        sub["code"] = code if i == body else f"{code}_SF{i + 1}"
        sub["bend"] = {**{key: v for key, v in bend.items() if key not in ("faces", "bends")},
                       "faces": seg["faces"], "bends": seg["bends"]}
        for key in _FEATURE_KEYS:
            items = []
            for n, item in enumerate(spec.get(key) or []):
                if "face" not in item:
                    fail(f"{code}: {key}[{n}] needs `face` on a split part (each piece has its own frame)")
                if item["face"] not in face_seg:
                    fail(f"{code}: {key}[{n}] unknown face {item['face']}")
                if face_seg[item["face"]] == i:
                    items.append(dict(item))
            if items:
                sub[key] = items
        if i == body and spec.get("flags"):
            sub["flags"] = spec["flags"]
        try:
            ch = bend_flat.unfold_chain(sub["bend"], spec["material"], float(spec["t"]), customer, code)
        except bend_flat.BendError as exc:
            fail(str(exc))
        sub["envelope"] = list(bend_flat.to_flat(ch, ch["total"], float(bend.get("width") or 0)))
        subs.append((sub, ch["total"]))
    built = [build_part(sub, customer) for sub, _ in subs]
    part = built[body]
    if part.get("canonical_rotation_deg"):
        fail(f"{code}: the split body would need a 180° turn for J/LJ; set jlj_edge or build by hand")
    starts, pos = [], 0.0
    for _, length in subs:
        starts.append(pos)
        pos += length + SPLIT_GAP_MM
    flags = list(part.get("flags", []))
    for seg in plan:
        if seg["split_after"]:
            sp = seg["split_after"]
            flags.append(f"{sp['bend']}: {sp['flag_vi']} (SPLIT_FLANGE_10MM)")
    ents = part["entities"]
    for i, sub_part in enumerate(built):
        if i == body:
            continue
        shift = starts[i] - starts[body]
        _translate_part(sub_part, *((shift, 0.0) if axis == "X" else (0.0, shift)))
        for e in sub_part["entities"]:
            if e.get("role") == "mark":
                continue
            if e.get("role") == "outer":
                e.update(role="split_flange", color=6)
            ents.append(e)
        for g in sub_part["source_groups"]:
            if g["family"] == "OUTER":
                g["family"] = "SPLIT_FLANGE"
                g["evidence"] = "SPLIT_FLANGE_10MM: " + ", ".join(_face_ids(plan[i]["faces"])) + " at their OD"
            part["source_groups"].append(g)
        part["canonical_members"] += sub_part["canonical_members"]
        for row in sub_part.get("corner_inventory", []):
            row["corner_id"] = f"SF{i + 1}_{row['corner_id']}"
            part["corner_inventory"].append(row)
        for key in ("witness_required_feature_ids", "slot_anchor_records", "piercing_authorizations",
                    "per_bend_witness_ledger"):
            if sub_part.get(key):
                part.setdefault(key, []).extend(sub_part[key])
        if sub_part.get("feature_witness_graph"):
            g = part.setdefault("feature_witness_graph", {"nodes": {}, "edges": [], "targets": []})
            g["nodes"].update(sub_part["feature_witness_graph"]["nodes"])
            g["edges"] += sub_part["feature_witness_graph"]["edges"]
            g["targets"] += sub_part["feature_witness_graph"]["targets"]
        part["face_graph"]["faces"] += sub_part["face_graph"]["faces"]
        part["face_graph"]["bends"] += sub_part["face_graph"]["bends"]
        piece = next(e for e in sub_part["entities"] if e.get("role") == "split_flange")
        xs, ys = [v[0] for v in piece["vertices"]], [v[1] for v in piece["vertices"]]
        ents.append({"entity_id": f"E_{sub_part['code']}_NOTE", "type": "TEXT", "role": "estimated_note",
                     "color": 6, "height": 5.0, "insert": [_r6(min(xs)), _r6(max(ys) + 6)],
                     "text": "FLAG: bích tách 10 mm - chưa có Nobi"})
    part["flags"] = list(dict.fromkeys(flags))
    part["status"] = "PREVIEW"
    part["preview_reason"] = "numeric_only_known_topology"
    part["split_flange"] = [{"bend": seg["split_after"]["bend"], "reason": seg["split_after"]["reason"]}
                            for seg in plan if seg["split_after"]]
    if spec.get("envelope"):
        part["envelope_mm"] = [float(v) for v in spec["envelope"]]
    return part


# ------------------------------------------------------------------ J/LJ orientation and marks
def _outer(part):
    return part["entities"][0]


def _blank(part):
    v = _outer(part)["vertices"]
    xs, ys = [p[0] for p in v], [p[1] for p in v]
    return min(xs), min(ys), max(xs), max(ys)


def _straight_long_edge(verts, level, length):
    segs = list(zip(verts, verts[1:] + verts[:1]))
    on = [(a, b) for a, b in segs if abs(a[1] - level) <= 1e-6 and abs(b[1] - level) <= 1e-6 and not a[2]]
    touching = [(a, b) for a, b in segs if abs(a[1] - level) <= 1e-6 or abs(b[1] - level) <= 1e-6]
    if len(on) != 1:
        return False
    a, b = on[0]
    return abs(a[0] - b[0]) >= 0.9 * length and len(touching) <= 3


def _jlj_rotation(part, mode):
    x0, y0, x1, y1 = _blank(part)
    if not (y1 - y0 <= 100 + 1e-6 and x1 - x0 >= 1000 - 1e-6):
        return False
    if mode == "top":
        return False
    if mode == "bottom":
        return True
    verts = _outer(part)["vertices"]
    if _straight_long_edge(verts, y1, x1 - x0):
        return False
    if _straight_long_edge(verts, y0, x1 - x0):
        return True
    fail(f"{part['code']}: JLJ_NO_STRAIGHT_LONG_EDGE: set jlj_edge top|bottom explicitly")


def _rotate_180(part):
    x0, y0, x1, y1 = _blank(part)
    sx, sy = x0 + x1, y0 + y1
    f = lambda q: [_r6(sx - q[0]), _r6(sy - q[1])]  # noqa: E731
    for e in part["entities"]:
        if e["type"] == "LWPOLYLINE":
            e["vertices"] = [f(v) + [v[2]] for v in e["vertices"]]
        elif e["type"] == "CIRCLE":
            e["center"] = f(e["center"])
        elif e["type"] == "POINT":
            e["point"] = f(e["point"])
        elif e["type"] == "LINE":
            e["start"], e["end"] = f(e["start"]), f(e["end"])
        elif e["type"] == "TEXT":
            e["insert"] = f(e["insert"])
    for row in part.get("corner_inventory", []):
        row["point"] = f(row["point"])
    g = part.get("feature_witness_graph")
    if g:
        for edge in g["edges"]:
            edge["value_mm"] = -edge["value_mm"]
        for tg in g["targets"]:
            s = sx if tg["axis"] == "X" else sy
            tg["coordinate_mm"] = -tg["coordinate_mm"]
            tg["datum_coordinate_mm"] = s - tg["datum_coordinate_mm"]
    for rec in part.get("slot_anchor_records", []):
        rec["anchor_point"] = f(rec["anchor_point"])
        rec["canonical_midpoint"] = f(rec["canonical_midpoint"])
        rec["axis_unit"] = [-rec["axis_unit"][0], -rec["axis_unit"][1]]


def _add_jlj_marks(part):
    """Same formula as export_dxf.jlj_marks_check (rules/OUTPUT.md J/LJ line)."""
    x0, y0, x1, y1 = _blank(part)
    length, width = x1 - x0, y1 - y0
    if not (width <= 100 + 1e-6 and length >= 1000 - 1e-6):
        return
    if length > 2500:
        fail(f"{part['code']}: J/LJ count undefined for L>2500")
    verts = _outer(part)["vertices"]
    tops = [(min(a[0], b[0]), max(a[0], b[0])) for a, b in zip(verts, verts[1:] + verts[:1])
            if not a[2] and abs(a[1] - y1) <= 1e-6 and abs(b[1] - y1) <= 1e-6]
    if not tops:
        fail(f"{part['code']}: J/LJ_MARKS_NOT_ON_TOP_MATERIAL_EDGE")
    n = 2 + (length > 1500) + (length > 2000)
    xa, xb = min(l for l, _ in tops) + JLJ_INSET_MM, max(r for _, r in tops) - JLJ_INSET_MM
    p = part["code"]
    for i in range(n):
        x = xa + i * (xb - xa) / (n - 1)
        txt = "LJ" if i == n - 1 else "J"
        part["entities"].append({"entity_id": f"E_{p}_MK{i + 1}P", "type": "POINT", "role": "mark", "point": [x, y1]})
        part["entities"].append({"entity_id": f"E_{p}_MK{i + 1}T", "type": "TEXT", "role": "mark", "text": txt,
                                 "height": 10.0, "insert": [x, y1]})


# ------------------------------------------------------------------ job
def build_job(spec):
    if not isinstance(spec, dict) or not spec.get("parts"):
        fail("spec needs job_id and parts")
    job = {"canonical_contract": CONTRACT, "job_id": str(spec.get("job_id") or fail("job_id required")),
           "parts": [build_part(ps, spec.get("customer_code")) for ps in spec["parts"]]}
    if spec.get("customer_code") is not None:
        job["customer_code"] = str(spec["customer_code"])
    return job


def build_from_files(paths):
    """One job from several files in page-1 order: build specs (YAML/JSON) and hand-written canonical job
    JSON (``canonical_contract`` set, e.g. tools/boxmet_job.py output) are merged part by part."""
    job, seen = None, set()
    for path in paths:
        data = load_spec(path)
        if not isinstance(data, dict):
            fail(f"{path}: not a spec or canonical job")
        if data.get("canonical_contract"):
            if data["canonical_contract"] != CONTRACT:
                fail(f"{path}: canonical_contract must be {CONTRACT}")
            part_job = data
        else:
            part_job = build_job(data)
        if job is None:
            job = {"canonical_contract": CONTRACT, "job_id": str(part_job.get("job_id")), "parts": []}
            if part_job.get("customer_code") is not None:
                job["customer_code"] = str(part_job["customer_code"])
        if str(part_job.get("job_id")) != job["job_id"]:
            fail(f"{path}: job_id {part_job.get('job_id')} != {job['job_id']} (one job per DXF)")
        cust = part_job.get("customer_code")
        if (None if cust is None else str(cust)) != job.get("customer_code"):
            fail(f"{path}: customer_code {cust} != {job.get('customer_code')} (set it in every file)")
        for part in part_job["parts"]:
            if part["code"] in seen:
                fail(f"{path}: duplicate part code {part['code']}")
            seen.add(part["code"])
            job["parts"].append(part)
    if job is None:
        fail("no input files")
    return job


def load_spec(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    if str(path).endswith((".yaml", ".yml")):
        import yaml
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if isinstance(data, dict) and not data.get("canonical_contract"):
        for part in data.get("parts") or []:  # a DATA path is relative to its spec file
            if isinstance(part, dict) and isinstance(part.get("data"), str):
                part["data"] = str((Path(path).parent / part["data"]).resolve())
            for view in (part.get("data_views") or []) if isinstance(part, dict) else []:
                if isinstance(view, dict) and isinstance(view.get("data"), str):
                    view["data"] = str((Path(path).parent / view["data"]).resolve())
    return data


def summary(job):
    rows = []
    for p in job["parts"]:
        inv = p.get("corner_inventory", [])
        count = lambda d: sum(r["decision"] == d for r in inv)  # noqa: E731
        has_outer = any(e.get("role") == "outer" for e in p["entities"][:1])
        x0, y0, x1, y1 = _blank(p) if has_outer else (0, 0, 0, 0)
        rows.append({"code": p["code"], "status": p["status"],
                     "blank_mm": [round(x1 - x0, 3), round(y1 - y0, 3)] if has_outer else None,
                     "auto_r": count("AUTO_R"), "called": count("CALLED"), "sharp": count("SHARP"),
                     "flag": count("FLAG"), "holes": sum(e["role"] == "hole" for e in p["entities"]),
                     "rotation_deg": p.get("canonical_rotation_deg", 0), "flags": p.get("flags", [])})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", type=Path, nargs="+", help="spec / canonical job files in page-1 order")
    ap.add_argument("-o", "--out", type=Path, required=True, help="job.json to write")
    a = ap.parse_args(argv)
    try:
        job = build_from_files(a.specs)
    except BuildError as exc:
        print(f"BUILD_FAIL: {exc}", file=sys.stderr)
        return 2
    a.out.write_text(json.dumps(job, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary(job), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
