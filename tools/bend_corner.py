#!/usr/bin/env python3
"""Bend domains and bend-end junctions in the canonical flat, for tools/build_canonical.py (rules/SLIT_RELIEF.md).

Everything is measured in the flat built from the reader's proved outline and face chains:

* Bend domain: each bend line runs only where both faces have material (the middle half of each face and the
  material at the zone), and stops at a perpendicular bend that shares a face with it: at that bend's web-side line, or, for
  an opposite-fold corner, line by line at the same-rank line.
* Bend end with a step (flat convention, user-approved samples HD t2 SUS and 061247/061248): B = the corner where
  the flange's side edge meets the web edge; S = (B − flange-side bend line), positive toward the web.
  S > 0 → no slit. S ≤ 0 → one Green LINE + ARC R0.5 + LINE from B along the flange side toward the web, ending
  T + 0.2 past the flange-side bend line (length T + 0.2 − S), lead `lead_val(material, t)` into the void.
* Opposite-fold corner of two perpendicular bends: the flange-side lines meet at P; the outline must have its corner
  at P; it is replaced by an R = t relief with R0.5 junctions (OPPOSITE_FOLD_R_T).
Sites, source edges and relief members are written for tools/bend_end_guard.py, which re-measures all of it.
"""
from __future__ import annotations

import math

import bend_flat
import slit_geometry as sg

EPS = 1e-6
FRAME = "CANONICAL_FLAT"


class CornerError(ValueError):
    pass


def _fail(msg):
    raise CornerError(msg)


def _k(axis):
    return 0 if axis == "X" else 1


def _other(axis):
    return "Y" if axis == "X" else "X"


def _flat(axis, along, across):
    return (along, across) if axis == "X" else (across, along)


def _r6(v):
    r = round(float(v), 6)
    return 0.0 if r == 0 else r


def across_intervals(verts, axis, along):
    """Material intervals across the flat on the line `along` = const (bend line direction)."""
    return bend_flat.line_intervals(verts, {"axis": axis}, along)


def _intersect(a, b):
    out = []
    for x0, x1 in a:
        for y0, y1 in b:
            lo, hi = max(x0, y0), min(x1, y1)
            if hi - lo > EPS:
                out.append((lo, hi))
    return out


def _straight_runs(verts, axis, across):
    """Merged along-intervals of straight outline edges lying on `across` = const (parallel to the chain axis)."""
    k, j = _k(axis), 1 - _k(axis)
    runs = []
    n = len(verts)
    for i in range(n):
        a, b = verts[i], verts[(i + 1) % n]
        if a[2] or abs(a[j] - across) > 1e-5 or abs(b[j] - across) > 1e-5:
            continue
        runs.append(tuple(sorted((a[k], b[k]))))
    runs.sort()
    merged = []
    for lo, hi in runs:
        if merged and lo <= merged[-1][1] + 1e-5:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def _cross_edge(verts, axis, along, across, s):
    """The straight outline edge on `along` = const that starts at (along, across) and runs toward s (±1 across)."""
    k, j = _k(axis), 1 - _k(axis)
    n = len(verts)
    for i in range(n):
        a, b = verts[i], verts[(i + 1) % n]
        if a[2] or abs(a[k] - along) > 1e-5 or abs(b[k] - along) > 1e-5:
            continue
        lo, hi = sorted((a[j], b[j]))
        if abs((lo if s > 0 else hi) - across) <= 1e-5 and hi - lo > EPS:
            far = hi if s > 0 else lo
            return (_flat(axis, along, across), _flat(axis, along, far))
    return None


# ------------------------------------------------------------------ bends and domains
def all_bends(chains):
    out = []
    for c in chains:
        for b in c["bends"]:
            out.append({"chain": c, "axis": c["axis"], "id": b["id"], "b": b, "l1": b["line1"], "l2": b["line2"],
                        "faces": b["faces"], "fold": b.get("fold")})
    return out


