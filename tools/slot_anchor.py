#!/usr/bin/env python3
"""Source-witness slot anchor semantics; never infer anchor from slot appearance."""
from __future__ import annotations

import math

ANCHORS = {"SLOT_MIDPOINT", "ARC_CENTER_1", "ARC_CENTER_2", "OUTER_TIP_1", "OUTER_TIP_2"}


class SlotAnchorError(ValueError):
    pass


def slot_midpoint(anchor, kind, axis, width_mm, center_distance_mm):
    if kind not in ANCHORS:
        raise SlotAnchorError("SLOT_ANCHOR_UNCLASSIFIED")
    try:
        w, c = float(width_mm), float(center_distance_mm)
        ax, ay = float(axis[0]), float(axis[1])
        px, py = float(anchor[0]), float(anchor[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise SlotAnchorError("SLOT_ANCHOR_INVALID") from exc
    if not all(math.isfinite(v) for v in (w, c, ax, ay, px, py)) or w <= 0 or c < 0:
        raise SlotAnchorError("SLOT_SIZE_INVALID")
    length = math.hypot(ax, ay)
    if not math.isclose(length, 1.0, abs_tol=1e-8):
        raise SlotAnchorError("SLOT_AXIS_NOT_UNIT")
    offset = {
        "SLOT_MIDPOINT": 0.0, "ARC_CENTER_1": c / 2, "ARC_CENTER_2": -c / 2,
        "OUTER_TIP_1": (c + w) / 2, "OUTER_TIP_2": -(c + w) / 2,
    }[kind]
    return (px + offset * ax, py + offset * ay)


def validate_slot_anchor(record):
    try:
        if not record.get("source_pdf_page") or not record.get("evidence_ref") or record.get("witness_verified") is not True:
            raise SlotAnchorError("SLOT_WITNESS_UNPROVED")
        expected = slot_midpoint(
            record["anchor_point"], record["anchor_type"], record["axis_unit"],
            record["width_mm"], record["center_distance_mm"],
        )
        total = record["width_mm"] + record["center_distance_mm"]
        if abs(total - float(record["overall_length_mm"])) > 1e-8:
            raise SlotAnchorError("SLOT_LENGTH_SEMANTICS_MISMATCH")
        actual = tuple(float(v) for v in record["canonical_midpoint"])
        if len(actual) != 2 or math.hypot(expected[0]-actual[0], expected[1]-actual[1]) > 1e-7:
            raise SlotAnchorError("SLOT_ANCHOR_MISMATCH")
    except SlotAnchorError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise SlotAnchorError("SLOT_ANCHOR_RECORD_INCOMPLETE") from exc
    return expected


def stadium_geometry(vertices, closed=True):
    """Return exact stadium-slot dimensions from its bulges and arc centers."""
    try:
        from ezdxf.math import Vec2, bulge_to_arc
        if not closed or len(vertices) != 4:
            raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
        pts = [(float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 0.0)
               for v in vertices]
        if not all(math.isfinite(c) for v in pts for c in v):
            raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
        arcs = []
        straight_segments = []
        for i, (x, y, bulge) in enumerate(pts):
            nx, ny, _ = pts[(i + 1) % 4]
            if math.hypot(nx - x, ny - y) <= 1e-10:
                raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
            if abs(bulge) <= 1e-10:
                straight_segments.append(((x, y), (nx, ny)))
                continue
            center, _, _, radius = bulge_to_arc(Vec2(x, y), Vec2(nx, ny), bulge)
            arcs.append((float(center.x), float(center.y), float(radius), bulge,
                         (x, y), (nx, ny)))
        # A convex stadium has two same-direction semicircles (CW: -1/-1, CCW: +1/+1).
        if (len(arcs) != 2 or len(straight_segments) != 2 or arcs[0][3] * arcs[1][3] <= 0 or
                any(abs(abs(a[3]) - 1.0) > 1e-7 for a in arcs)):
            raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
        if abs(arcs[0][2] - arcs[1][2]) > 1e-7:
            raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
        # Two equal semicircles alone do not prove a stadium. Every straight
        # side must meet *its own* arc tangentially at both endpoints.
        # Otherwise an oblique/warped quadrilateral can pass the size witness.
        for start, end in straight_segments:
            vx, vy = end[0] - start[0], end[1] - start[1]
            length = math.hypot(vx, vy)
            for endpoint in (start, end):
                touching = [a for a in arcs if
                            math.dist(endpoint, a[4]) <= 1e-7 or
                            math.dist(endpoint, a[5]) <= 1e-7]
                if len(touching) != 1:
                    raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
                arc = touching[0]
                radial_dot = ((endpoint[0] - arc[0]) * vx +
                              (endpoint[1] - arc[1]) * vy)
                if abs(radial_dot) > 1e-7 * max(1.0, arc[2] * length):
                    raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
        dx, dy = arcs[1][0] - arcs[0][0], arcs[1][1] - arcs[0][1]
        distance = math.hypot(dx, dy)
        if distance <= 1e-10:
            raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE")
        return {
            "width_mm": 2 * arcs[0][2],
            "center_distance_mm": distance,
            "overall_length_mm": 2 * arcs[0][2] + distance,
            "midpoint": ((arcs[0][0] + arcs[1][0]) / 2, (arcs[0][1] + arcs[1][1]) / 2),
            "axis_unit": (dx / distance, dy / distance),
        }
    except SlotAnchorError:
        raise
    except (TypeError, ValueError, IndexError, ZeroDivisionError) as exc:
        raise SlotAnchorError("SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE") from exc
