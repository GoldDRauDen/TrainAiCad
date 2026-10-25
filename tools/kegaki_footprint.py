#!/usr/bin/env python3
"""KEGAKI contact-footprint helpers (see rules/KEGAKI.md section 3).

Pure geometry on numbers read from the SOURCE views. Nothing here reads a
sample/reference DXF and nothing invents a dimension: every input must be a
printed/derived source dimension with its witness recorded by the caller.
"""
from __future__ import annotations

import math

EPS = 1e-6


def contact_width(t: float, *, slant_delta: float | None = None,
                  tilt_deg: float | None = None) -> float:
    """Width of the contact zone = projection of the child's thickness edge.

    * square edge            -> t
    * slanted end (two alternate lengths differ by slant_delta)
                             -> hypot(slant_delta, t)   (6, 3.5 -> 6.946)
    * child tilted tilt_deg  -> t / cos(tilt)            (6, 12 deg -> 6.134)
    """
    if t <= 0:
        raise ValueError("thickness must be positive")
    if slant_delta is not None and tilt_deg is not None:
        raise ValueError("use either slant_delta or tilt_deg")
    if slant_delta is not None:
        return math.hypot(slant_delta, t)
    if tilt_deg is not None:
        return t / math.cos(math.radians(tilt_deg))
    return float(t)


def slanted_edge_length(run: float, short_a: float, short_b: float) -> float:
    """Length of a slanted edge from the SHORTER alternate heights.

    062022: heights 95.7 and 90.3 over a 20 run -> 20.715 (angle is derived,
    never measured separately and never divided by cos of another angle).
    """
    return math.hypot(run, short_a - short_b)


def contact_length(edge_length: float, offset: float) -> float:
    """Contact length = contact edge length - printed offset (35-5=30)."""
    if not 0 <= offset < edge_length:
        raise ValueError("offset must lie inside the contact edge")
    return edge_length - offset


def single_line_offset(t_host: float, k: float) -> float:
    """Distance of the single KEGAKI line from the welded edge: t_host - k.

    Used when the other boundary of the contact zone coincides with the part
    contour (062113: 6-4=2, 062024: 6-2=4).
    """
    if not 0 < k < t_host:
        raise ValueError("k must be between 0 and the host thickness")
    return t_host - k


def _norm(seg):
    (x0, y0), (x1, y1) = seg
    a, b = (round(x0, 6), round(y0, 6)), (round(x1, 6), round(y1, 6))
    return (a, b) if a <= b else (b, a)


def _subtract_collinear(seg, others):
    """Remove from seg every positive-length piece collinear with `others`."""
    (x0, y0), (x1, y1) = seg
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < EPS:
        return []
    ux, uy = dx / length, dy / length
    cuts = []
    for (ox0, oy0), (ox1, oy1) in others:
        if abs((ox0 - x0) * uy - (oy0 - y0) * ux) > EPS or \
                abs((ox1 - x0) * uy - (oy1 - y0) * ux) > EPS:
            continue
        a = (ox0 - x0) * ux + (oy0 - y0) * uy
        b = (ox1 - x0) * ux + (oy1 - y0) * uy
        lo, hi = max(0.0, min(a, b)), min(length, max(a, b))
        if hi - lo > EPS:
            cuts.append((lo, hi))
    cuts.sort()
    out, pos = [], 0.0
    for lo, hi in cuts:
        if lo - pos > EPS:
            out.append((pos, lo))
        pos = max(pos, hi)
    if length - pos > EPS:
        out.append((pos, length))
    return [((x0 + ux * a, y0 + uy * a), (x0 + ux * b, y0 + uy * b)) for a, b in out]


def union_boundary_segments(rects, contour_segments=()):
    """Boundary of the UNION of axis-aligned contact rectangles, minus contour.

    rects: iterable of (x0, y0, x1, y1). Shared boundaries between touching or
    overlapping rectangles disappear (no duplicated lines); pieces lying on the
    part contour are not drawn. Returns sorted ((x0,y0),(x1,y1)) segments.
    """
    rects = [(min(a, c), min(b, d), max(a, c), max(b, d)) for a, b, c, d in rects]
    xs = sorted({round(v, 6) for r in rects for v in (r[0], r[2])})
    ys = sorted({round(v, 6) for r in rects for v in (r[1], r[3])})

    def covered(i, j):
        if not (0 <= i < len(xs) - 1 and 0 <= j < len(ys) - 1):
            return False
        cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in rects)

    raw = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if not covered(i, j):
                continue
            if not covered(i, j - 1):
                raw.append(((xs[i], ys[j]), (xs[i + 1], ys[j])))
            if not covered(i, j + 1):
                raw.append(((xs[i], ys[j + 1]), (xs[i + 1], ys[j + 1])))
            if not covered(i - 1, j):
                raw.append(((xs[i], ys[j]), (xs[i], ys[j + 1])))
            if not covered(i + 1, j):
                raw.append(((xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1])))
    # merge collinear touching cells
    merged = []
    for seg in sorted({_norm(s) for s in raw}):
        (x0, y0), (x1, y1) = seg
        for k, ((mx0, my0), (mx1, my1)) in enumerate(merged):
            horizontal = abs(y0 - y1) < EPS and abs(my0 - my1) < EPS and abs(y0 - my0) < EPS
            vertical = abs(x0 - x1) < EPS and abs(mx0 - mx1) < EPS and abs(x0 - mx0) < EPS
            if horizontal and abs(mx1 - x0) < EPS:
                merged[k] = ((mx0, my0), (x1, y1)); break
            if vertical and abs(my1 - y0) < EPS:
                merged[k] = ((mx0, my0), (x1, y1)); break
        else:
            merged.append(seg)
    result = []
    for seg in merged:
        result.extend(_subtract_collinear(seg, contour_segments))
    return sorted(_norm(s) for s in result)


def straight_contour_segments(vertices):
    """Straight (bulge 0) segments of a closed canonical LWPOLYLINE."""
    segs = []
    for i, (x, y, bulge) in enumerate(vertices):
        nx, ny, _ = vertices[(i + 1) % len(vertices)]
        if abs(bulge) < EPS:
            segs.append(((x, y), (nx, ny)))
    return segs


def overlapping_pair(seg_a, seg_b) -> bool:
    """True when two straight segments are collinear and share positive length."""
    return bool(_subtract_collinear(seg_a, [seg_b]) != [seg_a] and
                _shared_length(seg_a, seg_b) > EPS)


def _shared_length(seg, other):
    (x0, y0), (x1, y1) = seg
    length = math.hypot(x1 - x0, y1 - y0)
    if length < EPS:
        return 0.0
    kept = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in _subtract_collinear(seg, [other]))
    return length - kept
