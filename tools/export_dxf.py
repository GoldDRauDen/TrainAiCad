#!/usr/bin/env python3
"""Serialize checked canonical geometry to ONE labeled combined DXF (library of export_canonical_dxf.py).

Input is canonical geometry that has ALREADY passed the approved drawing
interpretation, tolerance, material, unfold and manufacturing checks.  This
serializer adds structural/packaging checks; it does NOT read or interpret PDFs.
Requires ezdxf>=1.4. Input: tools/CANONICAL_SCHEMA.md.
"""
import json
import math
import re
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.enums import TextEntityAlignment

import geom

CHECKS = ("contour_topology", "datum", "feature_count", "unfold", "containment",
          "bend_domain", "material_rules", "slot_semantics")
TYPES = {"LWPOLYLINE", "CIRCLE", "LINE", "ARC", "POINT", "TEXT"}
CUT_ROLES = {"outer", "cutout", "hole", "slot"}

# Output rules (user-approved). Canonical input may keep LWPOLYLINE;
# every saved DXF writes outlines/cutouts/slots as separate LINE and ARC entities.
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "CAD_OUTPUT_TEMPLATE.dxf"
JLJ_TEXT_HEIGHT_MM = 10.0         # J/LJ TEXT height (template sample)
JLJ_INSET_MM = 30.0               # first J / LJ sit 30 mm inside the ends of the top (max Y) edge
COMPOSITE_GAP_MM = 150.0          # edge-to-edge between code clusters in the combined DXF
SOURCE_VIEW_GAP_MM = 10.0         # separation between VIEWS_ONLY source views inside one code
# Label sizes/positions follow the sample layout stored in templates/CAD_OUTPUT_TEMPLATE.dxf
# (100x100 sample part: code label h10 baseline 10 mm above the outline, dx h20 right edge 23 mm
# left of the outline, FLAG h15 at 49 mm right of the outline with 25 mm line pitch).
CODE_LABEL_OFFSET_MM = 10.0       # code label baseline sits 10 mm above its cluster
CODE_LABEL_HEIGHT_MM = 10.0
LABEL_RESERVE_MM = CODE_LABEL_OFFSET_MM + CODE_LABEL_HEIGHT_MM  # space the label takes above a cluster
DX_LABEL_HEIGHT_MM = 20.0
DX_LABEL_CLEARANCE_MM = 23.0
FLAG_LABEL_CLEARANCE_MM = 49.0
FLAG_LABEL_HEIGHT_MM = 15.0
FLAG_LINE_PITCH_MM = 25.0       # one horizontal FLAG line per flag, stacked top to bottom
REVIEW_BANNER = "CHỈ XEM XÉT - KHÔNG CẮT - CÒN MÃ CHƯA GIẢI QUYẾT"  # all DXF notes are Vietnamese (JOB_CARD.md item 10)
LABEL_COLOR = 7                   # every AI_META note is white (AutoCAD colour 7), whatever the part status
PIECE_SEPARATOR = ":S"            # canonical entity piece id: <entity_id>:S0001


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
        fail(f"{part_code}: unsupported color {col}; the colour legend is mandatory")
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
    if role == "mark" and (col != 256 or t not in ("POINT", "TEXT")):
        fail(f"{part_code}: J/LJ mark must be ByLayer POINT or TEXT")
    if t == "TEXT" and role == "mark":
        if entity.get("text") not in ("J", "LJ") or entity.get("height") != JLJ_TEXT_HEIGHT_MM:
            fail(f"{part_code}: mark TEXT must be J or LJ, height 10")
    elif t == "TEXT" and (not preview or col != 6 or role != "estimated_note"):
        fail(f"{part_code}: source TEXT only for adjacent Magenta preview notes; code labels are generated in AI_META")
    if t == "LWPOLYLINE":
        vertices = entity.get("vertices")
        if not isinstance(vertices, list) or len(vertices) < 2:
            fail(f"{part_code}: polyline requires vertices")
        for v in vertices:
            if not isinstance(v, list) or len(v) != 3:
                fail(f"{part_code}: vertex requires [x,y,bulge]")
            for n in v:
                number(n, f"{part_code} polyline")
        segs = entity.get("flag_segments")
        if segs is not None:
            n_seg = len(vertices) if entity.get("closed") else len(vertices) - 1
            if (not isinstance(segs, list) or not segs or
                    any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < n_seg for i in segs)):
                fail(f"{part_code}: flag_segments must list segment indices of the polyline")
            if role != "outer" or col != 256:
                fail(f"{part_code}: flag_segments only on an uncoloured outer polyline")
        arc_closed = len(vertices) == 2 and any(v[2] for v in vertices)   # D-shaped loop: chord + arc
        if role in ("outer", "cutout", "slot") and (not entity.get("closed") or (len(vertices) < 3 and not arc_closed)):
            fail(f"{part_code}: outer, cutout and slot must be closed polylines")
        if entity.get("closed") and vertices[0][:2] == vertices[-1][:2]:
            fail(f"{part_code}: omit duplicate closing vertex; use closed=true")
        if entity.get("closed") and role in ("outer", "cutout", "slot"):
            area = signed_poly_area(vertices)
            if ((role == "outer" and area <= 0) or
                    (role in ("cutout", "slot") and abs(area) <= 1e-10) or
                    (role == "cutout" and area >= 0)):
                fail(f"{part_code}: wrong winding or degenerate closed {role} polyline")
            if role == "slot" and area > 0:
                # A proved convex stadium has identical physical CUT geometry
                # in CW and CCW. Do not relax winding for arbitrary cutouts.
                from slot_anchor import SlotAnchorError, stadium_geometry
                try:
                    stadium_geometry(vertices)
                except SlotAnchorError:
                    fail(f"{part_code}: CCW slot needs valid stadium geometry")
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


