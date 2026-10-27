"""Bent part harvested from SEVERAL customer DATA views (data_views): web view, plan view with a hidden-line hole.

U channel 30 / 120 / 30, SPCC t2, Nobi 3.68 (flat 172.64 x 200). Nothing is typed: face ranges, the flat edge and the
outline corners are `datum` members of the DXF views.
"""
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402

FLAT = 172.64


def _dxf(tmp_path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((0, 0), (200, 0)), ((0, 120), (200, 120)), ((0, 0), (0, 120)), ((200, 0), (200, 120)),      # web view
                 ((0, 230), (200, 230)), ((0, 200), (200, 200)), ((0, 200), (0, 230)), ((200, 200), (200, 230))):  # plan
        msp.add_line(a, b)
    msp.add_circle((50, 40), 5)
    msp.add_circle((150, 90), 5)
    msp.add_circle((50, 220), 3.5)                                       # top flange (visible from above)
    msp.add_circle((120, 220), 3.5, dxfattribs={"linetype": "DASHED"})   # bottom flange (hidden line in the plan)
    path = tmp_path / "views.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def _ids(dg):
    def line(a, b):
        return next(p["id"] for p in dg["pieces"] if p["type"] == "LINE" and
                    sorted((tuple(map(round, p["start"])), tuple(map(round, p["end"])))) == sorted((tuple(round(c) for c in a), tuple(round(c) for c in b))))

    def circle(c):
        return next(p["id"] for p in dg["pieces"] if p["type"] == "CIRCLE" and tuple(map(round, p["center"])) == c)
    return line, circle


def _plan(dg, members, transform=None):
    used = {i for m in members for i in m["pieces"]}
    rest = [p["id"] for p in dg["pieces"] if p["id"] not in used and not p.get("duplicate_of")]
    plan = {"members": members, "excluded": [{"reason": "OTHER", "note": "not part of this view's harvest", "pieces": rest}]}
    if transform:
        plan["transform"] = transform
    return plan


def _write(tmp_path, name, dg, plan):
    path = tmp_path / name
    path.write_text(json.dumps(dxf_assemble.assemble(dg, plan)), encoding="utf-8")
    return str(path)


def _spec(tmp_path, **over):
    dg = _digest = _dxf(tmp_path)
    line, circle = _ids(dg)
    web = _write(tmp_path, "web.json", dg, _plan(dg, [
        {"id": "LEFT", "role": "datum", "pieces": [line((0, 0), (0, 120))]},
        {"id": "RIGHT", "role": "datum", "pieces": [line((200, 0), (200, 120))]},
        {"id": "BOT", "role": "datum", "pieces": [line((0, 0), (200, 0))]},
        {"id": "TOP", "role": "datum", "pieces": [line((0, 120), (200, 120))]},
        {"id": "H1", "role": "hole", "pieces": [circle((50, 40))]},
        {"id": "H2", "role": "hole", "pieces": [circle((150, 90))]}]))
    ft = _write(tmp_path, "ft.json", dg, _plan(dg, [
        {"id": "FREE_T", "role": "datum", "pieces": [line((0, 230), (200, 230))]},
        {"id": "WEB_T", "role": "datum", "pieces": [line((0, 200), (200, 200))]},
        {"id": "HT", "role": "hole", "pieces": [circle((50, 220))]}]))
    mirror = {"mirror_x": True, "rotate_deg": 180, "evidence": "plan view of the hidden flange mirrored so that it runs with the chain"}
    fb = _write(tmp_path, "fb.json", dg, _plan(dg, [
        {"id": "FREE_B", "role": "datum", "pieces": [line((0, 230), (200, 230))]},
        {"id": "WEB_B", "role": "datum", "pieces": [line((0, 200), (200, 200))]},
        {"id": "HB", "role": "hole", "pieces": [circle((120, 220))]}], mirror))
    spec = {"code": "26-000900", "material": "SPCC", "t": 2, "page": 1, "envelope": [200, FLAT],
            "bend": {"axis": "Y", "width": 200, "width_ev": "plan 200",
                     "faces": [{"id": "FB", "od": 30, "ev": "30"}, {"id": "FW", "od": 120, "ev": "120"},
                               {"id": "FT", "od": 30, "ev": "30"}],
                     "bends": [{"id": "B1", "angle": 90, "sign": 1, "nobi": 3.68, "ev": "h"},
                               {"id": "B2", "angle": 90, "sign": 1, "nobi": 3.68, "ev": "h"}]},
            "data_views": [
                {"data": web, "origin": "LEFT.min.x", "width": "RIGHT.max.x",
                 "data_faces": [{"face": "FW", "from": "start", "at": "BOT.min.y", "to": "TOP.max.y"}],
                 "members": {"H1": {"group": "D10", "ev": "2-Ø10"}, "H2": {"group": "D10", "ev": "2-Ø10"}}},
                {"data": ft, "origin": "WEB_T.min.x",
                 "data_faces": [{"face": "FT", "from": "end", "at": "FREE_T.min.y", "to": "WEB_T.min.y"}],
                 "members": {"HT": {"group": "D7T", "qty": 1, "ev": "1-Ø7 top"}}},
                {"data": fb, "origin": "WEB_B.min.x",
                 "data_faces": [{"face": "FB", "from": "start", "at": "FREE_B.min.y", "to": "WEB_B.min.y"}],
                 "members": {"HB": {"group": "D7B", "qty": 1, "ev": "1-Ø7 (反対側)"}}}],
            "outline": [["LEFT.min.x", "START"], ["RIGHT.max.x", "START"], ["RIGHT.max.x", "END"], ["LEFT.min.x", "END"]]}
    spec.update(over)
    return spec


