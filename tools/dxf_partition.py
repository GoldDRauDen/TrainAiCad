#!/usr/bin/env python3
"""Propose the member split of one part of a customer-DATA digest from its geometry; the AI confirms it against the PDF.

    python tools/dxf_partition.py digest.json --box X0 Y0 X1 Y1 --out draft.json      # or --view V02
    -> draft.json: {"members": [...], "unresolved": [...], "other": {...}}   (paste `members` into the dxf_assemble plan)
    python tools/dxf_partition.py digest.json --box X0 Y0 X1 Y1 --plan --out plan.json
    -> a whole dxf_assemble plan: members, every other piece excluded by its drawing style (centre / hidden / dimension
       layer-0 colour-0 / noise / outside the box, notes start "auto ... confirm against the PDF") and `todo` = what only
       the AI can decide (unresolved contours, rings concentric with a hole, unstyled pieces). Exit 1 while todo remains;
       dxf_assemble refuses the plan until every todo piece is a member or an exclusion with a reason.

Only geometry decides here, never a name or a note:
  * contour pieces = LINE / ARC / open native SPLINE-ELLIPSE, CONTINUOUS, not a dimension-style piece (layer 0, colour 0);
  * a closed simple loop is `outer` (largest, not inside another), `slot` (stadium: two equal tangent arcs + two parallel lines)
    or `cutout` (inside the outer); a component that is not one simple loop (T-junction, free end, shared edge) is `unresolved`
    with its pieces - the AI decides what it is (a pad outline, an overlapped neighbour, ...);
  * CIRCLEs become `hole` members grouped by diameter (concentric pairs are listed as tap candidates);
  * everything else in the box is counted by (layer, colour, linetype, type) in `other` - exclusion reasons stay the AI's call.
It never edits a piece. A --plan exclusion is a drawing-style class only (never a size or a name); the AI confirms it.
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
    container = outer["poly"] if outer else None
    bigger = []   # an unresolved component larger than every loop is the real outline: no outer guess, nest inside it
    for u in unresolved:
        xy = [q for s in segs if s["id"] in u["pieces"] for q in (s["start"], s["end"])]
        x0, y0, x1, y1 = min(q[0] for q in xy), min(q[1] for q in xy), max(q[0] for q in xy), max(q[1] for q in xy)
        if (x1 - x0) * (y1 - y0) > (outer["area"] if outer else 0):
            bigger.append(((x1 - x0) * (y1 - y0), [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], u))
    if bigger:
        _, container, u = max(bigger, key=lambda b: b[0])
        u["why"] += "; the largest contour: the outer outline, decide its pieces (no outer member guessed)"
        outer = None
    if outer:
        members.append({"id": "OUT", "role": "outer", "pieces": outer["pieces"]})
    k_slot = k_cut = 0
    for l in loops:
        if l is outer:
            continue
        if container and not _inside(l["poly"][0], container):
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


AUTO = "auto (dxf_partition --plan), confirm against the PDF: "
CENTRE_LT = ("CENTER", "CENTER2", "CENTERX2", "DASHDOT", "DASHDOT2", "DASHDOTX2")
HIDDEN_LT = ("DASHED", "DASHED2", "DASHEDX2", "HIDDEN", "HIDDEN2", "HIDDENX2", "PHANTOM", "PHANTOM2")


def _where(p):
    if p.get("bbox"):
        b = p["bbox"]
        return [[b[0], b[1]], [b[2], b[3]]]
    if p.get("curve"):
        return [p["curve"]["start"], p["curve"]["end"]]
    return _pts(p)


def _auto_class(p, centres, arc_centres=frozenset()):
    """Exclusion class a job would give this leftover piece by its drawing style alone, else None (the AI decides)."""
    lt = str(p.get("linetype", "")).upper()
    if p["type"] == "ARC" and (round(p["center"][0], 3), round(p["center"][1], 3)) in centres:
        return None   # concentric with a hole: tap nominal ring or not is the AI's call (HOLE_TAP.md §1)
    if p.get("home") == "B_NOISE":
        return "EXPLODED_TEXT_OR_DIM_NOISE", "digest noise bucket (exploded text / dimension strokes)"
    if lt in CENTRE_LT:
        return "CENTRE_OR_CONSTRUCTION", "centre line (linetype " + lt + ")"
    if lt in HIDDEN_LT:
        return "HIDDEN_OR_PROJECTION_ONLY", "hidden / projection line (linetype " + lt + "); a bend line -> member role bend"
    if p.get("layer") == "0" and p.get("color") == 0 and p["type"] != "CIRCLE":
        return "DIMENSION_GRAPHIC", "dimension arrow / leader (layer 0 colour 0)"
    if p["type"] == "POINT" and (round(p["point"][0], 3), round(p["point"][1], 3)) in centres | arc_centres:
        return "CENTRE_OR_CONSTRUCTION", "centre POINT of a hole / arc (a PIERCING point -> member role point)"
    return None


def draft_plan(digest: dict, box, origin=None) -> dict:
    """A dxf_assemble plan for the part in `box`: the partition members, every other piece excluded by an automatic
    style class (centre / hidden / dimension / noise / outside the box) and the rest in `todo` for the AI. dxf_assemble
    refuses the plan until `todo` is empty (each todo piece moved to a member or an exclusion with a reason)."""
    res = partition(digest, box)
    members = res["members"]
    used = {i for m in members for i in m["pieces"]}
    pieces = {p["id"]: p for p in digest["pieces"]} | {u["id"]: u for u in digest["unsupported"]}
    def in_box(p):
        if p.get("bbox") or p.get("curve"):   # unsupported entity: wholly inside
            return all(box[0] <= q[0] <= box[2] and box[1] <= q[1] <= box[3] for q in _where(p))
        return bool(_pts(p)) and _in_box(p, box)
    inside = {pid for pid, p in pieces.items() if in_box(p)}
    nowhere = {pid for pid, p in pieces.items() if not _where(p)}
    def centres_of(kind):
        return {(round(p["center"][0], 3), round(p["center"][1], 3)) for pid, p in pieces.items()
                if pid in inside and p.get("type") == kind}
    centres, arc_centres = centres_of("CIRCLE"), centres_of("ARC")
    excluded, todo, classes = [], [], defaultdict(list)
    for v in digest["views"]:
        ids = [i for i in v["piece_ids"] if i not in used and not pieces.get(i, {}).get("duplicate_of")]
        if v["id"] == "B_NOISE":
            excluded.append({"reason": "EXPLODED_TEXT_OR_DIM_NOISE", "bucket": "B_NOISE", "note": AUTO + "digest noise bucket"})
        elif ids and not any(i in inside or i in nowhere for i in ids):
            excluded.append({"reason": "VIEW_NOT_USED", "view": v["id"], "note": AUTO + "no piece inside this part's box"})
        else:
            for i in ids:
                p = pieces[i]
                if i in nowhere:
                    classes[("OTHER", "unsupported entity without geometry (text / hatch / block), listed by the digest")].append(i)
                elif i not in inside:
                    classes[("OTHER", "outside this part's box (another view / part of the sheet)")].append(i)
                elif "type" in p and p["type"] in ("LINE", "ARC", "CIRCLE", "POINT") and _auto_class(p, centres, arc_centres):
                    classes[_auto_class(p, centres, arc_centres)].append(i)
                else:
                    todo.append(i)
    for (reason, note), ids in classes.items():
        excluded.append({"reason": reason, "note": AUTO + note, "pieces": sorted(ids)})
    todo_set = set(todo)
    items = [{"why": u["why"], "pieces": [i for i in u["pieces"] if i in todo_set]} for u in res["unresolved"]]
    in_comp = {i for it in items for i in it["pieces"]}
    groups = defaultdict(list)
    for i in todo:
        if i not in in_comp:
            p = pieces[i]
            groups[(p.get("type"), p.get("layer"), p.get("color"), p.get("linetype"))].append(i)
    items += [{"why": "no style class: " + "|".join(map(str, k)), "pieces": sorted(v)} for k, v in groups.items()]
    plan = {"source_sha256": digest["source"]["sha256"], "members": members, "excluded": excluded,
            "todo": [it for it in items if it["pieces"]], "tap_candidates": res["tap_candidates"]}
    outer = next((m for m in members if m["role"] == "outer"), None)
    if origin is None and outer:
        xy = [q for i in outer["pieces"] for q in _pts(pieces[i])]
        origin = (min(q[0] for q in xy), min(q[1] for q in xy))
    if origin is not None:
        plan["transform"] = {"translate": [-origin[0], -origin[1]]}
    return plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("digest")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--box", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    g.add_argument("--view", help="a view id of the digest (its bbox is the box)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", action="store_true", help="write a whole dxf_assemble plan (members + auto exclusions + todo)")
    a = ap.parse_args(argv)
    d = json.loads(Path(a.digest).read_text(encoding="utf-8-sig"))
    box = a.box or next(v["bbox"] for v in d["views"] if v["id"] == a.view)
    if a.plan:
        plan = draft_plan(d, box)
        Path(a.out).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"members": {m["id"]: len(m["pieces"]) for m in plan["members"]},
                          "excluded": {f"{e['reason']} {e.get('view') or e.get('bucket') or ''}".strip():
                                       len(e.get("pieces", [])) or "view" for e in plan["excluded"]},
                          "todo": [{**t, "pieces": t["pieces"][:12], "n": len(t["pieces"])} for t in plan["todo"]]},
                         ensure_ascii=False, indent=1))
        return 0 if not plan["todo"] else 1
    res = partition(d, box)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"members": {m["id"]: len(m["pieces"]) for m in res["members"]}, "unresolved": len(res["unresolved"]),
                      "tap_candidates": len(res["tap_candidates"]), "other": res["other"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
