"""Corner inventory gate and ledger (drawn R/C without callout -> FLAG, never silent auto-R)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from corner_guard import corner_errors, outer_sharp_corners
from ledger import ledger, main, render
from holistic_engineering_guard import canonical_job_anomalies

FIXTURE = ROOT / "regression/fixtures/521017-17_061099_positive_step.json"


def square_part(**extra):
    part = {"code": "T1", "status": "REVIEW_PREVIEW", "thickness_mm": 2.3, "material": "SPHCP",
            "entities": [{"entity_id": "OUT", "type": "LWPOLYLINE", "role": "outer", "closed": True,
                          "vertices": [[0, 0, 0], [100, 0, 0], [100, 50, 0], [0, 50, 0]]}],
            "canonical_members": [{"canonical_member_id": "CM_AR", "origin": "DERIVED_RULE", "status": "PROVED",
                                   "controlling_rule": "MATERIAL_AUTO_R", "source_member_ids": ["X"],
                                   "entity_ids": ["OUT"]}]}
    part.update(extra)
    return part


def row(i, point, shape="SHARP", decision="AUTO_R", member="CM_AR", **kw):
    r = {"corner_id": f"C{i}", "point": point, "drawn_shape": shape, "decision": decision,
         "canonical_member_id": member, "evidence_ref": "synthetic"}
    r.update(kw)
    return r


def test_square_has_four_sharp_corners():
    assert len(outer_sharp_corners(square_part())) == 4


def test_auto_r_without_inventory_is_rejected():
    assert corner_errors(square_part()) == ["CORNER_INVENTORY_MISSING"]


def test_legacy_part_without_auto_r_is_unaffected():
    part = square_part(canonical_members=[])
    assert corner_errors(part) == []


def test_auto_r_on_sharp_corners_with_full_census_passes():
    pts = [[0, 0], [100, 0], [100, 50], [0, 50]]
    inv = [row(0, pts[0])] + [row(i, p, decision="SHARP", member=None, no_auto_r_reason="synthetic: other rule")
                              for i, p in enumerate(pts[1:], 1)]
    assert corner_errors(square_part(corner_inventory=inv)) == []


def test_drawn_rounded_corner_with_auto_r_is_rejected():
    pts = [[0, 0], [100, 0], [100, 50], [0, 50]]
    inv = [row(0, pts[0], shape="ROUNDED")] + [row(i, p, decision="SHARP", member=None, no_auto_r_reason="x")
                                               for i, p in enumerate(pts[1:], 1)]
    errs = corner_errors(square_part(corner_inventory=inv))
    assert "CORNER_AUTO_R_UNPROVED:C0" in errs and "CORNER_AUTO_R_MEMBER_UNOWNED:CM_AR" in errs


@pytest.mark.parametrize("shape", ["ROUNDED", "CHAMFERED", "UNKNOWN"])
def test_drawn_shape_without_callout_must_be_flagged(shape):
    pts = [[0, 0], [100, 0], [100, 50], [0, 50]]
    inv = [row(i, p, shape=shape, decision="SHARP", member=None, no_auto_r_reason="x") for i, p in enumerate(pts)]
    errs = corner_errors(square_part(canonical_members=[], corner_inventory=inv))
    assert any(e.startswith("CORNER_DRAWN_SHAPE_WITHOUT_CALLOUT_NOT_FLAGGED") for e in errs)


def test_flagged_corner_is_local_flag_not_pass():
    pts = [[0, 0], [100, 0], [100, 50], [0, 50]]
    inv = [row(0, pts[0], shape="ROUNDED", decision="FLAG", member=None)] + [
        row(i, p, decision="SHARP", member=None, no_auto_r_reason="x") for i, p in enumerate(pts[1:], 1)]
    assert corner_errors(square_part(canonical_members=[], corner_inventory=inv)) == []
    assert "CORNER_FLAG_UNRESOLVED:C0" in corner_errors(square_part(canonical_members=[], corner_inventory=inv,
                                                                      status="PASS"))


def test_flag_cannot_own_auto_r_member():
    pts = [[0, 0], [100, 0], [100, 50], [0, 50]]
    inv = [row(0, pts[0], shape="ROUNDED", decision="FLAG", member="CM_AR")] + [
        row(i, p, decision="SHARP", member=None, no_auto_r_reason="x") for i, p in enumerate(pts[1:], 1)]
    assert "CORNER_FLAG_HAS_AUTO_R:C0" in corner_errors(square_part(corner_inventory=inv))


def test_missing_corner_census_row_is_reported():
    inv = [row(0, [0, 0])]
    errs = corner_errors(square_part(corner_inventory=inv))
    assert sum(e.startswith("CORNER_CENSUS_MISSING") for e in errs) == 3


def test_called_corner_needs_source_member():
    part = square_part(canonical_members=[{"canonical_member_id": "CM_C", "origin": "SOURCE", "status": "PROVED",
                                           "source_member_id": "G1", "entity_ids": ["OUT"]}])
    pts = [[0, 0], [100, 0], [100, 50], [0, 50]]
    inv = [row(0, pts[0], shape="CHAMFERED", decision="CALLED", member="CM_C")] + [
        row(i, p, decision="SHARP", member=None, no_auto_r_reason="x") for i, p in enumerate(pts[1:], 1)]
    assert corner_errors({**part, "corner_inventory": inv}) == []
    inv[0]["canonical_member_id"] = "MISSING"
    assert "CORNER_CALLOUT_MEMBER_UNPROVED:C0" in corner_errors({**part, "corner_inventory": inv})


def test_guard_runs_in_canonical_job_anomalies():
    job = json.loads(FIXTURE.read_text(encoding="utf-8"))["job"]
    part = job["parts"][0]
    part["canonical_members"].append({"canonical_member_id": "CM_AUTO", "origin": "DERIVED_RULE", "status": "PROVED",
                                      "controlling_rule": "MATERIAL_AUTO_R", "source_member_ids": ["X"],
                                      "entity_ids": [part["entities"][0]["entity_id"]]})
    assert any("CORNER_INVENTORY_MISSING" in e for e in canonical_job_anomalies(job))


def test_ledger_lists_corners_bend_ends_and_missing(tmp_path):
    inv = [row(0, [0, 0], shape="ROUNDED", decision="FLAG", member=None)]
    part = square_part(canonical_members=[], corner_inventory=inv)
    led = ledger(part)
    assert [c["decision"] for c in led["corners"]].count("THIẾU") == 3
    assert "THIẾU" in render("T1", led) and "FLAG" in render("T1", led)
    job = tmp_path / "j.json"
    job.write_text(json.dumps({"parts": [part]}), encoding="utf-8")
    assert main([str(job), "--out", str(tmp_path / "l.md")]) == 1
    assert (tmp_path / "l.md").read_text(encoding="utf-8").startswith("## T1")


def test_draft_inventory_is_all_flag_unknown_and_never_auto_r(tmp_path):
    from corner_guard import draft_inventory
    rows = draft_inventory(square_part())
    assert len(rows) == 4 and all(r["decision"] == "FLAG" and r["drawn_shape"] == "UNKNOWN" for r in rows)
    part = square_part(canonical_members=[], corner_inventory=rows)
    assert corner_errors(part) == []            # a drafted inventory is valid but every corner stays FLAGGED
    assert all("CORNER_FLAG_UNRESOLVED" in e for e in corner_errors({**part, "status": "PASS"}))
    job = tmp_path / "j.json"
    job.write_text(json.dumps({"parts": [square_part()]}), encoding="utf-8")
    assert main([str(job), "--draft", "--out", str(tmp_path / "d.json")]) == 0
    assert len(json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))["T1"]) == 4
