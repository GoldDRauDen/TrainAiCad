"""V4.34 521013-21 semantic negative gates and single DXF pose regression."""
import copy
import math
import sys
from pathlib import Path

import ezdxf
import pytest
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from canonical_contract import CanonicalContractError, validate_canonical_job
from dimension_witness import WitnessError, validate_graph
from material_resolver import MaterialResolveError, is_hairline, resolve_material
from slot_anchor import SlotAnchorError, slot_midpoint, validate_slot_anchor
from export_canonical_dxf import export_canonical_job
from export_dxf import CHECKS
from holistic_engineering_guard import canonical_job_anomalies
from slot_anchor import stadium_geometry


def source_group(code, family="OUTER", member="M_OUTER"):
    return {
        "group_id": "G_" + member,
        "family": family,
        "status": "PROVED",
        "source_quantity": 1,
        "members": [{"member_id": member, "status": "PROVED"}],
    }


def model(code="A", width=12, height=40, material="SS", grain=None):
    entity_id = "E_" + code + "_OUTER"
    part = {
        "code": code, "material": material, "thickness_mm": 1.6,
        "status": "PASS", "checks": {key: "PASS" for key in CHECKS}, "flags": [],
        "entities": [{"entity_id": entity_id, "type": "LWPOLYLINE", "role": "outer",
                      "closed": True, "vertices": [[0,0,0],[width,0,0],
                                                    [width,height,0],[0,height,0]]}],
        "source_groups": [source_group(code)],
        "canonical_members": [{
            "canonical_member_id": "CM_" + code, "origin": "SOURCE",
            "source_member_id": "M_OUTER", "group_id": "G_M_OUTER",
            "status": "PROVED", "entity_ids": [entity_id],
        }],
    }
    if grain is not None:
        part["grain"] = grain
    return part


def job(part, version="TrainAiCad-CANONICAL-V4.31"):
    return {"canonical_contract": version, "job_id": "QA_V434", "parts": [part]}


def test_excel_material_aliases_and_process_split():
    cases = [
        ("SECC", "SS"), ("ボンデ", "SS"), ("SECC-P", "SS"),
        ("SPCC", "SS"), ("SPHC", "SS"), ("SS400", "SS"),
        ("SUS304 HL", "SUS"), ("A5052", "AL"), ("銅", "CU_BRASS"),
    ]
    for name, group in cases:
        assert resolve_material(name)["material_family"] == group
    assert resolve_material("ボンデ")["source_cell"].endswith("A32")
    assert resolve_material("SECC=ボンデ")["material_family"] == "SS"
    assert resolve_material("SUS430", "NOBI")["process_group"] == "SS_SUS430_BRASS"
    assert resolve_material("430", "NOBI")["process_group"] == "SS_SUS430_BRASS"
    assert resolve_material("SUS430", "LASER_R")["process_group"] == "SUS"
    assert is_hairline("SUS304 HL")
    with pytest.raises(MaterialResolveError):
        resolve_material("HL")


def chain(wrong=False):
    end = "EDGE_R" if wrong else "HOLE_R"
    return {
        "nodes": {"EDGE_R":"OUTER_EDGE", "HOLE_R":"HOLE_CENTER",
                  "DIAMOND_R":"HOLE_CENTER"},
        "edges": [
            {"from_node":"EDGE_R","to_node":"HOLE_R","axis":"X","kind":"LOCAL",
             "value_mm":-10,"proof":{"pdf_page":3,"evidence_ref":"p3:right-hole",
                    "endpoint_verified":True,"from_type":"OUTER_EDGE","to_type":"HOLE_CENTER"}},
            {"from_node":end,"to_node":"DIAMOND_R","axis":"X","kind":"CHAIN",
             "value_mm":-265,"proof":{"pdf_page":3,"evidence_ref":"p3:dim265",
                    "endpoint_verified":True,"from_type":"OUTER_EDGE" if wrong else "HOLE_CENTER",
                    "to_type":"HOLE_CENTER"}},
        ],
        "targets":[{"feature_id":"M_4HOLES","datum_node":"EDGE_R",
                    "feature_node":"DIAMOND_R","axis":"X","coordinate_mm":-275}],
    }


