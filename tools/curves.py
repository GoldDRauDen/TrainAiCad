"""Native SPLINE / ELLIPSE segments of customer DATA: decode exactly, transform rigidly, write back as the same entity.

A curve is a plain dict (JSON friendly):
  {"kind": "SPLINE", "degree": 3, "fit_points": [[x, y], ...], "control_points": [...], "knots": [...], "weights": [...],
   "start_tangent": [x, y] | None, "end_tangent": [x, y] | None, "start": [x, y], "end": [x, y]}
  {"kind": "ELLIPSE", "center": [x, y], "major_axis": [x, y], "ratio": r, "start_param": t0, "end_param": t1,
   "start": [x, y], "end": [x, y]}
It is never flattened into the DXF; `flatten` exists only for containment / overlap validation.
"""
from __future__ import annotations

import math

KINDS = ("SPLINE", "ELLIPSE")


class CurveError(ValueError):
    pass


def _xy(v):
    return [float(v[0]), float(v[1])]


def _pt_on_ellipse(c, t):
    ca, sa = math.cos(t), math.sin(t)
    (cx, cy), (mx, my), r = c["center"], c["major_axis"], c["ratio"]
    return [cx + ca * mx - sa * r * my, cy + ca * my + sa * r * mx]


def decode(entity):
    """ezdxf SPLINE / ELLIPSE entity -> curve dict (every number of the DXF record, nothing simplified)."""
    t = entity.dxftype()
    if t == "ELLIPSE":
        d = entity.dxf
        if abs(float(d.end_param) - float(d.start_param)) >= 2 * math.pi - 1e-9:
            raise CurveError("a full ELLIPSE is a whole loop, not a contour segment")
        c = {"kind": "ELLIPSE", "center": _xy(d.center), "major_axis": _xy(d.major_axis), "ratio": float(d.ratio),
             "start_param": float(d.start_param), "end_param": float(d.end_param)}
        c["start"], c["end"] = _pt_on_ellipse(c, c["start_param"]), _pt_on_ellipse(c, c["end_param"])
        return c
    if t == "SPLINE":
        fit = [_xy(p) for p in entity.fit_points]
        ctl = [_xy(p) for p in entity.control_points]
        if not fit and not ctl:
            raise CurveError("SPLINE without fit or control points")
        c = {"kind": "SPLINE", "degree": int(entity.dxf.degree), "fit_points": fit, "control_points": ctl,
             "knots": [float(k) for k in entity.knots], "weights": [float(w) for w in entity.weights],
             "start_tangent": _xy(entity.dxf.start_tangent) if entity.dxf.hasattr("start_tangent") else None,
             "end_tangent": _xy(entity.dxf.end_tangent) if entity.dxf.hasattr("end_tangent") else None,
             "closed": bool(entity.closed)}
        if c["closed"]:
            raise CurveError("a closed SPLINE is a whole loop, not a contour segment")
        if fit:
            c["start"], c["end"] = fit[0], fit[-1]
        else:
            tool = entity.construction_tool()
            c["start"], c["end"] = _xy(tool.point(0.0)), _xy(tool.point(tool.max_t))
        return c
    raise CurveError(f"{t} is not a native curve")


def transform(curve, fwd, scale=1.0, mirror=False):
    """Rigid transform (translate / rotate / uniform scale) by the point map `fwd`. A mirror of an ELLIPSE is refused."""
    out = dict(curve)
    for k in ("start", "end", "center"):
        if k in out:
            out[k] = list(fwd(out[k]))
    if curve["kind"] == "SPLINE":
        for k in ("fit_points", "control_points"):
            out[k] = [list(fwd(p)) for p in curve[k]]
        o = fwd([0.0, 0.0])
        for k in ("start_tangent", "end_tangent"):
            if curve.get(k) is not None:
                p = fwd(curve[k])
                out[k] = [p[0] - o[0], p[1] - o[1]]
        return out
    if mirror:
        raise CurveError("ELLIPSE_MIRROR_NOT_SUPPORTED")
    o = fwd([0.0, 0.0])
    p = fwd(curve["major_axis"])
    out["major_axis"] = [p[0] - o[0], p[1] - o[1]]
    return out


