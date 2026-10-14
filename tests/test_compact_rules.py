"""Compact rule packs: 50 logical modules preserved in 11 physical files."""
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compact_rules import (CompactRuleError, read_rule_text, rule_module_map,
                           validate_rule_manifest, resolve_rule_path, rule_physical_paths)
from read_routed_rules import extract
from resolve_rules import resolve_rules
from audit_rule_coverage import audit


def test_every_former_module_is_present_exactly_once():
    manifest = validate_rule_manifest(ROOT)
    assert manifest == {"logical_modules": 50, "physical_rule_files": 11}
    mapping = rule_module_map(ROOT)
    for logical, physical in mapping.items():
        assert not (ROOT / logical).exists(), logical
        assert (ROOT / physical).is_file()
        section = read_rule_text(logical, ROOT)
        assert section.strip()
    assert audit(ROOT)["routed_active_module_count"] == 50


def test_selected_rule_isolated_not_entire_pack():
    mapping = rule_module_map(ROOT)
    slit = "skills/lispcad/features/SLIT_RELIEF.md"
    box = "references/BOXMET_SLIT_RELIEF.md"
    assert mapping[slit] == mapping[box]
    selected = extract([slit], ROOT)
    assert "BEGIN SELECTED RULE: " + slit in selected
    assert "BEGIN SELECTED RULE: " + box not in selected
    assert "D = t * sin(theta)" in read_rule_text(slit, ROOT)
    assert "Case A" in read_rule_text("references/BEND_EDGE_RELIEF_90.md", ROOT)


def test_release_pin_router_and_canonical_compatibility():
    pin = yaml.safe_load((ROOT / "config/RELEASE.yaml").read_text(encoding="utf-8"))
    router = yaml.safe_load((ROOT / "skills/lispcad/router/ROUTER.yaml").read_text(encoding="utf-8"))
    mapping = yaml.safe_load((ROOT / "config/RULE_MODULES.yaml").read_text(encoding="utf-8"))
    assert pin["current"] == router["release"] == mapping["release"] == "V4.34"
    assert pin["canonical_contract"] == "TrainAiCad-CANONICAL-V4.34"
    assert "TrainAiCad-CANONICAL-V4.31" in pin["legacy_canonical_contracts"]


def test_source_gates_and_stage_gate_are_still_selected():
    router = yaml.safe_load((ROOT / "skills/lispcad/router/ROUTER.yaml").read_text(encoding="utf-8"))
    census = {
        "source_mode": "PDF_ONLY", "part_mode": "BEND",
        "features": {k: {"state": "NO"} for k in router["feature_routes"]},
    }
    plan = resolve_rules(census, ROOT)
    assert plan["stage_order"] == [
        "L0_BOOTSTRAP", "L1_SOURCE_CENSUS", "L2_GEOMETRY", "L3_VALIDATE_EXPORT_QA",
    ]
    assert "skills/lispcad/modes/BEND_UNFOLD.md" in plan["rule_paths"]
    assert "skills/lispcad/core/VALIDATION.md" in plan["rule_paths"]
    assert "rules/04_BEND.md" in plan["physical_rule_paths"]
    assert "rules/11_QA_EXPORT.md" in plan["physical_rule_paths"]
    assert plan["section_sources"]["skills/lispcad/modes/BEND_UNFOLD.md"] == "rules/04_BEND.md"
    assert "FACE_GRAPH" in extract(["references/FACE_GRAPH_UNFOLD_PROTOCOL.md"], ROOT)


def test_unknown_module_and_unsafe_paths_fail_closed():
    with pytest.raises(CompactRuleError):
        read_rule_text("references/ABSENT_FEATURE.md", ROOT)
    with pytest.raises(CompactRuleError):
        resolve_rule_path("../regression/qa/example.md", ROOT)