def test_059759_dim265_uses_hole_center_not_outer_edge():
    assert validate_graph(chain())[("M_4HOLES","X")] == -275
    with pytest.raises(WitnessError, match="DIMENSION_CHAIN_MISMATCH"):
        validate_graph(chain(wrong=True))


def test_witness_endpoint_proof_is_required():
    bad = chain()
    bad["edges"][0]["proof"]["endpoint_verified"] = False
    with pytest.raises(WitnessError, match="WITNESS_ENDPOINT_UNPROVED"):
        validate_graph(bad)


def test_059761_to_059764_slot_midpoint_is_not_end_arc_center():
    rec = {
        "slot_id":"S1","entity_id":"E_SLOT", "source_pdf_page":5,
        "evidence_ref":"p5:dim32", "witness_verified":True,
        "anchor_point":[0,32], "anchor_type":"SLOT_MIDPOINT",
        "axis_unit":[0,1], "width_mm":6.6, "center_distance_mm":7.5,
        "overall_length_mm":14.1, "canonical_midpoint":[0,32],
    }
    assert validate_slot_anchor(rec) == (0,32)
    rec["anchor_type"] = "ARC_CENTER_1"
    with pytest.raises(SlotAnchorError, match="SLOT_ANCHOR_MISMATCH"):
        validate_slot_anchor(rec)
    assert slot_midpoint([0,32], "ARC_CENTER_1", [0,1], 6.6, 7.5) == (0,35.75)
    assert slot_midpoint([0,32], "OUTER_TIP_1", [0,1], 6.6, 7.5) == (0,39.05)


def test_v434_blocks_missing_hole_witness_while_v431_works():
    part = model()
    hole = {"entity_id":"E_HOLE", "type":"CIRCLE", "role":"hole",
            "center":[10,20], "radius":3.3}
    part["entities"].append(hole)
    part["source_groups"].append(source_group("A", family="HOLE", member="M_HOLE"))
    part["canonical_members"].append({
        "canonical_member_id":"CM_HOLE", "origin":"SOURCE",
        "source_member_id":"M_HOLE", "group_id":"G_M_HOLE",
        "status":"PROVED", "entity_ids":["E_HOLE"],
    })
    validate_canonical_job(job(part))
    with pytest.raises(CanonicalContractError, match="WITNESS_REQUIRED_FEATURE_MISSING"):
        validate_canonical_job(job(part, "TrainAiCad-CANONICAL-V4.34"))
    # A real source witness and X/Y coordinates are mandatory for V4.34 HOLE.
    part["witness_required_feature_ids"] = ["M_HOLE"]
    part["feature_witness_graph"] = chain()
    with pytest.raises(CanonicalContractError, match="WITNESS_CANONICAL_ENTITY_LINK_MISSING"):
        part["feature_witness_graph"]["targets"][0]["feature_id"] = "M_HOLE"
        validate_canonical_job(job(part, "TrainAiCad-CANONICAL-V4.34"))


def test_cut_x_long_y_short_and_xdata_readback(tmp_path):
    part = model(width=12, height=40)
    result = export_canonical_job(job(part), tmp_path, individual_dxf=True)
    cut = tmp_path / "parts_dxf/A.dxf"
    assert cut.exists()
    doc = ezdxf.readfile(cut)
    ext = bbox.extents(doc.modelspace(), fast=False)
    assert ext.extmax.x-ext.extmin.x >= ext.extmax.y-ext.extmin.y
    assert result["artifacts"]["parts"][0]["orientation"]["rotation_deg"] == 90
    assert {ent.dxftype() for ent in doc.modelspace()} <= {"LINE","ARC","CIRCLE"}
    assert all(ent.get_xdata("TRAINAICAD") for ent in doc.modelspace())


