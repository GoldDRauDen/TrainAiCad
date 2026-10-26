"""A circle is ONE CIRCLE and an arc ONE ARC (521026-13: disc outline and KEGAKI rings were split)."""
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc
from curve_guard import split_curve_errors
from export_canonical_dxf import export_canonical_job
from geometry_containment import part_containment_errors


def disc_job():
    spec = {"code": "26-000098", "material": "SPHCP", "t": 3.2, "page": 4, "envelope": [100, 100],
            "outline": {"circle": {"center": [50, 50], "d": 100, "ev": "Ø100 disc"}},
            "kegaki": [{"id": "K1", "group": "KEG_TUBE", "qty": 1, "ev": "tube end Ø34, handwritten ケガキ",
                        "circles": [{"center": [50, 50], "d": 34}]}]}
    return {"canonical_contract": bc.CONTRACT, "job_id": "TEST-CIRCLE", "parts": [bc.build_part(spec)]}


def test_round_blank_and_round_mark_are_one_entity_each(tmp_path):
    job = disc_job()
    manifest = export_canonical_job(job, tmp_path, require_slip_codes=False)
    saved = [e for e in ezdxf.readfile(tmp_path / manifest["filename"]).modelspace() if e.dxf.layer == "0"]
    assert sorted((e.dxftype(), e.dxf.get("color", 256), round(e.dxf.radius, 3)) for e in saved) == \
        [("CIRCLE", 1, 17.0), ("CIRCLE", 256, 50.0)]
    row, = bc.summary(job)
    assert row["blank_mm"] == [100.0, 100.0]


def test_kegaki_circle_outside_the_material_is_refused():
    part = disc_job()["parts"][0]
    next(e for e in part["entities"] if e["role"] == "kegaki")["center"] = [95, 50]
    assert any("FEATURE_OUTSIDE_MATERIAL" in e for e in part_containment_errors(part))


def semicircles(cx=0.0, cy=0.0, r=10.0):
    return {"entity_id": "E_OUT", "type": "LWPOLYLINE", "role": "outer", "closed": True,
            "vertices": [[cx - r, cy, 1], [cx + r, cy, 1]]}


def test_a_circle_written_as_two_arcs_or_many_lines_is_refused():
    assert split_curve_errors({"entities": [semicircles()]}) == []          # one polyline = one CIRCLE on export
    arcs = [{"entity_id": "A1", "type": "ARC", "center": [0, 0], "radius": 10, "start_angle": 0, "end_angle": 180},
            {"entity_id": "A2", "type": "ARC", "center": [0, 0], "radius": 10, "start_angle": 180, "end_angle": 360}]
    assert any(m.startswith("SPLIT_ARC_FAIL") for m in split_curve_errors({"entities": arcs}))
    n = 72
    pts = [(8 * math.cos(2 * math.pi * k / n), 8 * math.sin(2 * math.pi * k / n)) for k in range(n)]
    lines = [{"entity_id": f"L{k}", "type": "LINE", "start": list(pts[k]), "end": list(pts[(k + 1) % n])} for k in range(n)]
    assert any(m.startswith("SPLIT_CIRCLE_FAIL") for m in split_curve_errors({"entities": lines}))
    poly = {"entity_id": "P", "type": "LWPOLYLINE", "closed": True, "role": "kegaki",
            "vertices": [[x, y, 0] for x, y in pts]}
    assert any(m.startswith("SPLIT_CIRCLE_FAIL") for m in split_curve_errors({"entities": [poly]}))


def test_an_arc_cut_in_two_pieces_is_refused_but_corner_arcs_are_fine():
    a = {"entity_id": "A1", "type": "ARC", "center": [0, 0], "radius": 10, "start_angle": 0, "end_angle": 45}
    b = {"entity_id": "A2", "type": "ARC", "center": [0, 0], "radius": 10, "start_angle": 45, "end_angle": 90}
    assert any(m.startswith("SPLIT_ARC_FAIL") for m in split_curve_errors({"entities": [a, b]}))
    corner = {"entity_id": "A3", "type": "ARC", "center": [10, 10], "radius": 10, "start_angle": 180, "end_angle": 270}
    other = {"entity_id": "A4", "type": "ARC", "center": [40, 10], "radius": 10, "start_angle": 270, "end_angle": 360}
    assert split_curve_errors({"entities": [corner, other]}) == []          # same R, different centres


def test_facet_run_needs_a_curve_not_a_zigzag_or_a_box():
    zig = [{"entity_id": f"Z{k}", "type": "LINE", "start": [10 * k, 5 * (k % 2)], "end": [10 * (k + 1), 5 * ((k + 1) % 2)]}
           for k in range(16)]
    assert split_curve_errors({"entities": zig}) == []
    box = [{"entity_id": f"B{k}", "type": "LINE", "start": p, "end": q} for k, (p, q) in enumerate(
        zip([(0, 0), (10, 0), (10, 5), (0, 5)], [(10, 0), (10, 5), (0, 5), (0, 0)]))]
    assert split_curve_errors({"entities": box}) == []


def test_data_parts_keep_the_curves_of_the_customer_dxf():
    n = 72
    pts = [(8 * math.cos(2 * math.pi * k / n), 8 * math.sin(2 * math.pi * k / n)) for k in range(n)]
    lines = [{"entity_id": f"L{k}", "type": "LINE", "start": list(pts[k]), "end": list(pts[(k + 1) % n])} for k in range(n)]
    assert split_curve_errors({"entities": lines, "data_provenance": {"file": "x.dxf"}}) == []


def test_a_round_weld_mark_is_one_red_circle_for_the_kh851_guards():
    from canonical_contract import validate_canonical_job
    from test_weld_kegaki_guard import fixture_job, part_of
    job = fixture_job()
    mark = part_of(job)["entities"][2]
    mark.clear()
    mark.update(entity_id="E_MARK_B", type="CIRCLE", role="kegaki", color=1, center=[25, 10], radius=5)
    assert validate_canonical_job(job)["parts"][0]["weld_kegaki_closure"]["status"] == "PASS"
    mark["color"] = 256
    with pytest.raises(Exception, match="RED|Red|red"):
        validate_canonical_job(job)
