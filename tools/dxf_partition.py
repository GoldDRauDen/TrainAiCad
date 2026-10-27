#!/usr/bin/env python3
"""Propose the member split of one part of a customer-DATA digest from its geometry; the AI confirms it against the PDF.

    python tools/dxf_partition.py digest.json --box X0 Y0 X1 Y1 --out draft.json      # or --view V02
    -> draft.json: {"members": [...], "unresolved": [...], "other": {...}}   (paste `members` into the dxf_assemble plan)

Only geometry decides here, never a name or a note:
  * contour pieces = LINE / ARC / open native SPLINE-ELLIPSE, CONTINUOUS, not a dimension-style piece (layer 0, colour 0);
  * a closed simple loop is `outer` (largest, not inside another), `slot` (stadium: two equal tangent arcs + two parallel lines)
    or `cutout` (inside the outer); a component that is not one simple loop (T-junction, free end, shared edge) is `unresolved`
    with its pieces - the AI decides what it is (a pad outline, an overlapped neighbour, ...);
  * CIRCLEs become `hole` members grouped by diameter (concentric pairs are listed as tap candidates);
  * everything else in the box is counted by (layer, colour, linetype, type) in `other` - exclusion reasons stay the AI's call.
It never edits a piece and never writes a plan the assembler would accept without the exclusions the AI adds.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxf_digest import pieces_sha256  # noqa: E402

JOIN_TOL = 1e-3


def _pts(p):
    return [x for x in (p.get("start"), p.get("end"), p.get("center"), p.get("point")) if x]


def _in_box(p, box):
    q = _pts(p)
    inside = [box[0] <= x[0] <= box[2] and box[1] <= x[1] <= box[3] for x in q]
    return all(inside) if p["type"] == "LINE" else any(inside)


def _contour(p):
    return (p["type"] in ("LINE", "ARC") and p["linetype"] == "CONTINUOUS" and not p.get("duplicate_of")
            and p.get("home") not in ("B_NOISE", "B_DUPLICATE") and not (p["layer"] == "0" and p["color"] == 0))


def _components(segs):
    par = {}

    def find(a):
        while par.setdefault(a, a) != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def key(pt):
        return (round(pt[0] / JOIN_TOL), round(pt[1] / JOIN_TOL))
    for s in segs:
        par[find(key(s["start"]))] = find(key(s["end"]))
    out = defaultdict(list)
    for s in segs:
        out[find(key(s["start"]))].append(s)
    return list(out.values())


def _is_simple_loop(comp):
    deg = Counter()
    for s in comp:
        for e in ("start", "end"):
            deg[(round(s[e][0] / JOIN_TOL), round(s[e][1] / JOIN_TOL))] += 1
    return len(comp) >= 2 and all(d == 2 for d in deg.values())


def _polygon(comp):
    """Ordered sample points of a simple loop (arcs sampled) for area / nesting."""
    segs = list(comp)
    order = [segs.pop(0)]
    here = order[0]["end"]
    while segs:
        nxt = next((s for s in segs if math.dist(s["start"], here) <= JOIN_TOL or math.dist(s["end"], here) <= JOIN_TOL), None)
        if nxt is None:
            break
        segs.remove(nxt)
        order.append(nxt if math.dist(nxt["start"], here) <= JOIN_TOL else {**nxt, "start": nxt["end"], "end": nxt["start"], "_rev": True})
        here = order[-1]["end"]
    pts = []
    for s in order:
        if s["type"] == "ARC":
            a0 = math.radians(s["start_angle"])
            sw = math.radians((s["end_angle"] - s["start_angle"]) % 360 or 360)
            if s.get("_rev"):
                a0, sw = a0 + sw, -sw
            pts += [(s["center"][0] + s["radius"] * math.cos(a0 + sw * k / 8), s["center"][1] + s["radius"] * math.sin(a0 + sw * k / 8))
                    for k in range(8)]
        else:
            pts.append(tuple(s["start"]))
    return pts


def _area(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def _inside(pt, poly):
    ins = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > pt[1]) != (b[1] > pt[1]) and pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]:
            ins = not ins
    return ins


def _is_stadium(comp):
    arcs = [s for s in comp if s["type"] == "ARC"]
    lines = [s for s in comp if s["type"] == "LINE"]
    if len(comp) != 4 or len(arcs) != 2 or len(lines) != 2 or abs(arcs[0]["radius"] - arcs[1]["radius"]) > 1e-4:
        return False
    sweeps = [(a["end_angle"] - a["start_angle"]) % 360 for a in arcs]
    d = [(s["end"][0] - s["start"][0], s["end"][1] - s["start"][1]) for s in lines]
    cross = d[0][0] * d[1][1] - d[0][1] * d[1][0]
    return all(abs(sw - 180) < 1e-3 for sw in sweeps) and abs(cross) <= 1e-6 * math.hypot(*d[0]) * math.hypot(*d[1])


def partition(digest: dict, box) -> dict:
    if digest.get("pieces_sha256") != pieces_sha256(digest):
        raise ValueError("DIGEST_PIECES_ALTERED")
    pieces = [p for p in digest["pieces"] if _in_box(p, box)]
    curves_in = [u for u in digest["unsupported"] if u.get("curve") and u.get("bbox") and
                 box[0] <= u["bbox"][0] and u["bbox"][2] <= box[2] and box[1] <= u["bbox"][1] and u["bbox"][3] <= box[3]]
    segs = [p for p in pieces if _contour(p)]
    segs += [{"id": u["id"], "type": u["curve"]["kind"], "layer": u["layer"], "color": u.get("color", 256), "linetype": "CONTINUOUS",
              "start": u["curve"]["start"], "end": u["curve"]["end"]} for u in curves_in]
    loops, unresolved = [], []
    for comp in _components(segs):
        if _is_simple_loop(comp):
            poly = _polygon(comp)
            loops.append({"pieces": sorted(s["id"] for s in comp), "poly": poly, "area": _area(poly), "stadium": _is_stadium(comp)})
        else:
            unresolved.append({"pieces": sorted(s["id"] for s in comp), "why": "not one simple closed loop (T-junction, free end or shared edge)"})
    members = []
    loops.sort(key=lambda l: -l["area"])
    outer = next((l for l in loops if not l["stadium"]), None)
    if outer:
        members.append({"id": "OUT", "role": "outer", "pieces": outer["pieces"]})
    k_slot = k_cut = 0
    for l in loops:
        if l is outer:
            continue
        if outer and not _inside(l["poly"][0], outer["poly"]):
            unresolved.append({"pieces": l["pieces"], "why": "closed loop outside the outer contour"})
        elif l["stadium"]:
            k_slot += 1
            members.append({"id": f"SL{k_slot}", "role": "slot", "pieces": l["pieces"]})
        else:
            k_cut += 1
            members.append({"id": f"PK{k_cut:02d}", "role": "cutout", "pieces": l["pieces"]})
    holes = defaultdict(list)
    for p in pieces:
        if p["type"] == "CIRCLE" and not p.get("duplicate_of"):
            holes[round(2 * p["radius"], 4)].append(p["id"])
    for dia, ids in sorted(holes.items()):
        members.append({"id": f"HD{dia:g}".replace(".", "_"), "role": "hole", "pieces": sorted(ids), "dia": dia})
    centres = defaultdict(list)
    for p in pieces:
        if p["type"] == "CIRCLE":
            centres[(round(p["center"][0], 3), round(p["center"][1], 3))].append(round(2 * p["radius"], 4))
    taps = [{"centre": list(c), "dia": sorted(v)} for c, v in centres.items() if len(set(v)) > 1]
    used = {i for m in members for i in m["pieces"]} | {i for u in unresolved for i in u["pieces"]}
    other = Counter((p["layer"], p["color"], p["linetype"], p["type"]) for p in pieces if p["id"] not in used and p["type"] != "CIRCLE")
    return {"source_sha256": digest["source"]["sha256"], "box": list(box), "members": members, "unresolved": unresolved,
            "tap_candidates": taps, "other": {"|".join(map(str, k)): v for k, v in sorted(other.items(), key=lambda kv: -kv[1])}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("digest")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--box", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    g.add_argument("--view", help="a view id of the digest (its bbox is the box)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    d = json.loads(Path(a.digest).read_text(encoding="utf-8-sig"))
    box = a.box or next(v["bbox"] for v in d["views"] if v["id"] == a.view)
    res = partition(d, box)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"members": {m["id"]: len(m["pieces"]) for m in res["members"]}, "unresolved": len(res["unresolved"]),
                      "tap_candidates": len(res["tap_candidates"]), "other": res["other"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
