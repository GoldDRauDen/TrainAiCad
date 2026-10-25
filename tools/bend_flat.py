#!/usr/bin/env python3
"""Bent part (single unfold axis: L / U / Z / hat / multi-bend chain) for tools/build_canonical.py.

The reader declares the faces in unfold order with their proved OD and each bend's angle, fold sign
and (when printed) handwritten Nobi. This module derives the rest (rules/BEND.md):

* Nobi per bend from ``lookup.nobi`` (handwritten > 90° J table > SPLIT_FLANGE_10MM refusal);
* bend double lines ``line1 = ΣOD₁..ₖ − ΣN₁..ₖ``, ``line2 = ΣOD₁..ₖ − ΣN₁..ₖ₋₁`` and the flat length;
* face-relative points/holes ``{face, u, v, from: start|end}`` → flat coordinates
  (face start = previous bend's line1, face end = next bend's line2; first/last face from its free edge);
* bend lines clipped to the real material (outline ∩ line), one member per material interval;
* ``face_graph`` and ``per_bend_witness_ledger`` records for the canonical guards.

Refuses (with the reason) what is not automated yet: a missing Nobi (SPLIT_FLANGE_10MM), an outline that
changes inside a bend zone (bend-end junction: decide S by hand, rules/SLIT_RELIEF.md §3), unequal clipping
of the two lines of one bend.
"""
from __future__ import annotations

import math

import lookup

ZONE_TOL = 1e-6


class BendError(ValueError):
    pass


def _fail(msg):
    raise BendError(msg)


def unfold_chain(bend: dict, material: str, t: float, customer, code: str) -> dict:
    axis = str(bend.get("axis", "X")).upper()
    if axis not in ("X", "Y"):
        _fail(f"{code}: bend.axis must be X or Y (the direction the face chain runs in the flat)")
    faces = bend.get("faces") or _fail(f"{code}: bend.faces required (ordered from the flat origin)")
    bends = bend.get("bends") or _fail(f"{code}: bend.bends required")
    if len(bends) != len(faces) - 1:
        _fail(f"{code}: {len(faces)} faces need {len(faces) - 1} bends, got {len(bends)}")
    fids = []
    for i, f in enumerate(faces):
        fid = str(f.get("id") or f"F{i + 1}")
        if fid in fids:
            _fail(f"{code}: duplicate face id {fid}")
        if not f.get("ev"):
            _fail(f"{code}: face {fid} needs ev (which witnesses give its OD, incl. any +t)")
        if not isinstance(f.get("od"), (int, float)) or f["od"] <= 0:
            _fail(f"{code}: face {fid} needs a positive od")
        fids.append(fid)
    width = bend.get("width")
    out_bends = []
    for k, b in enumerate(bends):
        bid = str(b.get("id") or f"B{k + 1}")
        angle = float(b.get("angle", 90))
        sign = b.get("sign", 1)
        if sign not in (1, -1):
            _fail(f"{code}: bend {bid} sign must be 1 or -1 (fold direction)")
        if not b.get("ev"):
            _fail(f"{code}: bend {bid} needs ev (bend callout / view proving it)")
        L = b.get("L", width)
        if not isinstance(L, (int, float)) or L <= 0:
            _fail(f"{code}: bend {bid} needs L (physical bend-edge length) or bend.width")
        res = lookup.nobi(material, t, float(L), angle, b.get("surface"), b.get("nobi"),
                          bool(b.get("j", True)), customer)
        if res.get("status") != "OK":
            _fail(f"{code}: bend {bid}: {res.get('action')} — {res.get('flag_vi')} "
                  "(draw the split flange by hand: rules/BEND.md §6)")
        out_bends.append({"id": bid, "angle": angle, "sign": sign, "nobi": float(res["nobi"]),
                          "nobi_source": res.get("source"), "nobi_row": res.get("row"), "ev": b["ev"],
                          "L": float(L), "faces": (fids[k], fids[k + 1])})
    un = lookup.unfold([float(f["od"]) for f in faces], [b["nobi"] for b in out_bends])
    total = float(un["flat_length"])
    for b, line in zip(out_bends, un["bend_lines"]):
        b["line1"], b["line2"] = float(line["line1"]), float(line["line2"])
    starts = [0.0] + [b["line1"] for b in out_bends]
    ends = [b["line2"] for b in out_bends] + [total]
    face_rec = {fid: {"id": fid, "od": float(f["od"]), "ev": f["ev"], "start": s, "end": e,
                      "first": i == 0, "last": i == len(faces) - 1}
                for i, (fid, f, s, e) in enumerate(zip(fids, faces, starts, ends))}
    return {"axis": axis, "faces": face_rec, "order": fids, "bends": out_bends, "total": total}


