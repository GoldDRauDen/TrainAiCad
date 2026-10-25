"""Source-edge step measurement -> mechanism gate -> canonical saved-DXF QA."""
import copy
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from canonical_contract import CanonicalContractError
from export_canonical_dxf import export_canonical_job
from holistic_engineering_guard import canonical_job_anomalies
from slit_geometry import connected_slit, slit_depth_from_actual_edge

FIXTURE = ROOT / "regression/fixtures/521017-17_061099_positive_step.json"


def job():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["job"]


def add_relief(part, entities=None, rule="OPPOSITE_FOLD_R_T"):
    """A self-consistent but wrongly scoped manufacturing addition."""
    site = part["bend_end_junctions"][0]
    entities = entities or [{"type": "ARC", "role": "slit", "color": 3,
                             "center": [100, 30], "radius": 2,
                             "start_angle": 0, "end_angle": 90}]
    ids = []
    for i, entity in enumerate(entities):
        entity.update(entity_id=f"UNWANTED_RELIEF_{i}", bend_end_site_id=site["site_id"])
        part["entities"].append(entity)
        ids.append(entity["entity_id"])
    member = {"canonical_member_id": "CM_ADDED_RELIEF", "origin": "DERIVED_RULE",
              "controlling_rule": rule, "source_member_ids": [part["source_groups"][0]["members"][0]["member_id"]],
              "status": "PROVED", "entity_ids": ids, "bend_end_site_id": site["site_id"]}
    part["canonical_members"].append(member)
    site["relief_member_ids"] = [member["canonical_member_id"]]


def slit_case(step=0, depth=2.2):
    candidate = job()
    part = candidate["parts"][0]
    site = part["bend_end_junctions"][0]
    edge = part["bend_end_source_edges"][site["web_edge_id"]]
    for key in ("start", "end"):
        edge[key][1] = -2 + step
    site.update(S_mm=step, decision="SLIT")
    geo = connected_slit((100, 30), (0, 1), (-6, -6), depth)
    add_relief(part, [
        {"type": "LINE", "role": "slit", "color": 3, "start": list(geo["line1"][0]), "end": list(geo["line1"][1])},
        {"type": "ARC", "role": "slit", "color": 3, **geo["arc"], "center": list(geo["arc"]["center"])},
        {"type": "LINE", "role": "slit", "color": 3, "start": list(geo["line2"][0]), "end": list(geo["line2"][1])},
    ], rule="BEND_END_OFFSET_90")
    for eid, start, end, physical in (
        ("FLAT_WEB", [100, 30], [110, 30], edge["physical_edge_id"]),
        ("FLAT_SIDE", [100, 30], [100, 40], "SYNTHETIC_SIDE"),
    ):
        part["bend_end_source_edges"][eid] = {
            "physical_edge_id": physical, "type": "LINE", "frame_id": "CANONICAL_FLAT",
            "start": start, "end": end,
            "proof": {"source_ref": "synthetic local construction", "endpoint_verified": True,
                      "evidence_ref": "source edge mapped into canonical flat"}}
    site["slit_construction"] = {
        "actual_edge_id": "FLAT_WEB", "side_edge_id": "FLAT_SIDE", "bend_id": site["bend_ids"][1],
        "inward_hint": [0, 1], "side_void_normal": [-1, 0], "web_void_normal": [0, -1],
        "evidence_ref": "synthetic mapped actual-edge corner and void-side proof"}
    return candidate


@pytest.mark.parametrize("member_id", ["P061099_CM_OUTER", "P061099_CM_LOWER4_D7_H1"])
def test_required_slit_cannot_be_satisfied_by_an_outer_contour_or_hole(tmp_path, member_id):
    candidate = slit_case()
    part = candidate["parts"][0]
    part["canonical_members"].pop()
    part["entities"] = [e for e in part["entities"] if not e["entity_id"].startswith("UNWANTED_RELIEF_")]
    part["bend_end_junctions"][0]["relief_member_ids"] = [member_id]
    with pytest.raises(CanonicalContractError, match="BEND_END_RELIEF_MEMBER_UNPROVED"):
        export_canonical_job(candidate, tmp_path)


@pytest.mark.parametrize("mutation", ["depth", "detached", "wrong_actual_edge"])
def test_required_slit_checks_actual_edge_depth_and_connected_geometry(tmp_path, mutation):
    candidate = slit_case(depth=4.2 if mutation == "depth" else 2.2)
    part = candidate["parts"][0]
    if mutation == "detached":
        part["entities"][-1]["start"][0] += 1
    elif mutation == "wrong_actual_edge":
        part["bend_end_source_edges"]["FLAT_WEB"]["physical_edge_id"] = "UNRELATED_EDGE"
    with pytest.raises(CanonicalContractError, match="BEND_END_SLIT_CONSTRUCTION_UNPROVED"):
        export_canonical_job(candidate, tmp_path)


