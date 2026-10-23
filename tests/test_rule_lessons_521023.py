"""Approved 2026-10-23 (job 521023-16, regression/qa/521023-16_flat_flags_jlj_slope_APPROVED.md):
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


def test_settled_by_drawing_is_not_a_flag():
    chamfer = read("skills/lispcad/features/CHAMFER_RADIUS.md")
    assert "指示無き角部はC0.5程度の面取り" in chamfer and "is the shop Laser R → AUTO_R" in chamfer
    assert "CALLED from that callout" in chamfer
    assert "A bare `R` leader (no value)" in read("skills/lispcad/features/SLOTS.md")
    assert "is never a FLAG" in read("references/REVIEW_PREVIEW_POLICY.md")
    rules = yaml.safe_load(read("references/CUSTOMER_CAD_RULES.yaml"))
    assert "no printed label is not a FLAG" in str(rules)


def test_flagged_status_name_matches_exporter():
    policy = read("references/REVIEW_PREVIEW_POLICY.md")
    assert "`status: PREVIEW`" in policy and "`HL_DIRECTION_UNPROVED`" in policy
    assert "status PREVIEW" in read("JOB_CARD.md")


def test_jlj_long_straight_edge_rule_and_builder_agree():
    assert "long straight edge as top (max-Y) edge" in read("skills/lispcad/core/CAD_OUTPUT.md")
    strip = {"code": "26-000010", "material": "A2017", "t": 5, "envelope": [1500, 70],
             "outline": [[0, 0], [1500, 0], [1500, 70],
                         {"vnotch": {"start": 1475, "pitch": -200, "count": 8, "level": 70, "depth": 25,
                                     "inward": -1, "ev": "8-90 8-25"}}, [0, 70]]}
    part = bc.build_job({"job_id": "T", "parts": [strip]})["parts"][0]
    assert part["canonical_rotation_deg"] == 180
    marks = sorted(e["insert"][0] for e in part["entities"] if e["role"] == "mark" and e["type"] == "TEXT")
    assert marks == [30.5, 1469.5]          # J/LJ at X1+30 / X2-30 of the straight edge (R0.5 corners)


def test_close_dims_and_ledger_file_rules():
    card, reading = read("JOB_CARD.md"), read("skills/lispcad/core/DRAWING_READING.md")
    assert "ledger/spec to a file" in card and "≥900 dpi" in card
    assert "pdf_views.py pairs" in reading and "overlay_check.py" in reading


def test_rule_bundle_is_one_file_with_every_routed_rule(tmp_path):
    census = census_template()
    census["source_mode"] = "PDF_ONLY"
    plan = resolve_rules(census)
    res = write_bundle(plan, tmp_path / "rules.md")
    routed = {p for s in plan["stage_order"] for p in plan["stage_plans"][s]["rule_paths"]}
    assert set(res["files"]) == routed and len(res["files"]) == len(routed)
    text = (tmp_path / "rules.md").read_text(encoding="utf-8")
    assert all(f"===== {rel} (" in text for rel in routed)
