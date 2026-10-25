#!/usr/bin/env python3
"""Verified PASS-only cut-contour DXF packaging (one DXF per PASS code, named by the slip work number).

The existing canonical composite exporter remains the source of drawing
identity, geometrical truth and review annotations. This module only
deterministically decomposes its approved cut entities and checks read-back.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf

from canonical_contract import CanonicalContractError
from export_dxf import arc_from_bulge as _arc_from_bulge, entity_signature, new_doc, safe_name
from cut_orientation import orient_cut_doc
from ezdxf.math import Matrix44

APPID = "TRAINAICAD"
CUT_ROLES = frozenset({"outer", "cutout", "slot", "hole", "relief", "slit", "cut"})
NONCUT_ROLES = frozenset({
    "bend", "kegaki", "ordinary_point", "through_piercing",
    "source_view", "construction", "reference", "measurement",
    "estimated", "estimated_note", "mark",
})
TOLERANCE = 1e-6


def fail(msg: str) -> None:
    raise CanonicalContractError(msg)


def _same(a, b, tol=TOLERANCE):
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol


def _endpoints(entity):
    typ = entity.dxftype()
    if typ == "LINE":
        return ((float(entity.dxf.start.x), float(entity.dxf.start.y)),
                (float(entity.dxf.end.x), float(entity.dxf.end.y)))
    if typ == "ARC":
        c = entity.dxf.center
        r = entity.dxf.radius
        angles = (entity.dxf.start_angle, entity.dxf.end_angle)
        return tuple((c.x + r * math.cos(math.radians(angle)),
                      c.y + r * math.sin(math.radians(angle)))
                     for angle in angles)
    fail(f"Cannot derive segment endpoints from {typ}")


def _decompose_polyline(modelspace, entity):
    vertices = entity["vertices"]
    closed = entity.get("closed") is True
    if not closed or len(vertices) < 3:
        fail(f"{entity['entity_id']}: cut contour must be a closed polyline")
    output = []
    for i in range(len(vertices)):
        a, b = vertices[i], vertices[(i + 1) % len(vertices)]
        if _same(a, b, tol=0):
            fail(f"{entity['entity_id']}: zero-length contour segment")
        bulge = a[2]
        if bulge == 0:
            obj = modelspace.add_line(a[:2], b[:2], dxfattribs={"layer": "0"})
        else:
            center, radius, sa, ea = _arc_from_bulge(a, b, bulge)
            obj = modelspace.add_arc(center, radius, sa, ea, dxfattribs={"layer": "0"})
        p, q = _endpoints(obj)
        if not ((_same(p, a) and _same(q, b)) or
                (_same(p, b) and _same(q, a))):
            fail(f"{entity['entity_id']}: analytic segment lost original endpoints")
        output.append((obj, f"{entity['entity_id']}:S{i + 1:04d}", entity["entity_id"]))
    # Geometrical connectivity uses the exact canonical contour vertices:
    # each segment attaches to the next without guessed bridging entities.
    return output


def _is_cut_entity(entity):
    role = entity.get("role")
    typ = entity["type"]
    if role in NONCUT_ROLES:
        return False
    if role not in CUT_ROLES:
        fail(f"{entity.get('entity_id')}: unclassified entity role {role}; no silent CUT omission")
    if entity.get("color", 256) == 6:
        fail(f"{entity['entity_id']}: FLAG geometry cannot enter parts_dxf")
    if role == "hole" and typ != "CIRCLE":
        fail("Only a verified CIRCLE may represent a round hole")
    if typ not in {"LINE", "ARC", "CIRCLE", "LWPOLYLINE"}:
        fail(f"{entity['entity_id']}: unsupported physical CUT entity {typ}")
    return True


def _native_cut(msp, ent):
    typ = ent["type"]
    # Standalone cut reliefs/slits remain LINE/ARC (not guessed into contours).
    if typ == "LINE":
        return msp.add_line(ent["start"], ent["end"], dxfattribs={"layer": "0"})
    if typ == "ARC":
        return msp.add_arc(ent["center"], ent["radius"], ent["start_angle"],
                           ent["end_angle"], dxfattribs={"layer": "0"})
    if typ == "CIRCLE":
        return msp.add_circle(ent["center"], ent["radius"], dxfattribs={"layer": "0"})
    fail(f"Unexpected CUT primitive: {typ}")


def _owner_map(part):
    owners = {}
    for member in part["canonical_members"]:
        for eid in member.get("entity_ids", []):
            owners.setdefault(eid, []).append(member["canonical_member_id"])
    return owners


def _inverse_signature_equal(source_sig, restored_sig):
    """ARC angle 0/360 and negative/positive turns are the same physical arc."""
    if source_sig[0] != restored_sig[0]:
        return False
    if source_sig[0][0] != "ARC":
        return source_sig == restored_sig
    ac, ar, a0, a1 = source_sig[1]
    bc, br, b0, b1 = restored_sig[1]
    def angle_match(a, b):
        return abs((a - b + 180) % 360 - 180) <= 2e-6
    return ac == bc and ar == br and angle_match(a0, b0) and angle_match(a1, b1)


def _xdata(entry):
    return [tag.value for tag in entry.get_xdata(APPID) if tag.code == 1000]


def _plan_cut_doc(part):
    if part["status"] != "PASS" or part.get("flags"):
        fail(f"{part['code']}: only QA PASS parts can emit an individual CUT DXF")
    doc = new_doc()
    if APPID not in doc.appids:
        doc.appids.new(APPID)
    owners = _owner_map(part)
    expected = []
    contour_count = 0
    cut_count = 0
    for ent in part["entities"]:
        if not _is_cut_entity(ent):
            continue
        if ent["entity_id"] not in owners:
            fail(f"{part['code']}/{ent['entity_id']}: CUT member has no canonical owner")
        cut_count += 1
        if ent["type"] == "LWPOLYLINE":
            if ent["role"] not in {"outer", "cutout", "slot", "cut"}:
                fail(f"{ent['entity_id']}: unexpected contour role")
            pieces = _decompose_polyline(doc.modelspace(), ent)
            contour_count += 1
        else:
            obj = _native_cut(doc.modelspace(), ent)
            pieces = [(obj, ent["entity_id"], ent["entity_id"])]
            if ent["type"] == "CIRCLE":
                contour_count += 1
        for obj, eid, parent in pieces:
            obj.set_xdata(APPID, [
                (1000, "ENTITY_ID=" + eid),
                (1000, "SOURCE_ENTITY_ID=" + parent),
                (1000, "CANONICAL_MEMBER_IDS=" + ",".join(owners[parent])),
            ])
            expected.append((entity_signature(obj), eid, parent,
                             tuple(owners[parent])))
    if not expected or not contour_count:
        fail(f"{part['code']}: no closed verified contour or circle for CUT")
    if not any(e["role"] == "outer" for e in part["entities"]):
        fail(f"{part['code']}: missing proved outside contour")
    orientation = orient_cut_doc(doc, part)
    updated = []
    for obj, (source_sig, eid, parent, members) in zip(doc.modelspace(), expected):
        # Reverse-check final physical geometry against the unrotated canonical
        # manufacturing curve, independently of saved-file signature equality.
        restored = obj.copy()
        dx, dy = orientation["translation_mm"]
        restored.transform(Matrix44.translate(-dx, -dy, 0))
        restored.transform(Matrix44.z_rotate(-math.radians(orientation["rotation_deg"])))
        if not _inverse_signature_equal(source_sig, entity_signature(restored)):
            fail(f"{part['code']}/{eid}: INVERSE_TRANSFORM_MISMATCH")
        updated.append((entity_signature(obj), eid, parent, members))
    return doc, updated, cut_count, contour_count, orientation


def _verify_cut(path, expected):
    try:
        loaded = ezdxf.readfile(path)
        if loaded.audit().has_errors or loaded.header["$INSUNITS"] != 4:
            fail(f"{path.name}: invalid DXF read-back/units")
        entities = list(loaded.modelspace())
        if len(entities) != len(expected):
            fail(f"{path.name}: lost or extra CUT entity")
        for entity, (sig, eid, parent, members) in zip(entities, expected):
            if entity.dxftype() not in {"LINE", "ARC", "CIRCLE"} or entity.dxf.layer != "0":
                fail(f"{path.name}: non CUT entity/layer found in parts_dxf")
            if entity.dxf.get("color", 256) == 6:
                fail(f"{path.name}: flagged Magenta geometry in parts_dxf")
            if entity_signature(entity) != sig:
                fail(f"{path.name}: cut geometry changed after serialization")
            values = _xdata(entity)
            if not {"ENTITY_ID=" + eid, "SOURCE_ENTITY_ID=" + parent,
                    "CANONICAL_MEMBER_IDS=" + ",".join(members)} <= set(values):
                fail(f"{path.name}: missing/reassigned TRAINAICAD provenance")
        return True
    except (OSError, UnicodeError, ValueError, ezdxf.DXFError):
        return False


def export_part_artifacts(job, output_dir, composite_only=False):
    """Persist validated independent PASS CUT DXFs, one per PASS code, ONLY on explicit request
    (``composite_only=False``); the default E2E path passes composite_only=True and writes none.

    No per-code JSON is written (output contract). The DXF file name is the
    part code exactly as printed on the delivery slip (作業No, e.g. ``26-056522``).
    This is intentionally downstream of validate_canonical_job and successful
    composite canonical XDATA read-back. A review part has no individual DXF.
    Every PASS DXF is rebuilt and read back on each run (no stale cache).
    """
    root = Path(output_dir)
    cut_dir = root / "parts_dxf"
    if not composite_only:  # individual DXFs only on explicit request (default: combined DXF only)
        cut_dir.mkdir(parents=True, exist_ok=True)
    statuses = []
    keep_pass = set()
    for part in job["parts"]:
        code = safe_name(part["code"])
        entry = {"code": code, "status": part["status"]}
        if part["status"] == "PASS" and not part.get("flags") and not composite_only:
            doc, expected, members, contours, orientation = _plan_cut_doc(part)
            target_dxf = cut_dir / f"{code}.dxf"
            pending = target_dxf.with_name(target_dxf.name + ".pending")
            doc.saveas(pending)
            if not _verify_cut(pending, expected):
                pending.unlink(missing_ok=True)
                fail(f"{code}: individual DXF QA read-back failed")
            pending.replace(target_dxf)
            keep_pass.add(code)
            entry.update({"cut_dxf": target_dxf.relative_to(root).as_posix(), "cut_entity_count": len(expected),
                          "canonical_cut_member_count": members, "closed_contours": contours,
                          "cut_readback": "PASS", "orientation": orientation})
        else:
            entry.update({"cut_dxf": None,
                          "cut_readback": "COMPOSITE_ONLY" if composite_only else "NOT_PRODUCTION"})
        statuses.append(entry)
    # Generated-only directory: drop stale DXFs after status/code changes.
    if not composite_only:
        for p in cut_dir.glob("*.dxf"):
            if p.stem not in keep_pass:
                p.unlink()
    return {"parts_dxf_dir": None if composite_only else "parts_dxf", "parts": statuses}