def face_datum(chain: dict, face: str, frm: str, code: str):
    """(along datum coordinate, witness node type, sign, datum bend line) of a face-relative dimension.

    The datum bend line is (bend id, "L1"|"L2") when the face datum is the adjacent face's outer plane,
    None when it is the part's free edge (the outer contour).
    """
    f = chain["faces"].get(face) or _fail(f"{code}: unknown face {face}")
    k = chain["order"].index(face)
    frm = (frm or "start").lower()
    if frm == "start":
        return (f["start"], "OUTER_EDGE", 1.0, None) if f["first"] else \
            (f["start"], "REFERENCE_DATUM", 1.0, (chain["bends"][k - 1]["id"], "L1"))
    if frm == "end":
        return (f["end"], "OUTER_EDGE", -1.0, None) if f["last"] else \
            (f["end"], "REFERENCE_DATUM", -1.0, (chain["bends"][k]["id"], "L2"))
    _fail(f"{code}: face '{face}' from must be start or end")


def to_flat(chain: dict, along: float, across: float):
    return (along, across) if chain["axis"] == "X" else (across, along)


def resolve_outline(items, chain: dict, code: str):
    """Face-relative outline points {face, u, v, from, ...opts} -> [x, y, opts]."""
    out = []
    for item in items:
        if isinstance(item, dict) and "face" in item:
            d, _, s, _ = face_datum(chain, item["face"], item.get("from"), code)
            x, y = to_flat(chain, d + s * float(item.get("u", 0.0)), float(item.get("v", 0.0)))
            opts = {k: v for k, v in item.items() if k not in ("face", "u", "v", "from")}
            out.append([x, y, opts] if opts else [x, y])
        else:
            out.append(item)
    return out


def auto_outline(bend: dict, chain: dict, code: str):
    """Full-width rectangle: only when every face has the same proved width (bend.width + width_ev)."""
    w = bend.get("width")
    if not isinstance(w, (int, float)) or not bend.get("width_ev"):
        _fail(f"{code}: outline 'auto' needs bend.width and bend.width_ev (every face full width)")
    a, b = to_flat(chain, chain["total"], float(w))
    return [[0, 0], [a, 0], [a, b], [0, b]]


def _poly(verts, seg_per_rad: float = 20.0):
    """Polygon points of a closed LWPOLYLINE with bulges flattened finely."""
    pts = []
    n = len(verts)
    for i in range(n):
        x0, y0, bulge = verts[i]
        x1, y1 = verts[(i + 1) % n][:2]
        pts.append((x0, y0))
        if abs(bulge) > 1e-12:
            theta = 4 * math.atan(bulge)
            chord = math.hypot(x1 - x0, y1 - y0)
            r = chord / (2 * math.sin(abs(theta) / 2))
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            h = r * math.cos(abs(theta) / 2) * (1 if bulge > 0 else -1)
            ux, uy = (x1 - x0) / chord, (y1 - y0) / chord
            cx, cy = mx - uy * h, my + ux * h
            a0 = math.atan2(y0 - cy, x0 - cx)
            steps = max(4, int(abs(theta) * seg_per_rad))
            for s in range(1, steps):
                a = a0 + theta * s / steps
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def line_intervals(verts, chain: dict, pos: float):
    """Material intervals [v0, v1] across the flat where the bend line `along = pos` crosses the outline."""
    pts = _poly(verts)
    hits = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a0, c0 = (x0, y0) if chain["axis"] == "X" else (y0, x0)
        a1, c1 = (x1, y1) if chain["axis"] == "X" else (y1, x1)
        if (a0 <= pos < a1) or (a1 <= pos < a0):
            hits.append(c0 + (pos - a0) * (c1 - c0) / (a1 - a0))
    hits.sort()
    if len(hits) % 2:
        _fail(f"bend line at {pos:g} crosses the outline an odd number of times")
    return [(hits[i], hits[i + 1]) for i in range(0, len(hits), 2) if hits[i + 1] - hits[i] > 1e-6]


def check_bend_zones(verts, chain: dict, code: str):
    """Refuse an outline that changes inside a bend zone (a bend-end junction needs S by hand)."""
    for b in chain["bends"]:
        for x, y, _ in verts:
            along = x if chain["axis"] == "X" else y
            if b["line1"] - ZONE_TOL <= along <= b["line2"] + ZONE_TOL:
                _fail(f"{code}: bend {b['id']}: the outline has a corner at ({x:g}, {y:g}) inside the bend zone "
                      f"{b['line1']:g}..{b['line2']:g} — bend-end junction: decide S and the relief by hand "
                      "(rules/SLIT_RELIEF.md §3) and build the part as canonical JSON")


