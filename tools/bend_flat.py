#!/usr/bin/env python3
"""Bent part (single unfold axis: L / U / Z / hat / multi-bend chain) for tools/build_canonical.py.

The reader declares the faces in unfold order with their proved OD and each bend's angle, fold sign
and (when printed) handwritten Nobi. This module derives the rest (rules/BEND.md):

* Nobi per bend from ``lookup.nobi`` (handwritten > 90° J table; none -> SPLIT_FLANGE_10MM, see split_plan);
* bend double lines ``line1 = ΣOD₁..ₖ − ΣN₁..ₖ``, ``line2 = ΣOD₁..ₖ − ΣN₁..ₖ₋₁`` and the flat length;
* face-relative points/holes ``{face, u, v, from: start|end}`` → flat coordinates
  (face start = previous bend's line1, face end = next bend's line2; first/last face from its free edge);
* ``face_graph`` face records; bend lines, domains, bend-end junctions and two-axis corners: tools/bend_corner.py.

A bend without a Nobi source is split (``split_plan``): build_canonical draws each segment at its OD and the
flange 10 mm away (SPLIT_FLANGE_10MM, rules/BEND.md §6).
"""
from __future__ import annotations

import math

import lookup
from geom import bulge_circle, bulge_points

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
    bends = bend.get("bends")
    if bends is None or (not bends and len(faces) != 1):
        _fail(f"{code}: bend.bends required")
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
        res = _nobi(b, L, material, t, customer)
        if res.get("status") != "OK":
            _fail(f"{code}: bend {bid}: {res.get('action')} — {res.get('flag_vi')}")
        fold = b.get("fold")
        if fold not in (None, "toward", "away"):
            _fail(f"{code}: bend {bid} fold must be toward or away (the viewer of the flat)")
        out_bends.append({"id": bid, "angle": angle, "sign": sign, "nobi": float(res["nobi"]),
                          "nobi_source": res.get("source"), "nobi_row": res.get("row"), "ev": b["ev"],
                          "L": float(L), "faces": (fids[k], fids[k + 1]), "fold": fold})
    un = lookup.unfold([float(f["od"]) for f in faces], [b["nobi"] for b in out_bends])
    total = float(un["flat_length"])
    origin = float(bend.get("origin", 0.0))  # flat coordinate of the first face's free edge (two-axis parts)
    for b, line in zip(out_bends, un["bend_lines"]):
        b["line1"], b["line2"] = float(line["line1"]) + origin, float(line["line2"]) + origin
    starts = [origin] + [b["line1"] for b in out_bends]
    ends = [b["line2"] for b in out_bends] + [origin + total]
    face_rec = {fid: {"id": fid, "od": float(f["od"]), "ev": f["ev"], "start": s, "end": e,
                      "first": i == 0, "last": i == len(faces) - 1}
                for i, (fid, f, s, e) in enumerate(zip(fids, faces, starts, ends))}
    return {"axis": axis, "faces": face_rec, "order": fids, "bends": out_bends, "total": total, "origin": origin}


def _nobi(b: dict, L, material: str, t: float, customer):
    return lookup.nobi(material, t, float(L), float(b.get("angle", 90)), b.get("surface"), b.get("nobi"),
                       bool(b.get("j", True)), customer)


def split_plan(bend: dict, material: str, t: float, customer, code: str):
    """None when every bend has a Nobi; else the segments between SPLIT_FLANGE_10MM bends.

    Each segment: {faces, bends, split_after: {bend, flag_vi, reason} | None}."""
    faces, bends = bend.get("faces") or [], bend.get("bends") or []
    if len(bends) != len(faces) - 1:
        return None  # unfold_chain reports the shape error
    segs, cur_f, cur_b, split = [], [faces[0]] if faces else [], [], False
    for k, b in enumerate(bends):
        res = _nobi(b, b.get("L", bend.get("width")) or 1.0, material, t, customer)
        if res.get("status") != "OK" and res.get("action") == lookup.SPLIT_FLANGE:
            split = True
            segs.append({"faces": cur_f, "bends": cur_b,
                         "split_after": {"bend": str(b.get("id") or f"B{k + 1}"), "reason": res.get("reason"),
                                         "flag_vi": res.get("flag_vi")}})
            cur_f, cur_b = [faces[k + 1]], []
        else:
            cur_b.append(b)
            cur_f.append(faces[k + 1])
    segs.append({"faces": cur_f, "bends": cur_b, "split_after": None})
    return segs if split else None


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
        pts.append((x0, y0))
        if abs(bulge) > 1e-12:
            p1 = verts[(i + 1) % n][:2]
            theta = bulge_circle((x0, y0), p1, bulge)[3]
            pts += bulge_points((x0, y0), p1, bulge, max(4, int(abs(theta) * seg_per_rad)))
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


def face_records(chain: dict, page: int):
    """face_graph face records of one chain (local origin/axes, edges, OD evidence, normal)."""
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
    return faces


def mirror_ledger(part: dict, total_along: float) -> None:
    """After a 180° whole-part turn, bend positions are measured from the other end."""
    for item in part.get("per_bend_witness_ledger", []):
        l1, l2 = item["bend_pair_mm"]
        n = item["nobi_mm"]
        new1, new2 = round(total_along - l2, 6), round(total_along - l1, 6)
        item["bend_pair_mm"] = [new1, new2]
        item["od_actual_mm"] = [new2, round(item["flat_mm"] - new2 + n, 6)]
        item["ordered_faces"] = item["ordered_faces"][::-1]
