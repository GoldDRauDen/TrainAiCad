"""Approved 2026-10-23 (job 521023-16, regression/lessons/CORNER_RC/521023-16_flat_flags_jlj_slope_APPROVED.md):
FLAG only real unknowns, J/LJ on the long straight edge, close same-axis dims cropped, one-file rule bundle."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from resolve_rules import census_template, resolve_rules, write_bundle  # noqa: E402


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_jlj_long_straight_edge_rule_and_builder_agree():
    strip = {"code": "26-000010", "material": "A2017", "t": 5, "envelope": [1500, 70],
             "outline": [[0, 0], [1500, 0], [1500, 70],
                         {"vnotch": {"start": 1475, "pitch": -200, "count": 8, "level": 70, "depth": 25,
                                     "inward": -1, "ev": "8-90 8-25"}}, [0, 70]]}
    part = bc.build_job({"job_id": "T", "parts": [strip]})["parts"][0]
    assert part["canonical_rotation_deg"] == 180
    marks = sorted(e["insert"][0] for e in part["entities"] if e["role"] == "mark" and e["type"] == "TEXT")
    assert marks == [30.5, 1469.5]          # J/LJ at X1+30 / X2-30 of the straight edge (R0.5 corners)


def test_rule_bundle_is_one_file_with_every_routed_rule(tmp_path):
    census = census_template()
    census["source_mode"] = "PDF_ONLY"
    plan = resolve_rules(census)
    res = write_bundle(plan, tmp_path / "rules.md")
    routed = {p for s in plan["stage_order"] for p in plan["stage_plans"][s]["rule_paths"]}
    assert set(res["files"]) == routed and len(res["files"]) == len(routed)
    text = (tmp_path / "rules.md").read_text(encoding="utf-8")
    assert all(f"===== {rel} (" in text for rel in routed)