def _holes(part):
    return sorted((round(e["center"][0], 6), round(e["center"][1], 6), e["radius"]) for e in part["entities"] if e["type"] == "CIRCLE")


def test_every_coordinate_comes_from_the_data_views(tmp_path):
    part = bc.build_part(_spec(tmp_path))
    line1 = 30 - 3.68
    assert _holes(part) == [(50, line1 + 40, 5), (50, FLAT - 10, 3.5), (120, 10, 3.5), (150, line1 + 90, 5)]
    outer = next(e for e in part["entities"] if e["role"] == "outer")["vertices"]
    xs, ys = [v[0] for v in outer], [v[1] for v in outer]
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((0, 200, 0, FLAT))
    assert [m["file"] if isinstance(m, dict) else m for m in [part["data_provenance"]["file"]]] == ["web.json, ft.json, fb.json"]
    assert part["status"] == "PASS"


def test_hidden_flange_view_must_run_with_the_chain(tmp_path):
    spec = _spec(tmp_path)
    spec["data_views"][2]["data_faces"][0].update({"from": "end"})            # contradicts the mirrored view direction
    with pytest.raises(bc.BuildError, match="from end to a smaller one"):
        bc.build_part(spec)


def test_unknown_datum_reference_is_refused(tmp_path):
    spec = _spec(tmp_path)
    spec["outline"][1][0] = "NOWHERE.max.x"
    with pytest.raises(bc.BuildError, match="exactly one DATA view"):
        bc.build_part(spec)


def test_a_view_without_its_flat_edge_is_refused(tmp_path):
    spec = _spec(tmp_path)
    del spec["data_views"][0]["origin"]
    with pytest.raises(bc.BuildError, match="needs origin"):
        bc.build_part(spec)


def test_start_end_tokens_only_on_the_chain_axis(tmp_path):
    spec = _spec(tmp_path)
    spec["outline"][0] = ["START", "LEFT.min.y"]
    with pytest.raises(bc.BuildError, match="chain-axis"):
        bc.build_part(spec)


def test_flat_part_takes_outline_and_holes_from_datum_lines(tmp_path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((5, 10), (5, 50)), ((25, 10), (25, 50)), ((5, 10), (25, 10)), ((5, 50), (25, 50))):
        msp.add_line(a, b)
    msp.add_circle((15, 20), 2)
    path = tmp_path / "plate.dxf"
    doc.saveas(path)
    dg = dxf_digest.digest(str(path))
    line, circle = _ids(dg)
    plate = _write(tmp_path, "plate.json", dg, _plan(dg, [
        {"id": "L", "role": "datum", "pieces": [line((5, 10), (5, 50))]}, {"id": "R", "role": "datum", "pieces": [line((25, 10), (25, 50))]},
        {"id": "B", "role": "datum", "pieces": [line((5, 10), (25, 10))]}, {"id": "T", "role": "datum", "pieces": [line((5, 50), (25, 50))]},
        {"id": "H1", "role": "hole", "pieces": [circle((15, 20))]}]))
    spec = {"code": "26-000950", "material": "SPCC", "t": 2, "page": 1, "envelope": [20, 40],
            "data_views": [{"data": plate, "origin": ["L.min.x", "B.min.y"], "members": {"H1": {"group": "D4", "ev": "1-Ø4"}}}],
            "outline": [["L.min.x", "B.min.y"], ["R.min.x", "B.min.y"], ["R.min.x", "T.min.y"], ["L.min.x", "T.min.y"]]}
    part = bc.build_part(spec)
    assert _holes(part) == [(10, 10, 2)] and part["status"] == "PASS"
    xs = [v[0] for v in next(e for e in part["entities"] if e["role"] == "outer")["vertices"]]
    assert (min(xs), max(xs)) == pytest.approx((0, 20))
    spec["outline"][0][0] = "START"
    with pytest.raises(bc.BuildError, match="START/END need"):
        bc.build_part(spec)