def key(curve, nd=6):
    """Comparable fingerprint (rounded numbers, direction free: the geometry is the same walked either way)."""
    def r(v):
        if isinstance(v, (list, tuple)):
            return tuple(r(x) for x in v)
        if isinstance(v, float):
            return round(v, nd)
        return v
    ends = tuple(sorted((r(curve["start"]), r(curve["end"]))))
    return (ends, tuple(sorted((k, r(v)) for k, v in curve.items() if k not in ("start", "end"))))


def flatten(curve, tol=0.005):
    """Points along the curve for validation only (never written to a DXF)."""
    import ezdxf.math as em
    if curve["kind"] == "ELLIPSE":
        t0, t1 = curve["start_param"], curve["end_param"]
        if t1 <= t0:
            t1 += 2 * math.pi
        n = max(16, int(abs(t1 - t0) / 0.05) + 1)
        return [_pt_on_ellipse(curve, t0 + (t1 - t0) * i / n) for i in range(n + 1)]
    if curve["fit_points"]:
        tangents = None
        if curve.get("start_tangent") and curve.get("end_tangent"):
            tangents = [em.Vec3(*curve["start_tangent"], 0), em.Vec3(*curve["end_tangent"], 0)]
        tool = em.fit_points_to_cad_cv([em.Vec3(p[0], p[1], 0) for p in curve["fit_points"]], tangents=tangents) \
            if hasattr(em, "fit_points_to_cad_cv") else None
        if tool is None:
            return [list(p) for p in curve["fit_points"]]
        return [[p.x, p.y] for p in tool.flattening(tol)]
    tool = em.BSpline([em.Vec3(p[0], p[1], 0) for p in curve["control_points"]], order=curve["degree"] + 1,
                      knots=curve["knots"] or None, weights=curve["weights"] or None)
    return [[p.x, p.y] for p in tool.flattening(tol)]


def emit(msp, curve, attribs, move):
    """Write the curve as ONE native DXF entity, translated by `move`."""
    if curve["kind"] == "ELLIPSE":
        c = move(curve["center"])
        return msp.add_ellipse((c[0], c[1], 0), major_axis=(curve["major_axis"][0], curve["major_axis"][1], 0),
                               ratio=curve["ratio"], start_param=curve["start_param"], end_param=curve["end_param"],
                               dxfattribs=attribs)
    ent = msp.new_entity("SPLINE", dxfattribs={**attribs, "degree": curve["degree"]})
    if curve["fit_points"]:
        ent.fit_points = [(*move(p), 0.0) for p in curve["fit_points"]]
    if curve["control_points"]:
        ent.control_points = [(*move(p), 0.0) for p in curve["control_points"]]
    if curve["knots"]:
        ent.knots = list(curve["knots"])
    if curve["weights"]:
        ent.weights = list(curve["weights"])
    if curve.get("start_tangent") is not None:
        ent.dxf.start_tangent = (curve["start_tangent"][0], curve["start_tangent"][1], 0.0)
    if curve.get("end_tangent") is not None:
        ent.dxf.end_tangent = (curve["end_tangent"][0], curve["end_tangent"][1], 0.0)
    return ent


def signature(ent):
    """Fingerprint of a saved SPLINE / ELLIPSE entity for the DXF read-back."""
    if ent.dxftype() == "ELLIPSE":
        d = ent.dxf
        return (round(d.center.x, 6), round(d.center.y, 6), round(d.major_axis.x, 6), round(d.major_axis.y, 6),
                round(d.ratio, 8), round(d.start_param, 8), round(d.end_param, 8))
    return (ent.dxf.degree, tuple((round(p[0], 6), round(p[1], 6)) for p in ent.fit_points),
            tuple((round(p[0], 6), round(p[1], 6)) for p in ent.control_points), tuple(round(k, 8) for k in ent.knots),
            tuple(round(w, 8) for w in ent.weights))


def saved_ends(ent):
    """First / last point of a saved SPLINE / ELLIPSE entity (closed-contour read-back)."""
    if ent.dxftype() == "ELLIPSE":
        return (ent.start_point.x, ent.start_point.y), (ent.end_point.x, ent.end_point.y)
    if len(ent.fit_points):
        f = ent.fit_points
        return (f[0][0], f[0][1]), (f[-1][0], f[-1][1])
    pts = list(ent.flattening(0.01))
    return (pts[0].x, pts[0].y), (pts[-1].x, pts[-1].y)
