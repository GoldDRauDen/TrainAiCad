#!/usr/bin/env python3
"""Nonblocking, source-proved DATA gap flags: not production cut geometry.

A source gap is warning-only ONLY when its manufacturing disposition is
independently established. It never authorizes automatic bridge segments.
"""
from __future__ import annotations

import math
import re

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
CLASSES = {
    "NONCUT_SOURCE_OPEN",
    "INTENTIONAL_OPEN_CUT",
    "PROVED_MANUFACTURING_CLOSURE",
}


class DataGapFlagError(ValueError):
    pass


def fail(message):
    raise DataGapFlagError("DATA_GAP_DISPOSITION_FAIL: " + message)


def _nonempty(value, where):
    if not isinstance(value, str) or len(value.strip()) < 12:
        fail(where + ": scoped source evidence required")
    return value


def _ids(value, where, *, can_empty=False):
    if not isinstance(value, list) or (not can_empty and not value):
        fail(where + ": source/entity ID list required")
    if any(not isinstance(x, str) or not _ID.fullmatch(x) for x in value) or len(set(value)) != len(value):
        fail(where + ": IDs must be unique ASCII identifiers")
    return value


def _point(p, where):
    if not isinstance(p, (list, tuple)) or len(p) != 2:
        fail(where + ": 2D point required")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in p):
        fail(where + ": finite coordinates required")
    return (float(p[0]), float(p[1]))


def _transform(flag, where, mid):
    # Explicit source->part mapping, because DATA may come from a view/face.
    a = flag.get("source_to_part_transform")
    if not isinstance(a, list) or len(a) != 6 or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in a
    ):
        fail(where + ": source_to_part_transform [a,b,c,d,tx,ty] required")
    a, b, c, d, tx, ty = map(float, a)
    norm_x, norm_y = math.hypot(a, c), math.hypot(b, d)
    if (min(norm_x, norm_y) <= 1e-12 or
            abs(norm_x - norm_y) > 1e-8 * max(norm_x, norm_y) or
            abs(a * b + c * d) > 1e-8 * norm_x * norm_y):
        fail(where + ": only proved rigid/reflected/uniform-scale source transforms allowed")
    _nonempty(flag.get("transform_evidence"), where + "/transform")
    return [a * mid[0] + b * mid[1] + tx, c * mid[0] + d * mid[1] + ty]


def validate_data_gap_flags(part, source_mode):
    """Verify a nonblocking source issue cannot hide incomplete CUT geometry.

    Geometry/topology and source/PDF corroboration must already be independently
    PASS. This gate validates required ledger/provenance and representations.
    """
    code = part["code"]
    gaps = part.get("data_gap_flags", [])
    if not isinstance(gaps, list):
        fail(f"{code}: data_gap_flags must be an array")
    if not gaps:
        return []
    if source_mode != "PDF_DATA_RAW":
        fail(f"{code}: DATA gap flags require PDF_DATA_RAW mode")
    if part.get("status") != "PASS" or part.get("flags"):
        fail(f"{code}: warning-only DATA gaps require separately verified manufacturing PASS")
    checks = part.get("checks", {})
    if any(checks.get(k) != "PASS" for k in
           ("contour_topology", "datum", "feature_count", "containment", "material_rules")):
        fail(f"{code}: DATA source gap cannot bypass manufacturing/topology validation")
    entity_by_id = {e["entity_id"]: e for e in part["entities"]}
    ids = set()
    validated = []
    for flag in gaps:
        if not isinstance(flag, dict):
            fail(f"{code}: invalid DATA gap record")
        gap_id = flag.get("gap_id")
        if not isinstance(gap_id, str) or not _ID.fullmatch(gap_id) or gap_id in ids:
            fail(f"{code}: duplicate/invalid gap_id")
        ids.add(gap_id)
        place = f"{code}/{gap_id}"
        kind = flag.get("classification")
        if kind not in CLASSES:
            fail(f"{place}: unknown/non-proved gap classification")
        _ids(flag.get("source_entity_ids"), place + "/source")
        _nonempty(flag.get("source_view_id"), place + "/source_view")
        _nonempty(flag.get("source_evidence"), place + "/source")
        _nonempty(flag.get("disposition_evidence"), place + "/disposition")
        points = flag.get("source_endpoints")
        if not isinstance(points, list) or len(points) != 2:
            fail(f"{place}: TWO actual RAW DATA gap endpoints required")
        p, q = _point(points[0], place), _point(points[1], place)
        length = math.hypot(p[0] - q[0], p[1] - q[1])
        if length <= 1e-12:
            fail(f"{place}: no measurable source gap")
        local = _transform(flag, place, [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2])
        canonical_ids = _ids(flag.get("canonical_entity_ids"), place + "/canonical",
                             can_empty=(kind == "NONCUT_SOURCE_OPEN"))
        if any(eid not in entity_by_id for eid in canonical_ids):
            fail(f"{place}: canonical source geometry reference missing")
        if kind == "NONCUT_SOURCE_OPEN":
            if flag.get("source_role") not in ("DRAWING_ONLY", "PROJECTION_ONLY",
                                               "THICKNESS_REPRESENTATION", "CONSTRUCTION"):
                fail(f"{place}: noncut provenance must explicitly exclude physical CUT")
            if canonical_ids:
                fail(f"{place}: NONCUT source gap cannot own manufacturing CUT entities")
        elif kind == "INTENTIONAL_OPEN_CUT":
            if any(entity_by_id[eid].get("type") not in ("LINE", "ARC") or
                   entity_by_id[eid].get("role") not in ("slit", "relief")
                   for eid in canonical_ids):
                fail(f"{place}: only a proved SLIT/RELIEF may remain an open production cut")
            _nonempty(flag.get("manufacturing_instruction"), place + "/open cut instruction")
        else:
            # A missing raw CUT segment is never accepted simply because
            # assigning LWPOLYLINE.closed=True would fabricate a bridge.
            if any(entity_by_id[eid].get("type") != "LWPOLYLINE" or
                   entity_by_id[eid].get("role") not in ("outer", "cutout", "slot") or
                   entity_by_id[eid].get("closed") is not True
                   for eid in canonical_ids):
                fail(f"{place}: proved corrected CUT must be a separately proved closed contour")
            _nonempty(flag.get("manufacturing_change_ledger_ref"),
                      place + "/manufacturing change")
            _nonempty(flag.get("closure_witness"), place + "/PDF closure witness")
        validated.append({
            "gap_id": gap_id, "classification": kind,
            "gap_mm": length, "marker_local": local,
            "source_entity_ids": list(flag["source_entity_ids"]),
        })
    return validated
