"""The host output contract must describe every field the repository's exporter and guards read."""
import ast
from pathlib import Path

import pytest

from LuanAppTools.cad.contract import contract_notes, solve_part_schema
from LuanAppTools.cad.repository import PinnedRepository

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ["contour_topology", "datum", "feature_count", "unfold", "containment",
          "bend_domain", "material_rules", "slot_semantics"]

PART_READERS = {
    "export_dxf.py": {"part"}, "canonical_contract.py": {"part"},
    "holistic_engineering_guard.py": {"part"}, "weld_kegaki_guard.py": {"part"},
    "export_job_artifacts.py": {"part"},
}
ENTITY_READERS = {
    "export_dxf.py": {"entity", "ent", "e"}, "canonical_contract.py": {"ent"},
    "holistic_engineering_guard.py": {"e", "found", "slot_entity", "entity"},
    "export_job_artifacts.py": {"ent", "entity", "e"},
}


def keys_read(filename, receivers):
    tree = ast.parse((ROOT / "tools" / filename).read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id in receivers
                and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            found.add(node.args[0].value)
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in receivers
                and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
            found.add(node.slice.value)
    return found


def part_schema():
    return solve_part_schema(CHECKS, "26-000001")


def test_schema_keeps_the_existing_required_shape():
    schema = part_schema()
    assert schema["required"] == ["code", "material", "thickness_mm", "status", "checks", "flags",
                                  "entities", "source_groups", "canonical_members"]
    assert schema["properties"]["code"]["enum"] == ["26-000001"]
    assert schema["properties"]["checks"]["required"] == CHECKS
    assert schema["properties"]["status"]["enum"] == ["PASS", "PREVIEW", "VIEWS_ONLY", "REVIEW"]


def test_schema_documents_views_only_fields_the_model_used_to_guess():
    props = part_schema()["properties"]
    for key in ("preview_reason", "review_reason", "source_exhausted", "holistic_challenge_run",
                "face_graph_candidates", "unresolved_objects", "flat_attempted"):
        assert key in props, key
    assert props["preview_reason"]["enum"] == ["numeric_only_known_topology", "separate_source_views"]
    entity = props["entities"]["items"]["properties"]
    for key in ("view_id", "center", "radius", "start", "end", "start_angle", "end_angle",
                "point", "color", "linetype", "text", "insert", "height"):
        assert key in entity, key
    assert entity["color"]["enum"] == [1, 3, 6, 256]
    assert part_schema()["properties"]["entities"]["items"]["required"] == ["entity_id", "type", "role"]


def test_schema_covers_every_part_key_the_repository_reads():
    described = set(part_schema()["properties"])
    read = set().union(*(keys_read(name, receivers) for name, receivers in PART_READERS.items()))
    assert read - described == set()


def test_schema_covers_every_entity_key_the_repository_reads():
    described = set(part_schema()["properties"]["entities"]["items"]["properties"])
    read = set().union(*(keys_read(name, receivers) for name, receivers in ENTITY_READERS.items()))
    assert read - described == set()


def test_contract_notes_extract_the_input_section_of_the_schema_document():
    text = (ROOT / "tools" / "DXF_INPUT_SCHEMA.md").read_text(encoding="utf-8")
    notes = contract_notes(text)
    assert "preview_reason" in notes and "separate_source_views" in notes and "view_id" in notes
    assert "Minimal structural synthetic example" not in notes
    assert contract_notes("no heading here") == "no heading here"


def test_pinned_repository_exposes_contract_notes(tmp_path):
    repo = PinnedRepository.pin(ROOT, tmp_path / "engine")
    assert "separate_source_views" in repo.contract_notes()
