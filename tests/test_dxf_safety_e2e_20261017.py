"""Production DXF safety regressions: J/LJ, stadium, bend-end slit (read-back)."""
import copy
import math
import sys
from pathlib import Path

import ezdxf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_canonical_dxf import export_canonical_job
from export_dxf import CHECKS, export_job
from slot_anchor import SlotAnchorError, stadium_geometry
from slit_geometry import (connected_slit, lead_end_by_offset, lead_val,
                           slit_dir_from_bend, slit_depth_from_actual_edge)


def _part(length=1200, width=80, code="26-061234"):
    return {
        "code": code, "material": "SS", "thickness_mm": 2,
        "status": "PASS", "flags": [],
        "checks": dict.fromkeys(CHECKS, "PASS"),
        "entities": [{
            "type": "LWPOLYLINE", "role": "outer", "closed": True,
            "vertices": [[0, 0, 0], [length, 0, 0],
                         [length, width, 0], [0, width, 0]],
        }],
    }


def _mark(part, positions):
    top = max(v[1] for v in part["entities"][0]["vertices"])
    for i, x in enumerate(positions):
        part["entities"].extend([
            {"type": "POINT", "role": "mark", "point": [x, top]},
            {"type": "TEXT", "role": "mark", "insert": [x, top],
             "height": 10, "text": "LJ" if i == len(positions) - 1 else "J"},
        ])


@pytest.mark.parametrize("length,count", [
    (1000, 2), (1500, 2), (1500.01, 3),
    (2000, 3), (2000.01, 4), (2500, 4),
])
def test_jlj_exact_thresholds_and_composite_readback(tmp_path, length, count):
    p = _part(length=length)
    xs = [35 + i * (length - 67) / (count - 1) for i in range(count)]
    _mark(p, xs)
    name = f"J{int(length * 100)}"
    export_job({"job_id": name, "parts": [p]}, tmp_path)
    doc = ezdxf.readfile(tmp_path / f"{name}_ALL.dxf")
    texts = [e.dxf.text for e in doc.modelspace()
             if e.dxftype() == "TEXT" and e.dxf.layer == "0"]
    assert texts == ["J"] * (count - 1) + ["LJ"]
    assert len([e for e in doc.modelspace() if e.dxftype() == "POINT"]) == count


def test_jlj_rejects_marks_at_missing_top_material_edge(tmp_path):
    p = _part(length=1012)
    # The LJ nominal location x=980 is in an actual notch (970..990).
    p["entities"][0]["vertices"] = [
        [0, 0, 0], [1012, 0, 0], [1012, 80, 0],
        [990, 80, 0], [990, 70, 0], [970, 70, 0],
        [970, 80, 0], [0, 80, 0],
    ]
    _mark(p, [35, 980])
    with pytest.raises(ValueError, match="J/LJ_MARKS_NOT_ON_TOP_MATERIAL_EDGE"):
        export_job({"job_id": "NOTCH", "parts": [p]}, tmp_path)
    assert not list(tmp_path.glob("*.dxf"))


def test_jlj_production_cut_files_exclude_marks(tmp_path):
    p = _part(length=1200)
    p["entities"][0]["entity_id"] = "E_OUTER"
    _mark(p, [35, 1168])
    p["entities"][1]["entity_id"] = "E_J"
    p["entities"][2]["entity_id"] = "E_J_TEXT"
    p["entities"][3]["entity_id"] = "E_LJ"
    p["entities"][4]["entity_id"] = "E_LJ_TEXT"
    p["source_groups"] = [{
        "group_id": "G_OUTER", "family": "OUTER", "status": "PROVED",
        "source_quantity": 1,
        "members": [{"member_id": "M_OUTER", "status": "PROVED"}],
    }]
    p["canonical_members"] = [{
        "canonical_member_id": "CM_OUTER", "origin": "SOURCE",
        "source_member_id": "M_OUTER", "group_id": "G_OUTER",
        "status": "PROVED", "entity_ids": ["E_OUTER"],
    }]
    job = {
        "canonical_contract": "TrainAiCad-CANONICAL-V4.34",
        "job_id": "JLCUT", "parts": [p],
    }
    out = export_canonical_job(job, tmp_path, individual_dxf=True)
    assert out["status"] == "PASS"
    combined = ezdxf.readfile(tmp_path / "JLCUT_ALL.dxf")
    cut = ezdxf.readfile(tmp_path / "parts_dxf" / "26-061234.dxf")
    assert [e.dxf.text for e in combined.modelspace()
            if e.dxftype() == "TEXT" and e.dxf.layer == "0"] == ["J", "LJ"]
    assert {e.dxftype() for e in cut.modelspace()} == {"LINE"}
    assert not any(e.dxftype() in {"TEXT", "POINT"} for e in cut.modelspace())


