"""Host-owned description of the part JSON the repository's exporter and guards read.

Only structure lives here (field names, types, enums). Engineering meaning stays in the
pinned repository; `contract_notes` quotes its own schema document. tests/test_contract.py
fails when a key read by tools/*.py is missing from this description.
"""
from __future__ import annotations

_POINT = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
_FLAG = {"type": "boolean"}
_COUNT = {"type": "integer", "minimum": 0}
_TEXTS = {"type": "array", "items": {"type": "string"}}
_RECORDS = {"type": "array", "items": {"type": "object"}}
_OBJECT = {"type": "object"}

PREVIEW_REASONS = ["numeric_only_known_topology", "separate_source_views"]
STATUSES = ["PASS", "PREVIEW", "VIEWS_ONLY", "REVIEW"]

ENTITY_PROPERTIES = {
    "entity_id": {"type": "string"},
    "type": {"type": "string", "enum": ["LWPOLYLINE", "CIRCLE", "LINE", "ARC", "POINT", "TEXT"]},
    "role": {"type": "string", "description": "outer|cutout|hole|slot|bend|kegaki|ordinary_point|"
                                              "through_piercing|estimated|estimated_note|mark|source_view"},
    "closed": {"type": "boolean"},
    "vertices": {"type": "array", "items": {"type": "array", "items": {"type": "number"}},
                 "description": "LWPOLYLINE vertices as [x,y,bulge]"},
    "view_id": {"type": "string", "description": "VIEWS_ONLY: unique per-projection id on every non-TEXT entity"},
    "center": _POINT, "radius": {"type": "number", "exclusiveMinimum": 0},
    "start": _POINT, "end": _POINT,
    "start_angle": {"type": "number"}, "end_angle": {"type": "number"},
    "point": _POINT, "insert": _POINT,
    "text": {"type": "string"}, "height": {"type": "number"},
    "color": {"type": "integer", "enum": [1, 3, 6, 256]},
    "linetype": {"type": "string", "description": "DASHED for bend lines"},
    "layer": {"type": "string", "enum": ["0"]},
}

PART_PROPERTIES = {
    "preview_reason": {"type": "string", "enum": PREVIEW_REASONS,
                       "description": "PREVIEW needs numeric_only_known_topology; VIEWS_ONLY needs separate_source_views"},
    "review_reason": {"type": "string", "description": "REVIEW only: HL_DIRECTION_UNPROVED"},
    "dx_label": _FLAG,
    "grain": _OBJECT,
    "face_graph": _OBJECT,
    "feature_witness_graph": _OBJECT,
    "witness_required_feature_ids": _TEXTS,
    "slot_anchor_records": _RECORDS,
    "piercing_authorizations": _RECORDS,
    "per_bend_witness_ledger": _RECORDS,
    "assembly_indirect_candidates": _RECORDS,
    "assembly_datum_traces": _RECORDS,
    "dimensions": _RECORDS,
    "source_manufacturing_notes": _RECORDS,
    "source_assembly_view_ids": _TEXTS,
    "source_weld_site_ids": _TEXTS,
    "weld_site_census": _OBJECT,
    "complete_source_bundle_id": {"type": "string"},
    "shared_assembly_view_role": _FLAG,
    # Holistic challenge record read by tools/holistic_engineering_guard.py.
    "source_exhausted": {**_FLAG, "description": "VIEWS_ONLY: true only after every source view/face was harvested"},
    "holistic_challenge_run": {**_FLAG, "description": "VIEWS_ONLY: true only after the holistic challenge was run"},
    "flat_attempted": {**_FLAG, "description": "true when the flat pattern was actually attempted"},
    "high_source_evidence": _FLAG,
    "defensible_flat_exists": _FLAG,
    "only_local_uncertainty": _FLAG,
    "all_physical_members_drawing_only": _FLAG,
    "feature_family_yes_without_group": _FLAG,
    "source_physical_member_count": _COUNT,
    "proved_source_member_count": _COUNT,
    "unclassified_source_member_count": _COUNT,
    "proved_source_view_member_ids": _TEXTS,
    "views_only_canonical_member_ids": _TEXTS,
    "face_graph_candidates": {
        "type": "array",
        "description": "VIEWS_ONLY: every FACE_GRAPH candidate tested, with the constraint result and evidence used",
        "items": {"type": "object", "properties": {
            "candidate_id": {"type": "string"}, "constraint_result": {"type": "string"},
            "evidence_used": _TEXTS}, "required": ["candidate_id", "constraint_result", "evidence_used"]},
    },
    "unresolved_objects": {"type": "array", "items": {},
                           "description": "VIEWS_ONLY: the specific unresolved object(s) after source exhaustion"},
}


def solve_part_schema(check_names, code):
    """JSON schema for the `part` of a solve answer; `check_names` come from the exporter."""
    return {
        "type": "object",
        "properties": {
            "code": {"type": "string", "enum": [code]},
            "material": {"type": "string"},
            "thickness_mm": {"type": "number", "exclusiveMinimum": 0},
            "status": {"type": "string", "enum": STATUSES},
            "flags": {"type": "array", "items": {"type": "string"}},
            "checks": {"type": "object", "properties": {key: {"type": "string"} for key in check_names},
                       "required": list(check_names)},
            "entities": {"type": "array", "items": {
                "type": "object", "properties": dict(ENTITY_PROPERTIES),
                "required": ["entity_id", "type", "role"]}},
            "source_groups": {"type": "array", "items": {"type": "object", "properties": {
                "group_id": {"type": "string"}, "family": {"type": "string"}, "status": {"type": "string"},
                "source_quantity": {"type": ["integer", "null"]},
                "members": {"type": "array", "items": {"type": "object", "properties": {
                    "member_id": {"type": "string"}}, "required": ["member_id"]}},
            }, "required": ["group_id", "family", "status", "members", "source_quantity"]}},
            "canonical_members": {"type": "array", "items": {"type": "object", "properties": {
                "canonical_member_id": {"type": "string"}, "origin": {"type": "string"}, "status": {"type": "string"},
                "entity_ids": {"type": "array", "items": {"type": "string"}},
                "group_id": {"type": "string", "description": "Required for SOURCE; must match source group."},
                "source_member_id": {"type": "string", "description": "Required for SOURCE."},
                "source_member_ids": {"type": "array", "items": {"type": "string"},
                                      "description": "Required for DERIVED_RULE with controlling_rule."},
            }, "required": ["canonical_member_id", "origin", "status", "entity_ids"]}},
            **{key: dict(value) for key, value in PART_PROPERTIES.items()},
        },
        "required": ["code", "material", "thickness_mm", "status", "checks", "flags", "entities",
                     "source_groups", "canonical_members"],
    }


def contract_notes(text):
    """The part-level input contract of tools/DXF_INPUT_SCHEMA.md (from its own text)."""
    start = text.find("## Input JSON")
    if start < 0:
        return text
    end = text.find("### Minimal structural synthetic example", start)
    return text[start:end if end > 0 else len(text)].strip()
