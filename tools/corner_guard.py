"""Corner inventory gate: no automatic Laser R on a corner that is DRAWN rounded/chamfered without a callout.

User-approved 2026-10-20: a corner that the drawing shows with an R/C shape but that has no
R/C callout is NOT silently rounded by the material table; it is FLAGGED locally (the flat
keeps the drawn corner as preview geometry or no geometry) until the callout is resolved.
Automatic material R (MATERIAL_AUTO_R, data/material_rules.md) applies only to corners the
drawing shows SHARP and that no callout covers.

Inventory (optional for legacy jobs; REQUIRED as soon as any MATERIAL_AUTO_R member exists):

  "corner_inventory": [
    {"corner_id": "C1", "point": [x, y], "drawn_shape": "SHARP|ROUNDED|CHAMFERED|UNKNOWN",
     "decision": "CALLED|AUTO_R|FLAG|SHARP", "canonical_member_id": "...", "evidence_ref": "...",
     "no_auto_r_reason": "..."}   # SHARP decision only
  ]

When an outer LWPOLYLINE exists, every sharp convex corner of <= 90 degrees on it must have an
inventory row at its point (census closure), so a corner cannot be skipped silently.
"""
from __future__ import annotations

import math

DECISIONS = {"CALLED", "AUTO_R", "FLAG", "SHARP"}
SHAPES = {"SHARP", "ROUNDED", "CHAMFERED", "UNKNOWN"}
AUTO_RULE = "MATERIAL_AUTO_R"
POINT_TOL = 1e-3


def _finite_point(value):
    if (not isinstance(value, (list, tuple)) or len(value) < 2 or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value[:2])):
        return None
    return float(value[0]), float(value[1])


def outer_sharp_corners(part):
    """Sharp convex corners <= 90 degrees (+1e-6) of every outer LWPOLYLINE (no bulge on adjacent segments)."""
    corners = []
    for entity in part.get("entities", []):
        if entity.get("type") != "LWPOLYLINE" or entity.get("role") != "outer" or not entity.get("closed", True):
            continue
        verts = entity.get("vertices", [])
        pts = [_finite_point(v) for v in verts]
        if len(pts) < 3 or any(p is None for p in pts):
            continue
        bulges = [float(v[3]) if len(v) > 3 and isinstance(v[3], (int, float)) else 0.0 for v in verts]
        area2 = sum(pts[i][0]*pts[(i+1) % len(pts)][1] - pts[(i+1) % len(pts)][0]*pts[i][1] for i in range(len(pts)))
        if abs(area2) < 1e-9:
            continue
        sign = 1.0 if area2 > 0 else -1.0
        n = len(pts)
        for i in range(n):
            if bulges[i] or bulges[i-1]:
                continue  # arc end, not a sharp corner
            p0, p1, p2 = pts[i-1], pts[i], pts[(i+1) % n]
            a = (p0[0]-p1[0], p0[1]-p1[1])
            b = (p2[0]-p1[0], p2[1]-p1[1])
            la, lb = math.hypot(*a), math.hypot(*b)
            if la < 1e-9 or lb < 1e-9:
                continue
            cross = (p1[0]-p0[0])*(p2[1]-p1[1]) - (p1[1]-p0[1])*(p2[0]-p1[0])
            if cross*sign <= 1e-9:
                continue  # concave or straight
            cosang = max(-1.0, min(1.0, (a[0]*b[0]+a[1]*b[1])/(la*lb)))
            if math.degrees(math.acos(cosang)) <= 90.0 + 1e-6:
                corners.append(p1)
    return corners


def corner_errors(part):
    members = {m.get("canonical_member_id"): m for m in part.get("canonical_members", [])}
    auto_ids = {mid for mid, m in members.items() if m.get("controlling_rule") == AUTO_RULE}
    inventory = part.get("corner_inventory")
    if inventory is None:
        return ["CORNER_INVENTORY_MISSING"] if auto_ids else []
    if not isinstance(inventory, list) or any(not isinstance(r, dict) for r in inventory):
        return ["CORNER_INVENTORY_INVALID"]
    errors, seen, auto_owned = [], set(), set()
    for row in inventory:
        cid = row.get("corner_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            errors.append(f"CORNER_INVENTORY_INVALID:{cid}")
            continue
        seen.add(cid)
        decision, shape = row.get("decision"), row.get("drawn_shape")
        if decision not in DECISIONS or shape not in SHAPES or _finite_point(row.get("point")) is None \
                or not row.get("evidence_ref"):
            errors.append(f"CORNER_INVENTORY_INVALID:{cid}")
            continue
        mid = row.get("canonical_member_id")
        member = members.get(mid)
        if shape != "SHARP" and decision not in {"CALLED", "FLAG"}:
            errors.append(f"CORNER_DRAWN_SHAPE_WITHOUT_CALLOUT_NOT_FLAGGED:{cid}")
        if decision == "AUTO_R":
            if (shape != "SHARP" or member is None or mid not in auto_ids or member.get("status") != "PROVED"):
                errors.append(f"CORNER_AUTO_R_UNPROVED:{cid}")
            elif mid in auto_owned:
                errors.append(f"CORNER_AUTO_R_MEMBER_SHARED:{cid}")
            else:
                auto_owned.add(mid)
        elif decision == "CALLED":
            if member is None or member.get("origin") != "SOURCE" or member.get("controlling_rule") == AUTO_RULE:
                errors.append(f"CORNER_CALLOUT_MEMBER_UNPROVED:{cid}")
        elif decision == "FLAG":
            if mid in auto_ids:
                errors.append(f"CORNER_FLAG_HAS_AUTO_R:{cid}")
            if part.get("status") == "PASS":
                errors.append(f"CORNER_FLAG_UNRESOLVED:{cid}")
        elif decision == "SHARP":
            if shape != "SHARP" or not row.get("no_auto_r_reason") or mid in auto_ids:
                errors.append(f"CORNER_SHARP_UNPROVED:{cid}")
    for mid in sorted(auto_ids - auto_owned):
        errors.append(f"CORNER_AUTO_R_MEMBER_UNOWNED:{mid}")
    points = [p for p in (_finite_point(r.get("point")) for r in inventory) if p]
    for corner in outer_sharp_corners(part):
        if not any(math.dist(corner, p) <= POINT_TOL for p in points):
            errors.append(f"CORNER_CENSUS_MISSING:({corner[0]:.3f},{corner[1]:.3f})")
    return sorted(set(errors))


def draft_inventory(part):
    """Skeleton rows for every sharp convex corner (<= 90 degrees) of the outer polyline.

    Every row starts as drawn_shape UNKNOWN / decision FLAG on purpose: the reader must look at the drawing
    and set drawn_shape (and CALLED / AUTO_R / SHARP) per corner; nothing is defaulted to automatic R.
    """
    return [{"corner_id": f"C{i}", "point": [round(x, 6), round(y, 6)], "drawn_shape": "UNKNOWN",
             "decision": "FLAG", "evidence_ref": "TODO: drawing evidence for this corner's drawn shape"}
            for i, (x, y) in enumerate(outer_sharp_corners(part), 1)]