def test_hl_proof_takes_priority_over_x_long(tmp_path):
    part = model(width=12, height=40, material="SUS304 HL",
                 grain={"is_hl":True,"direction_xy":[1,0],"evidence_ref":"PDF:grain-arrow"})
    result = export_canonical_job(job(part, "TrainAiCad-CANONICAL-V4.34"), tmp_path, individual_dxf=True)
    cut = ezdxf.readfile(tmp_path / "parts_dxf/A.dxf")
    ext = bbox.extents(cut.modelspace(), fast=False)
    assert math.isclose(ext.extmax.x-ext.extmin.x,12,abs_tol=1e-7)
    assert math.isclose(ext.extmax.y-ext.extmin.y,40,abs_tol=1e-7)
    assert result["artifacts"]["parts"][0]["orientation"]["grain_along_x"]


def test_unproved_hl_is_review_not_fake_magenta(tmp_path):
    part = model(material="SUS304 HL", grain={"is_hl":True,"direction_xy":None,
                                              "evidence_ref":None})
    part.update(status="REVIEW", review_reason="HL_DIRECTION_UNPROVED",
                flags=["HL is printed but grain arrow is missing"])
    result = export_canonical_job(job(part, "TrainAiCad-CANONICAL-V4.34"),tmp_path)
    assert result["status"] == "REVIEW_ONLY"
    assert (tmp_path/"QA_V434_ALL_REVIEW_ONLY.dxf").exists()
    assert not list((tmp_path/"parts_dxf").glob("*.dxf"))
    with pytest.raises(CanonicalContractError, match="HL_DIRECTION_UNPROVED"):
        wrong = copy.deepcopy(part)
        wrong.update(status="PASS",flags=[])
        validate_canonical_job(job(wrong, "TrainAiCad-CANONICAL-V4.34"))


def test_pass_rejects_flagged_source_member_and_unknown_quantity():
    part = model()
    part["source_groups"][0]["members"][0]["status"] = "FLAGGED"
    part["canonical_members"][0]["status"] = "PREVIEW"
    with pytest.raises(CanonicalContractError, match="PASS_WITH_FLAGGED_SOURCE_MEMBERS"):
        validate_canonical_job(job(part))

    part = model()
    part["source_groups"][0]["source_quantity"] = None
    with pytest.raises(CanonicalContractError, match="PASS_WITH_UNKNOWN_SOURCE_QUANTITY"):
        validate_canonical_job(job(part))


def test_v434_rejects_zero_hl_vector_before_composite_export():
    part = model(material="SUS304 HL", grain={"is_hl":True,
        "direction_xy":[0,0], "evidence_ref":"PDF:grain-arrow"})
    with pytest.raises(CanonicalContractError, match="HL_DIRECTION_INVALID"):
        validate_canonical_job(job(part, "TrainAiCad-CANONICAL-V4.34"))


def test_v434_green_piercing_requires_scoped_english_stamp():
    part = model()
    part["entities"].append({"entity_id":"E_PIASU","type":"POINT",
        "role":"through_piercing","color":3,"point":[8,9]})
    part["source_groups"].append(source_group("A", family="PIASU", member="M_PIASU"))
    part["canonical_members"].append({"canonical_member_id":"CM_PIASU","origin":"SOURCE",
        "source_member_id":"M_PIASU","group_id":"G_M_PIASU","status":"PROVED",
        "entity_ids":["E_PIASU"]})
    v434 = "TrainAiCad-CANONICAL-V4.34"
    with pytest.raises(CanonicalContractError, match="THROUGH_PIERCING_SOURCE_SCOPE_UNPROVED"):
        validate_canonical_job(job(part, v434))
    part["piercing_authorizations"] = [{"member_id":"M_PIASU","entity_id":"E_PIASU",
        "source_pdf_page":2,"evidence_ref":"PDF:p2:stamp","stamp_text":"PIERCING THROUGH HOLE"}]
    validate_canonical_job(job(part, v434))
    part["piercing_authorizations"][0]["stamp_text"] = "PIERCING 通シ"
    with pytest.raises(CanonicalContractError, match="THROUGH_PIERCING_SOURCE_SCOPE_UNPROVED"):
        validate_canonical_job(job(part, v434))


