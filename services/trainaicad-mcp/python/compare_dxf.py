#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

import ezdxf


def pt(v, scale=1.0):
    return (float(v[0]) * scale, float(v[1]) * scale)


def angle_norm(a):
    a = a % 360.0
    return a + 360.0 if a < 0 else a


def ccw_delta(a, b):
    return (angle_norm(b) - angle_norm(a)) % 360.0


def in_ccw_sweep(angle, start, end, eps=1e-9):
    total = ccw_delta(start, end)
    pos = ccw_delta(start, angle)
    return pos <= total + eps


def transform_point(p, cfg):
    x, y = p
    if cfg.get("mirrorX"):
        x = -x
    if cfg.get("mirrorY"):
        y = -y
    deg = float(cfg.get("rotationDeg", 0.0))
    if deg:
        a = math.radians(deg)
        x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    return (x, y)


def point_segment_distance(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    denom = vx * vx + vy * vy
    if denom <= 1e-24:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / denom))
    qx, qy = ax + t * vx, ay + t * vy
    return math.hypot(px - qx, py - qy)


def bulge_arc(a, b, bulge):
    theta = 4.0 * math.atan(float(bulge))
    chord = math.hypot(b[0] - a[0], b[1] - a[1])
    if chord <= 1e-12 or abs(theta) <= 1e-12:
        return None
    radius = chord / (2.0 * abs(math.sin(theta / 2.0)))
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    ux, uy = (b[0] - a[0]) / chord, (b[1] - a[1]) / chord
    nx, ny = -uy, ux
    h = radius * math.cos(abs(theta) / 2.0)
    sign = 1.0 if theta > 0 else -1.0
    center = (mx + sign * nx * h, my + sign * ny * h)
    start = math.degrees(math.atan2(a[1] - center[1], a[0] - center[0]))
    end = math.degrees(math.atan2(b[1] - center[1], b[0] - center[0]))
    if theta < 0:
        start, end = end, start
    return ("ARC", center, radius, angle_norm(start), angle_norm(end))


def family_of(ent):
    layer = str(ent.dxf.get("layer", "0"))
    if layer == "AI_META":
        return None
    typ = ent.dxftype()
    if typ == "TEXT":
        return None
    linetype = str(ent.dxf.get("linetype", "BYLAYER")).upper()
    color = int(ent.dxf.get("color", 256))
    if linetype == "DASHED":
        return "BEND"
    if color == 1:
        return "KEGAKI"
    if color == 3:
        return "GREEN_PROCESS"
    if typ == "POINT":
        return "POINT"
    return "CUT"


def entity_primitives(ent, scale):
    typ = ent.dxftype()
    out = []
    if typ == "LINE":
        out.append(("LINE", pt(ent.dxf.start, scale), pt(ent.dxf.end, scale)))
    elif typ == "CIRCLE":
        out.append(("CIRCLE", pt(ent.dxf.center, scale), float(ent.dxf.radius) * scale))
    elif typ == "ARC":
        out.append(("ARC", pt(ent.dxf.center, scale), float(ent.dxf.radius) * scale,
                    angle_norm(float(ent.dxf.start_angle)), angle_norm(float(ent.dxf.end_angle))))
    elif typ == "POINT":
        out.append(("POINT", pt(ent.dxf.location, scale)))
    elif typ == "LWPOLYLINE":
        verts = [(float(x) * scale, float(y) * scale, float(b)) for x, y, b in ent.get_points("xyb")]
        count = len(verts)
        last = count if ent.closed else count - 1
        for i in range(last):
            x1, y1, bulge = verts[i]
            x2, y2, _ = verts[(i + 1) % count]
            a, b = (x1, y1), (x2, y2)
            arc = bulge_arc(a, b, bulge)
            out.append(arc if arc else ("LINE", a, b))
    return out