def test_slit_short_ray_cannot_point_into_the_proved_void(tmp_path):
    candidate = slit_case()
    part = candidate["parts"][0]
    part["bend_end_junctions"][0]["slit_construction"]["inward_hint"] = [0, -1]
    geo = connected_slit((100, 30), (0, -1), (-6, -6), 2.2)
    part["entities"][-3].update(start=list(geo["line1"][0]), end=list(geo["line1"][1]))
    part["entities"][-2].update(**{**geo["arc"], "center": list(geo["arc"]["center"])})
    part["entities"][-1].update(start=list(geo["line2"][0]), end=list(geo["line2"][1]))
    with pytest.raises(CanonicalContractError, match="BEND_END_SLIT_CONSTRUCTION_UNPROVED"):
        export_canonical_job(candidate, tmp_path)


@pytest.mark.parametrize("omit_inventory", [False, True])
def test_unscoped_non90_relief_cannot_bypass_mechanism_proof(tmp_path, omit_inventory):
    candidate = job()
    part = candidate["parts"][0]
    add_relief(part, rule="NON_90_RELIEF")
    part["canonical_members"][-1].pop("bend_end_site_id")
    part["entities"][-1].pop("bend_end_site_id")
    part["bend_end_junctions"][0]["relief_member_ids"] = []
    if omit_inventory:
        for key in ("source_bend_end_site_ids", "bend_end_junctions", "bend_end_source_edges"):
            part.pop(key)
    with pytest.raises(CanonicalContractError, match="BEND_END_(RELIEF_SCOPE_MISSING|SITE_CENSUS_MISMATCH)"):
        export_canonical_job(candidate, tmp_path)


def test_crossing_bend_mechanism_removed_duplicate_of_step_slit():
    """CROSSING_BEND duplicated the step slit (user 2026-10-20); it is no longer a mechanism."""
    candidate = job()
    part = candidate["parts"][0]
    add_relief(part, rule="CROSSING_BEND")
    site = part["bend_end_junctions"][0]
    site.update(mechanism="CROSSING_BEND", decision="SEPARATE_RULE",
                special_rule_evidence_ref="synthetic", intersection_edge_ids=["X1", "X2"])
    errors = canonical_job_anomalies(candidate)
    assert any("BEND_END_MECHANISM_UNPROVED" in e or "BEND_END_RELIEF_SCOPE_MISSING" in e for e in errors)


def corner_site(candidate, **witness):
    site = candidate["parts"][0]["bend_end_junctions"][0]
    base = {"flange_ids": ["F_A", "F_B"], "depth_mm": {"F_A": 30.0, "F_B": 30.0},
            "bend_edge_length_mm": {"F_A": 265.0, "F_B": 83.2},
            "site_flange_id": "F_A", "retreated_flange_id": "F_B", "evidence_ref": "synthetic corner"}
    base.update(witness)
    site["corner_retreat"] = base
    return site


def test_corner_retreat_equal_depth_either_flange_is_valid():
    candidate = job()
    corner_site(candidate)  # F_A end is S=+t (not retreated), t=2, S=2
    assert not canonical_job_anomalies(candidate)


def test_corner_retreat_deeper_flange_leaves_khuyet_t():
    candidate = job()
    corner_site(candidate, depth_mm={"F_A": 70.0, "F_B": 30.0}, retreated_flange_id="F_A", site_flange_id="F_B")
    assert any("BEND_END_CORNER_RETREAT_KHUYET_T" in e for e in canonical_job_anomalies(candidate))


def test_corner_retreat_shallower_flange_is_valid():
    candidate = job()
    corner_site(candidate, depth_mm={"F_A": 70.0, "F_B": 30.0}, retreated_flange_id="F_B", site_flange_id="F_A")
    assert not canonical_job_anomalies(candidate)


def test_corner_retreat_sign_must_match_retreated_flange():
    candidate = job()
    corner_site(candidate, site_flange_id="F_B")  # F_B is the retreated one but the site has S=+2
    assert any("BEND_END_CORNER_RETREAT_S_MISMATCH" in e for e in canonical_job_anomalies(candidate))


