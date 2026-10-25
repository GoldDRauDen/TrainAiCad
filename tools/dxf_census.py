#!/usr/bin/env python3
"""Physical-curve census of a customer DXF (rules/DATA_DXF.md §1): what is really in the DATA.

    python tools/dxf_census.py data.dxf                     # compact summary per layer
    python tools/dxf_census.py data.dxf --out decoded.json  # + every decoded LINE/ARC/CIRCLE/POINT piece

Every POLYLINE/LWPOLYLINE segment is decoded with its start-vertex bulge (ARC, never the chord),
closed polylines include the last->first segment, INSERTs are exploded through their transform.
Holes are summarised by diameter, arcs by radius, so families and R/C can be checked against the PDF.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

GEOM = {"LINE", "ARC", "CIRCLE", "POINT", "ELLIPSE", "SPLINE"}
ANNOT = {"TEXT", "MTEXT", "DIMENSION", "LEADER", "MULTILEADER", "HATCH", "ATTRIB", "ATTDEF"}


def _r(v: float, nd: int = 4) -> float:
    return round(float(v), nd) + 0.0


def _pieces(entity, depth: int = 0):
    """Yield (piece, source_type, bulged) for one modelspace entity, fully decoded."""
    t = entity.dxftype()
    if t in ("LWPOLYLINE", "POLYLINE"):
        bulges = []
        if t == "LWPOLYLINE":
            bulges = [p[4] for p in entity.get_points("xyseb")]
        else:
            bulges = [v.dxf.get("bulge", 0.0) for v in entity.vertices]
        bulged = any(abs(b) > 1e-12 for b in bulges)
        for v in entity.virtual_entities():
            yield v, t, bulged
    elif t == "INSERT" and depth < 8:
        for v in entity.virtual_entities():
            yield from _pieces(v, depth + 1)
    else:
        yield entity, t, False


def _bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return [_r(min(xs), 3), _r(min(ys), 3), _r(max(xs), 3), _r(max(ys), 3)] if xs else None


def _piece_bbox(r):
    if r["type"] == "LINE":
        (x0, y0), (x1, y1) = r["start"], r["end"]
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    if r["type"] in ("ARC", "CIRCLE"):
        (cx, cy), rad = r["center"], r["radius"]
        return cx - rad, cy - rad, cx + rad, cy + rad
    if r["type"] == "POINT":
        x, y = r["point"]
        return x, y, x, y
    return None


def _clusters(decoded, gap: float = 1.0):
    """Connected groups of geometry (touching within `gap` mm): one per part in a stacked composite."""
    boxes = [(i, b) for i, b in ((i, _piece_bbox(r)) for i, r in enumerate(decoded)) if b]
    parent = {i: i for i, _ in boxes}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    cell = 50.0
    grid = defaultdict(list)
    for i, (x0, y0, x1, y1) in boxes:
        for gx in range(int(math.floor((x0 - gap) / cell)), int(math.floor((x1 + gap) / cell)) + 1):
            for gy in range(int(math.floor((y0 - gap) / cell)), int(math.floor((y1 + gap) / cell)) + 1):
                grid[(gx, gy)].append(i)
    bb = dict(boxes)
    for members in grid.values():
        for a_i, a in enumerate(members):
            ax0, ay0, ax1, ay1 = bb[a]
            for b in members[a_i + 1:]:
                bx0, by0, bx1, by1 = bb[b]
                if ax0 - gap <= bx1 and bx0 - gap <= ax1 and ay0 - gap <= by1 and by0 - gap <= ay1:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[ra] = rb
    groups = defaultdict(list)
    for i, _ in boxes:
        groups[find(i)].append(i)

    def gbox(ids):
        x0, y0, x1, y1 = zip(*(bb[i] for i in ids))
        return min(x0), min(y0), max(x1), max(y1)
    # holes/slots/marks inside an outline belong to that part: merge into the smallest containing group
    merged = sorted(groups.values(), key=lambda ids: (lambda b: (b[2] - b[0]) * (b[3] - b[1]))(gbox(ids)))
    final = []
    for k, ids in enumerate(merged):
        x0, y0, x1, y1 = gbox(ids)
        host = next((h for h in merged[k + 1:] if (lambda b: b[0] - gap <= x0 and b[1] - gap <= y0 and
                                                   x1 <= b[2] + gap and y1 <= b[3] + gap)(gbox(h))), None)
        if host is not None:
            host.extend(ids)
        else:
            final.append(ids)
    out = []
    for ids in final:
        xs0, ys0, xs1, ys1 = zip(*(bb[i] for i in ids))
        types = Counter(decoded[i]["type"] for i in ids)
        holes = Counter(_r(2 * decoded[i]["radius"], 3) for i in ids if decoded[i]["type"] == "CIRCLE")
        radii = Counter(_r(decoded[i]["radius"], 3) for i in ids if decoded[i]["type"] == "ARC")
        colors = Counter(decoded[i]["color"] for i in ids)
        out.append({"bbox": [_r(min(xs0), 3), _r(min(ys0), 3), _r(max(xs1), 3), _r(max(ys1), 3)],
                    "size": [_r(max(xs1) - min(xs0), 3), _r(max(ys1) - min(ys0), 3)],
                    "geometry": dict(types), "holes_by_dia": {f"Ø{d:g}": n for d, n in sorted(holes.items())},
                    "arc_radii": {f"R{r:g}": n for r, n in sorted(radii.items())},
                    "colors": {str(k): v for k, v in sorted(colors.items())}})
    out.sort(key=lambda c: -c["bbox"][3])
    return out


def census(path: str) -> dict:
    doc = ezdxf.readfile(path)
    layers: dict[str, dict] = defaultdict(lambda: {"types": Counter(), "holes_by_dia": Counter(),
                                                    "arc_radii": Counter(), "points": [], "bulged_polylines": 0,
                                                    "closed_polylines": 0, "annotations": Counter()})
    decoded, unsupported = [], Counter()
    for e in doc.modelspace():
        t = e.dxftype()
        lay = layers[e.dxf.get("layer", "0")]
        if t in ANNOT:
            lay["annotations"][t] += 1
            continue
        if t in ("LWPOLYLINE", "POLYLINE"):
            if e.is_closed if t == "POLYLINE" else e.closed:
                lay["closed_polylines"] += 1
        any_bulge = False
        for piece, src, bulged in _pieces(e):
            any_bulge = any_bulge or bulged
            pt = piece.dxftype()
            player = layers[piece.dxf.get("layer", e.dxf.get("layer", "0"))]
            if pt in ANNOT:
                player["annotations"][pt] += 1
                continue
            if pt not in GEOM:
                unsupported[pt] += 1
                continue
            player["types"][pt] += 1
            rec = {"type": pt, "layer": piece.dxf.get("layer", "0"), "from": src, "color": piece.dxf.get("color", 256)}
            if pt == "LINE":
                a, b = piece.dxf.start, piece.dxf.end
                rec.update(start=[_r(a.x), _r(a.y)], end=[_r(b.x), _r(b.y)])
                player["points"] += [(a.x, a.y), (b.x, b.y)]
            elif pt == "ARC":
                c, r = piece.dxf.center, piece.dxf.radius
                rec.update(center=[_r(c.x), _r(c.y)], radius=_r(r), start_angle=_r(piece.dxf.start_angle, 3),
                           end_angle=_r(piece.dxf.end_angle, 3))
                player["arc_radii"][_r(r, 3)] += 1
                player["points"] += [(p.x, p.y) for p in (piece.start_point, piece.end_point)]
                if src != "ARC":
                    rec["bulge_decoded"] = True
            elif pt == "CIRCLE":
                c, r = piece.dxf.center, piece.dxf.radius
                rec.update(center=[_r(c.x), _r(c.y)], radius=_r(r))
                player["holes_by_dia"][_r(2 * r, 3)] += 1
                player["points"] += [(c.x - r, c.y - r), (c.x + r, c.y + r)]
            elif pt == "POINT":
                p = piece.dxf.location
                rec.update(point=[_r(p.x), _r(p.y)])
                player["points"].append((p.x, p.y))
            else:
                unsupported[pt] += 1  # ELLIPSE / SPLINE: keep UNKNOWN, never flatten
            if bulged:
                rec["in_bulged_polyline"] = True
            decoded.append(rec)
        if any_bulge:
            lay["bulged_polylines"] += 1
    out_layers = {}
    for name, lay in sorted(layers.items()):
        if not (lay["types"] or lay["annotations"]):
            continue
        out_layers[name] = {
            "geometry": dict(lay["types"]),
            "bbox": _bbox(lay["points"]),
            "holes_by_dia": {f"Ø{d:g}": n for d, n in sorted(lay["holes_by_dia"].items())},
            "arc_radii": {f"R{r:g}": n for r, n in sorted(lay["arc_radii"].items())},
            "closed_polylines": lay["closed_polylines"],
            "bulged_polylines": lay["bulged_polylines"],
            "annotations": dict(lay["annotations"]),
        }
    clusters = _clusters(decoded)
    units = {0: "unitless", 1: "inch", 4: "mm"}.get(doc.header.get("$INSUNITS", 0), str(doc.header.get("$INSUNITS")))
    return {"file": path, "insunits": units, "layers": out_layers, "clusters_top_to_bottom": clusters,
            "unsupported": dict(unsupported),
            "note": ("$INSUNITS is metadata: prove real units against PDF dimensions. ELLIPSE/SPLINE stay UNKNOWN "
                     "(FLAG), never simplified."),
            "_decoded": decoded}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf")
    ap.add_argument("--out", help="write every decoded piece to this JSON file")
    a = ap.parse_args(argv)
    res = census(a.dxf)
    decoded = res.pop("_decoded")
    if a.out:
        Path(a.out).write_text(json.dumps(decoded, ensure_ascii=False, indent=0), encoding="utf-8")
        res["decoded_file"] = a.out
    res["decoded_pieces"] = len(decoded)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