def test_slot_guard_compares_stadium_dimensions_not_only_midpoint():
    part = model()
    # Same midpoint and width, but the physical slot has a shorter center gap.
    slot_vertices = [[-3.3,1.75,0],[-3.3,5.75,-1],[3.3,5.75,0],[3.3,1.75,1]]
    part["entities"].append({"entity_id":"E_SLOT","type":"LWPOLYLINE","role":"slot",
        "closed":True,"vertices":slot_vertices})
    part["source_groups"].append(source_group("A", family="SLOT", member="M_SLOT"))
    part["canonical_members"].append({"canonical_member_id":"CM_SLOT","origin":"SOURCE",
        "source_member_id":"M_SLOT","group_id":"G_M_SLOT","status":"PROVED",
        "entity_ids":["E_SLOT"]})
    part["slot_anchor_records"] = [{"slot_id":"M_SLOT","entity_id":"E_SLOT",
        "source_pdf_page":2,"evidence_ref":"PDF:slot-dim","witness_verified":True,
        "anchor_point":[0,3.75],"anchor_type":"SLOT_MIDPOINT","axis_unit":[0,1],
        "width_mm":6.6,"center_distance_mm":7.5,"overall_length_mm":14.1,
        "canonical_midpoint":[0,3.75]}]
    assert stadium_geometry(slot_vertices)["center_distance_mm"] == pytest.approx(4)
    assert any("SLOT_CANONICAL_DIMENSION_MISMATCH" in e for e in canonical_job_anomalies(job(part)))
    rec = part["slot_anchor_records"][0]
    rec["center_distance_mm"], rec["overall_length_mm"] = 4, 10.6
    rec["axis_unit"] = [1,0]
    assert any("SLOT_CANONICAL_AXIS_MISMATCH" in e for e in canonical_job_anomalies(job(part)))


def test_v434_pass_rejects_hole_whose_edge_crosses_blank_boundary():
    part = model()
    part["entities"].append({"entity_id":"E_EDGE_HOLE","type":"CIRCLE","role":"hole",
        "center":[11,20],"radius":3.3})
    part["source_groups"].append(source_group("A", family="HOLE", member="M_EDGE_HOLE"))
    part["canonical_members"].append({"canonical_member_id":"CM_EDGE_HOLE","origin":"SOURCE",
        "source_member_id":"M_EDGE_HOLE","group_id":"G_M_EDGE_HOLE","status":"PROVED",
        "entity_ids":["E_EDGE_HOLE"]})
    assert any("FEATURE_OUTSIDE_MATERIAL:E_EDGE_HOLE" in e
               for e in canonical_job_anomalies(job(part, "TrainAiCad-CANONICAL-V4.34")))


def test_v434_bent_pass_requires_face_graph_and_per_bend_ledger():
    part = model()
    for eid, x in (("E_BEND_A", 3), ("E_BEND_B", 9)):
        part["entities"].append({"entity_id":eid,"type":"LINE","role":"bend",
            "linetype":"DASHED","start":[x,0],"end":[x,40]})
    part["source_groups"].append(source_group("A", family="BEND", member="M_BEND"))
    part["canonical_members"].append({"canonical_member_id":"CM_BEND","origin":"SOURCE",
        "source_member_id":"M_BEND","group_id":"G_M_BEND","status":"PROVED",
        "entity_ids":["E_BEND_A","E_BEND_B"]})
    v434 = "TrainAiCad-CANONICAL-V4.34"
    with pytest.raises(CanonicalContractError, match="PASS_WITHOUT_CLOSED_FACE_GRAPH"):
        validate_canonical_job(job(part, v434))
    part["face_graph"] = {"faces":[
        {"face_id":"F1","source_view":"PDF:p2","local_origin":[0,0],
         "local_axis_u":[1,0],"local_axis_v":[0,1],"contour_edge_ids":["E_OUTER"],
         "source_dimensions":["PDF:p2:width"],"normal_orientation":"PROVED"},
        {"face_id":"F2","source_view":"PDF:p3","local_origin":[0,0],
         "local_axis_u":[1,0],"local_axis_v":[0,1],"contour_edge_ids":["E_OUTER"],
         "source_dimensions":["PDF:p3:height"],"normal_orientation":"PROVED"}],
        "bends":[{"bend_id":"B1","source_member_ids":["M_BEND"],"face_A":"F1","face_B":"F2",
         "face_A_shared_edge":"F1:E1","face_B_shared_edge":"F2:E1","edge_orientation":"PROVED",
         "attachment_source_evidence":"PDF:p3:section","signed_angle_deg":90,
         "material_domain":{"entity_ids":["E_BEND_A","E_BEND_B"],"evidence_ref":"PDF:p3"}}]}
    with pytest.raises(CanonicalContractError, match="BEND_WITNESS_LEDGER_MISSING"):
        validate_canonical_job(job(part, v434))