def jlj_marks_check(part):
    """Laser_SheetMetal J/LJ: blank Oy<=100 and Ox>=1000 -> POINT+TEXT on the top edge, x = X1+30 .. X2-30 evenly (X1/X2 = left/right ends of the max-Y edge)."""
    code = part.get("code", "?")
    outer = [e for e in part["entities"] if e.get("role") == "outer"]
    marks = [e for e in part["entities"] if e.get("role") == "mark"]
    xs = [v[0] for e in outer for v in e["vertices"]]
    ys = [v[1] for e in outer for v in e["vertices"]]
    length, width = max(xs) - min(xs), max(ys) - min(ys)
    if not (width <= 100 + 1e-6 and length >= 1000 - 1e-6):
        if marks:
            fail(f"{code}: J/LJ marks only for blank Oy<=100 and Ox>=1000")
        return
    if length > 2500:
        fail(f"{code}: J/LJ count undefined for L>2500; flag instead of guessing")
    n = 2 + (length > 1500) + (length > 2000)  # J count + 1 LJ
    top = max(ys)
    # Top (max Y) material edge first: X1 / X2 are its left / right ends, so a chamfer
    # C5 on the left and C2 on the right give 35 and L-32 for a rectangle-like blank.
    top_edges = []
    for ent in outer:
        vertices = ent["vertices"]
        segments = (vertices + vertices[:1]) if ent.get("closed") else vertices
        for a, b in zip(segments, segments[1:]):
            if (abs(a[2]) <= 1e-10 and
                    abs(a[1] - top) <= 1e-6 and abs(b[1] - top) <= 1e-6):
                top_edges.append((min(a[0], b[0]), max(a[0], b[0])))
    if not top_edges:
        fail(f"{code}: J/LJ_MARKS_NOT_ON_TOP_MATERIAL_EDGE")
    x_first = min(left for left, _ in top_edges) + JLJ_INSET_MM
    x_last = max(right for _, right in top_edges) - JLJ_INSET_MM
    want = [(x_first + i * (x_last - x_first) / (n - 1), top, "LJ" if i == n - 1 else "J") for i in range(n)]
    if any(not any(left - 1e-6 <= x <= right + 1e-6
                   for left, right in top_edges) for x, _, _ in want):
        fail(f"{code}: J/LJ_MARKS_NOT_ON_TOP_MATERIAL_EDGE")
    pts = sorted((round(e["point"][0], 6), round(e["point"][1], 6)) for e in marks if e["type"] == "POINT")
    txt = sorted((round(e["insert"][0], 6), round(e["insert"][1], 6), e["text"]) for e in marks if e["type"] == "TEXT")
    if pts != [(round(x, 6), round(y, 6)) for x, y, _ in want] or \
            txt != [(round(x, 6), round(y, 6), t) for x, y, t in want]:
        fail(f"{code}: J/LJ_MARKS_MISSING_OR_WRONG expected {[(round(x, 3), t) for x, _, t in want]}")


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
        if "dx_label" in part and not isinstance(part["dx_label"], bool):
            fail(f"{code}: dx_label must be true or false")
        if state not in ("PASS", "PREVIEW", "VIEWS_ONLY", "REVIEW"):
            fail(f"{code}: invalid status, expected PASS/PREVIEW/VIEWS_ONLY/REVIEW")
        checks = part.get("checks")
        permitted = ("PASS", "N/A", "FLAGGED") if state == "VIEWS_ONLY" else ("PASS", "N/A")
        if not isinstance(checks, dict) or any(checks.get(key) not in permitted for key in CHECKS):
            fail(f"{code}: all eight upstream semantic checks require explicit PASS/N/A (or VIEWS_ONLY FLAGGED) evidence")
        if state == "PASS" and (part.get("flags") or any(e == "N/A" for e in (checks[k] for k in ("contour_topology", "datum", "feature_count", "containment", "material_rules")))):
            fail(f"{code}: production PASS requires no flags and applicable critical checks")
        if state == "PREVIEW" and (not part.get("flags") or part.get("preview_reason") != "numeric_only_known_topology"):
            fail(f"{code}: preview permitted ONLY for numeric uncertainty on proved topology with flags")
        if state == "REVIEW" and (
            part.get("review_reason") != "HL_DIRECTION_UNPROVED" or not part.get("flags") or
            not part.get("grain", {}).get("is_hl") or
            part.get("grain", {}).get("direction_xy") is not None
        ):
            fail(f"{code}: REVIEW requires unresolved HL direction, not guessed geometry")
        if state == "VIEWS_ONLY" and (not part.get("flags") or part.get("preview_reason") != "separate_source_views"):
            fail(f"{code}: VIEWS_ONLY requires independently proved source views, reason and unresolved flags")
        ents = part.get("entities")
        if not isinstance(ents, list) or not ents:
            fail(f"{code}: entities required")
        for ent in ents:
            validate_entity(ent, code, state != "PASS")
            if state == "VIEWS_ONLY" and ent["type"] != "TEXT":
                safe_name(ent.get("view_id"))
        if state != "VIEWS_ONLY" and sum(ent.get("role") == "outer" for ent in ents) != 1:
            fail(f"{code}: exactly one proved closed outside contour required")
        if state != "VIEWS_ONLY":
            jlj_marks_check(part)
        if state == "VIEWS_ONLY" and not any(ent["type"] != "TEXT" for ent in ents):
            fail(f"{code}: no proved source-view geometry")
        if state == "PREVIEW" and not any(e.get("color") == 6 or e.get("flag_segments") for e in ents):
            fail(f"{code}: preview requires Magenta geometry (the flagged entity); the FLAG note is generated on AI_META")
    return jid


