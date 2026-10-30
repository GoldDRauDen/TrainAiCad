"""SOURCE_DRAWN_RELIEF: a relief the PDF/DATA already draws (box-corner void + R) is the junction mechanism; no slit.
Custom source slit at the intersection of two outer edges carries the lead (vòi dẫn)."""
import copy
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import boxmet_job
from boxmet_flat import BoxMetError
from corner_guard import outer_sharp_corners
from holistic_engineering_guard import canonical_job_anomalies
from slit_geometry import custom_slit_at_intersection

L, W, H, T, N = 200.0, 150.0, 30.0, 1.5, 2.54
S = 3.5                         # square corner void (outer dims), as drawn by the customer DATA
F = S - N                       # depth of the void inside a flap (a flap's flat starts N inside the outer plane)


def drawn_relief_job():
    """BOXMET star whose four corners are drawn by the source as a square void (no Green slit anywhere)."""
    job = boxmet_job.build_job("26-000001", L, W, (H, H, H, H), T, "SPCC", N, job_id="TEST", customer="646")
    part = job["parts"][0]
    xl, yb = H - N, H - N
    xr, yt = xl + L, yb + W
    xe, ytop = xr + H - N, yt + H - N
    xa, xb, xc = xl + T, xl + S, xl - F
    xa2, xb2, xc2 = xr - T, xr - S, xr + F
    ylo, yc, ya, yd = yb - F, yb + S, yt + F, yt - S
    pts = [(xa, 0), (xa2, 0), (xa2, ylo), (xb2, ylo), (xb2, yc), (xc2, yc), (xc2, yb), (xe, yb), (xe, yt), (xc2, yt),
           (xc2, yd), (xb2, yd), (xb2, ya), (xa2, ya), (xa2, ytop), (xa, ytop), (xa, ya), (xb, ya), (xb, yd), (xc, yd),
           (xc, yt), (0, yt), (0, yb), (xc, yb), (xc, yc), (xb, yc), (xb, ylo), (xa, ylo)]
    outer = next(e for e in part["entities"] if e["role"] == "outer")
    outer["vertices"] = [[round(x, 6), round(y, 6), 0.0] for x, y in pts]
    part["entities"] = [e for e in part["entities"] if e["role"] != "slit"]
    part["canonical_members"] = [m for m in part["canonical_members"] if "_CM_SLIT_" not in m["canonical_member_id"]
                                 and "_CM_AUTO_R_" not in m["canonical_member_id"]]
    lo_x, hi_x, lo_y, hi_y = xl + S, xr - S, yb + S, yt - S
    for e in part["entities"]:
        if e["role"] != "bend":
            continue
        name = e["entity_id"].split("_B_")[1]
        if name.startswith(("BOTTOM", "TOP")):
            y = e["start"][1]
            e["start"], e["end"] = [lo_x, y], [hi_x, y]
        else:
            x = e["start"][0]
            e["start"], e["end"] = [x, lo_y], [x, hi_y]
    for b in part["face_graph"]["bends"]:
        md = b["material_domain"]
        md["span_mm"] = [S, (L if md["axis"] == "X" else W) - S]
        md["edge_length_mm"] = (L if md["axis"] == "X" else W) - 2 * S
    group = {"group_id": "TEST_G_CORNER_RELIEF", "family": "RELIEF_DRAWN", "status": "PROVED", "source_quantity": 4,
             "evidence": "source draws a 3.5 x 3.5 void at every box corner",
             "members": [{"member_id": f"TEST_RELIEF_{c}", "status": "PROVED"} for c in ("BL", "BR", "TR", "TL")]}
    part["source_groups"].append(group)
    corner_pt = {"BL": (xl, yb), "BR": (xr, yb), "TR": (xr, yt), "TL": (xl, yt)}
    for site in part["bend_end_junctions"]:
        c = site["site_id"].rsplit("_", 1)[1]
        member = {"canonical_member_id": f"CM_TEST_RELIEF_{c}", "origin": "SOURCE", "source_member_id": f"TEST_RELIEF_{c}",
                  "group_id": group["group_id"], "status": "PROVED", "entity_ids": [outer["entity_id"]],
                  "bend_end_site_id": site["site_id"]}
        part["canonical_members"].append(member)
        site.update(mechanism="SOURCE_DRAWN_RELIEF", decision="SEPARATE_RULE", relief_member_ids=[member["canonical_member_id"]],
                    source_group_id=group["group_id"], relief_point=list(corner_pt[c]),
                    special_rule_evidence_ref="DATA corner void 3.5 x 3.5, inner corner drawn by the customer")
    part["source_groups"] = [g for g in part["source_groups"]]
    n_src = sum(len(g["members"]) for g in part["source_groups"])
    part["source_physical_member_count"] = part["proved_source_member_count"] = n_src
    part["corner_inventory"] = [
        {"corner_id": f"S{i}", "point": [x, y], "drawn_shape": "SHARP", "decision": "SHARP",
         "evidence_ref": "source draws the corner sharp", "no_auto_r_reason": "test outline without arcs"}
        for i, (x, y) in enumerate(outer_sharp_corners(part), 1)]
    part["bend_end_relief_audit"] = {"controlling_rule": "SOURCE_DRAWN_RELIEF", "junctions": [
        {"site": s["site_id"], "decision": "SEPARATE_RULE", "reason": "relief drawn by the source"} for s in part["bend_end_junctions"]]}
    return job


