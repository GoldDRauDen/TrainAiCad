#!/usr/bin/env python3
"""Compact FLAT part spec -> complete TrainAiCad-CANONICAL-V4.34 job.json (no bends).

The reader states only what the drawing says: outline corners with their R/C callouts,
repeated notch patterns, holes/slots with their dimension chains, and the overall envelope.
This tool derives the rest deterministically and runs the checks it reports as PASS:

* Laser R from ``lookup.laser_r`` on every uncalled convex corner <=90 deg (AUTO), tangent fillets;
* source_groups / canonical_members / corner_inventory (CALLED / AUTO_R / SHARP / FLAG);
* typed witness graph for every hole/slot (center derived from the chain when ``at`` is omitted);
* closed CCW, non-self-intersecting outline, full containment, envelope match;
* J/LJ marks on the long straight edge: when the max-Y edge is notched/sloped and the
  min-Y edge is straight, the whole part is rotated 180 deg (CAD_OUTPUT.md J/LJ line).

Spec format and an example: tools/BUILD_CANONICAL_SPEC.md, examples/flat_minimal.yaml.
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
import lookup  # noqa: E402
from dimension_witness import validate_graph  # noqa: E402
from export_dxf import (CHECKS, JLJ_INSET_MM, signed_poly_area)  # noqa: E402
from geometry_containment import _intersects, _loop, part_containment_errors  # noqa: E402

CONTRACT = "TrainAiCad-CANONICAL-V4.34"
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


def laser_r_mm(material, t):
    res = lookup.laser_r(material, t)
    if res.get("status") != "OK":
        fail(f"LASER_R_LOOKUP_FLAG: {res.get('flag_vi') or res}")
    m = re.fullmatch(r"R(\d+(?:\.\d+)?)", str(res.get("laser_r")))
    return (float(m.group(1)) if m else None), res


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


def build_outline(corners, auto_r, where):
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
            if eligible and auto_r:
                kind, size, decision = "R", auto_r, "AUTO_R"
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


# ------------------------------------------------------------------ part
def build_part(spec):
    code = str(spec.get("code") or fail("part: code required"))
    where = code
    material = str(spec.get("material") or fail(f"{code}: material required"))
    t = _num(spec.get("t"), f"{code}.t")
    page = int(spec.get("page", 1))
    if spec.get("bends"):
        fail(f"{code}: bends are outside build_canonical (FLAT only); use the BEND_UNFOLD route")
    auto_r, laser = laser_r_mm(material, t)
    corners, patterns = expand_outline(spec.get("outline") or fail(f"{code}: outline required"), where)
    verts, decisions = build_outline(corners, auto_r, where)
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
                            "entity_ids": [eo], "laser_r": laser.get("laser_r"), "excel_row": laser.get("excel_row")})
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

    # holes and slots with witness chains
    nodes, edges, targets, required, slot_records = {}, [], [], [], []
    by_group = {}
    for i, h in enumerate(spec.get("holes") or []):
        hid = str(h.get("id") or f"H{i + 1}")
        fid = f"{p}_{hid}"
        dx0, dy0 = float(h.get("datum_x", 0.0)), float(h.get("datum_y", 0.0))
        nx, sx = _chain(fid, "X", h.get("wx"), dx0, page, nodes, edges)
        ny, sy = _chain(fid, "Y", h.get("wy"), dy0, page, nodes, edges)
        center = (dx0 + sx, dy0 + sy)
        if "at" in h and math.dist(_pt(h["at"], fid), center) > 1e-6:
            fail(f"{code}: DIMENSION_CHAIN_MISMATCH hole {hid}: at {h['at']} but chain gives {center}")
        dia = _num(h.get("d"), f"{fid}.d")
        hl = lookup.hole(material, t, dia)
        if hl.get("status") != "OK" or hl.get("entity") != "CIRCLE":
            fail(f"{code}: hole {hid} Ø{dia:g}: lookup says {hl.get('entity') or hl.get('flag_vi')} - "
                 "declare it as a POINT feature by hand (HOLES_TAPS.md)")
        eid = f"E_{p}_{hid}"
        ents.append({"entity_id": eid, "type": "CIRCLE", "role": "hole", "center": [_r6(center[0]), _r6(center[1])],
                     "radius": dia / 2})
        by_group.setdefault(h.get("group", f"D{dia:g}".replace(".", "_")), []).append((hid, eid, h))
        for axis, datum, node, total in (("X", dx0, nx, sx), ("Y", dy0, ny, sy)):
            targets.append({"feature_id": fid, "datum_node": f"{fid}_{axis}_D", "feature_node": node, "axis": axis,
                            "coordinate_mm": total, "datum_coordinate_mm": datum, "datum_entity_id": eo,
                            "entity_id": eid})
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
        nx, sx = _chain(fid, "X", s.get("wx"), dx0, page, nodes, edges, end_type="SLOT_MIDPOINT")
        ny, sy = _chain(fid, "Y", s.get("wy"), dy0, page, nodes, edges, end_type="SLOT_MIDPOINT")
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
                            "coordinate_mm": total, "datum_coordinate_mm": datum, "datum_entity_id": eo,
                            "entity_id": eid})
        required.append(fid)
    for name, items in slots_by_group.items():
        qty = next((it[2].get("qty") for it in items if it[2].get("qty") is not None), None)
        ev = next((it[2].get("ev") for it in items if it[2].get("ev")), name)
        add_group(name, "SLOT", [it[0] for it in items], ev, ["PROVED"] * len(items), [[it[1]] for it in items], qty)

    status = "PREVIEW" if flags else "PASS"
    part = {"code": code, "material": material, "thickness_mm": t, "status": status, "flags": flags,
            "entities": ents, "source_groups": groups, "canonical_members": members, "corner_inventory": inventory,
            "laser_r_lookup": {k: laser.get(k) for k in ("laser_r", "group", "excel_row")},
            "envelope_mm": [float(env[0]), float(env[1])]}
    if required:
        part["witness_required_feature_ids"] = required
        part["feature_witness_graph"] = {"nodes": nodes, "edges": edges, "targets": targets}
        validate_graph(part["feature_witness_graph"])
    if slot_records:
        part["slot_anchor_records"] = slot_records
    if spec.get("dx_label"):
        part["dx_label"] = True

    # orientation for J/LJ, then marks
    rot = _jlj_rotation(part, spec.get("jlj_edge", "auto"))
    if rot:
        _rotate_180(part)
        part["canonical_rotation_deg"] = 180
        part["canonical_rotation_reason"] = "J/LJ trên cạnh dài thẳng (cạnh max-Y gốc có rãnh/nghiêng)"
    _add_jlj_marks(part)

    errors = part_containment_errors(part)
    if errors:
        fail(f"{code}: CONTAINMENT {errors}")
    checks = {k: "N/A" for k in CHECKS}
    checks.update(contour_topology="PASS", datum="PASS", feature_count="PASS", containment="PASS",
                  material_rules="PASS")
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
    """Same formula as export_dxf.jlj_marks_check (CAD_OUTPUT.md J/LJ line)."""
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
           "parts": [build_part(ps) for ps in spec["parts"]]}
    if spec.get("customer_code") is not None:
        job["customer_code"] = str(spec["customer_code"])
    return job


def load_spec(path):
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith((".yaml", ".yml")):
        import yaml
        return yaml.safe_load(text)
    return json.loads(text)


def summary(job):
    rows = []
    for p in job["parts"]:
        inv = p.get("corner_inventory", [])
        count = lambda d: sum(r["decision"] == d for r in inv)  # noqa: E731
        x0, y0, x1, y1 = _blank(p)
        rows.append({"code": p["code"], "status": p["status"], "blank_mm": [round(x1 - x0, 3), round(y1 - y0, 3)],
                     "auto_r": count("AUTO_R"), "called": count("CALLED"), "sharp": count("SHARP"),
                     "flag": count("FLAG"), "holes": sum(e["role"] == "hole" for e in p["entities"]),
                     "rotation_deg": p.get("canonical_rotation_deg", 0), "flags": p["flags"]})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True, help="job.json to write")
    a = ap.parse_args(argv)
    try:
        job = build_job(load_spec(a.spec))
    except BuildError as exc:
        print(f"BUILD_FAIL: {exc}", file=sys.stderr)
        return 2
    a.out.write_text(json.dumps(job, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary(job), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