def apply_transform(primitive, cfg):
    kind = primitive[0]
    if kind == "LINE":
        return ("LINE", transform_point(primitive[1], cfg), transform_point(primitive[2], cfg))
    if kind == "POINT":
        return ("POINT", transform_point(primitive[1], cfg))
    if kind == "CIRCLE":
        return ("CIRCLE", transform_point(primitive[1], cfg), primitive[2])
    if kind == "ARC":
        c, radius, start, end = primitive[1:]
        p1 = (c[0] + radius * math.cos(math.radians(start)), c[1] + radius * math.sin(math.radians(start)))
        p2 = (c[0] + radius * math.cos(math.radians(end)), c[1] + radius * math.sin(math.radians(end)))
        tc = transform_point(c, cfg)
        tp1, tp2 = transform_point(p1, cfg), transform_point(p2, cfg)
        s = angle_norm(math.degrees(math.atan2(tp1[1] - tc[1], tp1[0] - tc[0])))
        e = angle_norm(math.degrees(math.atan2(tp2[1] - tc[1], tp2[0] - tc[0])))
        mirrored = bool(cfg.get("mirrorX")) ^ bool(cfg.get("mirrorY"))
        return ("ARC", tc, radius, e if mirrored else s, s if mirrored else e)
    raise ValueError(kind)


def primitive_bbox(p):
    samples = sample_primitive(p, step=2.0)
    xs = [q[0] for q in samples]
    ys = [q[1] for q in samples]
    return (min(xs), min(ys), max(xs), max(ys))


def window_contains(window, p):
    if not window:
        return True
    x0, y0, x1, y1 = map(float, window)
    bx0, by0, bx1, by1 = primitive_bbox(p)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    return min(x0, x1) <= cx <= max(x0, x1) and min(y0, y1) <= cy <= max(y0, y1)