def arc_from_bulge(start, end, bulge):
    """Analytic bulge -> CCW ARC (center, radius, start_deg, end_deg); a curve that cannot be exact fails."""
    try:
        return geom.arc_from_bulge(start, end, bulge)
    except geom.GeometryError as exc:
        fail(str(exc))


def emit_entity(msp, ent, dx=0.0, dy=0.0):
    """Write one canonical entity translated by (dx, dy). Returns the created DXF entities.

    LWPOLYLINE is exploded into LINE/ARC pieces (a full circle becomes one CIRCLE), so saved cut geometry never
    contains LWPOLYLINE. A closed polyline yields one piece per segment, including the
    closing segment; an open polyline yields n-1 pieces.
    """
    attrs = {"layer": "0"}
    if ent.get("color", 256) != 256:
        attrs["color"] = ent["color"]
    if ent.get("linetype"):
        attrs["linetype"] = ent["linetype"]

    def move(v):
        return (v[0] + dx, v[1] + dy)

    t = ent["type"]
    if t == "LWPOLYLINE":
        vertices = ent["vertices"]
        circle = geom.full_circle(vertices, bool(ent.get("closed")))
        if circle:   # a full circle is ONE CIRCLE, never two ARCs
            return [msp.add_circle(move(circle[0]), circle[1], dxfattribs=attrs)]
        n = len(vertices)
        segments = n if ent.get("closed") else n - 1
        flagged = set(ent.get("flag_segments") or [])     # only these pieces are Magenta (local FLAG, e.g. one R or C)
        pieces = []
        for i in range(segments):
            a = vertices[i]
            b = vertices[(i + 1) % n]
            if a[:2] == b[:2]:
                fail("zero-length polyline segment")
            piece_attrs = {**attrs, "color": 6} if i in flagged else attrs
            if a[2] == 0:
                pieces.append(msp.add_line(move(a[:2]), move(b[:2]), dxfattribs=piece_attrs))
            else:
                center, radius, sa, ea = arc_from_bulge(a[:2], b[:2], a[2])
                pieces.append(msp.add_arc(move(center), radius, sa, ea, dxfattribs=piece_attrs))
        return pieces
    if t == "CIRCLE":
        return [msp.add_circle(move(ent["center"]), ent["radius"], dxfattribs=attrs)]
    if t == "LINE":
        return [msp.add_line(move(ent["start"]), move(ent["end"]), dxfattribs=attrs)]
    if t == "ARC":
        return [msp.add_arc(move(ent["center"]), ent["radius"],
                            ent["start_angle"], ent["end_angle"], dxfattribs=attrs)]
    if t == "POINT":
        return [msp.add_point(move(ent["point"]), dxfattribs=attrs)]
    if t == "TEXT":
        attrs["height"] = ent.get("height", 2.5)
        attrs["insert"] = move(ent["insert"])
        return [msp.add_text(ent["text"], dxfattribs=attrs)]
    fail(f"Unknown entity type {t}")