def test_corner_retreat_requires_evidence():
    candidate = job()
    corner_site(candidate, evidence_ref="")
    assert any("BEND_END_CORNER_RETREAT_UNPROVED" in e for e in canonical_job_anomalies(candidate))


def test_positive_step_blocks_spurious_relief_before_any_dxf_is_saved(tmp_path):
    candidate = job()
    add_relief(candidate["parts"][0])
    with pytest.raises(CanonicalContractError, match="BEND_END_RELIEF_FOR_POSITIVE_STEP"):
        export_canonical_job(candidate, tmp_path)
    assert not list(tmp_path.glob("*.dxf"))


def test_claimed_s_cannot_override_measured_physical_edges(tmp_path):
    candidate = job()
    candidate["parts"][0]["bend_end_junctions"][0].update(S_mm=0, decision="SLIT")
    with pytest.raises(CanonicalContractError, match="BEND_END_STEP_MISMATCH"):
        export_canonical_job(candidate, tmp_path)


def test_automatic_relief_cannot_evade_guard_by_omitting_the_entire_inventory():
    candidate = job()
    part = candidate["parts"][0]
    add_relief(part)
    for key in ("source_bend_end_site_ids", "bend_end_junctions", "bend_end_source_edges"):
        part.pop(key)
    assert any("BEND_END_SITE_CENSUS_MISMATCH" in e for e in canonical_job_anomalies(candidate))


@pytest.mark.parametrize("mutation,want", [
    ("drop_site", "BEND_END_SITE_CENSUS_MISMATCH"),
    ("duplicate_site", "BEND_END_SITE_CENSUS_MISMATCH"),
    ("unproved", "BEND_END_EDGE_UNPROVED"),
    ("mixed_frame", "BEND_END_FRAME_MISMATCH"),
    ("missing_direction", "BEND_END_DIRECTION_UNPROVED"),
    ("oblique_measurement", "BEND_END_MEASUREMENT_AXIS_INVALID"),
])
def test_missing_or_wrong_source_witnesses_cannot_pass(mutation, want):
    candidate = job()
    part = candidate["parts"][0]
    site = part["bend_end_junctions"][0]
    edge = part["bend_end_source_edges"][site["web_edge_id"]]
    if mutation == "drop_site":
        part["bend_end_junctions"].pop()
    elif mutation == "duplicate_site":
        part["bend_end_junctions"].append(copy.deepcopy(site))
    elif mutation == "unproved":
        edge["proof"]["endpoint_verified"] = False
    elif mutation == "mixed_frame":
        edge["frame_id"] = "UNRELATED_PROJECTION"
    elif mutation == "missing_direction":
        site.pop("positive_axis_evidence_ref")
    else:
        site["positive_axis"] = [1, 0]
    assert any(want in error for error in canonical_job_anomalies(candidate))


def test_different_fold_directions_do_not_prove_an_r_t_intersection():
    candidate = job()
    part = candidate["parts"][0]
    add_relief(part)
    site = part["bend_end_junctions"][0]
    site.update(mechanism="OPPOSITE_FOLD_R_T", decision="SEPARATE_RULE",
                special_rule_evidence_ref="The folds have different signs",
                intersection_edge_ids=[site["flush_edge_id"], site["web_edge_id"]])
    assert any("BEND_END_PHYSICAL_INTERSECTION_UNPROVED" in e
               for e in canonical_job_anomalies(candidate))


def test_separate_rule_cannot_claim_a_relief_without_physical_members():
    candidate = job()
    part = candidate["parts"][0]
    site = part["bend_end_junctions"][0]
    site.update(mechanism="NON_90_RELIEF", included_angle_deg=135,
                decision="SEPARATE_RULE", special_rule_evidence_ref="synthetic angle control",
                angle_evidence_ref="synthetic printed135deg")
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e for e in canonical_job_anomalies(candidate))