CW = [[-3.3, 1.75, 0], [-3.3, 5.75, -1],
      [3.3, 5.75, 0], [3.3, 1.75, -1]]
CCW = [[3.3, 1.75, 0], [3.3, 5.75, 1],
       [-3.3, 5.75, 0], [-3.3, 1.75, 1]]


def test_stadium_cw_ccw_are_same_physical_cut_in_saved_dxf(tmp_path):
    for i, vertices in enumerate((CW, CCW)):
        dims = stadium_geometry(vertices)
        assert dims["width_mm"] == pytest.approx(6.6)
        assert dims["overall_length_mm"] == pytest.approx(10.6)
        p = _part(length=30, width=25)
        p["entities"].append({
            "type": "LWPOLYLINE", "role": "slot", "closed": True,
            "vertices": [[x + 12, y + 6, bulge] for x, y, bulge in vertices],
        })
        jid = f"SLOT{i}"
        export_job({"job_id": jid, "parts": [p]}, tmp_path)
        doc = ezdxf.readfile(tmp_path / f"{jid}_ALL.dxf")
        assert len([e for e in doc.modelspace() if e.dxftype() == "ARC"]) == 2
        assert not any(e.dxftype() == "LWPOLYLINE" for e in doc.modelspace())


def test_stadium_same_sign_arcs_but_nontangent_sides_are_rejected():
    bad = copy.deepcopy(CW)
    bad[1][0] += 1
    bad[2][0] += 1
    with pytest.raises(SlotAnchorError, match="SLOT_CANONICAL_GEOMETRY_UNVERIFIABLE"):
        stadium_geometry(bad)
    bad = copy.deepcopy(CW)
    bad[3][2] = 1
    with pytest.raises(SlotAnchorError):
        stadium_geometry(bad)


@pytest.mark.parametrize("material,thickness,expected", [
    ("SS400", 3.2, 3.0), ("SECC-P", 1.2, 3.0),
    ("ボンデ", 2.0, 3.0), ("SPCC", 3.3, 6.0),
    ("A5052", 2.5, 6.0), ("SUS304-2B", 2.0, 6.0),
])
def test_lead_material_uses_source_backed_family(material, thickness, expected):
    assert lead_val(material, thickness) == expected


def test_bend_end_slit_signed_s_and_saved_geometry(tmp_path):
    assert slit_depth_from_actual_edge(5.1, 1.2) is None  # 060722
    assert slit_depth_from_actual_edge(1.6, 1.2) is None
    depth = slit_depth_from_actual_edge(0, 2.5)  # 060730/060732
    assert depth == pytest.approx(2.7)
    delta = lead_end_by_offset((25, 10), (-1, 0), (0, -1), 6)
    assert delta == (19, 4)
    geo = connected_slit((25, 10), (0, 1), (-6, -6), depth)
    p = _part(length=50, width=30)
    p["entities"].extend([
        {"type": "LINE", "role": "slit", "color": 3,
         "start": list(geo["line1"][0]), "end": list(geo["line1"][1])},
        {"type": "ARC", "role": "slit", "color": 3,
         "center": list(geo["arc"]["center"]), "radius": geo["arc"]["radius"],
         "start_angle": geo["arc"]["start_angle"],
         "end_angle": geo["arc"]["end_angle"]},
        {"type": "LINE", "role": "slit", "color": 3,
         "start": list(geo["line2"][0]), "end": list(geo["line2"][1])},
    ])
    export_job({"job_id": "SLITCUT", "parts": [p]}, tmp_path)
    entities = list(ezdxf.readfile(tmp_path / "SLITCUT_ALL.dxf").modelspace())
    assert len([e for e in entities if e.dxftype() == "LINE" and
                e.dxf.get("color", 256) == 3]) == 2
    arcs = [e for e in entities if e.dxftype() == "ARC" and e.dxf.get("color", 256) == 3]
    assert len(arcs) == 1 and arcs[0].dxf.radius == pytest.approx(0.5)


@pytest.mark.parametrize("side,web", [
    ((1, 0), (1, 0)), ((1, 0), (-1, 0)),
])
def test_parallel_edges_cannot_supply_lead(side, web):
    with pytest.raises(ValueError, match="SLIT_EDGES_PARALLEL_REVIEW"):
        lead_end_by_offset((10, 10), side, web, 6)


