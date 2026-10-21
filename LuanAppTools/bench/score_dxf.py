"""Compare a produced DXF with a reference DXF (a human calibration aid).

The reference is opened only here and never reaches a job. Parts are paired from top to
bottom; every pair may be translated and rotated by 0/90/180/270 degrees. A difference
counts as a match only when it is strictly below the tolerance (the repository's
reference-audit rule, references/REFERENCE_CALIBRATION_AUDIT.md section 2.4).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import ezdxf

DEFAULT_TOL = 0.01
DEFAULT_GAP = 50.0
LEVELS = (0.01, 0.1, 1.0)
LOOSE = 1.0
ROTATIONS = (0, 90, 180, 270)
VOTE_BIN = 0.5
MAX_LISTED = 25
KEYPOINT_CAP = 160
EPS = 1e-9  # "strictly below": 0.0099999999999 must not slip under 0.01 through float noise
META_LAYERS = {"AI_META"}
ANNOTATIONS = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "LEADER", "MLEADER", "VIEWPORT", "IMAGE"}


@dataclass(frozen=True)
class Prim:
    kind: str  # LINE (x1,y1,x2,y2) | ARC (cx,cy,r,start,sweep) | CIRCLE (cx,cy,r) | POINT (x,y)
    cat: str   # CUT | BEND | KEGAKI | GREEN | PREVIEW
    v: tuple


# ----------------------------------------------------------------------------- extraction

def _layer_attr(doc, name, attr, default):
    try:
        return getattr(doc.layers.get(name).dxf, attr)
    except Exception:
        return default


def _category(doc, entity):
    layer = entity.dxf.layer
    color = entity.dxf.get("color", 256)
    if color in (256, 0):
        color = abs(_layer_attr(doc, layer, "color", 7))
    linetype = str(entity.dxf.get("linetype", "BYLAYER")).upper()
    if linetype == "BYLAYER":
        linetype = str(_layer_attr(doc, layer, "linetype", "CONTINUOUS")).upper()
    if "DASH" in linetype:
        return "BEND"
    return {1: "KEGAKI", 3: "GREEN", 6: "PREVIEW"}.get(color, "CUT")


def _expand(doc, entity, out, skipped, depth=0):
    kind = entity.dxftype()
    if entity.dxf.layer.upper() in META_LAYERS or kind in ANNOTATIONS:
        return
    if kind == "LINE":
        s, e = entity.dxf.start, entity.dxf.end
        if math.hypot(e.x - s.x, e.y - s.y) > 1e-9:
            out.append(Prim("LINE", _category(doc, entity), (s.x, s.y, e.x, e.y)))
    elif kind == "ARC":
        c, r = entity.dxf.center, entity.dxf.radius
        start = entity.dxf.start_angle % 360.0
        sweep = (entity.dxf.end_angle % 360.0 - start) % 360.0
        if sweep < 1e-9 or sweep > 360.0 - 1e-6:
            out.append(Prim("CIRCLE", _category(doc, entity), (c.x, c.y, r)))
        else:
            out.append(Prim("ARC", _category(doc, entity), (c.x, c.y, r, start, sweep)))
    elif kind == "CIRCLE":
        c = entity.dxf.center
        out.append(Prim("CIRCLE", _category(doc, entity), (c.x, c.y, entity.dxf.radius)))
    elif kind == "POINT":
        p = entity.dxf.location
        out.append(Prim("POINT", _category(doc, entity), (p.x, p.y)))
    elif kind in ("LWPOLYLINE", "POLYLINE", "INSERT") and depth < 4:
        for child in entity.virtual_entities():
            _expand(doc, child, out, skipped, depth + 1)
    else:
        skipped[kind] += 1


def extract(path):
    doc = ezdxf.readfile(path)
    prims, skipped = [], Counter()
    for entity in doc.modelspace():
        _expand(doc, entity, prims, skipped)
    return prims, dict(skipped)


# ----------------------------------------------------------------------------- transforms

_ROT = {0: lambda x, y: (x, y), 90: lambda x, y: (-y, x), 180: lambda x, y: (-x, -y), 270: lambda x, y: (y, -x)}


def _rotate(p, deg):
    if deg == 0:
        return p
    f, v = _ROT[deg], p.v
    if p.kind == "LINE":
        return Prim("LINE", p.cat, (*f(v[0], v[1]), *f(v[2], v[3])))
    if p.kind == "ARC":
        return Prim("ARC", p.cat, (*f(v[0], v[1]), v[2], (v[3] + deg) % 360.0, v[4]))
    if p.kind == "CIRCLE":
        return Prim("CIRCLE", p.cat, (*f(v[0], v[1]), v[2]))
    return Prim("POINT", p.cat, f(v[0], v[1]))


def _shift(p, dx, dy):
    v = p.v
    if p.kind == "LINE":
        return Prim("LINE", p.cat, (v[0] + dx, v[1] + dy, v[2] + dx, v[3] + dy))
    if p.kind == "ARC":
        return Prim("ARC", p.cat, (v[0] + dx, v[1] + dy, *v[2:]))
    if p.kind == "CIRCLE":
        return Prim("CIRCLE", p.cat, (v[0] + dx, v[1] + dy, v[2]))
    return Prim("POINT", p.cat, (v[0] + dx, v[1] + dy))


def _weight(p):
    v = p.v
    if p.kind == "LINE":
        return math.hypot(v[2] - v[0], v[3] - v[1])
    if p.kind == "ARC":
        return math.radians(v[4]) * v[2]
    if p.kind == "CIRCLE":
        return 2 * math.pi * v[2]
    return 1.0


def _arc_points(v):
    cx, cy, r, start, sweep = v
    pts = [(cx + r * math.cos(math.radians(start + a)), cy + r * math.sin(math.radians(start + a)))
           for a in (0.0, sweep)]
    for quadrant in (0.0, 90.0, 180.0, 270.0, 360.0, 450.0):
        if 0.0 < (quadrant - start) % 360.0 < sweep:
            pts.append((cx + r * math.cos(math.radians(quadrant)), cy + r * math.sin(math.radians(quadrant))))
    return pts


def _bbox(p):
    v = p.v
    if p.kind == "LINE":
        return min(v[0], v[2]), min(v[1], v[3]), max(v[0], v[2]), max(v[1], v[3])
    if p.kind == "ARC":
        pts = _arc_points(v)
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        return min(xs), min(ys), max(xs), max(ys)
    if p.kind == "CIRCLE":
        return v[0] - v[2], v[1] - v[2], v[0] + v[2], v[1] + v[2]
    return v[0], v[1], v[0], v[1]


def _union_bbox(prims):
    boxes = [_bbox(p) for p in prims]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


# ----------------------------------------------------------------------------- normalisation

class _DisjointSet:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)

    def groups(self):
        out = defaultdict(list)
        for i in range(len(self.parent)):
            out[self.find(i)].append(i)
        return list(out.values())


def _lies_on(longer, shorter, tol):
    x1, y1, x2, y2 = longer
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length

    def perp(x, y):
        return abs((x - x1) * uy - (y - y1) * ux)

    if perp(shorter[0], shorter[1]) >= tol or perp(shorter[2], shorter[3]) >= tol:
        return False
    t1 = (shorter[0] - x1) * ux + (shorter[1] - y1) * uy
    t2 = (shorter[2] - x1) * ux + (shorter[3] - y1) * uy
    lo, hi = min(t1, t2), max(t1, t2)
    return lo <= length + tol and hi >= -tol


def _merge_lines(items, tol):
    sets = _DisjointSet(len(items))
    lengths = [math.hypot(v[2] - v[0], v[3] - v[1]) for v in items]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = (i, j) if lengths[i] >= lengths[j] else (j, i)
            if _lies_on(items[a], items[b], tol):
                sets.union(i, j)
    merged = []
    for group in sets.groups():
        base = max(group, key=lambda i: lengths[i])
        x1, y1, x2, y2 = items[base]
        ux, uy = (x2 - x1) / lengths[base], (y2 - y1) / lengths[base]
        ts = []
        for i in group:
            for x, y in ((items[i][0], items[i][1]), (items[i][2], items[i][3])):
                ts.append((x - x1) * ux + (y - y1) * uy)
        lo, hi = min(ts), max(ts)
        merged.append((x1 + ux * lo, y1 + uy * lo, x1 + ux * hi, y1 + uy * hi))
    return merged


def _merge_arcs(items, tol):
    sets = _DisjointSet(len(items))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if math.hypot(a[0] - b[0], a[1] - b[1]) < tol and abs(a[2] - b[2]) < tol:
                sets.union(i, j)
    merged, circles = [], []
    for group in sets.groups():
        cx, cy, r = items[group[0]][:3]
        gap = math.degrees(tol / r)
        spans = sorted((items[i][3], items[i][3] + items[i][4]) for i in group)
        joined = []
        for lo, hi in spans:
            if joined and lo - joined[-1][1] < gap:
                joined[-1][1] = max(joined[-1][1], hi)
            else:
                joined.append([lo, hi])
        while len(joined) > 1 and joined[-1][1] - 360.0 >= joined[0][0] - gap:
            last = joined.pop()
            joined[0][0] = min(joined[0][0], last[0] - 360.0)
            joined[0][1] = max(joined[0][1], last[1] - 360.0)
        for lo, hi in joined:
            if hi - lo >= 360.0 - gap:
                circles.append((cx, cy, r))
            else:
                merged.append((cx, cy, r, lo % 360.0, hi - lo))
    return merged, circles


def _dedupe(items, tol, same):
    kept = []
    for item in items:
        if not any(same(item, other, tol) for other in kept):
            kept.append(item)
    return kept


def _same_circle(a, b, tol):
    return math.hypot(a[0] - b[0], a[1] - b[1]) < tol and abs(a[2] - b[2]) < tol


def _same_point(a, b, tol):
    return math.hypot(a[0] - b[0], a[1] - b[1]) < tol


def _normalise(prims, tol):
    tol -= EPS
    out = []
    for cat in sorted({p.cat for p in prims}):
        of = lambda kind: [p.v for p in prims if p.cat == cat and p.kind == kind]  # noqa: E731
        out += [Prim("LINE", cat, v) for v in _merge_lines(of("LINE"), tol)]
        arcs, extra_circles = _merge_arcs(of("ARC"), tol)
        out += [Prim("ARC", cat, v) for v in arcs]
        out += [Prim("CIRCLE", cat, v) for v in _dedupe(of("CIRCLE") + extra_circles, tol, _same_circle)]
        out += [Prim("POINT", cat, v) for v in _dedupe(of("POINT"), tol, _same_point)]
    return out


# ----------------------------------------------------------------------------- matching

def _union_intervals(intervals, gap):
    merged = []
    for lo, hi in sorted(intervals):
        if merged and lo - merged[-1][1] < gap:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return merged


class _Match:
    def __init__(self):
        self.total_ref = self.total_res = self.matched_ref = self.matched_res = 0.0
        self.max_dev = 0.0
        self.missing, self.extra = [], []
        self.circles_ref = self.circles_matched = 0


def _line_cover(base, others, tol):
    x1, y1, x2, y2 = base
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    spans, dev = [], 0.0
    for o in others:
        d1 = abs((o[0] - x1) * uy - (o[1] - y1) * ux)
        d2 = abs((o[2] - x1) * uy - (o[3] - y1) * ux)
        if d1 < tol and d2 < tol:
            t1 = (o[0] - x1) * ux + (o[1] - y1) * uy
            t2 = (o[2] - x1) * ux + (o[3] - y1) * uy
            lo, hi = max(min(t1, t2), 0.0), min(max(t1, t2), length)
            if hi > lo:
                spans.append((lo, hi))
                dev = max(dev, d1, d2)
    merged = _union_intervals(spans, tol)
    full = len(merged) == 1 and merged[0][0] < tol and length - merged[0][1] < tol
    covered = length if full else sum(hi - lo for lo, hi in merged)
    return length, covered, full, dev, ((x1 + x2) / 2, (y1 + y2) / 2)


def _arc_cover(base, others, tol):
    cx, cy, r, start, sweep = base
    gap = math.degrees(tol / r)
    spans, dev = [], 0.0
    for o in others:
        centre, dr = math.hypot(o[0] - cx, o[1] - cy), abs(o[2] - r)
        if centre < tol and dr < tol:
            rel = (o[3] - start) % 360.0
            for shift in (0.0, -360.0):
                lo, hi = max(rel + shift, 0.0), min(rel + shift + o[4], sweep)
                if hi > lo:
                    spans.append((lo, hi))
                    dev = max(dev, centre, dr)
    merged = _union_intervals(spans, gap)
    full = len(merged) == 1 and merged[0][0] < gap and sweep - merged[0][1] < gap
    covered = sweep if full else sum(hi - lo for lo, hi in merged)
    mid = math.radians(start + sweep / 2)
    return sweep, covered, full, dev, (cx + r * math.cos(mid), cy + r * math.sin(mid)), math.radians(1.0) * r


def _record(out, side, cat, kind, length, at):
    target = out.missing if side == "ref" else out.extra
    target.append({"kind": kind, "category": cat, "length": round(length, 4), "at": [round(at[0], 3), round(at[1], 3)]})


def _match_kind(kind, cat, ref, res, tol, out):
    for side, base, others in (("ref", ref, res), ("res", res, ref)):
        for v in base:
            if kind == "LINE":
                length, covered, full, dev, at = _line_cover(v, others, tol)
                weight, matched = length, covered
            elif kind == "ARC":
                sweep, covered, full, dev, at, per_degree = _arc_cover(v, others, tol)
                weight, matched = math.radians(sweep) * v[2], math.radians(covered) * v[2]
            elif kind == "CIRCLE":
                hits = [o for o in others if _same_circle(v, o, tol)]
                full = bool(hits)
                dev = max([max(math.hypot(v[0] - o[0], v[1] - o[1]), abs(v[2] - o[2])) for o in hits] or [0.0])
                weight = matched = 2 * math.pi * v[2]
                matched = weight if full else 0.0
                at = (v[0], v[1])
                if side == "ref":
                    out.circles_ref += 1
                    out.circles_matched += int(full)
            else:
                hits = [o for o in others if _same_point(v, o, tol)]
                full = bool(hits)
                dev = max([math.hypot(v[0] - o[0], v[1] - o[1]) for o in hits] or [0.0])
                weight, matched, at = 1.0, (1.0 if full else 0.0), (v[0], v[1])
            if side == "ref":
                out.total_ref += weight
                out.matched_ref += matched
            else:
                out.total_res += weight
                out.matched_res += matched
            out.max_dev = max(out.max_dev, dev) if full or matched else out.max_dev
            if not full:
                _record(out, side, cat, kind, weight - matched, at)


def _match(ref, res, tol):
    tol -= EPS
    out = _Match()
    for cat in sorted({p.cat for p in ref} | {p.cat for p in res}):
        for kind in ("LINE", "ARC", "CIRCLE", "POINT"):
            r = [p.v for p in ref if p.cat == cat and p.kind == kind]
            s = [p.v for p in res if p.cat == cat and p.kind == kind]
            if r or s:
                _match_kind(kind, cat, r, s, tol, out)
    return out


# ----------------------------------------------------------------------------- alignment

def _keypoints(prims):
    pts = set()
    for p in prims:
        v = p.v
        if p.kind == "LINE":
            pts |= {(round(v[0], 6), round(v[1], 6)), (round(v[2], 6), round(v[3], 6))}
        elif p.kind == "ARC":
            pts |= {(round(v[0], 6), round(v[1], 6))}
            pts |= {(round(x, 6), round(y, 6)) for x, y in _arc_points(v)[:2]}
        else:
            pts.add((round(v[0], 6), round(v[1], 6)))
    pts = sorted(pts)
    if len(pts) > KEYPOINT_CAP:
        step = len(pts) / KEYPOINT_CAP
        pts = [pts[int(i * step)] for i in range(KEYPOINT_CAP)]
    return pts


def _candidates(ref, rotated):
    kr, ks = _keypoints(ref), _keypoints(rotated)
    votes = defaultdict(list)
    for fx, fy in kr:
        for rx, ry in ks:
            dx, dy = fx - rx, fy - ry
            votes[(round(dx / VOTE_BIN), round(dy / VOTE_BIN))].append((dx, dy))
    found = set()
    for cell in sorted(votes, key=lambda c: -len(votes[c]))[:4]:
        vectors = votes[cell]
        xs, ys = sorted(v[0] for v in vectors), sorted(v[1] for v in vectors)
        found.add((round(xs[len(xs) // 2], 9), round(ys[len(ys) // 2], 9)))
        mode = Counter((round(v[0], 6), round(v[1], 6)) for v in vectors).most_common(1)[0][0]
        found.add(mode)
    # Corner-anchored only: centring would let a size error be split between both sides
    # and hide it under the tolerance.
    a, b = _union_bbox(ref), _union_bbox(rotated)
    found.add((a[0] - b[0], a[1] - b[1]))
    found.add((a[2] - b[2], a[3] - b[3]))
    return found


def _align(ref, res, tol):
    """Best (rotation, dx, dy, loose_score). Loose score picks the geometry, strict breaks ties."""
    best = (-1.0, -1.0, 0, 0.0, 0.0)
    for rot in ROTATIONS:
        rotated = [_rotate(p, rot) for p in res]
        scored = []
        for dx, dy in _candidates(ref, rotated):
            m = _match(ref, [_shift(p, dx, dy) for p in rotated], LOOSE)
            scored.append((m.matched_ref + m.matched_res, dx, dy))
        top = max(s[0] for s in scored)
        for loose, dx, dy in scored:
            if loose < top * 0.98:
                continue
            m = _match(ref, [_shift(p, dx, dy) for p in rotated], tol)
            candidate = (loose, m.matched_ref + m.matched_res, rot, dx, dy)
            if candidate[:2] > best[:2]:
                best = candidate
    return best[2], best[3], best[4], best[0]


# ----------------------------------------------------------------------------- clusters

def _clusters(prims, gap):
    if not prims:
        return []
    boxes = [_bbox(p) for p in prims]
    half = gap / 2
    cell = max(gap, 1.0)
    grid = defaultdict(list)
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        for gx in range(int((x0 - half) // cell), int((x1 + half) // cell) + 1):
            for gy in range(int((y0 - half) // cell), int((y1 + half) // cell) + 1):
                grid[(gx, gy)].append(i)
    sets = _DisjointSet(len(prims))
    for members in grid.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                i, j = members[a], members[b]
                bi, bj = boxes[i], boxes[j]
                if bi[0] - half <= bj[2] + half and bj[0] - half <= bi[2] + half \
                        and bi[1] - half <= bj[3] + half and bj[1] - half <= bi[3] + half:
                    sets.union(i, j)
    groups = [[prims[i] for i in g] for g in sets.groups()]
    structural = [g for g in groups if any(p.kind in ("LINE", "ARC") for p in g)]
    floating = [g for g in groups if g not in structural]
    for group in floating:
        cx, cy = _union_bbox(group)[:2]
        for host in structural:
            x0, y0, x1, y1 = _union_bbox(host)
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                host.extend(group)
                break
        else:
            structural.append(group)
    out = []
    for g in structural:
        box = _union_bbox(g)
        out.append({"prims": g, "bbox": box})
    out.sort(key=lambda c: (-(c["bbox"][1] + c["bbox"][3]) / 2, c["bbox"][0]))
    for index, c in enumerate(out):
        c["index"] = index
    return out


def _describe(cluster):
    return {"index": cluster["index"], "bbox": [round(v, 3) for v in cluster["bbox"]],
            "entities": len(cluster["prims"])}


# ----------------------------------------------------------------------------- pairing

def _pairs(weights, n, m):
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1] + weights[i - 1][j - 1])
    pairs, i, j = [], n, m
    while i > 0 and j > 0:
        if weights[i - 1][j - 1] > 0 and abs(dp[i][j] - (dp[i - 1][j - 1] + weights[i - 1][j - 1])) < 1e-9:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif abs(dp[i][j] - dp[i - 1][j]) < 1e-9:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


def _fill_gaps(pairs, n, m):
    anchors = [(-1, -1), *pairs, (n, m)]
    result = list(pairs)
    for (a_i, a_j), (b_i, b_j) in zip(anchors, anchors[1:]):
        refs, ress = list(range(a_i + 1, b_i)), list(range(a_j + 1, b_j))
        result += list(zip(refs, ress))
    return sorted(result)


# ----------------------------------------------------------------------------- report

def _levels_for(tol):
    return sorted({round(t, 9) for t in (*LEVELS, tol)})


def _part_report(index, ref_cluster, res_cluster, tol):
    ref = _normalise(ref_cluster["prims"], tol)
    res = _normalise(res_cluster["prims"], tol)
    rot, dx, dy, _ = _align(ref, res, tol)
    placed = [_shift(_rotate(p, rot), dx, dy) for p in res]
    levels = {}
    for level in _levels_for(tol):
        m = _match(_normalise(ref_cluster["prims"], level), _normalise(
            [_shift(_rotate(p, rot), dx, dy) for p in res_cluster["prims"]], level), level)
        levels[f"{level:g}"] = {
            "recall": round(m.matched_ref / m.total_ref, 6) if m.total_ref else 0.0,
            "precision": round(m.matched_res / m.total_res, 6) if m.total_res else 0.0,
        }
    m = _match(ref, placed, tol)
    recall = m.matched_ref / m.total_ref if m.total_ref else 0.0
    precision = m.matched_res / m.total_res if m.total_res else 0.0
    exact = not m.missing and not m.extra and m.total_ref > 0
    status = "MATCH" if exact else ("PARTIAL" if recall >= 0.5 else "DIFF")
    categories = {}
    for cat in sorted({p.cat for p in ref} | {p.cat for p in placed}):
        categories[cat] = {
            "reference": sum(1 for p in ref if p.cat == cat),
            "result": sum(1 for p in placed if p.cat == cat),
            "missing": sum(1 for item in m.missing if item["category"] == cat),
            "extra": sum(1 for item in m.extra if item["category"] == cat),
        }
    return {
        "index": index,
        "reference_cluster": _describe(ref_cluster),
        "result_cluster": _describe(res_cluster),
        "status": status,
        "recall": round(recall, 6),
        "precision": round(precision, 6),
        "rotation": rot,
        "translation": [round(dx, 6), round(dy, 6)],
        "max_deviation": round(m.max_dev, 6),
        "circles": {"reference": m.circles_ref, "matched": m.circles_matched},
        "categories": categories,
        "missing": m.missing[:MAX_LISTED],
        "extra": m.extra[:MAX_LISTED],
        "levels": levels,
    }


def score(result, reference, *, tol=DEFAULT_TOL, gap=DEFAULT_GAP):
    ref_prims, ref_skipped = extract(reference)
    res_prims, res_skipped = extract(result)
    ref_clusters, res_clusters = _clusters(ref_prims, gap), _clusters(res_prims, gap)
    n, m = len(ref_clusters), len(res_clusters)
    weights = [[0.0] * m for _ in range(n)]
    for i, rc in enumerate(ref_clusters):
        ref_norm = _normalise(rc["prims"], tol)
        for j, sc in enumerate(res_clusters):
            rot, dx, dy, loose = _align(ref_norm, _normalise(sc["prims"], tol), tol)
            weights[i][j] = loose
    pairs = _fill_gaps(_pairs(weights, n, m), n, m)
    parts = [_part_report(k, ref_clusters[i], res_clusters[j], tol) for k, (i, j) in enumerate(pairs)]
    paired_ref, paired_res = {i for i, _ in pairs}, {j for _, j in pairs}
    summary = {
        "parts_reference": n,
        "parts_result": m,
        **{status.lower(): sum(1 for p in parts if p["status"] == status) for status in ("MATCH", "PARTIAL", "DIFF")},
        "unsupported_entities": {"reference": ref_skipped, "result": res_skipped},
    }
    return {
        "tolerance": tol,
        "gap": gap,
        "parts": parts,
        "unmatched_reference": [_describe(c) for i, c in enumerate(ref_clusters) if i not in paired_ref],
        "unmatched_result": [_describe(c) for j, c in enumerate(res_clusters) if j not in paired_res],
        "summary": summary,
    }


def _format(out):
    lines = [f"tolerance < {out['tolerance']} mm, cluster gap {out['gap']} mm",
             f"{'#':>2} {'status':8} {'recall':>7} {'precis.':>7} {'rot':>4} {'shift':>22} {'miss':>5} {'extra':>5} circles"]
    for p in out["parts"]:
        lines.append(f"{p['index']:>2} {p['status']:8} {p['recall']:7.3f} {p['precision']:7.3f} {p['rotation']:>4} "
                     f"{str(tuple(p['translation'])):>22} {len(p['missing']):>5} {len(p['extra']):>5} "
                     f"{p['circles']['matched']}/{p['circles']['reference']}")
        lines.append(f"     recall by tolerance: " + ", ".join(f"{k}: {v['recall']:.3f}" for k, v in p["levels"].items()))
    for label, key in (("reference", "unmatched_reference"), ("result", "unmatched_result")):
        for c in out[key]:
            lines.append(f"unmatched {label} cluster {c['index']}: bbox {c['bbox']} ({c['entities']} entities)")
    s = out["summary"]
    lines.append(f"parts: reference {s['parts_reference']}, result {s['parts_result']}, "
                 f"MATCH {s['match']}, PARTIAL {s['partial']}, DIFF {s['diff']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("result", type=Path)
    ap.add_argument("reference", type=Path)
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL)
    ap.add_argument("--gap", type=float, default=DEFAULT_GAP)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = score(args.result, args.reference, tol=args.tol, gap=args.gap)
    print(json.dumps(out, indent=2) if args.json else _format(out))
    clean = all(p["status"] == "MATCH" for p in out["parts"]) and not out["unmatched_reference"] \
        and not out["unmatched_result"]
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
