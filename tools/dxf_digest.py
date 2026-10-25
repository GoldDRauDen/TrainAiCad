#!/usr/bin/env python3
"""Digest of a customer DXF DATA sheet: every primitive gets an id and exactly one home. Nothing is altered or dropped.

    python tools/dxf_digest.py file.dxf                       # summary: views top-to-bottom, holes by Ø, arc radii, colours
    python tools/dxf_digest.py data.dxf --out digest.json [--png views.png] [--profile auto|catia|generic] [--noise-mm 5]

The one DXF reader of the repo: customer DATA sheets, samples, and QA targets (an AI composite DXF gives one view per
part, top-to-bottom).

* Decodes like rules/DATA_DXF.md §1 (bulge start vertex, closed last->first, INSERT transforms); numbers are copied
  from the file (9 decimals), never rounded to a drawing value.
* Each piece: id (`P0001`), type, source handle/layer/colour/linetype, geometry, and a linetype `hint` only.
* Homes: views `V01..` (touching pieces; circles/cut-outs inside a view join it) and the buckets
  `B_ISOLATED`, `B_NOISE` (exploded glyph/dimension candidates, only with --noise-mm), `B_DUPLICATE`,
  `B_UNSUPPORTED` (ELLIPSE/SPLINE/... listed, never flattened). Frame/title-block/iso are *candidates*: the reader decides.
* TEXT/MTEXT/DIMENSION go to `annotations` (dimension measurements are free witnesses, never geometry).
Use `tools/dxf_assemble.py` to pick pieces by id; layer/colour/linetype is the only thing it may change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

SUPPORTED = {"LINE", "ARC", "CIRCLE", "POINT"}
CURVES_UNSUPPORTED = {"ELLIPSE", "SPLINE"}
ANNOT = {"TEXT", "MTEXT", "DIMENSION", "LEADER", "MULTILEADER", "HATCH", "ATTRIB", "ATTDEF"}
GLYPH_LINE_MM = 2.0          # a LINE shorter than this counts toward "exploded glyph" detection
CATIA_MIN_LINES = 50
CATIA_GLYPH_SHARE = 0.5
CATIA_NOISE_MM = 5.0
GLYPH_MEAN_MM = 1.2          # exploded words: >= 6 LINEs averaging below this, in a blob under GLYPH_MAX_MM
GLYPH_MAX_MM = 30.0
FRAME_SPAN = 0.8             # a frame candidate spans >= this share of the sheet in both axes
TOUCH = 1e-3                 # endpoint touch tolerance (mm) for grouping pieces into views
DECIMALS = 9


def _n(v: float) -> float:
    return round(float(v), DECIMALS) + 0.0


def _xy(p) -> list[float]:
    return [_n(p[0]), _n(p[1])]


def _hint(linetype: str) -> str:
    lt = linetype.upper()
    if any(k in lt for k in ("DASHDOT", "CENTER", "PHANTOM", "DOT")):
        return "BEND_SUPPORT_OR_CENTRE"
    if any(k in lt for k in ("DASH", "HIDDEN")):
        return "HIDDEN_OR_PROJECTION_ONLY"
    return "UNCLASSIFIED"


def _decode(entity, depth=0, via=False):
    t = entity.dxftype()
    if t in ("LWPOLYLINE", "POLYLINE"):
        for v in entity.virtual_entities():
            yield v, t, via
    elif t == "INSERT" and depth < 8:
        for v in entity.virtual_entities():
            yield from _decode(v, depth + 1, True)
    else:
        yield entity, t, via


def _eff_linetype(doc, piece) -> str:
    lt = piece.dxf.get("linetype", "BYLAYER")
    if str(lt).upper() in ("BYLAYER", ""):
        layer = piece.dxf.get("layer", "0")
        try:
            lt = doc.layers.get(layer).dxf.linetype
        except Exception:
            lt = "CONTINUOUS"
    return str(lt).upper()


def _arc_bbox(c, r, a0, a1):
    pts = [(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a))) for a in (a0, a1)]
    sweep = (a1 - a0) % 360
    for q in (0, 90, 180, 270):
        if (q - a0) % 360 <= sweep:
            pts.append((c[0] + r * math.cos(math.radians(q)), c[1] + r * math.sin(math.radians(q))))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox(rec):
    t = rec["type"]
    if t == "LINE":
        (x0, y0), (x1, y1) = rec["start"], rec["end"]
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    if t == "ARC":
        return _arc_bbox(rec["center"], rec["radius"], rec["start_angle"], rec["end_angle"])
    if t == "CIRCLE":
        (cx, cy), r = rec["center"], rec["radius"]
        return cx - r, cy - r, cx + r, cy + r
    x, y = rec["point"]
    return x, y, x, y


def _union_bbox(boxes):
    x0, y0, x1, y1 = zip(*boxes)
    return [_n(min(x0)), _n(min(y0)), _n(max(x1)), _n(max(y1))]


def _dup_key(rec):
    geo = {k: rec[k] for k in ("start", "end", "center", "radius", "start_angle", "end_angle", "point") if k in rec}
    if rec["type"] == "LINE":
        geo = tuple(sorted((tuple(rec["start"]), tuple(rec["end"]))))
    else:
        geo = tuple(sorted((k, json.dumps(v)) for k, v in geo.items()))
    return (rec["type"], geo, rec["linetype"], rec["color"])


def _read(path):
    doc = ezdxf.readfile(path)
    pieces, unsupported, annotations, warnings = [], [], [], []
    for e in doc.modelspace():
        t = e.dxftype()
        handle = e.dxf.get("handle", "")
        ext = tuple(e.dxf.get("extrusion", (0, 0, 1))) if t not in ("ELLIPSE",) and e.dxf.hasattr("extrusion") else (0, 0, 1)
        if abs(ext[0]) > 1e-9 or abs(ext[1]) > 1e-9 or abs(ext[2] - 1) > 1e-9:
            warnings.append(f"OCS_EXTRUSION {t} {handle}: coordinates are in the entity's own system")
        if t in ANNOT:
            rec = {"id": f"A{len(annotations) + 1:04d}", "type": t, "layer": e.dxf.get("layer", "0"), "handle": handle}
            if t == "TEXT":
                rec["text"] = e.dxf.get("text", "")
                rec["insert"] = _xy(e.dxf.insert)
            elif t == "MTEXT":
                rec["text"] = e.text
                rec["insert"] = _xy(e.dxf.insert)
            elif t == "DIMENSION":
                rec["text"] = e.dxf.get("text", "")
                try:
                    rec["measurement"] = _n(e.get_measurement())
                except Exception:
                    rec["measurement"] = None
            annotations.append(rec)
            continue
        if t in CURVES_UNSUPPORTED or (t not in SUPPORTED and t not in ("LWPOLYLINE", "POLYLINE", "INSERT")):
            box = None
            try:
                from ezdxf import bbox as ebbox
                ex = ebbox.extents([e])
                if ex.has_data:
                    box = [_n(ex.extmin.x), _n(ex.extmin.y), _n(ex.extmax.x), _n(ex.extmax.y)]
            except Exception:
                pass
            unsupported.append({"id": f"U{len(unsupported) + 1:04d}", "type": t, "layer": e.dxf.get("layer", "0"),
                                "handle": handle, "bbox": box,
                                "reason": "UNSUPPORTED_CURVE_FLAG" if t in CURVES_UNSUPPORTED else "UNSUPPORTED_ENTITY"})
            continue
        for piece, src, via in _decode(e):
            pt = piece.dxftype()
            if pt not in SUPPORTED:
                unsupported.append({"id": f"U{len(unsupported) + 1:04d}", "type": pt, "layer": piece.dxf.get("layer", "0"),
                                    "handle": handle, "bbox": None, "reason": "UNSUPPORTED_ENTITY"})
                continue
            lt = _eff_linetype(doc, piece)
            rec = {"id": f"P{len(pieces) + 1:04d}", "type": pt, "handle": handle, "layer": piece.dxf.get("layer", "0"),
                   "color": piece.dxf.get("color", 256), "linetype": lt, "hint": _hint(lt), "from": src}
            if via:
                rec["in_insert"] = True
            if pt == "LINE":
                rec["start"], rec["end"] = _xy(piece.dxf.start), _xy(piece.dxf.end)
            elif pt == "ARC":
                rec["center"], rec["radius"] = _xy(piece.dxf.center), _n(piece.dxf.radius)
                rec["start_angle"], rec["end_angle"] = _n(piece.dxf.start_angle), _n(piece.dxf.end_angle)
                rec["start"], rec["end"] = _xy(piece.start_point), _xy(piece.end_point)
                if src in ("LWPOLYLINE", "POLYLINE"):
                    rec["bulge_decoded"] = True
            elif pt == "CIRCLE":
                rec["center"], rec["radius"] = _xy(piece.dxf.center), _n(piece.dxf.radius)
            else:
                rec["point"] = _xy(piece.dxf.location)
            pieces.append(rec)
    return doc, pieces, unsupported, annotations, warnings


def _detect_profile(pieces):
    lines = [p for p in pieces if p["type"] == "LINE"]
    if len(lines) < CATIA_MIN_LINES:
        return "generic"
    short = sum(1 for p in lines if math.hypot(p["end"][0] - p["start"][0], p["end"][1] - p["start"][1]) < GLYPH_LINE_MM)
    return "catia_exploded_sheet" if short / len(lines) >= CATIA_GLYPH_SHARE else "generic"


def _components(live):
    """Union pieces whose endpoints touch (<= TOUCH); CIRCLE/POINT stay single."""
    parent = {p["id"]: p["id"] for p in live}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    grid = defaultdict(list)
    cell = TOUCH * 4
    for p in live:
        if p["type"] in ("LINE", "ARC"):
            for pt in (p["start"], p["end"]):
                grid[(math.floor(pt[0] / cell), math.floor(pt[1] / cell))].append((pt, p["id"]))
    for (gx, gy), items in grid.items():
        near = [it for dx in (-1, 0, 1) for dy in (-1, 0, 1) for it in grid.get((gx + dx, gy + dy), [])]
        for pt, pid in items:
            for q, qid in near:
                if qid != pid and abs(pt[0] - q[0]) <= TOUCH and abs(pt[1] - q[1]) <= TOUCH:
                    a, b = find(pid), find(qid)
                    if a != b:
                        parent[a] = b
    comps = defaultdict(list)
    for p in live:
        comps[find(p["id"])].append(p["id"])
    return list(comps.values())


def _contains(outer, inner, eps=1e-6):
    return (outer[0] - eps <= inner[0] and outer[1] - eps <= inner[1] and
            inner[2] <= outer[2] + eps and inner[3] <= outer[3] + eps)


def digest(path: str, profile: str = "auto", noise_mm: float | None = None) -> dict:
    raw = Path(path).read_bytes()
    doc, pieces, unsupported, annotations, warnings = _read(path)
    by_id = {p["id"]: p for p in pieces}
    prof = _detect_profile(pieces) if profile == "auto" else {"catia": "catia_exploded_sheet"}.get(profile, profile)
    if noise_mm is None:
        noise_mm = CATIA_NOISE_MM if prof == "catia_exploded_sheet" else 0.0

    seen, duplicates = {}, []
    live = []
    for p in pieces:
        key = _dup_key(p)
        if key in seen:
            p["duplicate_of"] = seen[key]
            duplicates.append(p["id"])
        else:
            seen[key] = p["id"]
            live.append(p)

    comps = _components(live)
    boxes = {p["id"]: _bbox(p) for p in live}
    info = []
    for ids in comps:
        recs = [by_id[i] for i in ids]
        box = _union_bbox([boxes[i] for i in ids])
        info.append({"ids": list(ids), "bbox": box, "types": Counter(r["type"] for r in recs)})

    all_box = _union_bbox([boxes[p["id"]] for p in live]) if live else [0, 0, 0, 0]
    sheet_w, sheet_h = all_box[2] - all_box[0], all_box[3] - all_box[1]

    noise_ids, noise_comps = [], []
    for c in info:
        w, h = c["bbox"][2] - c["bbox"][0], c["bbox"][3] - c["bbox"][1]
        glyph_like = False
        if noise_mm > 0 and set(c["types"]) == {"LINE"} and len(c["ids"]) >= 6 and max(w, h) < GLYPH_MAX_MM:
            total = sum(math.hypot(by_id[i]["end"][0] - by_id[i]["start"][0], by_id[i]["end"][1] - by_id[i]["start"][1])
                        for i in c["ids"])
            glyph_like = total / len(c["ids"]) <= GLYPH_MEAN_MM
        if noise_mm > 0 and set(c["types"]) == {"LINE"} and (max(w, h) < noise_mm or glyph_like):
            c["noise"] = True
            noise_comps.append(c)
            noise_ids += c["ids"]
    rest = [c for c in info if not c.get("noise")]

    for c in rest:
        c["area"] = (c["bbox"][2] - c["bbox"][0]) * (c["bbox"][3] - c["bbox"][1])
        c["n"] = len(c["ids"])
    for c in rest:   # frame candidate: spans the sheet and holds several other multi-piece groups
        w, h = c["bbox"][2] - c["bbox"][0], c["bbox"][3] - c["bbox"][1]
        if sheet_w > 0 and sheet_h > 0 and w >= FRAME_SPAN * sheet_w and h >= FRAME_SPAN * sheet_h and set(c["types"]) <= {"LINE"}:
            inside = [o for o in rest if o is not c and o["n"] >= 4 and _contains(c["bbox"], o["bbox"])]
            if len(inside) >= 2:
                c["frame"] = True

    order = sorted(range(len(rest)), key=lambda i: (rest[i]["area"], -rest[i]["n"], i))
    rank = {i: k for k, i in enumerate(order)}
    host_of = {}
    for i in order:
        c = rest[i]
        if c.get("frame"):
            continue
        best = None
        for j in order:
            o = rest[j]
            if rank[j] <= rank[i] or o.get("frame") or o["n"] < 4:
                continue
            if _contains(o["bbox"], c["bbox"]):
                best = j
                break
        if best is not None:
            host_of[i] = best

    def root(i):
        while i in host_of:
            i = host_of[i]
        return i
    groups = defaultdict(list)
    for i, c in enumerate(rest):
        groups[root(i)].append(c)
    views, isolated = [], []
    for r, members in groups.items():
        ids = [pid for m in members for pid in m["ids"]]
        if len(ids) == 1 and not rest[r].get("frame"):
            isolated += ids
            continue
        views.append((rest[r], ids))

    def view_rec(c, ids, vid):
        recs = [by_id[i] for i in ids]
        box = _union_bbox([boxes[i] for i in ids])
        types = Counter(r["type"] for r in recs)
        holes = Counter(round(2 * r["radius"], 4) for r in recs if r["type"] == "CIRCLE")
        radii = Counter(round(r["radius"], 4) for r in recs if r["type"] == "ARC")
        if c.get("frame"):
            kind = "FRAME_CANDIDATE"
        elif len(ids) >= 8 or types.get("ARC") or types.get("CIRCLE"):
            kind = "PART_VIEW_CANDIDATE"
        else:
            kind = "SMALL_GROUP"
        inside_u = [u["id"] for u in unsupported if u["bbox"] and _contains(box, u["bbox"])]
        return {"id": vid, "kind": kind, "bbox": box, "size": [_n(box[2] - box[0]), _n(box[3] - box[1])],
                "piece_ids": sorted(ids), "geometry": dict(types),
                "holes_by_dia": {f"Ø{d:g}": n for d, n in sorted(holes.items())},
                "arc_radii": {f"R{r:g}": n for r, n in sorted(radii.items())},
                "colors": {str(k): v for k, v in sorted(Counter(r["color"] for r in recs).items())},
                "linetypes": dict(sorted(Counter(r["linetype"] for r in recs).items())),
                "unsupported_inside_count": len(inside_u), "unsupported_inside": inside_u[:20]}
    ordered = sorted(views, key=lambda cv: (-_union_bbox([boxes[i] for i in cv[1]])[3], _union_bbox([boxes[i] for i in cv[1]])[0]))
    view_list = [view_rec(c, ids, f"V{k + 1:02d}") for k, (c, ids) in enumerate(ordered)]

    def bucket(bid, kind, ids):
        recs = [by_id[i] for i in ids if i in by_id]
        box = _union_bbox([boxes.get(i) or _bbox(by_id[i]) for i in ids]) if ids else None
        return {"id": bid, "kind": kind, "bbox": box, "piece_ids": sorted(ids),
                "geometry": dict(Counter(r["type"] for r in recs))}
    if isolated:
        view_list.append(bucket("B_ISOLATED", "ISOLATED_PIECES", isolated))
    if noise_ids:
        view_list.append(bucket("B_NOISE", "NOISE_CANDIDATES", noise_ids))
    if duplicates:
        for i in duplicates:
            boxes[i] = _bbox(by_id[i])
        view_list.append(bucket("B_DUPLICATE", "DUPLICATE_COINCIDENT", duplicates))
    if unsupported:
        boxes_u = [u["bbox"] for u in unsupported if u["bbox"]]
        view_list.append({"id": "B_UNSUPPORTED", "kind": "UNSUPPORTED_CURVES", "bbox": _union_bbox(boxes_u) if boxes_u else None,
                          "piece_ids": [u["id"] for u in unsupported], "geometry": dict(Counter(u["type"] for u in unsupported))})

    home = {}
    for v in view_list:
        for i in v["piece_ids"]:
            home[i] = v["id"]
    for p in pieces:
        p["home"] = home.get(p["id"])

    circles = defaultdict(list)
    for p in pieces:
        if p["type"] == "CIRCLE":
            circles[(round(p["center"][0], 3), round(p["center"][1], 3))].append(p)
    taps = [{"center": list(c), "dia": sorted(round(2 * p["radius"], 4) for p in ps), "piece_ids": [p["id"] for p in ps]}
            for c, ps in sorted(circles.items()) if len({round(p["radius"], 6) for p in ps}) >= 2]

    homeless = [p["id"] for p in pieces if p["home"] is None]
    return {
        "source": {"file": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "dxfversion": doc.dxfversion,
                   "insunits": doc.header.get("$INSUNITS", 0),
                   "note": "$INSUNITS is metadata: prove real units/scale per view against the PDF."},
        "profile": prof, "noise_mm": noise_mm, "warnings": warnings,
        "views": view_list, "pieces": pieces, "unsupported": unsupported, "annotations": annotations,
        "tap_pair_candidates": taps,
        "ledger": {"pieces": len(pieces), "views": len(view_list), "duplicates": len(duplicates),
                   "unsupported": len(unsupported), "annotations": len(annotations), "homeless": len(homeless)},
    }


def _png(d, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig, ax = plt.subplots(figsize=(16, 12), dpi=100)
    cmap = plt.get_cmap("tab20")
    home_color = {v["id"]: cmap(k % 20) for k, v in enumerate(d["views"])}
    for p in d["pieces"]:
        col = home_color.get(p["home"], "k")
        if p["type"] == "LINE":
            ax.add_collection(LineCollection([[p["start"], p["end"]]], colors=[col], linewidths=0.6))
        elif p["type"] == "ARC":
            a0, sw = p["start_angle"], (p["end_angle"] - p["start_angle"]) % 360
            pts = [(p["center"][0] + p["radius"] * math.cos(math.radians(a0 + sw * k / 24)),
                    p["center"][1] + p["radius"] * math.sin(math.radians(a0 + sw * k / 24))) for k in range(25)]
            ax.add_collection(LineCollection([pts], colors=[col], linewidths=0.6))
        elif p["type"] == "CIRCLE":
            ax.add_patch(plt.Circle(p["center"], p["radius"], fill=False, color=col, linewidth=0.8))
    for v in d["views"]:
        if v["bbox"]:
            ax.annotate(v["id"], (v["bbox"][0], v["bbox"][3]), fontsize=8, color=home_color[v["id"]])
    ax.autoscale()
    ax.set_aspect("equal")
    fig.savefig(out)


def summary(d: dict) -> dict:
    keys = ("id", "kind", "size", "bbox", "holes_by_dia", "arc_radii", "colors", "linetypes")
    layers = Counter(p["layer"] for p in d["pieces"])
    return {"file": d["source"]["file"], "insunits": d["source"]["insunits"], "profile": d["profile"],
            "ledger": d["ledger"], "layers": dict(sorted(layers.items())),
            "annotations": dict(Counter(a["type"] for a in d["annotations"])),
            "views_top_to_bottom": [{k: v[k] for k in keys if k in v} | {"pieces": len(v["piece_ids"])}
                                    for v in d["views"]],
            "tap_pair_candidates": len(d["tap_pair_candidates"]), "warnings": d["warnings"][:5],
            "note": d["source"]["note"] + " ELLIPSE/SPLINE stay UNKNOWN (FLAG), never simplified."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf")
    ap.add_argument("--out", help="digest JSON to write (needed by tools/dxf_assemble.py)")
    ap.add_argument("--png", help="optional overview image, coloured by home (needs matplotlib)")
    ap.add_argument("--profile", default="auto", choices=["auto", "catia", "generic"])
    ap.add_argument("--noise-mm", type=float, default=None, help="LINE-only groups smaller than this go to B_NOISE")
    a = ap.parse_args(argv)
    d = digest(a.dxf, a.profile, a.noise_mm)
    if a.out:
        Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.png:
        _png(d, a.png)
    print(json.dumps(summary(d), ensure_ascii=False, indent=1))
    return 0 if d["ledger"]["homeless"] == 0 else 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