def _union(ivs):
    out = []
    for lo, hi in sorted(ivs):
        if out and lo <= out[-1][1] + EPS:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def face_extent(verts, chain, face):
    """Material across the flat in the middle half of a face (5 sections, united: a chamfer or step at one
    section does not narrow the face)."""
    f = chain["faces"][face]
    lo, hi = sorted((f["start"], f["end"]))
    return _union([iv for k in range(5) for iv in across_intervals(verts, chain["axis"], lo + (hi - lo) * (0.25 + k / 8))])


def pre_domain(verts, bend):
    c, axis = bend["chain"], bend["axis"]
    dom = _intersect(across_intervals(verts, axis, bend["l1"] + 1e-4), across_intervals(verts, axis, bend["l2"] - 1e-4))
    for face in bend["faces"]:
        dom = _intersect(dom, face_extent(verts, c, face))
    return dom


def _web_side(bend, face):
    """(web-side line, flange-side line, d) of `bend` when `face` is the web; d = +1 if the web is at higher along."""
    if face == bend["faces"][0]:
        return bend["l1"], bend["l2"], -1
    return bend["l2"], bend["l1"], 1


def domains(verts, chains, code):
    """Per bend: members [{'iv': {'L1': (v0, v1), 'L2': (v0, v1)}, 'ends': {...}}] plus corner pairs."""
    bends = all_bends(chains)
    for b in bends:
        b["pre"] = pre_domain(verts, b)
        if not b["pre"]:
            _fail(f"{code}: bend {b['id']} has no material on both faces")
    pairs = []
    for i, b in enumerate(bends):
        for p in bends[i + 1:]:
            if b["axis"] == p["axis"]:
                continue
            common = set(b["faces"]) & set(p["faces"])
            touch_b = any(v0 < p["l2"] + EPS and v1 > p["l1"] - EPS for v0, v1 in b["pre"])
            touch_p = any(v0 < b["l2"] + EPS and v1 > b["l1"] - EPS for v0, v1 in p["pre"])
            if not (touch_b and touch_p):
                continue
            if len(common) != 1:
                _fail(f"{code}: bends {b['id']} and {p['id']} meet without a shared face: build by hand")
            if not b["fold"] or not p["fold"]:
                _fail(f"{code}: bends {b['id']} and {p['id']} meet at a corner: give both `fold: toward|away` "
                      "(solid = toward the viewer, dashed = away; rules/SLIT_RELIEF.md §5)")
            pairs.append((b, p, common.pop()))
    for b in bends:
        b["members"] = [{"iv": {"L1": iv, "L2": iv}, "ends": {}} for iv in b["pre"]]
    for b, p, web in pairs:
        same = b["fold"] == p["fold"]
        for me, other in ((b, p), (p, b)):
            w_line, f_line, _ = _web_side(other, web)
            my_w = "L1" if web == me["faces"][0] else "L2"
            for m in me["members"]:
                v0, v1 = m["iv"]["L1"]
                if not (v0 < other["l2"] + EPS and v1 > other["l1"] - EPS):
                    continue
                at_high = (other["l1"] + other["l2"]) / 2 > (v0 + v1) / 2
                for name in ("L1", "L2"):
                    stop = w_line if (same or name == my_w) else f_line
                    lo, hi = m["iv"][name]
                    m["iv"][name] = (lo, min(hi, stop)) if at_high else (max(lo, stop), hi)
                m["ends"]["hi" if at_high else "lo"] = {"pair": other, "web": web, "same": same}
    return bends, pairs


def check_zones(verts, bends, code):
    """An outline corner strictly inside a bend zone AND inside that bend's domain changes the bend: refuse."""
    for b in bends:
        k, j = _k(b["axis"]), 1 - _k(b["axis"])
        for v in verts:
            if not (b["l1"] + 1e-5 < v[k] < b["l2"] - 1e-5):
                continue
            for m in b["members"]:
                lo = min(m["iv"]["L1"][0], m["iv"]["L2"][0])
                hi = max(m["iv"]["L1"][1], m["iv"]["L2"][1])
                if lo + 1e-5 < v[j] < hi - 1e-5:
                    _fail(f"{code}: bend {b['id']}: the outline has a corner at ({v[0]:g}, {v[1]:g}) inside the bend "
                          "zone and its material domain — build the part as canonical JSON by hand")


