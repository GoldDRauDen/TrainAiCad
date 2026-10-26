"""Shared bulge geometry (DXF LWPOLYLINE segment p0 -> p1 with bulge b = tan(sweep/4)). Pure math, no I/O."""
from __future__ import annotations

import math


class GeometryError(ValueError):
    pass


def bulge_circle(p0, p1, bulge):
    """(cx, cy, radius, theta) of the bulged segment; theta = 4·atan(b) is signed (+ = CCW).

    Raises GeometryError for a zero/non-finite bulge, a zero chord or a (near) full circle."""
    x0, y0, x1, y1 = float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1])
    b = float(bulge)
    dx, dy = x1 - x0, y1 - y0
    chord = math.hypot(dx, dy)
    if not math.isfinite(b) or abs(b) < 1e-14 or chord <= 0:
        raise GeometryError("Degenerate or non-finite bulge/segment")
    theta = 4 * math.atan(b)
    if abs(theta) >= 2 * math.pi - 1e-10:
        raise GeometryError("Bulge too close to full circle; cannot represent as ARC")
    radius = chord / (2 * abs(math.sin(theta / 2)))
    k = (1 - b * b) / (4 * b)  # signed centre offset from the chord midpoint, in chord lengths, to the left
    cx, cy = (x0 + x1) / 2 - dy * k, (y0 + y1) / 2 + dx * k
    if any(not math.isfinite(v) for v in (radius, cx, cy)) or radius <= 0:
        raise GeometryError("Invalid bulge-derived circle")
    return cx, cy, radius, theta


def arc_from_bulge(start, end, bulge):
    """Bulged segment -> DXF ARC ((cx, cy), radius, start_deg, end_deg), always CCW (a CW bulge swaps the ends)."""
    cx, cy, radius, theta = bulge_circle(start, end, bulge)
    u, v = (start, end) if bulge > 0 else (end, start)
    sa = math.degrees(math.atan2(float(u[1]) - cy, float(u[0]) - cx)) % 360
    ea = math.degrees(math.atan2(float(v[1]) - cy, float(v[0]) - cx)) % 360
    if not math.isclose((ea - sa) % 360, abs(math.degrees(theta)), abs_tol=1e-6):
        raise GeometryError("Bulge sweep mismatch; rejected instead of faceting the curve")
    return (cx, cy), radius, sa, ea


def bulge_points(p0, p1, bulge, steps: int):
    """The steps-1 points strictly between p0 and p1 on the bulged segment (for polygon tests, never for output)."""
    cx, cy, radius, theta = bulge_circle(p0, p1, bulge)
    a0 = math.atan2(float(p0[1]) - cy, float(p0[0]) - cx)
    return [(cx + radius * math.cos(a0 + theta * k / steps), cy + radius * math.sin(a0 + theta * k / steps))
            for k in range(1, steps)]


def full_circle(vertices, closed=True):
    """((cx, cy), radius) when a closed polyline is exactly one full circle (two vertices, both bulges +-1 of one
    sign), else None. Such a loop is saved as ONE CIRCLE, never as two ARCs (rules/OUTPUT.md section 4)."""
    if not closed or len(vertices) != 2:
        return None
    (x0, y0, b0), (x1, y1, b1) = [(float(v[0]), float(v[1]), float(v[2])) for v in vertices]
    if abs(abs(b0) - 1.0) > 1e-9 or abs(b1 - b0) > 1e-9:
        return None
    radius = math.hypot(x1 - x0, y1 - y0) / 2.0
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0), radius


def polyline_bbox(vertices, closed=True):
    """(xmin, ymin, xmax, ymax) of a polyline including the bulge arcs (a full circle gives its own box)."""
    circle = full_circle(vertices, closed)
    if circle:
        (cx, cy), r = circle
        return cx - r, cy - r, cx + r, cy + r
    xs, ys = [v[0] for v in vertices], [v[1] for v in vertices]
    n = len(vertices)
    for i in range(n if closed else n - 1):
        a, b = vertices[i], vertices[(i + 1) % n]
        if len(a) < 3 or abs(a[2]) < 1e-14:
            continue
        cx, cy, r, theta = bulge_circle(a[:2], b[:2], a[2])
        a0 = math.atan2(a[1] - cy, a[0] - cx)
        for k in range(4):                      # cardinal points lying on the swept arc
            ang = k * math.pi / 2
            rel = ((ang - a0) % (2 * math.pi)) if theta > 0 else ((a0 - ang) % (2 * math.pi))
            if rel <= abs(theta):
                xs.append(round(cx + r * math.cos(ang), 6))
                ys.append(round(cy + r * math.sin(ang), 6))
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    # an arc end that only touches the vertex box (fillet tangent point) must not grow it by float noise
    vx, vy = [v[0] for v in vertices], [v[1] for v in vertices]
    snap = lambda value, ref: ref if abs(value - ref) <= 1e-5 else value  # noqa: E731
    return snap(x0, min(vx)), snap(y0, min(vy)), snap(x1, max(vx)), snap(y1, max(vy))
