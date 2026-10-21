"""DXF scorer: geometry-only comparison against a reference, used by humans after a run."""
import json

import ezdxf
import pytest

from LuanAppTools.bench.score_dxf import main, score


def new_doc():
    doc = ezdxf.new("R2010", setup=True)  # setup=True registers the DASHED linetype
    doc.layers.add("AI_META")
    return doc


def save(doc, tmp_path, name):
    path = tmp_path / name
    doc.saveas(path)
    return path


def plate(msp, tf=lambda p: p, *, w=200.0, h=100.0, hole=(50.0, 50.0), radius=5.0):
    corners = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        msp.add_line(tf(a), tf(b))
    msp.add_circle(tf(hole), radius)


def rotate90_then_move(p):
    return (-p[1] + 500.0, p[0] + 700.0)


def test_single_part_translated_and_rotated_is_match(tmp_path):
    ref, res = new_doc(), new_doc()
    plate(ref.modelspace())
    plate(res.modelspace(), rotate90_then_move)
    out = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))
    assert len(out["parts"]) == 1
    part = out["parts"][0]
    assert part["status"] == "MATCH"
    assert part["rotation"] == 270  # degrees CCW applied to the result to land on the reference
    assert part["missing"] == [] and part["extra"] == []
    assert part["circles"] == {"reference": 1, "matched": 1}
    assert out["unmatched_reference"] == [] and out["unmatched_result"] == []


def test_hole_off_by_point_two_is_partial_at_strict_tolerance_but_exact_at_one_mm(tmp_path):
    ref, res = new_doc(), new_doc()
    plate(ref.modelspace())
    plate(res.modelspace(), hole=(50.2, 50.0))
    out = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))
    part = out["parts"][0]
    assert part["status"] == "PARTIAL"
    assert part["circles"]["matched"] == 0
    assert part["levels"]["0.01"]["recall"] < 1.0
    assert part["levels"]["1"]["recall"] == pytest.approx(1.0)
    assert part["levels"]["1"]["precision"] == pytest.approx(1.0)


def test_dimension_exactly_at_tolerance_fails_strictly(tmp_path):
    ref, res = new_doc(), new_doc()
    plate(ref.modelspace())
    plate(res.modelspace(), w=200.01)  # repo rule: exactly 0.01 mm is not below the threshold
    out = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))
    assert out["parts"][0]["status"] != "MATCH"


def test_top_to_bottom_pairing_skips_an_extra_reference_cluster(tmp_path):
    ref, res = new_doc(), new_doc()
    rm, sm = ref.modelspace(), res.modelspace()
    plate(rm, lambda p: (p[0], p[1] + 1000.0), w=100.0, h=50.0, hole=(20.0, 25.0), radius=3.0)
    for a, b in [((0, 700), (20, 700)), ((20, 700), (20, 720)), ((20, 720), (0, 720)), ((0, 720), (0, 700))]:
        rm.add_line(a, b)  # small gusset-like cluster that the result does not have
    plate(rm, lambda p: (p[0], p[1] + 300.0), w=60.0, h=60.0, hole=(30.0, 30.0), radius=4.0)
    plate(sm, lambda p: (p[0] + 40.0, p[1] + 800.0), w=100.0, h=50.0, hole=(20.0, 25.0), radius=3.0)
    plate(sm, lambda p: (p[0] - 10.0, p[1] + 100.0), w=60.0, h=60.0, hole=(30.0, 30.0), radius=4.0)
    out = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))
    assert [p["status"] for p in out["parts"]] == ["MATCH", "MATCH"]
    assert len(out["unmatched_reference"]) == 1
    assert out["unmatched_result"] == []
    assert out["summary"]["parts_reference"] == 3 and out["summary"]["parts_result"] == 2


def test_text_labels_and_polylines_are_handled(tmp_path):
    ref, res = new_doc(), new_doc()
    ref.modelspace().add_arc((50, 0), 50, 180, 360)
    ref.modelspace().add_line((100, 0), (0, 0))
    sm = res.modelspace()
    sm.add_lwpolyline([(0, 0, 1), (100, 0, 0)], format="xyb", close=True)
    sm.add_text("26-000001", dxfattribs={"layer": "AI_META", "insert": (0, 10), "height": 3})
    sm.add_text("note", dxfattribs={"layer": "0", "insert": (0, 20), "height": 3})
    out = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))
    assert out["parts"][0]["status"] == "MATCH"


def test_points_and_block_inserts_do_not_crash_and_still_match(tmp_path):
    ref, res = new_doc(), new_doc()
    plate(ref.modelspace())
    ref.modelspace().add_point((10, 10))
    block = res.blocks.new("P")
    corners = [(0, 0), (200, 0), (200, 100), (0, 100)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        block.add_line(a, b)
    block.add_circle((50, 50), 5)
    res.modelspace().add_blockref("P", (300, 300))
    res.modelspace().add_point((310, 310))
    out = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))
    assert out["parts"][0]["status"] == "MATCH"


def test_dashed_bend_line_is_compared_by_category(tmp_path):
    ref, res = new_doc(), new_doc()
    plate(ref.modelspace())
    ref.modelspace().add_line((0, 50), (200, 50), dxfattribs={"linetype": "DASHED"})
    plate(res.modelspace())
    res.modelspace().add_line((0, 50), (200, 50))
    part = score(save(res, tmp_path, "res.dxf"), save(ref, tmp_path, "ref.dxf"))["parts"][0]
    assert part["status"] != "MATCH"
    assert any(item["category"] == "BEND" for item in part["missing"])
    assert any(item["category"] == "CUT" for item in part["extra"])


def test_cli_prints_json_and_signals_mismatch(tmp_path, capsys):
    ref, res = new_doc(), new_doc()
    plate(ref.modelspace())
    plate(res.modelspace(), hole=(60.0, 50.0))
    code = main([str(save(res, tmp_path, "res.dxf")), str(save(ref, tmp_path, "ref.dxf")), "--json"])
    printed = json.loads(capsys.readouterr().out)
    assert printed["parts"][0]["status"] == "PARTIAL"
    assert code == 1
