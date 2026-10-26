"""Conservative closed-cut containment against a canonical outer contour."""
from __future__ import annotations

import math

from geom import GeometryError, bulge_circle, bulge_points


class ContainmentError(ValueError):
    pass


def _loop(vertices, tolerance=0.005):
    if len(vertices) < 3 and not (len(vertices) == 2 and any(len(v) > 2 and v[2] for v in vertices)):
        raise ContainmentError("CONTAINMENT_OUTER_GEOMETRY_UNVERIFIABLE")
    points = [(float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 0.0)
              for v in vertices]
    if not all(math.isfinite(x) for v in points for x in v):
        raise ContainmentError("CONTAINMENT_NONFINITE_GEOMETRY")
    out = []
    for i, (x0, y0, bulge) in enumerate(points):
        x1, y1, _ = points[(i + 1) % len(points)]
        if not out:
            out.append((x0, y0))
        if abs(bulge) < 1e-14:
            if i < len(points)-1:
                out.append((x1, y1))
            continue
        try:
            cx, cy, radius, theta = bulge_circle((x0, y0), (x1, y1), bulge)
        except GeometryError:
            raise ContainmentError("CONTAINMENT_ARC_UNVERIFIABLE") from None
        sagitta = min(tolerance, radius * 0.1)
        max_step = 2 * math.acos(max(-1.0, min(1.0, 1 - sagitta/radius)))
        count = max(1, math.ceil(abs(theta) / max(max_step, 1e-4)))
        if count > 20000:
            raise ContainmentError("CONTAINMENT_ARC_TOO_COMPLEX")
        out.extend(bulge_points((x0, y0), (x1, y1), bulge, count))
        if i < len(points)-1:
            out.append((x1, y1))
    return out


def _on_segment(p, a, b, tol=1e-9):
    cross = (p[0]-a[0])*(b[1]-a[1]) - (p[1]-a[1])*(b[0]-a[0])
    if abs(cross) > tol * max(1.0, math.dist(a, b)):
        return False
    return (min(a[0], b[0])-tol <= p[0] <= max(a[0], b[0])+tol and
            min(a[1], b[1])-tol <= p[1] <= max(a[1], b[1])+tol)


def _inside(p, polygon):
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if _on_segment(p, a, b):
            return False
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = (b[0]-a[0]) * (p[1]-a[1]) / (b[1]-a[1]) + a[0]
            if p[0] < x:
                inside = not inside
    return inside


def _orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _intersects(a, b, c, d):
    return (_orient(a,b,c) * _orient(a,b,d) <= 1e-12 and
            _orient(c,d,a) * _orient(c,d,b) <= 1e-12 and
            max(min(a[0],b[0]),min(c[0],d[0])) <= min(max(a[0],b[0]),max(c[0],d[0])) + 1e-9 and
            max(min(a[1],b[1]),min(c[1],d[1])) <= min(max(a[1],b[1]),max(c[1],d[1])) + 1e-9)


def _contained(inner, outer):
    if len(inner) < 3:
        raise ContainmentError("CONTAINMENT_FEATURE_GEOMETRY_UNVERIFIABLE")
    if not all(_inside(p, outer) for p in inner):
        return False
    for a, b in zip(inner, inner[1:] + inner[:1]):
        for c, d in zip(outer, outer[1:] + outer[:1]):
            if _intersects(a, b, c, d):
                return False
    return True


def part_containment_errors(part):
    """Check complete round holes and closed slot/cutout loops, not centers alone."""
    outers = [e for e in part.get("entities", []) if e.get("role") == "outer"]
    if len(outers) != 1 or outers[0].get("type") != "LWPOLYLINE" or outers[0].get("closed") is not True:
        return ["CONTAINMENT_OUTER_GEOMETRY_UNVERIFIABLE"]
    try:
        outer = _loop(outers[0].get("vertices", []))
        errors = []
        for entity in part.get("entities", []):
            role, typ = entity.get("role"), entity.get("type")
            if role in ("hole", "kegaki") and typ == "CIRCLE":
                cx, cy = map(float, entity["center"][:2])
                radius = float(entity["radius"])
                if not all(math.isfinite(x) for x in (cx,cy,radius)) or radius <= 0:
                    raise ContainmentError("CONTAINMENT_FEATURE_GEOMETRY_UNVERIFIABLE")
                sagitta = min(0.005, radius * 0.1)
                count = max(64, math.ceil(math.pi / math.acos(max(-1.0, min(1.0, 1 - sagitta/radius)))))
                if count > 20000:
                    raise ContainmentError("CONTAINMENT_FEATURE_TOO_COMPLEX")
                loop = [(cx+radius*math.cos(2*math.pi*i/count),
                         cy+radius*math.sin(2*math.pi*i/count)) for i in range(count)]
            elif role in {"slot", "cutout"} and typ == "LWPOLYLINE" and entity.get("closed") is True:
                loop = _loop(entity.get("vertices", []))
            else:
                continue
            if not _contained(loop, outer):
                errors.append(f"FEATURE_OUTSIDE_MATERIAL:{entity.get('entity_id','?')}")
        return errors
    except (ContainmentError, KeyError, TypeError, ValueError, OverflowError) as exc:
        return [str(exc) if isinstance(exc, ContainmentError)
                else "CONTAINMENT_FEATURE_GEOMETRY_UNVERIFIABLE"]