def check_features(entities, bends, code):
    """A hole/slot/cut-out/POINT overlapping a bend zone within the bend's domain: refuse (draw by hand)."""
    for e in entities:
        if e.get("role") not in ("hole", "slot", "cutout", "ordinary_point", "through_piercing"):
            continue
        for b in bends:
            k, j = _k(b["axis"]), 1 - _k(b["axis"])
            if e["type"] == "CIRCLE":
                box = [(e["center"][i] - e["radius"], e["center"][i] + e["radius"]) for i in (0, 1)]
            elif e["type"] == "POINT":
                box = [(e["point"][i], e["point"][i]) for i in (0, 1)]
            else:
                pts = bend_flat._poly(e["vertices"])
                box = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in (0, 1)]
            if not (box[k][0] < b["l2"] + bend_flat.ZONE_TOL and box[k][1] > b["l1"] - bend_flat.ZONE_TOL):
                continue
            if any(box[j][0] < max(m["iv"]["L1"][1], m["iv"]["L2"][1]) and
                   box[j][1] > min(m["iv"]["L1"][0], m["iv"]["L2"][0]) for m in b["members"]):
                _fail(f"{code}: {e['entity_id']} overlaps bend {b['id']} zone {b['l1']:g}..{b['l2']:g} "
                      "— the bend lines must stop at the void: build this part by hand")


# ------------------------------------------------------------------ bend-end step
def _slanted_edge(verts, axis, along, across, s, d):
    """The straight outline edge that leaves the corner (along, across) toward +s across and toward the web (d along)
    without lying on `along` = const: a web edge slanted against the bend (rules/SLIT_RELIEF.md §3)."""
    k, j = _k(axis), 1 - _k(axis)
    n = len(verts)
    for i in range(n):
        a, b = verts[i], verts[(i + 1) % n]
        if a[2]:
            continue
        for p, q in ((a, b), (b, a)):
            if abs(p[k] - along) > 1e-5 or abs(p[j] - across) > 1e-5:
                continue
            if (q[j] - across) * s > 1e-5 and (q[k] - along) * d > 1e-5:
                return (_flat(axis, along, across), _flat(axis, q[k], q[j]))
    return None


