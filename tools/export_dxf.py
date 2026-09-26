#!/usr/bin/env python3
"""TrainAiCad V4.7: serialize independently verified flat geometry to DXF.

Input is canonical geometry that has ALREADY passed the approved drawing
interpretation, tolerance, material, unfold and manufacturing checks.  This
serializer adds structural/packaging checks; it does NOT read or interpret PDFs.
Requires ezdxf>=1.4. See tools/DXF_INPUT_SCHEMA.md.
"""
import argparse
import json
import math
import re
from pathlib import Path

import ezdxf
from ezdxf import bbox

CHECKS = ("contour_topology", "datum", "feature_count", "unfold", "containment",
          "bend_domain", "material_rules", "slot_semantics")
TYPES = {"LWPOLYLINE", "CIRCLE", "LINE", "ARC", "POINT", "TEXT"}
CUT_ROLES = {"outer", "cutout", "hole", "slot"}


def fail(message):
    raise ValueError(message)


def number(value, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"{context}: finite numeric value required")
    return float(value)


def point(value, context):
    if not isinstance(value, list) or len(value) != 2:
        fail(f"{context}: expected [x, y]")
    return (number(value[0], context), number(value[1], context))


def safe_name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        fail("job_id/code: use 1-64 ASCII letters, digits, underscore or hyphen")
    return value


def signed_poly_area(vertices):
    """Exact signed area of closed bulged LWPOLYLINE (straight + circular segment)."""
    area = 0.0
    for v, w in zip(vertices, vertices[1:] + vertices[:1]):
        x, y, bulge = v
        xx, yy = w[:2]
        area += (x * yy - xx * y) / 2
        if bulge:
            chord = math.hypot(xx - x, yy - y)
            theta = 4 * math.atan(bulge)
            radius = chord / (2 * abs(math.sin(theta / 2)))
            area += radius * radius * (theta - math.sin(theta)) / 2
    return area


def validate_entity(entity, part_code, preview):
    t = entity.get("type")
    role = entity.get("role")
    if t not in TYPES or not isinstance(role, str) or not role:
        fail(f"{part_code}: invalid entity type/role")
    if entity.get("layer", "0") != "0":
        fail(f"{part_code}: all entities must use Layer 0")
    col = entity.get("color", 256)
    if col not in (1, 3, 6, 256):
        fail(f"{part_code}: unsupported color {col}; V4.6 legend is mandatory")
    if role in ("outer", "cutout", "hole", "slot") and col not in (256, 6):
        fail(f"{part_code}: cut geometry cannot be red/green")
    if role == "ordinary_point" and (t != "POINT" or col != 256):
        fail(f"{part_code}: ordinary POINT must be ByLayer")
    if role == "through_piercing" and (t != "POINT" or col != 3):
        fail(f"{part_code}: PIERCING + THROUGH HOLE must be Green POINT")
    if role == "kegaki" and col != 1:
        fail(f"{part_code}: Kegaki must be Red")
    if role == "bend" and (t != "LINE" or entity.get("linetype") != "DASHED"):
        fail(f"{part_code}: bend must be double DASHED LINEs")
    if role == "estimated" and col != 6:
        fail(f"{part_code}: estimated geometry must be Magenta")
    if t == "TEXT" and (not preview or col != 6 or role != "estimated_note"):
        fail(f"{part_code}: TEXT only for adjacent Magenta preview notes")
    if t == "LWPOLYLINE":
        vertices = entity.get("vertices")
        if not isinstance(vertices, list) or len(vertices) < 2:
            fail(f"{part_code}: polyline requires vertices")
        for v in vertices:
            if not isinstance(v, list) or len(v) != 3:
                fail(f"{part_code}: vertex requires [x,y,bulge]")
            for n in v:
                number(n, f"{part_code} polyline")
        if role in ("outer", "cutout", "slot") and (not entity.get("closed") or len(vertices) < 3):
            fail(f"{part_code}: outer, cutout and slot must be closed polylines")
        if entity.get("closed") and vertices[0][:2] == vertices[-1][:2]:
            fail(f"{part_code}: omit duplicate closing vertex; use closed=true")
        if entity.get("closed") and role in ("outer", "cutout", "slot"):
            area = signed_poly_area(vertices)
            if (role == "outer" and area <= 0) or (role in ("cutout", "slot") and area >= 0):
                fail(f"{part_code}: wrong winding or degenerate closed {role} polyline")
    elif t == "CIRCLE":
        point(entity.get("center"), f"{part_code} circle")
        if number(entity.get("radius"), f"{part_code} radius") <= 0:
            fail(f"{part_code}: radius must be positive")
    elif t == "POINT":
        point(entity.get("point"), f"{part_code} POINT")
    elif t == "LINE":
        a = point(entity.get("start"), f"{part_code} line")
        b = point(entity.get("end"), f"{part_code} line")
        if a == b:
            fail(f"{part_code}: zero-length LINE")
    elif t == "ARC":
        point(entity.get("center"), f"{part_code} arc")
        if number(entity.get("radius"), f"{part_code} arc radius") <= 0:
            fail(f"{part_code}: arc radius must be positive")
        number(entity.get("start_angle"), f"{part_code} arc start")
        number(entity.get("end_angle"), f"{part_code} arc end")
    elif t == "TEXT":
        point(entity.get("insert"), f"{part_code} text")
        if not entity.get("text") or number(entity.get("height", 2.5), f"{part_code} text height") <= 0:
            fail(f"{part_code}: invalid TEXT")
    if role == "slot" and t != "LWPOLYLINE":
        fail(f"{part_code}: slot must be one closed LWPOLYLINE")
    if role == "outer" and t != "LWPOLYLINE":
        fail(f"{part_code}: outline must be a LWPOLYLINE")
    if role == "cutout" and t != "LWPOLYLINE":
        fail(f"{part_code}: cutout must be a LWPOLYLINE")
    if role == "hole" and t != "CIRCLE":
        fail(f"{part_code}: round hole must be a CIRCLE")
    if col == 6 and not preview:
        fail(f"{part_code}: Magenta FLAG geometry cannot enter production DXF")


