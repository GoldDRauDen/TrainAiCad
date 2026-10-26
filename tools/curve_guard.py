#!/usr/bin/env python3
"""A circle is ONE CIRCLE and an arc is ONE ARC (rules/OUTPUT.md section 4).

Fails a canonical part whose curves are assembled from pieces: several ARCs of one centre/radius that touch
end to end (a split arc, or two semicircles making a circle), or a run of short LINEs lying on one circle
(a faceted circle/arc). DATA parts keep the curves of the customer DXF (``data_provenance``) and are exempt.
Pure geometry on the canonical entities; no I/O.
"""
from __future__ import annotations

import math

from geom import GeometryError, bulge_circle, full_circle

TOL = 1e-4          # centre / radius / end-point coincidence, mm
MIN_FACETS_CLOSED = 8
MIN_FACETS_OPEN = 5


def _key(p):
    return (round(p[0] / TOL), round(p[1] / TOL))


def _arc_ends(cx, cy, r, sa, ea):
    return ((cx + r * math.cos(sa), cy + r * math.sin(sa)), (cx + r * math.cos(ea), cy + r * math.sin(ea)))


def _pieces(part):
    """(arcs, lines): arcs = (id, cx, cy, r, end0, end1); lines = (id, p, q) from LINE, ARC and LWPOLYLINE entities."""
    arcs, lines = [], []
    for e in part.get("entities", []):
        eid, typ = e.get("entity_id", "?"), e.get("type")
        if typ == "LINE":
            lines.append((eid, tuple(e["start"][:2]), tuple(e["end"][:2])))
        elif typ == "ARC":
            c, r = e["center"], float(e["radius"])
            ends = _arc_ends(c[0], c[1], r, math.radians(e["start_angle"]), math.radians(e["end_angle"]))
            arcs.append((eid, float(c[0]), float(c[1]), r, ends[0], ends[1]))
        elif typ == "LWPOLYLINE":
            v = e.get("vertices") or []
            if full_circle(v, bool(e.get("closed"))):
                continue                    # exported as ONE CIRCLE
            n = len(v)
            for i in range(n if e.get("closed") else n - 1):
                a, b = v[i], v[(i + 1) % n]
                if not a[2]:
                    lines.append((f"{eid}#{i}", tuple(a[:2]), tuple(b[:2])))
                    continue
                try:
                    cx, cy, r, _ = bulge_circle(a[:2], b[:2], a[2])
                except GeometryError:       # a full circle written as one bulge: a single piece already
                    continue
                arcs.append((f"{eid}#{i}", cx, cy, r, tuple(a[:2]), tuple(b[:2])))
    return arcs, lines


def _split_arcs(arcs):
    out = []
    for i, a in enumerate(arcs):
        for b in arcs[i + 1:]:
            if abs(a[1] - b[1]) > TOL or abs(a[2] - b[2]) > TOL or abs(a[3] - b[3]) > TOL:
                continue
            if {_key(a[4]), _key(a[5])} & {_key(b[4]), _key(b[5])}:
                out.append(f"SPLIT_ARC_FAIL:{a[0]}+{b[0]} (centre {a[1]:.3f},{a[2]:.3f} R{a[3]:g} joined end to end: "
                           "draw ONE ARC, or ONE CIRCLE for a full circle)")
    return out


def _smooth_turns(xy, closed):
    """Facets of a curve: every vertex turns the same way by a small angle and the edges are of similar length
    (a zigzag, a notch row or a rectangle is not a curve)."""
    n = len(xy)
    turns, lengths = [], []
    for i in range(n if closed else n - 2):
        p, q, r = xy[i], xy[(i + 1) % n], xy[(i + 2) % n]
        u, v = (q[0] - p[0], q[1] - p[1]), (r[0] - q[0], r[1] - q[1])
        turns.append(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))
        lengths.append(math.hypot(*u))
    if not turns or min(lengths) <= TOL:
        return False
    same_sign = all(t > 0 for t in turns) or all(t < 0 for t in turns)
    return same_sign and all(0.5 <= abs(t) <= 45 for t in turns) and max(lengths) <= 2 * min(lengths)


def _facet_runs(lines):
    """Connected runs of LINEs (degree <= 2 at every vertex) lying on one circle."""
    adj = {}
    for eid, p, q in lines:
        if math.dist(p, q) <= TOL:
            continue
        adj.setdefault(_key(p), []).append((eid, p, q))
        adj.setdefault(_key(q), []).append((eid, q, p))
    seen, out = set(), []
    for start in adj:
        if start in seen:
            continue
        comp, stack = [], [start]
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            comp.append(k)
            stack.extend(_key(o) for _, _, o in adj[k])
        if any(len(adj[k]) > 2 for k in comp):
            continue
        ends = [k for k in comp if len(adj[k]) == 1]
        closed = not ends
        if len(comp) < (MIN_FACETS_CLOSED if closed else MIN_FACETS_OPEN + 1):
            continue
        # walk the run in order
        cur = ends[0] if ends else comp[0]
        pts, used = [cur], set()
        while True:
            nxt = next(((eid, o) for eid, _, o in adj[cur] if eid not in used), None)
            if nxt is None:
                break
            used.add(nxt[0])
            cur = _key(nxt[1])
            if cur == pts[0]:
                break
            pts.append(cur)
        xy = [(k[0] * TOL, k[1] * TOL) for k in pts]
        ids = sorted(used)
        if not _smooth_turns(xy, closed):
            continue
        a, b, c = xy[0], xy[len(xy) // 2], xy[-1]
        d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-9:
            continue
        ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1]) + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
        uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0]) + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
        r = math.dist((ux, uy), a)
        if r <= TOL or any(abs(math.dist((ux, uy), p) - r) > max(0.02, 0.003 * r) for p in xy):
            continue
        out.append(f"SPLIT_{'CIRCLE' if closed else 'ARC'}_FAIL:{ids[0]}..{ids[-1]} ({len(ids)} LINEs on one circle, "
                   f"centre {ux:.3f},{uy:.3f} R{r:g}: draw ONE {'CIRCLE' if closed else 'ARC'})")
    return out


def split_curve_errors(part):
    """List of SPLIT_CIRCLE_FAIL / SPLIT_ARC_FAIL messages for one canonical part ([] when clean or DATA)."""
    if part.get("data_provenance"):
        return []
    arcs, lines = _pieces(part)
    return _split_arcs(arcs) + _facet_runs(lines)