def piece_ids(entity_id, count):
    """Canonical ENTITY_ID per written DXF piece: plain id for one piece, else id:S0001..."""
    if count == 1:
        return [entity_id]
    return [f"{entity_id}{PIECE_SEPARATOR}{i + 1:04d}" for i in range(count)]


def source_entity_id(piece_id):
    return piece_id.split(PIECE_SEPARATOR, 1)[0]


def new_doc():
    """start from the approved CAD output template (environment, dimstyles, DASHED).

    Only the unit declaration is overridden: coordinates are millimetres. The modelspace
    must be empty; DIM dimensions are never written into CUT output.

    The template file carries a sample layout (part, labels, J/LJ marks) as the visual spec of
    text style, text sizes and POINT/TEXT placement. Those sample entities are removed here;
    the sizes live in the constants above and tests/test_cad_output_template.py keeps them in sync.
    """
    if not TEMPLATE.exists():
        fail(f"CAD output template missing: {TEMPLATE.name}")
    doc = ezdxf.readfile(TEMPLATE)
    doc.modelspace().delete_all_entities()
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    if "DASHED" not in doc.linetypes:
        doc.linetypes.new("DASHED", dxfattribs={"pattern": [4.0, 2.0, -2.0], "description": "2 mm dash, 2 mm gap"})
    return doc