# ---------------------------------------------------------------------------------------- spans, scalars, corners, closure
def test_face_ods_and_width_come_from_data_spans_with_the_pdf_as_a_gate(tmp_path):
    spec = _spec(tmp_path)
    spec["bend"]["faces"][0]["od"] = {"span": ["FREE_B.min.y", "WEB_B.min.y"], "pdf": 30}
    spec["bend"]["faces"][1]["od"] = {"span": ["BOT.min.y", "TOP.max.y"], "pdf": 120}
    spec["bend"]["faces"][2]["od"] = {"span": ["FREE_T.min.y", "WEB_T.min.y"], "pdf": 30}
    spec["bend"]["width"] = {"span": ["LEFT.min.x", "RIGHT.max.x"], "pdf": 200}
    part = bc.build_part(spec)
    assert part["status"] == "PASS" and part["unfold"]["flat_length_mm"] == pytest.approx(FLAT)
    spec["bend"]["faces"][2]["od"]["pdf"] = 29.8                      # PDF says 29.8, DATA span is 30
    part = bc.build_part(spec)
    assert part["status"] == "PREVIEW" and any("Lệch PDF DATA OD FT" in f for f in part["flags"])
    assert part["unfold"]["flat_length_mm"] == pytest.approx(FLAT)    # DATA wins
    spec["bend"]["faces"][0]["od"]["span"] = ["FREE_B.min.y", "LEFT_T.min.y"]          # two different views
    with pytest.raises(bc.BuildError, match="exactly one DATA view|inside one DATA view"):
        bc.build_part(spec)


def _plate_dxf(tmp_path, right_x2=25.0):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((5, 10), (5, 50)), ((25, 10), (25, 50)), ((right_x2, 10), (right_x2, 50)), ((5, 10), (25, 10)), ((5, 50), (25, 50))):
        if a != b:
            msp.add_line(a, b)
    msp.add_arc((8, 13), 3, 180, 270)                                       # R3 at the lower left corner
    msp.add_line((25, 48), (23, 50))                                        # C2 at the upper right corner
    msp.add_line((0, 0), (30, 40))                                          # length 50
    msp.add_line((100, 0), (100, 4))
    msp.add_line((127, 0), (127, 4))
    path = tmp_path / "plate2.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def _plate_spec(tmp_path, **over):
    dg = _plate_dxf(tmp_path)
    line, _ = _ids(dg)
    arc = next(p["id"] for p in dg["pieces"] if p["type"] == "ARC")
    plate = _write(tmp_path, "plate2.json", dg, _plan(dg, [
        {"id": "L", "role": "datum", "pieces": [line((5, 10), (5, 50))]}, {"id": "R", "role": "datum", "pieces": [line((25, 10), (25, 50))]},
        {"id": "B", "role": "datum", "pieces": [line((5, 10), (25, 10))]}, {"id": "T", "role": "datum", "pieces": [line((5, 50), (25, 50))]},
        {"id": "RC", "role": "datum", "pieces": [arc]}, {"id": "CH", "role": "datum", "pieces": [line((25, 48), (23, 50))]},
        {"id": "DG", "role": "datum", "pieces": [line((0, 0), (30, 40))]},
        {"id": "W1", "role": "datum", "pieces": [line((100, 0), (100, 4))]}, {"id": "W2", "role": "datum", "pieces": [line((127, 0), (127, 4))]}]))
    spec = {"code": "26-000960", "material": "SPCC", "t": 2, "page": 1, "envelope": [20, 40],
            "data_views": [{"data": plate, "origin": ["L.min.x", "B.min.y"], "members": {}}],
            "outline": [["L.min.x", "B.min.y", {"R": "RC.radius", "pdf_R": 3, "group": "R3", "ev": "R3"}], ["R.min.x", "B.min.y"],
                        ["R.min.x", "T.min.y", {"C": "CH.leg", "pdf_C": 2, "group": "C2", "ev": "C2"}], ["L.min.x", "T.min.y"]]}
    spec.update(over)
    return spec


def test_corner_r_and_c_come_from_datum_arc_and_chamfer(tmp_path):
    part = bc.build_part(_plate_spec(tmp_path))
    assert part["status"] == "PASS"
    called = sorted(r["decision"] for r in part["corner_inventory"] if r["decision"] == "CALLED")
    assert called == ["CALLED", "CALLED"]
    spec = _plate_spec(tmp_path)
    spec["outline"][0][2]["pdf_R"] = 3.5                                   # PDF R3.5 against DATA R3
    part = bc.build_part(spec)
    assert part["status"] == "PREVIEW" and any("Lệch PDF" in f and "R" in f for f in part["flags"])