def end_step(verts, bend, v_end, s, web, code, reach=0.0):
    """Corner B, step S and the two edges at one bend end; None when the outline runs straight across the zone.

    v_end: the domain end (across); s: +1 for the high end, -1 for the low end; web: the web face id or None
    (free end: the face that continues beyond the end); reach: how far beyond the end the side edge may lie
    (0 at a free end, the perpendicular zone at a corner)."""
    axis = bend["axis"]
    shoulder = False
    if web is None:
        straight = [r for r in _straight_runs(verts, axis, v_end)
                    if r[0] <= bend["l1"] + 1e-5 and r[1] >= bend["l2"] - 1e-5]
        shoulder = any(_cross_edge(verts, axis, u, v_end, s) for r in straight for u in r)
        if straight and not shoulder:
            return None   # collinear through the zone and no shoulder leaves toward the void: no corner
        beyond = v_end + s * 1e-3
        cont = [f for f in bend["faces"] if any(lo < beyond < hi for lo, hi in face_extent(verts, bend["chain"], f))]
        if len(cont) != 1 and straight:
            return None   # a shoulder that does not single out the continuing face is not a bend-end step
        if len(cont) != 1:
            _fail(f"{code}: bend {bend['id']} end at {v_end:g}: cannot tell the flange from the web (outline steps on "
                  "both or neither face) — build by hand")
        web = cont[0]
    w_line, f_line, d = _web_side(bend, web)
    flange = [f for f in bend["faces"] if f != web][0]
    # the flange side edge: a straight run parallel to the axis that reaches into the flange, at the domain end
    # (free end) or just beyond it inside the perpendicular bend zone (corner), nearest to the end
    best = None
    for across in sorted({round(v[1 - _k(axis)], 6) for v in verts}):
        off = (across - v_end) * s
        if off < -1e-5 or off > reach + 1e-5:
            continue
        for lo, hi in _straight_runs(verts, axis, across):
            into_flange = lo < f_line - 1e-6 if d > 0 else hi > f_line + 1e-6
            # several collinear runs on one line (a tab edge flush with the web edge): the one nearest the zone is this end's
            near = -hi if d > 0 else lo
            if into_flange and (best is None or (off, near) < (best[0], best[4])):
                best = (off, across, lo, hi, near)
    if best is None:
        _fail(f"{code}: bend {bend['id']} end at {v_end:g}: no straight flange side edge (R/C at the bend end?) "
              "— build by hand")
    _, side, lo, hi, _ = best
    run = (lo, hi)
    u_b = run[1] if d > 0 else run[0]
    web_edge = _cross_edge(verts, axis, u_b, side, s) or _slanted_edge(verts, axis, u_b, side, s, d)
    if (u_b - w_line) * d > 1e-5 and not (shoulder and web_edge):
        return None  # the side edge passes the whole zone and no shoulder steps at its end: no corner
    if web_edge is None:
        _fail(f"{code}: bend {bend['id']} end: no straight web edge from the corner ({_flat(axis, u_b, side)}) "
              "— build by hand")
    B = _flat(axis, u_b, side)
    side_far = run[0] if d > 0 else run[1]
    return {"bend": bend, "web": web, "flange": flange, "d": d, "s": s, "B": B, "S": round((u_b - f_line) * d, 9),
            "f_line": f_line, "side_edge": (B, _flat(axis, side_far, side)), "web_edge": web_edge,
            "shoulder": shoulder and (u_b - w_line) * d > 1e-5}


def _relief_angle(angle):
    """90 up to the bend tolerance above it (and below 90), else the printed angle (relief depth t*sin(theta) above 90)."""
    return angle if angle - 90 > 0.5 else 90.0


def slit_entities(step, material, t, sid):
    """Green LINE + ARC + LINE of one slit (length T + 0.2 − S from B, lead into the void)."""
    axis, d, s = step["bend"]["axis"], step["d"], step["s"]
    direction = _flat(axis, d, 0.0)
    n_side = _flat(axis, 0.0, s)
    n_web = _flat(axis, -d, 0.0)
    (x0, y0), (x1, y1) = step["web_edge"]
    if abs((x1 - x0) * direction[0] + (y1 - y0) * direction[1]) > 1e-9 * math.hypot(x1 - x0, y1 - y0):
        # web edge slanted against the bend: its own void-side normal (away from the web), same LeadVal offset
        length = math.hypot(x1 - x0, y1 - y0)
        n_web = ((y0 - y1) / length, (x1 - x0) / length)
        if n_web[0] * direction[0] + n_web[1] * direction[1] > 0:
            n_web = (-n_web[0], -n_web[1])
    lead = sg.lead_val(material, t)
    B = step["B"]
    end = sg.lead_end_by_offset(B, n_side, n_web, lead)
    geo = sg.connected_slit(B, direction, (end[0] - B[0], end[1] - B[1]),
                             sg.slit_depth_from_reference(step["S"], t, _relief_angle(step["bend"]["b"]["angle"])))
    ents = [{"entity_id": f"{sid}_L1", "type": "LINE", "start": list(geo["line1"][0]), "end": list(geo["line1"][1])},
            {"entity_id": f"{sid}_A", "type": "ARC", "center": list(geo["arc"]["center"]),
             "radius": geo["arc"]["radius"], "start_angle": geo["arc"]["start_angle"],
             "end_angle": geo["arc"]["end_angle"]},
            {"entity_id": f"{sid}_L2", "type": "LINE", "start": list(geo["line2"][0]), "end": list(geo["line2"][1])}]
    for e in ents:
        e.update(role="slit", color=3, layer="0", bend_end_site_id=sid)
    return ents, {"inward_hint": list(direction), "side_void_normal": list(n_side), "web_void_normal": list(n_web)}


