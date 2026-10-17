"""Host-owned description of the part JSON the repository's exporter and guards read.

Only structure lives here (field names, types, enums). Engineering meaning stays in the
pinned repository; `contract_notes` quotes its own schema document. tests/test_contract.py
fails when a key read by tools/*.py is missing from this description.
"""
from __future__ import annotations

import copy
import re

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

WELD_SITE_PROPERTIES = {
    "weld_site_id": {"type": "string"},
    "status": {"type": "string", "enum": ["PROVED", "FLAGGED"]},
    "parent_code": {"type": "string", "description": "the host fills this with the code being described"},
    "child_part_id": {"type": "string"},
    "assembly_view_id": {"type": "string"},
    "source_evidence": {"type": "string", "description": "scoped source/witness evidence, 8+ characters"},
    "host_face": {"type": "string"},
    "unresolved_fields": _TEXTS,
    "weld_required_cue": _FLAG,
    "self_locating": _FLAG,
    "mark_required_by_source": _FLAG,
    "not_required_evidence": {"type": "string"},
    "mark_status": {"type": "string", "enum": ["PROVED", "FLAGGED"]},
    "mark_member_ids": _TEXTS,
    "datum_evidence": {"type": "string"},
}

WELD_CENSUS_SCHEMA = {
    "type": "object",
    "properties": {
        "inspected_assembly_view_ids": {**_TEXTS, "description": "host-owned: always equals source_assembly_view_ids"},
        "source_evidence": {"type": "string"},
        "no_weld_evidence": {"type": "string"},
        "sites": {"type": "array", "items": {
            "type": "object", "properties": WELD_SITE_PROPERTIES,
            "required": ["weld_site_id", "status", "child_part_id", "assembly_view_id", "source_evidence"]}},
    },
    "required": ["source_evidence", "sites"],
}

# Per-code weld inventory as references/WELD_SITE_KEGAKI_CLOSURE.md defines it.
WELD_SCHEMA = {
    "type": "object",
    "properties": {"source_assembly_view_ids": _TEXTS, "source_weld_site_ids": _TEXTS,
                   "weld_site_census": WELD_CENSUS_SCHEMA},
    "required": ["source_assembly_view_ids", "source_weld_site_ids", "weld_site_census"],
}
WELD_KEYS = tuple(WELD_SCHEMA["properties"])

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
    "weld_site_census": WELD_CENSUS_SCHEMA,
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


def solve_part_schema(check_names, code=None):
    """JSON schema for the `part` of a solve answer; `check_names` come from the exporter.

    Leave `code` out for the real runs: the output schema is a tool definition that sits before the
    shared rules in the provider's cache prefix, so any per-code detail in it stops codes from reusing
    each other's cache. The host checks the code itself.
    """
    return {
        "type": "object",
        "properties": {
            "code": {"type": "string", "enum": [code]} if code else {"type": "string"},
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


class ContractError(ValueError):
    """The part breaks a rule the repository states but its exporter does not enforce."""


# Printed/handwritten flat arithmetic such as "161+41-9.78=192.22" (HOLISTIC_ENGINEERING_CHALLENGE section 3).
FLAT_ARITHMETIC = re.compile(r"\d+(?:\.\d+)?(?:\s*[+\-\u2212\u2013]\s*\d+(?:\.\d+)?)+\s*=\s*\d+(?:\.\d+)?")

HOST_VIEWS_ONLY_NOTE = (
    "VIEWS_ONLY is a last executable fallback, never a shortcut (AI_ENTRYPOINT section 2). Set source_exhausted=true "
    "and holistic_challenge_run=true only after you really harvested every source view/face and ran the holistic "
    "challenge. List every FACE_GRAPH candidate you tested in face_graph_candidates "
    "[{candidate_id, constraint_result, evidence_used}]; evidence_used must include the id of each printed or "
    "handwritten flat-arithmetic note of this code (the host rejects a VIEWS_ONLY part that ignores one). Name what "
    "stays unresolved in unresolved_objects, keep views_only_canonical_member_ids equal to "
    "proved_source_view_member_ids, and set flat_attempted=true when you attempted the flat. The host sets "
    "high_source_evidence when the drawing carries flat arithmetic: build the flat from it instead of giving up. A "
    "VIEWS_ONLY part also needs preview_reason=separate_source_views, non-empty flags and a unique view_id on every "
    "non-TEXT entity."
)


def flat_arithmetic_notes(notes):
    return [n for n in notes if isinstance(n, dict) and FLAT_ARITHMETIC.search(str(n.get("text", "")))]


def prepare_part(part, notes, census=None):
    """Host-owned restatements derived from the code's own source records; never overrides the model."""
    if not isinstance(part, dict):
        return part
    prepared = dict(part)
    if flat_arithmetic_notes(notes):
        prepared.setdefault("high_source_evidence", True)
        if prepared.get("status") in ("PASS", "PREVIEW", "REVIEW"):
            prepared.setdefault("flat_attempted", True)
    for key in WELD_KEYS:
        if census and census.get(key) is not None:
            prepared.setdefault(key, copy.deepcopy(census[key]))
    welds = prepared.get("weld_site_census")
    if isinstance(welds, dict) and isinstance(prepared.get("source_assembly_view_ids"), list):
        # The repository requires the inspected views to equal the assembly views; it is one fact.
        prepared["weld_site_census"] = {**welds, "inspected_assembly_view_ids": list(prepared["source_assembly_view_ids"])}
    return prepared


def check_flat_attempt(part, notes):
    """A VIEWS_ONLY part must show it tested the flat that printed arithmetic closes."""
    if not isinstance(part, dict) or part.get("status") != "VIEWS_ONLY":
        return
    cited = {ref for candidate in part.get("face_graph_candidates") or [] if isinstance(candidate, dict)
             for ref in candidate.get("evidence_used") or [] if isinstance(ref, str)}
    missing = [n for n in flat_arithmetic_notes(notes) if n.get("id") not in cited]
    if missing:
        listed = "; ".join(f"{n.get('id')} ({FLAT_ARITHMETIC.search(str(n.get('text'))).group(0)})" for n in missing)
        raise ContractError(
            f"FLAT_ARITHMETIC_NOT_TESTED: {listed} - test the formed topology this flat arithmetic closes and cite "
            "its note id in face_graph_candidates[].evidence_used before choosing VIEWS_ONLY "
            "(HOLISTIC_ENGINEERING_CHALLENGE section 3)")


HOST_CANONICAL_NOTE = (
    "Every PROVED HOLE or SLOT source member needs witness_required_feature_ids and a feature_witness_graph (V4.34 "
    "canonical contract), even in a VIEWS_ONLY part. A hole you cannot witness must have its source member FLAGGED "
    "instead of PROVED, with canonical status SOURCE_VIEW (or PREVIEW / FLAGGED_NO_GEOMETRY)."
)

HOST_WELD_NOTE = (
    "This code has weld sites (customer 851). Record every weld mark you cannot prove yet like this before "
    "validating: a source_groups entry {group_id, family: KEGAKI, status: FLAGGED, source_quantity: 1, members: "
    "[{member_id, status: FLAGGED}]}, a canonical_members entry {canonical_member_id, origin: SOURCE, "
    "source_member_id, group_id, status: FLAGGED_NO_GEOMETRY, entity_ids: []}, and that member_id in the site's "
    "mark_member_ids inside weld_site_census; the part then needs non-empty flags and cannot be PASS. A mark you can "
    "prove is a RED (color 1, role kegaki) LINE entity owned by a PROVED member, on a PROVED weld site whose "
    "mark_status is PROVED and has datum_evidence."
)