def extents_of(doc):
    ext = bbox.extents(doc.modelspace(), fast=False)
    if not ext.has_data:
        fail("No bounded CAD geometry to export")
    return [round(ext.extmin.x, 6), round(ext.extmin.y, 6),
            round(ext.extmax.x, 6), round(ext.extmax.y, 6)]


def entity_signature(ent):
    """Coordinate/attribute fingerprint including arc bulges for saved-DXF roundtrip."""
    t = ent.dxftype()
    attrs = (t, ent.dxf.layer, ent.dxf.get("color", 256), ent.dxf.get("linetype", "BYLAYER"))
    def xy(v):
        return (round(v[0], 6), round(v[1], 6))
    if t == "LWPOLYLINE":
        geometry = (ent.closed, tuple((round(x, 6), round(y, 6), round(b, 8)) for x, y, b in ent.get_points("xyb")))
    elif t == "CIRCLE":
        geometry = (xy(ent.dxf.center), round(ent.dxf.radius, 6))
    elif t == "POINT":
        geometry = xy(ent.dxf.location)
    elif t == "LINE":
        geometry = (xy(ent.dxf.start), xy(ent.dxf.end))
    elif t == "ARC":
        geometry = (xy(ent.dxf.center), round(ent.dxf.radius, 6), round(ent.dxf.start_angle, 6), round(ent.dxf.end_angle, 6))
    elif t == "TEXT":
        geometry = (xy(ent.dxf.insert), ent.dxf.text, round(ent.dxf.height, 6))
    else:
        fail(f"Unexpected written DXF entity {t}")
    return (attrs, geometry)


def write_and_audit(doc, target, expected_count):
    before = [entity_signature(ent) for ent in doc.modelspace()]
    doc.saveas(target)
    loaded = ezdxf.readfile(target)
    errors = loaded.audit()
    if errors.has_errors:
        fail(f"DXF audit failed: {target.name}")
    ents = list(loaded.modelspace())
    if len(ents) != expected_count or any(ent.dxf.layer != "0" and
            not (ent.dxf.layer == "AI_META" and ent.dxftype() == "TEXT") for ent in ents):
        fail(f"DXF read-back/layer/entity-count failure: {target.name}")
    if "AI_META" in loaded.layers and loaded.layers.get("AI_META").dxf.get("plot", 1) != 0:
        fail(f"AI_META must be non-plot annotation: {target.name}")
    if loaded.header["$INSUNITS"] != 4:
        fail(f"DXF unit failure: {target.name}")
    # CUT output is LINE/ARC/CIRCLE/POINT only; DIM is for the checker, never cut output.
    if any(ent.dxftype() == "LWPOLYLINE" for ent in ents if ent.dxf.layer == "0"):
        fail(f"output rule: LWPOLYLINE must be exploded to LINE/ARC: {target.name}")
    if any(ent.dxftype() == "DIMENSION" or ent.dxf.layer == "DIM" for ent in loaded.modelspace()):
        fail(f"output rule: dimensions cannot enter CUT DXF: {target.name}")
    if [entity_signature(ent) for ent in ents] != before:
        fail(f"DXF entity/coordinate/attribute roundtrip mismatch: {target.name}")
    return extents_of(loaded)


def source_view_boxes(part):
    """Source-view extents only; used to prove independently separated projections."""
    groups = {}
    for ent in part["entities"]:
        if ent["type"] != "TEXT":
            groups.setdefault(ent["view_id"], []).append(ent)
    boxes = {}
    for vid, ents in groups.items():
        doc = new_doc()
        for ent in ents:
            emit_entity(doc.modelspace(), ent)
        boxes[vid] = extents_of(doc)
    ids = list(boxes)
    for i, first in enumerate(ids):
        for second in ids[i + 1:]:
            a, b = boxes[first], boxes[second]
            x_gap = max(b[0] - a[2], a[0] - b[2])
            y_gap = max(b[1] - a[3], a[1] - b[3])
            if max(x_gap, y_gap) < SOURCE_VIEW_GAP_MM - 1e-6:
                fail(f"{part['code']}: source views {first}/{second} must be separated by >=10 mm")
    return boxes