# ------------------------------------------------------------------ R = t relief at an opposite-fold corner
def keyhole(verts, P, t, code, r=0.5):
    """Replace the concave outline corner at P by an R = t relief joined with R0.5 arcs (exact bulges)."""
    n = len(verts)
    i = next((k for k, v in enumerate(verts) if math.dist(v[:2], P) <= 1e-5), None)
    if i is None:
        _fail(f"{code}: opposite-fold corner: the outline must have its corner at the flange-side line "
              f"intersection {tuple(round(c, 3) for c in P)} (R = t relief, rules/SLIT_RELIEF.md §5)")
    prev, nxt = verts[i - 1], verts[(i + 1) % n]
    if prev[2] or verts[i][2]:
        _fail(f"{code}: opposite-fold corner at {P}: both edges must be straight")

    def unit(a, b):
        L = math.dist(a, b)
        return ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    e_in, e_out = unit(prev[:2], P), unit(P, nxt[:2])
    if e_in[0] * e_out[1] - e_in[1] * e_out[0] >= -1e-9:
        _fail(f"{code}: opposite-fold corner at {P} is not a concave outline corner")
    h = math.sqrt((t + r) ** 2 - r ** 2)
    nl_in, nl_out = (-e_in[1], e_in[0]), (-e_out[1], e_out[0])
    c1 = (P[0] - e_in[0] * h + nl_in[0] * r, P[1] - e_in[1] * h + nl_in[1] * r)
    c2 = (P[0] + e_out[0] * h + nl_out[0] * r, P[1] + e_out[1] * h + nl_out[1] * r)
    T1 = (P[0] - e_in[0] * h, P[1] - e_in[1] * h)
    T2 = (P[0] + e_out[0] * h, P[1] + e_out[1] * h)
    Q1 = (P[0] + (c1[0] - P[0]) * t / (t + r), P[1] + (c1[1] - P[1]) * t / (t + r))
    Q2 = (P[0] + (c2[0] - P[0]) * t / (t + r), P[1] + (c2[1] - P[1]) * t / (t + r))
    if math.dist(prev[:2], P) <= h + EPS or math.dist(nxt[:2], P) <= h + EPS:
        _fail(f"{code}: opposite-fold corner at {P}: an edge is shorter than the R = t relief")

    def minor(c, a, b):
        sw = (math.atan2(b[1] - c[1], b[0] - c[0]) - math.atan2(a[1] - c[1], a[0] - c[0]) + math.pi) % (2 * math.pi) - math.pi
        return math.tan(sw / 4)
    a1 = math.atan2(Q1[1] - P[1], Q1[0] - P[0])
    a2 = math.atan2(Q2[1] - P[1], Q2[0] - P[0])
    void = math.atan2(-(nl_in[1] + nl_out[1]), -(nl_in[0] + nl_out[0]))
    ccw = (a2 - a1) % (2 * math.pi)
    sweep = ccw if not ((void - a1) % (2 * math.pi) < ccw) else ccw - 2 * math.pi
    new = [[_r6(T1[0]), _r6(T1[1]), minor(c1, T1, Q1)], [_r6(Q1[0]), _r6(Q1[1]), math.tan(sweep / 4)],
           [_r6(Q2[0]), _r6(Q2[1]), minor(c2, Q2, T2)], [_r6(T2[0]), _r6(T2[1]), 0]]
    return verts[:i] + new + verts[i + 1:]


# ------------------------------------------------------------------ records for the canonical part
def _edge(start, end, physical, evidence, bend_id=None):
    e = {"physical_edge_id": physical, "frame_id": FRAME, "type": "LINE",
         "start": [_r6(start[0]), _r6(start[1])], "end": [_r6(end[0]), _r6(end[1])],
         "proof": {"source_ref": "canonical flat (spec outline + face chains)", "endpoint_verified": True,
                   "evidence_ref": evidence}}
    if bend_id:
        e["bend_id"] = bend_id
    return e