def test_length_and_span_scalars_build_a_rectangle_without_typed_numbers(tmp_path):
    spec = _plate_spec(tmp_path, envelope=[50, 27])
    spec["outline"] = [["ZERO", "ZERO"], ["DG.length", "ZERO"], ["DG.length", {"span": ["W1.min.x", "W2.min.x"]}], ["ZERO", {"span": ["W1.min.x", "W2.min.x"]}]]
    spec["data_views"][0]["origin"] = None
    spec["data_views"][0].pop("origin")
    part = bc.build_part(spec)
    outer = next(e for e in part["entities"] if e["role"] == "outer")["vertices"]
    assert (max(v[0] for v in outer), max(v[1] for v in outer)) == pytest.approx((50, 27))


def _snap_spec(tmp_path, offset, nominal):
    dg = _plate_dxf(tmp_path)           # not used for geometry of the outline below: the right edge comes from two lines
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((5, 10), (5, 50)), ((25, 10), (25, 30)), ((25 + offset, 30), (25 + offset, 50)), ((5, 10), (25, 10)), ((5, 50), (25, 50))):
        msp.add_line(a, b)
    path = tmp_path / "snap.dxf"
    doc.saveas(path)
    dg = dxf_digest.digest(str(path))
    line, _ = _ids(dg)
    plate = _write(tmp_path, "snap.json", dg, _plan(dg, [
        {"id": "L", "role": "datum", "pieces": [line((5, 10), (5, 50))]}, {"id": "RA", "role": "datum", "pieces": [line((25, 10), (25, 30))]},
        {"id": "RB", "role": "datum", "pieces": [line((25 + offset, 30), (25 + offset, 50))]},
        {"id": "B", "role": "datum", "pieces": [line((5, 10), (25, 10))]}, {"id": "T", "role": "datum", "pieces": [line((5, 50), (25, 50))]}]))
    return {"code": "26-000970", "material": "SPCC", "t": 2, "page": 1, "envelope": [20, 40],
            "data_views": [{"data": plate, "origin": ["L.min.x", "B.min.y"], "members": {}}],
            "outline": [["L.min.x", "B.min.y"], ["RA.min.x", "B.min.y", {"pdf": nominal}], ["RA.min.x", "RA.max.y"],
                        ["RB.min.x", "RB.min.y", {"pdf": nominal}], ["RB.min.x", "T.min.y"], ["L.min.x", "T.min.y"]]}


def test_two_views_that_disagree_by_0_01_are_closed_keeping_the_edge_nearer_to_the_pdf(tmp_path):
    part = bc.build_part(_snap_spec(tmp_path, 0.01, [20, None]))
    xs = sorted({round(v[0], 6) for v in next(e for e in part["entities"] if e["role"] == "outer")["vertices"]})
    assert max(xs) == 20.0 and part["status"] == "PASS"                    # RB (20.01) was moved to RA (20.0)
    ledger = part["manufacturing_change_ledger"]
    assert any(r["rule"] == "CLOSURE_SNAP" and r["old"] == 20.01 and r["new"] == 20.0 for r in ledger)


def test_closure_without_a_pdf_dimension_is_flagged_and_a_larger_gap_is_not_touched(tmp_path):
    part = bc.build_part(_snap_spec(tmp_path, 0.01, None))
    assert any("CLOSURE_SNAP" in f and "chưa có kích thước PDF" in f for f in part["flags"])
    part = bc.build_part(_snap_spec(tmp_path, 0.05, [20, None]))
    xs = {round(v[0], 3) for v in next(e for e in part["entities"] if e["role"] == "outer")["vertices"]}
    assert 20.05 in xs and not any(r["rule"] == "CLOSURE_SNAP" for r in part["manufacturing_change_ledger"])


def test_roundtrip_to_data_catches_a_moved_hole(tmp_path):
    import data_part
    spec = _spec(tmp_path)
    out, extra = data_part.to_spec(spec)
    part = bc.build_part(out)
    next(e for e in part["entities"] if e["type"] == "CIRCLE")["center"][0] += 0.01
    with pytest.raises(data_part.DataPartError, match="DATA_ROUNDTRIP_FAIL"):
        data_part.finish(part, extra)


def test_hypot_scalar_builds_a_slanted_length_from_two_spans(tmp_path):
    spec = _plate_spec(tmp_path, envelope=[45, 27])
    width = {"span": ["W1.min.x", "W2.min.x"]}                              # 27
    length = {"hypot": [width, 36]}                                         # 27-36-45
    spec["outline"] = [["ZERO", "ZERO"], [length, "ZERO"], [length, width], ["ZERO", width]]
    spec["data_views"][0].pop("origin")
    part = bc.build_part(spec)
    outer = next(e for e in part["entities"] if e["role"] == "outer")["vertices"]
    assert (max(v[0] for v in outer), max(v[1] for v in outer)) == pytest.approx((45, 27))