@pytest.mark.parametrize("short,delta,depth", [
    ((0, 1), (0, 6), 2.7),
    ((0, 1), (0, -6), 2.7),
    ((0, 1), (-0.1, 6), 0.1),
    ((0, 1), (0, 0), 2.7),
])
def test_degenerate_slit_fails_closed(short, delta, depth):
    with pytest.raises(ValueError):
        connected_slit((0, 0), short, delta, depth)


def test_unproved_inward_side_and_zero_bend_dir_fail_closed():
    with pytest.raises(ValueError):
        slit_dir_from_bend((0, 0), (0, 1))
    with pytest.raises(ValueError):
        slit_dir_from_bend((1, 0), (1, 0))


@pytest.mark.parametrize("source_vertices", [CW, CCW])
def test_v434_slot_witness_to_composite_and_individual_cut(tmp_path, source_vertices):
    """Real V4.34 gate chain: member -> witness -> saved composite -> saved CUT."""
    verts = [[x + 12, y + 6, bulge] for x, y, bulge in source_vertices]
    p = _part(length=40, width=30)
    p["entities"][0]["entity_id"] = "E_OUTER"
    p["entities"].append({
        "entity_id": "E_SLOT", "type": "LWPOLYLINE", "role": "slot",
        "closed": True, "vertices": verts,
    })
    p["source_groups"] = [
        {"group_id": "G_OUTER", "family": "OUTER", "status": "PROVED",
         "source_quantity": 1, "members": [{"member_id": "M_OUTER", "status": "PROVED"}]},
        {"group_id": "G_SLOT", "family": "SLOT", "status": "PROVED",
         "source_quantity": 1, "members": [{"member_id": "M_SLOT", "status": "PROVED"}]},
    ]
    p["canonical_members"] = [
        {"canonical_member_id": "CM_OUTER", "origin": "SOURCE",
         "source_member_id": "M_OUTER", "group_id": "G_OUTER",
         "status": "PROVED", "entity_ids": ["E_OUTER"]},
        {"canonical_member_id": "CM_SLOT", "origin": "SOURCE",
         "source_member_id": "M_SLOT", "group_id": "G_SLOT",
         "status": "PROVED", "entity_ids": ["E_SLOT"]},
    ]
    p["slot_anchor_records"] = [{
        "slot_id": "M_SLOT", "entity_id": "E_SLOT",
        "source_pdf_page": 2, "evidence_ref": "PDF:p2:slot",
        "witness_verified": True, "anchor_point": [12, 9.75],
        "anchor_type": "SLOT_MIDPOINT", "axis_unit": [0, 1],
        "width_mm": 6.6, "center_distance_mm": 4,
        "overall_length_mm": 10.6, "canonical_midpoint": [12, 9.75],
    }]
    p["witness_required_feature_ids"] = ["M_SLOT"]
    p["feature_witness_graph"] = {
        "nodes": {"D": "OUTER_EDGE", "S": "SLOT_MIDPOINT"},
        "edges": [
            {"from_node": "D", "to_node": "S", "axis": axis, "kind": "LOCAL",
             "value_mm": value,
             "proof": {"pdf_page": 2, "evidence_ref": "PDF:p2:slot",
                       "endpoint_verified": True, "from_type": "OUTER_EDGE",
                       "to_type": "SLOT_MIDPOINT"}}
            for axis, value in (("X", 12), ("Y", 9.75))
        ],
        "targets": [
            {"feature_id": "M_SLOT", "datum_node": "D", "feature_node": "S",
             "axis": axis, "coordinate_mm": value, "entity_id": "E_SLOT",
             "datum_entity_id": "E_OUTER", "datum_coordinate_mm": 0}
            for axis, value in (("X", 12), ("Y", 9.75))
        ],
    }
    index = 1 if source_vertices is CCW else 0
    jid = f"V434SLOT{index}"
    result = export_canonical_job({
        "canonical_contract": "TrainAiCad-CANONICAL-V4.34",
        "job_id": jid, "parts": [p],
    }, tmp_path, individual_dxf=True)
    assert result["status"] == "PASS"
    combined = ezdxf.readfile(tmp_path / f"{jid}_ALL.dxf")
    cut = ezdxf.readfile(tmp_path / "parts_dxf" / "26-061234.dxf")
    assert sum(e.dxftype() == "ARC" for e in combined.modelspace()) == 2
    assert sum(e.dxftype() == "ARC" for e in cut.modelspace()) == 2
    assert all(e.dxftype() in {"LINE", "ARC", "CIRCLE"}
               for e in cut.modelspace())
    assert cut.audit().has_errors is False