def sample_primitive(p, step=0.5):
    kind = p[0]
    if kind == "POINT":
        return [p[1]]
    if kind == "LINE":
        a, b = p[1], p[2]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(2, min(2001, int(math.ceil(length / step)) + 1))
        return [(a[0] + (b[0] - a[0]) * i / (n - 1),
                 a[1] + (b[1] - a[1]) * i / (n - 1)) for i in range(n)]
    if kind == "CIRCLE":
        c, r = p[1], p[2]
        n = max(24, min(2001, int(math.ceil(2 * math.pi * r / step))))
        return [(c[0] + r * math.cos(2 * math.pi * i / n),
                 c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    c, r, start, end = p[1:]
    sweep = ccw_delta(start, end)
    if sweep <= 1e-12:
        sweep = 360.0
    length = r * math.radians(sweep)
    n = max(3, min(2001, int(math.ceil(length / step)) + 1))
    return [(c[0] + r * math.cos(math.radians(start + sweep * i / (n - 1))),
             c[1] + r * math.sin(math.radians(start + sweep * i / (n - 1)))) for i in range(n)]


def point_primitive_distance(q, p):
    kind = p[0]
    if kind == "POINT":
        return math.hypot(q[0] - p[1][0], q[1] - p[1][1])
    if kind == "LINE":
        return point_segment_distance(q, p[1], p[2])
    if kind == "CIRCLE":
        return abs(math.hypot(q[0] - p[1][0], q[1] - p[1][1]) - p[2])
    c, r, start, end = p[1:]
    dx, dy = q[0] - c[0], q[1] - c[1]
    angle = angle_norm(math.degrees(math.atan2(dy, dx)))
    if in_ccw_sweep(angle, start, end):
        return abs(math.hypot(dx, dy) - r)
    p1 = (c[0] + r * math.cos(math.radians(start)), c[1] + r * math.sin(math.radians(start)))
    p2 = (c[0] + r * math.cos(math.radians(end)), c[1] + r * math.sin(math.radians(end)))
    return min(math.hypot(q[0] - p1[0], q[1] - p1[1]), math.hypot(q[0] - p2[0], q[1] - p2[1]))


def primitive_length(p):
    if p[0] == "POINT":
        return 0.0
    if p[0] == "LINE":
        return math.hypot(p[2][0] - p[1][0], p[2][1] - p[1][1])
    if p[0] == "CIRCLE":
        return 2 * math.pi * p[2]
    sweep = ccw_delta(p[3], p[4])
    if sweep <= 1e-12:
        sweep = 360.0
    return p[2] * math.radians(sweep)


def bbox(primitives):
    boxes = [primitive_bbox(p) for p in primitives]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def translate(primitives, dx, dy):
    cfg = {"rotationDeg": 0, "mirrorX": False, "mirrorY": False}
    out = []
    for p in primitives:
        kind = p[0]
        if kind == "LINE":
            out.append(("LINE", (p[1][0] + dx, p[1][1] + dy), (p[2][0] + dx, p[2][1] + dy)))
        elif kind == "POINT":
            out.append(("POINT", (p[1][0] + dx, p[1][1] + dy)))
        elif kind == "CIRCLE":
            out.append(("CIRCLE", (p[1][0] + dx, p[1][1] + dy), p[2]))
        else:
            out.append(("ARC", (p[1][0] + dx, p[1][1] + dy), p[2], p[3], p[4]))
    return out


def directed_distance(a, b):
    if not a or not b:
        return math.inf
    maxd = 0.0
    for primitive in a:
        for q in sample_primitive(primitive):
            d = min(point_primitive_distance(q, target) for target in b)
            maxd = max(maxd, d)
    return maxd


def compare_family(a, b, tol):
    if not a and not b:
        return {"status": "N/A", "maxDistanceMm": 0.0, "lengthDeltaMm": 0.0, "aPrimitives": 0, "bPrimitives": 0}
    if not a or not b:
        return {"status": "DIFF", "maxDistanceMm": None, "lengthDeltaMm": None, "aPrimitives": len(a), "bPrimitives": len(b)}
    d = max(directed_distance(a, b), directed_distance(b, a))
    ld = abs(sum(map(primitive_length, a)) - sum(map(primitive_length, b)))
    status = "MATCH" if d <= tol and ld <= max(tol, tol * (len(a) + len(b))) else "DIFF"
    return {"status": status, "maxDistanceMm": d, "lengthDeltaMm": ld, "aPrimitives": len(a), "bPrimitives": len(b)}


def load(path, scale, cfg, window=None):
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    if audit.has_errors:
        raise RuntimeError(f"DXF_AUDIT_ERRORS:{path}")
    families = {}
    allp = []
    for ent in doc.modelspace():
        family = family_of(ent)
        if not family:
            continue
        for primitive in entity_primitives(ent, scale):
            p = apply_transform(primitive, cfg)
            if window_contains(window, p):
                families.setdefault(family, []).append(p)
                allp.append(p)
    return families, allp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ai", type=Path)
    ap.add_argument("reference", type=Path)
    ap.add_argument("config", type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    tol = float(cfg["curveToleranceMm"])
    results = []

    for part in cfg["parts"]:
        code = part["code"]
        ai_f, ai_all = load(args.ai, float(cfg["aiMmPerUnit"]), part.get("aiTransform", {}), part.get("aiWindow"))
        rf_f, rf_all = load(args.reference, float(cfg["referenceMmPerUnit"]), part.get("referenceTransform", {}), part.get("referenceWindow"))
        if not ai_all or not rf_all:
            results.append({"code": code, "status": "UNVERIFIED", "reason": "EMPTY_MAPPED_GEOMETRY", "families": {}})
            continue

        ba, br = bbox(ai_all), bbox(rf_all)
        dx, dy = br[0] - ba[0], br[1] - ba[1]
        ai_f = {k: translate(v, dx, dy) for k, v in ai_f.items()}
        ai_all = translate(ai_all, dx, dy)

        families = {}
        names = sorted(set(ai_f) | set(rf_f))
        for name in names:
            families[name] = compare_family(ai_f.get(name, []), rf_f.get(name, []), tol)
        whole = compare_family(ai_all, rf_all, tol)
        matching = [v for v in families.values() if v["status"] == "MATCH"]
        diffs = [v for v in families.values() if v["status"] == "DIFF"]
        if whole["status"] == "MATCH" and not diffs:
            status = "MATCH"
        elif matching:
            status = "PARTIAL"
        else:
            status = "DIFF"

        results.append({
            "code": code,
            "status": status,
            "translationRemovedMm": [dx, dy],
            "whole": whole,
            "families": families,
            "note": "Rotation/mirror applied only when explicitly supplied in config; layout translation removed automatically."
        })

    print(json.dumps({"results": results}, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
