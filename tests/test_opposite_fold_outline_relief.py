"""OPPOSITE_FOLD_R_T relief drawn inside the outer contour (ByLayer arc R = t) is accepted by the bend-end guard."""
import copy
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bend_end_guard import bend_end_errors

T = 3.2


def keyhole_vertices(cx, cy, radius, fillet=0.5):
    """Outer contour with an R=radius relief hole centred on (cx, cy) and R0.5 junctions (CCW outline, bulged)."""
    dy = math.sqrt((radius + fillet) ** 2 - fillet ** 2)
    th = math.atan2(dy, fillet)
    f1, f2 = (cx - fillet, cy - dy), (cx + dy, cy + fillet)
    k = radius / (radius + fillet)
    t1 = (cx + k * (f1[0] - cx), cy + k * (f1[1] - cy))
    t2 = (cx + k * (f2[0] - cx), cy + k * (f2[1] - cy))
    big = (math.pi + th) - (math.pi / 2 - th)
    return [[0, 0, 0], [cx, 0, 0], [cx, f1[1], math.tan(th / 4)], [t1[0], t1[1], -math.tan(big / 4)],
            [t2[0], t2[1], math.tan(th / 4)], [f2[0], cy, 0], [cx + 30, cy, 0], [cx + 30, cy + 80, 0], [0, cy + 80, 0]]


def edge(pid, a, b, bend):
    return {"physical_edge_id": pid, "frame_id": "PDF_FRONT", "type": "LINE", "bend_id": bend, "start": a, "end": b,
            "proof": {"source_pdf_page": 5, "evidence_ref": "test", "endpoint_verified": True}}


def part(radius=T, declared_radius=T, declared_center=(265.0, 78.6), vertices=None):
    return {
        "code": "T", "thickness_mm": T, "status": "PASS",
        "entities": [{"entity_id": "OUT", "type": "LWPOLYLINE", "role": "outer", "closed": True,
                      "vertices": vertices or keyhole_vertices(265.0, 78.6, radius)}],
        "canonical_members": [{"canonical_member_id": "CM_R", "origin": "DERIVED_RULE", "status": "PROVED",
                               "controlling_rule": "OPPOSITE_FOLD_R_T", "source_member_ids": ["S"],
                               "entity_ids": ["OUT"], "bend_end_site_id": "BR",
                               "outline_relief": {"center": list(declared_center), "radius": declared_radius}}],
        "face_graph": {"bends": [{"bend_id": "B2"}, {"bend_id": "B4"}]},
        "source_bend_end_site_ids": ["BR"],
        "bend_end_source_edges": {"E2": edge("F2F3.EDGE", [0.0, 0.0], [265.0, 0.0], "B2"),
                                  "E4": edge("F3F5.EDGE", [265.0, 0.0], [265.0, 83.2], "B4")},
        "bend_end_junctions": [{
            "site_id": "BR", "status": "PROVED", "frame_id": "PDF_FRONT", "bend_ids": ["B2", "B4"],
            "flush_edge_id": "E2", "web_edge_id": "E4", "positive_axis": [0.0, 1.0],
            "positive_axis_evidence_ref": "test", "included_angle_deg": 90, "S_mm": 0,
            "mechanism": "OPPOSITE_FOLD_R_T", "decision": "SEPARATE_RULE", "special_rule_evidence_ref": "test",
            "intersection_edge_ids": ["E2", "E4"], "relief_member_ids": ["CM_R"]}],
    }


def test_relief_arc_inside_the_outline_is_accepted():
    assert bend_end_errors(part()) == []


def test_relief_radius_must_equal_t():
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e for e in bend_end_errors(part(radius=2.0, declared_radius=2.0)))


def test_declared_arc_must_exist_in_the_outline():
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e for e in bend_end_errors(part(radius=2.5)))      # outline arc R2.5
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e for e in bend_end_errors(part(declared_center=(266.0, 78.6))))
    plain = [[0, 0, 0], [295, 0, 0], [295, 160, 0], [0, 160, 0]]
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e for e in bend_end_errors(part(vertices=plain)))


def test_member_must_own_the_outer_polyline_and_the_right_rule():
    wrong_entity = part()
    wrong_entity["entities"][0]["role"] = "cutout"
    assert any("BEND_END_RELIEF_MEMBER_UNPROVED" in e for e in bend_end_errors(wrong_entity))
    wrong_site = part()
    wrong_site["bend_end_junctions"][0]["mechanism"] = "BOXMET"
    assert bend_end_errors(wrong_site)
    wrong_rule = copy.deepcopy(part())
    wrong_rule["canonical_members"][0]["controlling_rule"] = "BEND_END_OFFSET_90"
    assert bend_end_errors(wrong_rule)