def _flange_line_id(bend, member, f_line):
    return member["lines"][0] if abs(f_line - bend["l1"]) < 1e-9 else member["lines"][1]


def records(verts, chains, code, page, material, t):
    """All bend and junction records of one part (see build_canonical.build_part)."""
    p = code
    bends, pairs = domains(verts, chains, code)
    check_zones(verts, bends, code)
    out = {"entities": [], "groups": [], "ledger": [], "graph_bends": [], "sites": [], "edges": {},
           "relief_entities": [], "relief_members": [], "flags": []}
    by_id = {}
    for b in bends:
        for i, m in enumerate(b["members"], 1):
            m["mid"] = b["id"] if len(b["members"]) == 1 else f"{b['id']}_{i}"
    # opposite-fold corners first: they change the outline (R = t relief at P)
    rt = {}
    for b, q, web in pairs:
        if b["fold"] != q["fold"]:
            P = _flat(b["axis"], _web_side(b, web)[1], _web_side(q, web)[1])
            verts = keyhole(verts, P, t, code)
            rt[frozenset((id(b), id(q)))] = P
    for b in bends:
        c, axis, bb = b["chain"], b["axis"], b["b"]
        origin, total = c.get("origin", 0.0), c["total"]
        ids, owners = [], []
        for m in b["members"]:
            lines = []
            for name, pos in (("L1", b["l1"]), ("L2", b["l2"])):
                v0, v1 = m["iv"][name]
                eid = f"E_{p}_{m['mid']}_{name}"
                s, e = _flat(axis, pos, v0), _flat(axis, pos, v1)
                ent = {"entity_id": eid, "type": "LINE", "role": "bend", "linetype": "DASHED",
                       "start": [_r6(s[0]), _r6(s[1])], "end": [_r6(e[0]), _r6(e[1])]}
                out["entities"].append(ent)
                by_id[eid] = ent
                lines.append(eid)
            m["lines"] = lines
            ids.append(m["mid"])
            owners.append(lines)
            fa, fb = b["faces"]
            l1, l2 = bb["line1"] - origin, bb["line2"] - origin
            out["graph_bends"].append({
                "bend_id": f"{p}_{m['mid']}", "source_member_ids": [f"{p}_{m['mid']}"], "face_A": fa, "face_B": fb,
                "face_A_shared_edge": f"{fa}.{b['id']}", "face_B_shared_edge": f"{fb}.{b['id']}",
                "edge_orientation": f"bend lines {'x' if axis == 'X' else 'y'} = const across the flat",
                "attachment_source_evidence": bb["ev"], "signed_angle_deg": bb["sign"] * bb["angle"],
                "N_mm": bb["nobi"],
                "material_domain": {"entity_ids": lines, "evidence_ref":
                                    "material of both faces, stopped at perpendicular bends"}})
            out["ledger"].append({
                "bend_id": f"{p}_{m['mid']}", "source_group_id": f"{p}_G_{b['id']}", "ordered_faces": [fa, fb],
                "od_actual_mm": [_r6(l2), _r6(total - l2 + bb["nobi"])], "nobi_mm": bb["nobi"],
                "flat_mm": total, "bend_pair_mm": [_r6(l1), _r6(l2)], "source_pdf_page": page,
                "evidence_ref": f"Nobi {bb['nobi']:g} {bb['nobi_source']}"
                                f"{' ' + bb['nobi_row'] if bb.get('nobi_row') else ''}; L {bb['L']:g}; {bb['ev']}",
                "thickness_single_use": "each face OD as declared in faces[].ev (t counted once)"})
        out["groups"].append((b["id"], ids, bb["ev"], owners))
    count = [0]

    def new_site():
        count[0] += 1
        return f"{p}_J{count[0]}"

    def step_site(steps, bend_ids):
        """BEND_END_OFFSET_90 (NON_90_RELIEF above 90°) site from the measured steps at one corner (one or two bend ends)."""
        slits = [st for st in steps if st["S"] <= 1e-9]
        if len(slits) > 1:
            _fail(f"{code}: two slits at one corner {slits[0]['B']}: one mechanism per junction — build by hand")
        st = slits[0] if slits else min(steps, key=lambda x: x["S"])
        sid = new_site()
        angle = st["bend"]["b"]["angle"]
        non90 = angle - 90 > 0.5               # same S gate at every angle; only above 90 the angle changes the depth
        mechanism = "NON_90_RELIEF" if non90 else "BEND_END_OFFSET_90"
        depth = sg.relief_depth(t, _relief_angle(angle))
        flush_id, web_id, side_id = f"{sid}_FLUSH", f"{sid}_WEB", f"{sid}_SIDE"
        fl = by_id[_flange_line_id(st["bend"], st["member"], st["f_line"])]
        out["edges"][flush_id] = _edge(fl["start"], fl["end"], f"{fl['entity_id']}.FLANGE_SIDE_LINE",
                                       f"flange-side bend line of {st['bend']['id']}")
        out["edges"][web_id] = _edge(*st["web_edge"], f"{sid}.WEB_EDGE", "web edge at the corner B (outline)")
        out["edges"][side_id] = _edge(*st["side_edge"], f"{sid}.FLANGE_SIDE_EDGE", "flange side edge (outline)")
        site = {"site_id": sid, "status": "PROVED", "frame_id": FRAME, "bend_ids": bend_ids,
                "flush_edge_id": flush_id, "web_edge_id": web_id, "side_edge_id": side_id,
                "positive_axis": [float(v) for v in _flat(st["bend"]["axis"], st["d"], 0.0)],
                "positive_axis_evidence_ref": "toward the web face in the canonical flat",
                "included_angle_deg": angle if non90 else 90, "S_mm": st["S"], "mechanism": mechanism,
                "decision": "NO_RELIEF", "relief_member_ids": [],
                "steps_mm": {s2["bend"]["id"]: s2["S"] for s2 in steps},
                "corner_B": [_r6(st["B"][0]), _r6(st["B"][1])]}
        if non90:
            site["angle_evidence_ref"] = st["bend"]["b"]["ev"]
        if slits:
            try:
                ents, wit = slit_entities(st, material, t, sid)
            except sg.LeadValueUnproved as exc:
                site.update(status="FLAGGED", decision="FLAGGED")
                out["flags"].append(f"{st['bend']['id']}: {exc} - chưa vẽ đường rạch tại "
                                    f"({st['B'][0]:g}, {st['B'][1]:g})")
                out["sites"].append(site)
                return
            out["relief_entities"] += ents
            out["relief_members"].append({
                "canonical_member_id": f"CM_{sid}", "origin": "DERIVED_RULE", "controlling_rule": mechanism,
                "source_member_ids": [f"{p}_{st['member']['mid']}"], "status": "PROVED",
                "entity_ids": [e["entity_id"] for e in ents], "bend_end_site_id": sid})
            site.update(decision="SLIT", relief_member_ids=[f"CM_{sid}"], slit_construction={
                "actual_edge_id": web_id, "side_edge_id": side_id, "bend_id": f"{p}_{st['member']['mid']}",
                "evidence_ref": f"S {st['S']:g}: slit {depth - st['S']:g} from B along the flange side", **wit})
        out["sites"].append(site)

    done, shoulders = set(), []
    for b in bends:
        for m in b["members"]:
            for end, s in (("lo", -1), ("hi", 1)):
                corner = m["ends"].get(end)
                if corner is None:
                    v_end = m["iv"]["L1"][0] if s < 0 else m["iv"]["L1"][1]
                    st = end_step(verts, b, v_end, s, None, code)
                    if st and st["shoulder"]:        # a shoulder past the zone: recorded unless a corner site owns that B
                        st["member"] = m
                        shoulders.append((st, [f"{p}_{m['mid']}"]))
                    elif st:
                        st["member"] = m
                        step_site([st], [f"{p}_{m['mid']}"])
                    continue
                q = corner["pair"]
                key = frozenset((id(b), id(q)))
                if key in done:
                    continue
                done.add(key)
                qm, q_s = next((mm, s2) for mm in q["members"] for e2, s2 in (("lo", -1), ("hi", 1))
                               if mm["ends"].get(e2, {}).get("pair") is b)
                if not corner["same"]:
                    P = rt[key]
                    sid = new_site()
                    e_ids = []
                    for bend_, mem_ in ((b, m), (q, qm)):
                        fl = by_id[_flange_line_id(bend_, mem_, _web_side(bend_, corner["web"])[1])]
                        eid = f"{sid}_{bend_['id']}_FLANGE_LINE"
                        out["edges"][eid] = _edge(fl["start"], fl["end"], f"{fl['entity_id']}.FLANGE_SIDE_LINE",
                                                  f"flange-side line of {bend_['id']}", bend_id=f"{p}_{mem_['mid']}")
                        e_ids.append(eid)
                    out["relief_members"].append({
                        "canonical_member_id": f"CM_{sid}", "origin": "DERIVED_RULE",
                        "controlling_rule": "OPPOSITE_FOLD_R_T", "source_member_ids": [f"{p}_{m['mid']}"],
                        "status": "PROVED", "entity_ids": ["__OUTER__"], "bend_end_site_id": sid,
                        "outline_relief": {"center": [_r6(P[0]), _r6(P[1])], "radius": t}})
                    out["sites"].append({
                        "site_id": sid, "status": "PROVED", "frame_id": FRAME,
                        "bend_ids": [f"{p}_{m['mid']}", f"{p}_{qm['mid']}"], "included_angle_deg": 90,
                        "mechanism": "OPPOSITE_FOLD_R_T", "decision": "SEPARATE_RULE",
                        "special_rule_evidence_ref": f"{b['id']} {b['fold']} / {q['id']} {q['fold']}: opposite folds, "
                                                     "flange-side lines meet at the outline corner",
                        "intersection_edge_ids": e_ids, "relief_member_ids": [f"CM_{sid}"],
                        "corner_P": [_r6(P[0]), _r6(P[1])]})
                    continue
                steps = []
                for bend_, mem_, s_ in ((b, m, s), (q, qm, q_s)):
                    v_e = mem_["iv"]["L1"][1] if s_ > 0 else mem_["iv"]["L1"][0]
                    other = q if bend_ is b else b
                    st = end_step(verts, bend_, v_e, s_, corner["web"], code,
                                  reach=other["l2"] - other["l1"] + t + 1.0)
                    if st:
                        st["member"] = mem_
                        steps.append(st)
                if not steps:
                    _fail(f"{code}: corner of {b['id']} and {q['id']}: no step on either flange — build by hand")
                step_site(steps, [f"{p}_{m['mid']}", f"{p}_{qm['mid']}"])
                if len(steps) == 2:
                    slit = [x for x in steps if x["S"] <= 1e-9]
                    other = [x for x in steps if x["S"] > 1e-9]
                    if slit and other:
                        dr = slit[0]["bend"]["chain"]["faces"][slit[0]["flange"]]["od"]
                        dk = other[0]["bend"]["chain"]["faces"][other[0]["flange"]]["od"]
                        if dr > dk + 0.1:
                            out["flags"].append(f"{slit[0]['bend']['id']}: bích sâu hơn (OD {dr:g}) đang lùi t, "
                                                f"bích nông (OD {dk:g}) mới phải lùi (khuyết_t, SLIT_RELIEF §5)")
    for st, ids in shoulders:
        if not any(site.get("corner_B") and math.dist(site["corner_B"], st["B"]) <= 1e-4 for site in out["sites"]):
            step_site([st], ids)
    out["verts"] = verts
    out["bends"] = bends
    return out
