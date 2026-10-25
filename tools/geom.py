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