def validate_job(job):
    jid = safe_name(job.get("job_id"))
    parts = job.get("parts")
    if not isinstance(parts, list) or not parts:
        fail("Job must contain a nonempty ordered parts list")
    codes = set()
    for part in parts:
        code = safe_name(part.get("code"))
        if code in codes:
            fail(f"Duplicate code {code}; use unique code for each manufacturing part")
        codes.add(code)
        if not isinstance(part.get("material"), str) or not part["material"].strip():
            fail(f"{code}: material required")
        if number(part.get("thickness_mm"), f"{code} thickness") <= 0:
            fail(f"{code}: thickness must be positive")
        state = part.get("status")
        if state not in ("PASS", "PREVIEW"):
            fail(f"{code}: status must be PASS or PREVIEW; blocked parts must not be exported")
        checks = part.get("checks")
        if not isinstance(checks, dict) or any(checks.get(key) not in ("PASS", "N/A") for key in CHECKS):
            fail(f"{code}: all eight upstream semantic checks require explicit PASS/N/A evidence")
        if state == "PASS" and (part.get("flags") or any(e == "N/A" for e in (checks[k] for k in ("contour_topology", "datum", "feature_count", "containment", "material_rules")))):
            fail(f"{code}: production PASS requires no flags and applicable critical checks")
        if state == "PREVIEW" and (not part.get("flags") or part.get("preview_reason") != "numeric_only_known_topology"):
            fail(f"{code}: preview permitted ONLY for numeric uncertainty on proved topology with flags")
        ents = part.get("entities")
        if not isinstance(ents, list) or not ents:
            fail(f"{code}: entities required")
        for ent in ents:
            validate_entity(ent, code, state == "PREVIEW")
        if sum(ent.get("role") == "outer" for ent in ents) != 1:
            fail(f"{code}: exactly one proved closed outside contour required")
        if state == "PREVIEW" and not (any(e.get("color") == 6 for e in ents) and any(e.get("type") == "TEXT" for e in ents)):
            fail(f"{code}: preview requires Magenta geometry AND adjacent Magenta TEXT")
    return jid


