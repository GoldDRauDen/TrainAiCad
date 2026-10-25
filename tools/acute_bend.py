#!/usr/bin/env python3
"""Acute bend (included angle <=85 deg): outside-envelope OD from the real bend radius.

    python tools/acute_bend.py od --t 3 --angle 75 --rin 0.6 --inside 179.2 49.5
    python tools/acute_bend.py fixture regression/fixtures/acute_bend_lt85/ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf

`--inside a1 a2`: each face's inside-surface length from its free edge to the theoretical
sharp inside corner. OD_i = a_i - Rin/tan(angle/2) + Rin + t (centre of the Rin arc, then the
outside envelope; never the sharp intersection). Nobi is applied afterwards:
L_flat = OD1 + OD2 - Nobi. Rule: rules/BEND_ACUTE.md.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def od_from_inside(a1: float, a2: float, t: float, angle_deg: float, rin: float) -> dict:
    if not 0.0 < angle_deg <= 85.0:
        raise ValueError("acute construction applies only to 0 < angle <= 85")
    setback = rin / math.tan(math.radians(angle_deg) / 2.0)
    rout = rin + t
    return {"OD1": a1 - setback + rout, "OD2": a2 - setback + rout, "Rin": rin, "Rout": rout,
            "angle_deg": angle_deg, "t": t}


# --- solver for a DXF with two rectangular faces on layers FACE_1 / FACE_2 -----------------
def _sub(a, b): return (a[0] - b[0], a[1] - b[1])
def _add(a, b): return (a[0] + b[0], a[1] + b[1])
def _mul(a, s): return (a[0] * s, a[1] * s)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1]
def _norm(a): return math.hypot(a[0], a[1])
def _unit(a):
    n = _norm(a)
    return (a[0] / n, a[1] / n)
def _dist(a, b): return _norm(_sub(a, b))
def _mid(a, b): return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _intersect(p, d, q, e):
    det = d[0] * (-e[1]) + e[0] * d[1]
    if abs(det) < 1e-12:
        raise RuntimeError("parallel lines")
    bb = _sub(q, p)
    s = (bb[0] * (-e[1]) + e[0] * bb[1]) / det
    return _add(p, _mul(d, s))


def _corners(lines):
    pts = []
    for e in lines:
        for p in ((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)):
            if not any(_dist(p, q) < 1e-8 for q in pts):
                pts.append(p)
    c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return sorted(pts, key=lambda p: math.atan2(p[1] - c[1], p[0] - c[0])), c


def _long_edges(pts):
    ee = [(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    order = sorted(range(4), key=lambda i: _dist(*ee[i]))
    t = (_dist(*ee[order[0]]) + _dist(*ee[order[1]])) / 2
    return t, [ee[order[2]], ee[order[3]]]


def solve_fixture(path, rin: float = 0.6) -> dict:
    import ezdxf
    msp = ezdxf.readfile(path).modelspace()
    faces = [list(msp.query(f'LINE[layer=="FACE_{i}"]')) for i in (1, 2)]
    if any(len(f) != 4 for f in faces):
        raise RuntimeError("expected 4 LINEs per face")
    (p1, c1), (p2, c2) = _corners(faces[0]), _corners(faces[1])
    t1, e1 = _long_edges(p1)
    t2, e2 = _long_edges(p2)
    if abs(t1 - t2) > 1e-6:
        raise RuntimeError("thickness mismatch")
    out = []
    for edges, other in ((e1, c2), (e2, c1)):
        a, b = min(edges, key=lambda e: _dist(_mid(*e), other))   # inside surface faces the other face
        free, bend = (b, a) if _dist(a, other) <= _dist(b, other) else (a, b)
        d = _unit(_sub(bend, free))
        n = (-d[1], d[0])
        if _dot(n, _sub(other, _mid(free, bend))) < 0:
            n = (-n[0], -n[1])
        out.append((free, d, n))
    (f1, d1, n1), (f2, d2, n2) = out
    angle = math.degrees(math.acos(max(-1.0, min(1.0, abs(_dot(d1, d2))))))
    centre = _intersect(_add(f1, _mul(n1, rin)), d1, _add(f2, _mul(n2, rin)), d2)
    vertex = _intersect(f1, d1, f2, d2)
    t = (t1 + t2) / 2
    rout = rin + t
    return {"t": t, "angle_deg": angle, "Rin": rin, "Rout": rout,
            "inside": [_dot(_sub(vertex, f1), d1), _dot(_sub(vertex, f2), d2)],
            "OD1": _dot(_sub(centre, f1), d1) + rout, "OD2": _dot(_sub(centre, f2), d2) + rout}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("od")
    o.add_argument("--t", type=float, required=True)
    o.add_argument("--angle", type=float, required=True, help="included angle, <=85")
    o.add_argument("--rin", type=float, required=True)
    o.add_argument("--inside", type=float, nargs=2, required=True, metavar=("A1", "A2"))
    f = sub.add_parser("fixture")
    f.add_argument("dxf")
    f.add_argument("--rin", type=float, default=0.6)
    a = ap.parse_args(argv)
    res = (od_from_inside(*a.inside, a.t, a.angle, a.rin) if a.cmd == "od"
           else solve_fixture(a.dxf, a.rin))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