@pytest.mark.parametrize("step", [0.5, 1, 3])
def test_all_proved_positive_steps_remain_no_relief_without_a_t_threshold(step):
    candidate = job()
    part = candidate["parts"][0]
    site = part["bend_end_junctions"][0]
    edge = part["bend_end_source_edges"][site["web_edge_id"]]
    for key in ("start", "end"):
        edge[key][1] = -2+step
    site["S_mm"] = step
    assert not canonical_job_anomalies(candidate)


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("mirror", [False, True])
def test_source_step_is_pose_invariant_and_normal_unfold_survives_readback(tmp_path, angle, mirror):
    candidate = job()
    part = candidate["parts"][0]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    def pose(point, translate=False):
        x, y = point
        if mirror:
            x = -x
        return [c*x-s*y+(400 if translate else 0), s*x+c*y-(70 if translate else 0)]
    for edge in part["bend_end_source_edges"].values():
        edge["start"], edge["end"] = pose(edge["start"], True), pose(edge["end"], True)
    for site in part["bend_end_junctions"]:
        site["positive_axis"] = pose(site["positive_axis"])
    manifest = export_canonical_job(candidate, tmp_path, require_slip_codes=True)
    saved = ezdxf.readfile(tmp_path / manifest["filename"])
    geometry = [e for e in saved.modelspace() if e.dxf.layer == "0"]
    assert manifest["status"] == "PASS"
    assert len(geometry) == 30
    assert sum(e.dxftype() == "CIRCLE" for e in geometry) == 8
    assert sum(e.dxftype() == "LINE" and e.dxf.linetype == "DASHED" for e in geometry) == 8
    assert not any(e.dxf.get("color", 256) in {3, 6} for e in geometry)
    assert not any(e.dxftype() == "ARC" for e in geometry)
    assert all(e.get_xdata("TRAINAICAD") for e in geometry)
    assert len(part["face_graph"]["faces"]) == 5


@pytest.mark.parametrize("step", [0, -2])
def test_flush_and_recessed_sites_still_require_a_slit_and_correct_depth(tmp_path, step):
    candidate = slit_case(step)
    part = candidate["parts"][0]
    depth = slit_depth_from_actual_edge(step, 2)
    assert depth == pytest.approx(2.2)
    manifest = export_canonical_job(candidate, tmp_path)
    saved = ezdxf.readfile(tmp_path / manifest["filename"])
    green = [e for e in saved.modelspace() if e.dxf.layer == "0" and e.dxf.get("color", 256) == 3]
    assert sorted(e.dxftype() for e in green) == ["ARC", "LINE", "LINE"]


@pytest.mark.parametrize("mechanism,angle", [("BOXMET", 90), ("CUSTOM_SOURCE_SLIT", 90), ("NON_90_RELIEF", 135)])
def test_separately_proved_mechanisms_keep_their_own_rules(mechanism, angle):
    candidate = job()
    part = candidate["parts"][0]
    add_relief(part, rule=mechanism)
    site = part["bend_end_junctions"][0]
    site.update(mechanism=mechanism, included_angle_deg=angle, decision="SEPARATE_RULE",
                special_rule_evidence_ref="synthetic control: independently proved routed mechanism")
    if mechanism == "BOXMET":
        # Synthetic four-flange star, NOT the real fixture's five-face chain.
        for bend, flap in zip(part["face_graph"]["bends"], ("F1", "F2", "F4", "F5")):
            bend.update(face_A="F3", face_B=flap)
    elif mechanism == "CUSTOM_SOURCE_SLIT":
        group = {"group_id": "SYNTHETIC_CUSTOM_SLIT", "family": "SLIT_RELIEF",
                 "status": "PROVED", "source_quantity": 1,
                 "evidence": "synthetic explicit custom slit leader",
                 "members": [{"member_id": "CUSTOM_SLIT", "status": "PROVED"}]}
        part["source_groups"].append(group)
        part["canonical_members"][-1].update(origin="SOURCE", source_member_id="CUSTOM_SLIT", group_id=group["group_id"])
        site["source_group_id"] = group["group_id"]
    else:
        site["angle_evidence_ref"] = "synthetic printed135deg source witness"
    assert not canonical_job_anomalies(candidate)


def test_one_unresolved_site_stays_local_and_cannot_be_production_pass():
    candidate = job()
    part = candidate["parts"][0]
    site = part["bend_end_junctions"][0]
    site.update(status="FLAGGED", decision="FLAGGED")
    site.pop("S_mm")
    assert any("BEND_END_STEP_UNRESOLVED" in error for error in canonical_job_anomalies(candidate))
    part["status"] = "PREVIEW"
    assert not canonical_job_anomalies(candidate)


def test_perpendicular_touching_bends_must_own_a_declared_site():
    """Closes the census against the part's own face graph (no silently skipped corner)."""
    candidate = job()
    part = candidate["parts"][0]
    from bend_end_guard import undeclared_corner_pairs
    entities = {e["entity_id"]: e for e in part["entities"]}
    assert undeclared_corner_pairs(part, entities) == []
    part["bend_end_junctions"] = part["bend_end_junctions"][:1]
    part["source_bend_end_site_ids"] = part["source_bend_end_site_ids"][:1]
    errors = canonical_job_anomalies(candidate)
    assert any("BEND_END_CORNER_SITE_MISSING" in e for e in errors), errors