def test_source_drawn_corner_relief_is_a_valid_mechanism_without_any_slit():
    job = drawn_relief_job()
    assert not [e for e in job["parts"][0]["entities"] if e["role"] == "slit"]
    assert canonical_job_anomalies(job) == []


def test_a_green_slit_on_top_of_the_drawn_relief_is_two_reliefs():
    job = drawn_relief_job()
    part = job["parts"][0]
    site = part["bend_end_junctions"][0]
    part["entities"].append({"entity_id": "EXTRA_SLIT", "type": "LINE", "role": "slit", "color": 3, "start": [0, 0], "end": [1, 0],
                             "bend_end_site_id": site["site_id"]})
    assert any("BEND_END_TWO_RELIEFS" in e for e in canonical_job_anomalies(job))


def test_bend_line_must_stop_at_the_drawn_relief():
    job = drawn_relief_job()
    part = job["parts"][0]
    line = next(e for e in part["entities"] if e["role"] == "bend" and e["entity_id"].endswith("B_BOTTOM_1"))
    line["start"] = [H - N + 1.0, line["start"][1]]          # runs 2.5 mm into the corner void
    assert any("BEND_END_BEND_LINE_ENTERS_RELIEF" in e for e in canonical_job_anomalies(job))


def test_relief_point_must_lie_in_the_void_and_the_group_must_be_proved_source():
    job = drawn_relief_job()
    part = job["parts"][0]
    part["bend_end_junctions"][0]["relief_point"] = [H - N + 50, H - N + 50]      # inside the base material
    assert any("BEND_END_RELIEF_POINT_NOT_IN_VOID" in e for e in canonical_job_anomalies(job))
    job = drawn_relief_job()
    member = next(m for m in job["parts"][0]["canonical_members"] if m.get("source_member_id") == "TEST_RELIEF_BL")
    member["origin"], member["controlling_rule"] = "DERIVED_RULE", "BOXMET"
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e or "BEND_END_SPECIAL_RULE_UNPROVED" in e for e in canonical_job_anomalies(job))
    job = drawn_relief_job()
    job["parts"][0]["bend_end_junctions"][0].pop("special_rule_evidence_ref")
    assert any("BEND_END_SPECIAL_RULE_UNPROVED" in e for e in canonical_job_anomalies(job))


def test_boxmet_generator_refuses_a_box_whose_corner_relief_is_drawn():
    with pytest.raises(BoxMetError, match="BOXMET_SOURCE_DRAWN_RELIEF"):
        boxmet_job.build_job("26-000001", L, W, (H, H, H, H), T, "SPCC", N, drawn_corners="RELIEF")


# ---- custom source slit at the intersection of two outer edges: lead = LeadVal(material, t) on both edges ----
FIXTURE = ROOT / "regression/fixtures/521017-17_061099_positive_step.json"


