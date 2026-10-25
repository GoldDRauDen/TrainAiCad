"""Census -> rule cards: fail-closed routing (rules/ROUTER.yaml via tools/resolve_rules.py)."""
from copy import deepcopy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import resolve_rules as mod  # noqa: E402

ROUTER = yaml.safe_load((ROOT / mod.ROUTER).read_text(encoding="utf-8"))
ALWAYS = ["JOB_CARD.md", "rules/READ_SOURCE.md", "rules/CENSUS.md", "rules/DATUM.md",
          "rules/CORNER_RC.md", "rules/VALIDATE.md", "rules/OUTPUT.md"]


def census(source="PDF_ONLY", mode="FLAT_NO_BEND", **extra):
    c = {"source_mode": source, "part_mode": mode, "reference_present": "NO",
         "multi_code_or_assembly": "NO",
         "features": {key: {"state": "NO"} for key in ROUTER["feature_routes"]}}
    c.update(extra)
    return c


def test_minimal_flat_reads_only_the_always_cards():
    result = mod.resolve_rules(census())
    assert result["rule_paths"] == ALWAYS
    assert result["release"] == ROUTER["release"]


def test_cards_are_staged():
    plans = mod.resolve_rules(census())["stage_plans"]
    assert plans["L1_SOURCE_CENSUS"]["rule_paths"] == ["rules/READ_SOURCE.md", "rules/CENSUS.md"]
    assert plans["L2_GEOMETRY"]["rule_paths"] == ["rules/DATUM.md", "rules/CORNER_RC.md"]
    assert plans["L3_VALIDATE_EXPORT_QA"]["rule_paths"] == ["rules/VALIDATE.md", "rules/OUTPUT.md"]


def test_unknown_mode_loads_bend_and_relief_once():
    x = census("PDF_DATA_RAW", "UNKNOWN")
    x["features"]["TAP"]["state"] = "YES"
    x["features"]["SLIT_RELIEF"]["state"] = "UNKNOWN"
    paths = mod.resolve_rules(x)["rule_paths"]
    for card in ("rules/BEND.md", "rules/SLIT_RELIEF.md", "rules/HOLE_TAP.md", "rules/DATA_DXF.md"):
        assert paths.count(card) == 1


def test_unknown_feature_and_unproven_context_load_their_cards():
    x = census()
    x["features"]["CURVED_SLOT"]["state"] = "UNKNOWN"
    del x["reference_present"], x["multi_code_or_assembly"]
    paths = mod.resolve_rules(x)["rule_paths"]
    assert {"rules/SLOT.md", "rules/REFERENCE.md", "rules/MULTI_PART.md"} <= set(paths)


def test_dependencies_pull_in_the_bend_card():
    x = census()
    x["features"]["ACUTE_BEND_LT85"]["state"] = "YES"
    x["features"]["BOXMET"]["state"] = "YES"
    paths = mod.resolve_rules(x)["rule_paths"]
    assert {"rules/BEND.md", "rules/BEND_ACUTE.md", "rules/SLIT_RELIEF.md"} <= set(paths)


def test_incomplete_census_is_not_silently_no():
    x = census()
    del x["features"]["TAP"]
    with pytest.raises(mod.ResolutionError, match="missing"):
        mod.resolve_rules(x)


def test_no_route_may_select_regression_or_tests():
    router = deepcopy(ROUTER)
    router["feature_routes"]["HOLE"]["load"] = ["regression/lessons/READ_SOURCE/520709-07_APPROVED.md"]
    x = census()
    x["features"]["HOLE"]["state"] = "YES"
    with pytest.raises(mod.ResolutionError, match="Forbidden"):
        mod.resolve_rules(x, router=router)


def test_template_starts_everything_unknown():
    t = mod.census_template()
    assert set(t["features"]) == set(ROUTER["feature_routes"])
    assert all(v["state"] == "UNKNOWN" for v in t["features"].values())


def test_bundle_is_one_file_with_every_card(tmp_path):
    plan = mod.resolve_rules(census())
    res = mod.write_bundle(plan, tmp_path / "rules.md")
    assert res["files"] == plan["rule_paths"]
    text = (tmp_path / "rules.md").read_text(encoding="utf-8")
    assert all(f"===== {rel} (" in text for rel in plan["rule_paths"])