def export_single_job(job, output_dir, gap_mm=COMPOSITE_GAP_MM, write_manifest=False):
    """One composite : code-labelled, top-to-bottom, 150 mm between code clusters.

    Cluster = outline bounding box plus its code label above the outline. The 150 mm gap
    is measured from the bottom of the upper outline to the top of the lower cluster label.
    'dx' (20 mm, left, centred) marks a PDF back-face part; FLAG (top-right, reading
    downward) marks any part with flags. Individual CUT files never carry labels.
    """
    jid = validate_job(job)
    gap_mm = number(gap_mm, "gap_mm")
    if gap_mm < COMPOSITE_GAP_MM:
        fail("Composite drawing requires at least 150 mm between part outlines")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    parts = job["parts"]
    review = any(p["status"] != "PASS" or p.get("flags") for p in parts)
    records = []
    for p in parts:
        scratch = new_doc()
        count = 0
        for e in p["entities"]:
            count += len(emit_entity(scratch.modelspace(), e))
        view_boxes = source_view_boxes(p) if p["status"] == "VIEWS_ONLY" else {}
        records.append({"code": p["code"], "material": p["material"],
                        "thickness_mm": p["thickness_mm"], "status": p["status"],
                        "bbox_mm": extents_of(scratch), "entity_count": count,
                        "flags": p.get("flags", []), "checks": p["checks"],
                        "dx_label": bool(p.get("dx_label", False)),
                        "hl_label": bool(p.get("grain", {}).get("is_hl", False)),
                        "source_view_boxes": view_boxes})
    stack_height = (sum(r["bbox_mm"][3] - r["bbox_mm"][1] for r in records)
                    + (len(records) - 1) * (gap_mm + LABEL_RESERVE_MM))
    merged = new_doc()
    merged.layers.new("AI_META", dxfattribs={"color": LABEL_COLOR, "plot": 0})
    merged.appids.new("AICAD")
    msp = merged.modelspace()
    layout = []
    expected_geometry = []
    geometry_ids = []
    expected_labels = []
    dx_expected = 0
    hl_expected = 0
    annotation_count = 0
    cursor = stack_height

    def label(text_value, where, color=LABEL_COLOR, height=CODE_LABEL_HEIGHT_MM, align=None, rotation=0.0):
        nonlocal annotation_count
        attrs = {"layer": "AI_META", "color": color, "height": height, "rotation": rotation}
        if align is None:
            attrs["insert"] = where
        obj = msp.add_text(text_value, dxfattribs=attrs)
        if align is not None:
            obj.set_placement(where, align=align)
        obj.set_xdata("AICAD", [(1000, "NON_CUT_ANNOTATION")])
        annotation_count += 1
        return obj

    for p, rec in zip(parts, records):
        xmin, ymin, xmax, ymax = rec["bbox_mm"]
        h = ymax - ymin
        bottom = cursor - h
        dx, dy = -xmin, bottom - ymin
        before = len(expected_geometry)
        for index, e in enumerate(p["entities"]):
            objs = emit_entity(msp, e, dx, dy)
            # Canonical jobs always carry entity_id; ad hoc composites get a stable local id.
            entity_id = e.get("entity_id") or f"{p['code']}.E{index:04d}"
            for obj, pid in zip(objs, piece_ids(entity_id, len(objs))):
                expected_geometry.append(entity_signature(obj))
                geometry_ids.append(pid)
        if len(expected_geometry) - before != rec["entity_count"]:
            fail(f"{p['code']}: source-to-composite piece count changed")
        code_label = p["code"]            # the drawing code only; the FLAG notes stand at the right
        label(code_label, (0.0, cursor + CODE_LABEL_OFFSET_MM))
        expected_labels.append(code_label)
        for index, flag in enumerate(p.get("flags", [])):
            label(f"FLAG: {flag}",
                  (xmax - xmin + FLAG_LABEL_CLEARANCE_MM, cursor - index * FLAG_LINE_PITCH_MM),
                  height=FLAG_LABEL_HEIGHT_MM, align=TextEntityAlignment.TOP_LEFT)
        left_notes = (["dx"] if rec["dx_label"] else []) + (["HL"] if rec["hl_label"] else [])
        for k, note in enumerate(left_notes):          # left of the part: dx (inner face), HL (hairline), stacked downward
            label(note, (-DX_LABEL_CLEARANCE_MM, bottom + h / 2 - k * 2 * DX_LABEL_HEIGHT_MM), height=DX_LABEL_HEIGHT_MM,
                  align=TextEntityAlignment.MIDDLE_RIGHT)
        dx_expected += int(rec["dx_label"])
        hl_expected += int(rec["hl_label"])
        if p["status"] == "VIEWS_ONLY":
            for view_id, bounds in rec["source_view_boxes"].items():
                label(p["code"] + " VIEW " + view_id, (bounds[0] + dx, bounds[3] + dy + CODE_LABEL_OFFSET_MM))
        placed = [0.0, bottom, xmax - xmin, cursor]
        layout.append({"code": p["code"], "status": p["status"],
                       "translation_mm": [round(dx, 6), round(dy, 6)],
                       "combined_bbox_mm": [round(v, 6) for v in placed],
                       "entity_count": rec["entity_count"]})
        cursor = bottom - gap_mm - LABEL_RESERVE_MM
    if review:
        # above the first code label (baseline +10, height 10) so the two never overlap
        label(REVIEW_BANNER, (0, stack_height + LABEL_RESERVE_MM + 10))
    filename = f"{jid}_ALL_REVIEW_ONLY.dxf" if review else f"{jid}_ALL.dxf"
    target = out / filename
    write_and_audit(merged, target, len(expected_geometry) + annotation_count)
    loaded = ezdxf.readfile(target)
    actual_geometry = [entity_signature(e) for e in loaded.modelspace() if e.dxf.layer == "0"]
    if actual_geometry != expected_geometry:
        fail("Combined source geometry does not match canonical translated part-local geometry")
    labels = [e.dxf.text for e in loaded.modelspace() if e.dxf.layer == "AI_META"]
    if [x for x in labels if x in expected_labels] != expected_labels:
        fail("Missing or misordered code labels in combined DXF")
    if labels.count("dx") != dx_expected:
        fail("dx label count does not match PDF back-face parts")
    if labels.count("HL") != hl_expected:
        fail("HL label count does not match hairline parts")
    if review and REVIEW_BANNER not in labels:
        fail("REVIEW_ONLY output missing global NO CUT label")
    for upper, lower in zip(layout, layout[1:]):
        lower_label_top = lower["combined_bbox_mm"][3] + LABEL_RESERVE_MM
        if upper["combined_bbox_mm"][1] - lower_label_top < gap_mm - 1e-5:
            fail("Combined source-code clusters overlap or lack required 150 mm gap")
    manifest = {"contract": "TrainAiCad-DXF", "job_id": jid,
                "coordinate_units": "mm", "layout": "code-labeled top-to-bottom",
                "rules": "LINE/ARC output, 150 mm gap, dx/FLAG labels, template",
                "status": "REVIEW_ONLY" if review else "PASS",
                "filename": filename, "parts": records, "positions": layout,
                "entity_map": geometry_ids,
                "source": "independently checked canonical geometry",
                "warning": "AI_META is non-cut; review-only files are NEVER production CAD"}
    if write_manifest:
        (out / f"{jid}_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def export_job(job, output_dir, gap_mm=COMPOSITE_GAP_MM, write_manifest=False):
    return export_single_job(job, output_dir, gap_mm, write_manifest=write_manifest)