def custom_slit_job(shift=0.0, base=(50.0, 0.0)):
    import json
    job = json.loads(FIXTURE.read_text(encoding="utf-8"))["job"]
    part = job["parts"][0]                                        # SUS304-2B t2 -> LeadVal 6
    site = part["bend_end_junctions"][0]
    frame = site["frame_id"]
    proof = {"source_pdf_page": 6, "evidence_ref": "synthetic outer edge", "endpoint_verified": True}
    part["bend_end_source_edges"].update(
        OUT_WEB={"physical_edge_id": "X.WEB", "frame_id": frame, "type": "LINE", "start": [0, 0], "end": [50, 0], "proof": proof},
        OUT_SIDE={"physical_edge_id": "X.SIDE", "frame_id": frame, "type": "LINE", "start": [50, 0], "end": [50, -30], "proof": proof})
    geo = custom_slit_at_intersection((50.0, 0.0), (0.0, 1.0), (1.0, 0.0), (0.0, -1.0), 10.0, part["material"], part["thickness_mm"])
    assert geo["lead"] == 6.0
    ents = [{"entity_id": "CS_L1", "type": "LINE", "role": "slit", "color": 3, "start": list(geo["line1"][0]), "end": list(geo["line1"][1])},
            {"entity_id": "CS_ARC", "type": "ARC", "role": "slit", "color": 3, "center": list(geo["arc"]["center"]),
             "radius": geo["arc"]["radius"], "start_angle": geo["arc"]["start_angle"], "end_angle": geo["arc"]["end_angle"]},
            {"entity_id": "CS_L2", "type": "LINE", "role": "slit", "color": 3,
             "start": [geo["line2"][0][0] + shift, geo["line2"][0][1]], "end": list(geo["line2"][1])}]
    for e in ents:
        e["bend_end_site_id"] = site["site_id"]
        part["entities"].append(e)
    group = {"group_id": "CUSTOM_SLIT_G", "family": "SLIT_RELIEF", "status": "PROVED", "source_quantity": 1,
             "evidence": "printed スリット 10 at the intersection of the two outer edges", "members": [{"member_id": "CUSTOM_SLIT", "status": "PROVED"}]}
    part["source_groups"].append(group)
    member = {"canonical_member_id": "CM_CUSTOM_SLIT", "origin": "SOURCE", "source_member_id": "CUSTOM_SLIT", "group_id": group["group_id"],
              "status": "PROVED", "entity_ids": [e["entity_id"] for e in ents], "bend_end_site_id": site["site_id"]}
    part["canonical_members"].append(member)
    site.update(mechanism="CUSTOM_SOURCE_SLIT", decision="SEPARATE_RULE", relief_member_ids=[member["canonical_member_id"]],
                source_group_id=group["group_id"], special_rule_evidence_ref="printed スリット 10", at_edge_intersection=True,
                slit_construction={"base": list(base), "direction": [0.0, 1.0], "length": 10.0, "side_void_normal": [1.0, 0.0],
                                   "web_void_normal": [0.0, -1.0], "web_edge_id": "OUT_WEB", "side_edge_id": "OUT_SIDE"})
    site.pop("S_mm", None)
    return job


def test_custom_slit_lead_values_follow_material_and_thickness():
    geo = custom_slit_at_intersection((0, 0), (0, 1), (-1, 0), (0, -1), 10, "SUS304", 6)
    assert geo["lead"] == 6.0 and geo["line2"][1] == pytest.approx((-6.0, -6.0))       # SUS t6 -> 6|6
    assert custom_slit_at_intersection((0, 0), (0, 1), (-1, 0), (0, -1), 10, "SS400", 9)["lead"] == 6.0
    assert custom_slit_at_intersection((0, 0), (0, 1), (-1, 0), (0, -1), 10, "SS400", 12)["lead"] == 10.0


def test_custom_slit_at_the_edge_intersection_with_its_lead_is_accepted():
    assert canonical_job_anomalies(custom_slit_job()) == []


def test_custom_slit_at_the_edge_intersection_without_the_right_lead_is_rejected():
    assert any("BEND_END_SLIT_LEAD_UNPROVED" in e for e in canonical_job_anomalies(custom_slit_job(shift=0.5)))


def test_custom_slit_claimed_at_the_intersection_must_start_there():
    assert any("BEND_END_SLIT_LEAD_UNPROVED" in e for e in canonical_job_anomalies(custom_slit_job(base=(40.0, 0.0))))


def test_source_drawn_relief_box_exports_pass_with_no_green_entity(tmp_path):
    import ezdxf
    from export_canonical_dxf import export_canonical_job
    manifest = export_canonical_job(drawn_relief_job(), tmp_path, require_slip_codes=True)
    saved = ezdxf.readfile(tmp_path / manifest["filename"])
    geometry = [e for e in saved.modelspace() if e.dxf.layer == "0" and e.dxftype() != "TEXT"]
    assert manifest["status"] == "PASS" and manifest["filename"].endswith("_ALL.dxf")
    assert not any(e.dxf.get("color", 256) == 3 for e in geometry)