def bend_records(verts, chain: dict, part_code: str, page: int):
    """Entities, groups (name, ids, ev, owners), face_graph and ledger for every bend."""
    p = part_code
    entities, groups, graph_bends, ledger = [], [], [], []
    total = chain["total"]
    for b in chain["bends"]:
        iv1 = line_intervals(verts, chain, b["line1"])
        iv2 = line_intervals(verts, chain, b["line2"])
        if not iv1 or len(iv1) != len(iv2) or any(abs(a[0] - c[0]) > 1e-6 or abs(a[1] - c[1]) > 1e-6
                                                for a, c in zip(iv1, iv2)):
            _fail(f"{p}: bend {b['id']}: the two bend lines cross different material ({iv1} vs {iv2}) — "
                  "bend-end junction, build by hand")
        ids, owners = [], []
        for i, (v0, v1) in enumerate(iv1, 1):
            mid = b["id"] if len(iv1) == 1 else f"{b['id']}_{i}"
            lines = []
            for n, pos in (("L1", b["line1"]), ("L2", b["line2"])):
                eid = f"E_{p}_{mid}_{n}"
                s, e = to_flat(chain, pos, v0), to_flat(chain, pos, v1)
                entities.append({"entity_id": eid, "type": "LINE", "role": "bend", "linetype": "DASHED",
                                 "start": [round(s[0], 6), round(s[1], 6)], "end": [round(e[0], 6), round(e[1], 6)]})
                lines.append(eid)
            ids.append(mid)
            owners.append(lines)
            fa, fb = b["faces"]
            graph_bends.append({
                "bend_id": f"{p}_{mid}", "source_member_ids": [f"{p}_{mid}"], "face_A": fa, "face_B": fb,
                "face_A_shared_edge": f"{fa}.{b['id']}", "face_B_shared_edge": f"{fb}.{b['id']}",
                "edge_orientation": f"bend lines {'x' if chain['axis'] == 'X' else 'y'} = const across the flat",
                "attachment_source_evidence": b["ev"], "signed_angle_deg": b["sign"] * b["angle"],
                "material_domain": {"entity_ids": lines,
                                    "evidence_ref": f"outline ∩ bend line: {v0:g}..{v1:g}"}})
            ledger.append({
                "bend_id": f"{p}_{mid}", "source_group_id": f"{p}_G_{b['id']}", "ordered_faces": [fa, fb],
                "od_actual_mm": [b["line2"], round(total - b["line2"] + b["nobi"], 6)], "nobi_mm": b["nobi"],
                "flat_mm": total, "bend_pair_mm": [b["line1"], b["line2"]], "source_pdf_page": page,
                "evidence_ref": f"Nobi {b['nobi']:g} {b['nobi_source']}"
                                f"{' ' + b['nobi_row'] if b.get('nobi_row') else ''}; L {b['L']:g}; {b['ev']}",
                "thickness_single_use": "each face OD as declared in faces[].ev (t counted once)"})
        groups.append((b["id"], ids, b["ev"], owners))
    faces, theta = [], 0.0
    for k, fid in enumerate(chain["order"]):
        f = chain["faces"][fid]
        u = [1, 0] if chain["axis"] == "X" else [0, 1]
        v = [0, 1] if chain["axis"] == "X" else [1, 0]
        edges = ([f"{fid}.FREE"] if f["first"] else [f"{fid}.{chain['bends'][k - 1]['id']}"]) + \
                ([f"{fid}.FREE"] if f["last"] else [f"{fid}.{chain['bends'][k]['id']}"])
        faces.append({"face_id": fid, "source_view": f"PDF p{page}: {f['ev']}",
                      "local_origin": list(to_flat(chain, f["start"], 0.0)), "local_axis_u": u, "local_axis_v": v,
                      "contour_edge_ids": edges, "source_dimensions": [{"OD_mm": f["od"], "evidence_ref": f["ev"]}],
                      "normal_orientation": [round(-math.sin(math.radians(theta)), 6),
                                             round(math.cos(math.radians(theta)), 6)]})
        if k < len(chain["bends"]):
            b = chain["bends"][k]
            theta += b["sign"] * (180.0 - b["angle"])
    return entities, groups, {"faces": faces, "bends": graph_bends}, ledger


def mirror_ledger(part: dict, total_along: float) -> None:
    """After a 180° whole-part turn, bend positions are measured from the other end."""
    for item in part.get("per_bend_witness_ledger", []):
        l1, l2 = item["bend_pair_mm"]
        n = item["nobi_mm"]
        new1, new2 = round(total_along - l2, 6), round(total_along - l1, 6)
        item["bend_pair_mm"] = [new1, new2]
        item["od_actual_mm"] = [new2, round(item["flat_mm"] - new2 + n, 6)]
        item["ordered_faces"] = item["ordered_faces"][::-1]


def check_features_off_bend_zones(entities, chain: dict, code: str):
    """A hole/slot/cut-out/POINT overlapping a bend zone would put the bend line through a void: refuse (draw by hand)."""
    k = 0 if chain["axis"] == "X" else 1
    for e in entities:
        if e.get("role") not in ("hole", "slot", "cutout", "ordinary_point", "through_piercing"):
            continue
        if e["type"] == "CIRCLE":
            lo, hi = e["center"][k] - e["radius"], e["center"][k] + e["radius"]
        elif e["type"] == "POINT":
            lo = hi = e["point"][k]
        else:
            vals = [pt[k] for pt in _poly(e["vertices"])]  # bulged caps included
            lo, hi = min(vals), max(vals)
        for b in chain["bends"]:
            if lo < b["line2"] + ZONE_TOL and hi > b["line1"] - ZONE_TOL:
                _fail(f"{code}: {e['entity_id']} overlaps bend {b['id']} zone {b['line1']:g}..{b['line2']:g} "
                      "— the bend lines must stop at the void: build this part by hand")