def test_witness_offsets_are_added_to_the_linked_physical_datum():
    part = model()
    part["entities"][0]["vertices"] = [[100,200,0],[112,200,0],[112,240,0],[100,240,0]]
    part["entities"].append({"entity_id":"E_HOLE","type":"CIRCLE","role":"hole",
        "center":[109,220],"radius":2})
    part["source_groups"].append(source_group("A", family="HOLE", member="M_HOLE"))
    part["canonical_members"].append({"canonical_member_id":"CM_HOLE","origin":"SOURCE",
        "source_member_id":"M_HOLE","group_id":"G_M_HOLE","status":"PROVED",
        "entity_ids":["E_HOLE"]})
    proof = lambda axis: {"pdf_page":2,"evidence_ref":f"PDF:p2:{axis}",
        "endpoint_verified":True,"from_type":"OUTER_EDGE","to_type":"HOLE_CENTER"}
    part["witness_required_feature_ids"] = ["M_HOLE"]
    part["feature_witness_graph"] = {"nodes":{"O":"OUTER_EDGE","H":"HOLE_CENTER"},
        "edges":[
            {"from_node":"O","to_node":"H","axis":"X","kind":"LOCAL","value_mm":9,"proof":proof("X")},
            {"from_node":"O","to_node":"H","axis":"Y","kind":"LOCAL","value_mm":20,"proof":proof("Y")}],
        "targets":[
            {"feature_id":"M_HOLE","datum_node":"O","feature_node":"H","axis":"X","coordinate_mm":9,
             "datum_coordinate_mm":100,"datum_entity_id":"E_A_OUTER","entity_id":"E_HOLE"},
            {"feature_id":"M_HOLE","datum_node":"O","feature_node":"H","axis":"Y","coordinate_mm":20,
             "datum_coordinate_mm":200,"datum_entity_id":"E_A_OUTER","entity_id":"E_HOLE"}]}
    validate_canonical_job(job(part, "TrainAiCad-CANONICAL-V4.34"))
    assert canonical_job_anomalies(job(part, "TrainAiCad-CANONICAL-V4.34")) == []
    part["feature_witness_graph"]["edges"][0]["value_mm"] = 109
    part["feature_witness_graph"]["targets"][0]["coordinate_mm"] = 109
    assert any("WITNESS_CANONICAL_COORDINATE_MISMATCH" in e
               for e in canonical_job_anomalies(job(part, "TrainAiCad-CANONICAL-V4.34")))


def test_composite_only_preserves_json_and_no_parts(tmp_path):
    part = model()
    result = export_canonical_job(job(part), tmp_path, composite_only=True)
    assert result["filename"] == "QA_V434_ALL.dxf"
    assert not (tmp_path/"geometry_json").exists()
    assert not list((tmp_path/"parts_dxf").glob("*.dxf"))
    assert result["artifacts"]["parts"][0]["cut_readback"] == "COMPOSITE_ONLY"
