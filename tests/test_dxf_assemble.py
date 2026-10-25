"""tools/dxf_assemble.py: pick DATA pieces by id, change only layer/colour/linetype + a declared rigid transform."""
import copy
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402
from export_dxf import signed_poly_area  # noqa: E402

Q = math.tan(math.radians(90) / 4)


def _digest(tmp_path):
    """Frame + plate (50..150 x 100..150, R3 corner at bottom-right as a bulge) + hole + slot + bend line + noise."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (400, 0), (400, 300), (0, 300)], close=True)
    msp.add_lwpolyline([(50, 100, 0), (147, 100, Q), (150, 103, 0), (150, 150, 0), (50, 150, 0)],
                       format="xyb", close=True)
    msp.add_circle((70, 125), 3.3)
    msp.add_lwpolyline([(100, 120, 0), (110, 120, 1), (110, 130, 0), (100, 130, 1)], format="xyb", close=True)  # slot
    msp.add_line((90, 100), (90, 150), dxfattribs={"linetype": "DASHED", "layer": "0"})
    msp.add_lwpolyline([(200, 100), (240, 100), (240, 120), (200, 120)], close=True)                            # side view
    msp.add_line((300, 50), (301, 50))                                                                          # noise dash
    msp.add_line((60, 60), (80, 60))
    msp.add_line((60, 70), (80, 70))                                                                            # second stray line
    msp.add_line((60, 60), (80, 60))                                                                            # duplicate
    path = tmp_path / "sheet.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path), noise_mm=5.0)


def _ids(d, **match):
    return [p["id"] for p in d["pieces"] if all(p.get(k) == v for k, v in match.items())]


def _plate_view(d):
    return next(v for v in d["views"] if v["kind"] == "PART_VIEW_CANDIDATE" and v["size"] == [100.0, 50.0])


def _full_plan(d, transform=None):
    pieces = {p["id"]: p for p in d["pieces"]}
    plate_ids = _plate_view(d)["piece_ids"]
    plate_id = _plate_view(d)["id"]
    hole = [i for i in plate_ids if pieces[i]["type"] == "CIRCLE"]
    bend = [i for i in plate_ids if pieces[i]["linetype"] == "DASHED"]
    slot = [i for i in plate_ids if pieces[i]["from"] == "LWPOLYLINE" and pieces[i]["type"] in ("LINE", "ARC")
            and 99.9 < pieces[i]["start"][0] < 110.1 and 119.9 < pieces[i]["start"][1] < 130.1
            and 99.9 < pieces[i]["end"][0] < 110.1 and 119.9 < pieces[i]["end"][1] < 130.1]
    outer = [i for i in plate_ids if i not in hole + bend + slot]
    excluded = []
    for v in d["views"]:
        if v["id"] == plate_id:
            continue
        if v["kind"] == "FRAME_CANDIDATE":
            excluded.append({"reason": "FRAME_OR_TITLE_BLOCK", "view": v["id"]})
        elif v["id"] == "B_NOISE":
            excluded.append({"reason": "EXPLODED_TEXT_OR_DIM_NOISE", "bucket": v["id"]})
        elif v["id"] == "B_ISOLATED":
            excluded.append({"reason": "OTHER", "note": "test fixture stray line", "bucket": v["id"]})
        elif v["id"] != "B_DUPLICATE":
            excluded.append({"reason": "VIEW_NOT_USED", "view": v["id"]})
    plan = {"members": [{"id": "OUT", "role": "outer", "pieces": outer},
                        {"id": "H1", "role": "hole", "pieces": hole},
                        {"id": "SL1", "role": "slot", "pieces": slot},
                        {"id": "BL1", "role": "bend", "pieces": bend}],
            "excluded": excluded}
    if transform:
        plan["transform"] = transform
    return plan


def test_full_plan_builds_canonical_entities_and_closes_the_ledger(tmp_path):
    d = _digest(tmp_path)
    res = dxf_assemble.assemble(d, _full_plan(d))
    by_role = {e["role"]: e for e in res["entities"]}
    assert set(by_role) == {"outer", "hole", "slot", "bend"}
    assert res["ledger"]["unaccounted"] == 0 and res["invariance"]["ok"] is True
    assert by_role["hole"]["center"] == pytest.approx([70, 125]) and by_role["hole"]["radius"] == pytest.approx(3.3)
    assert by_role["bend"]["linetype"] == "DASHED" and by_role["bend"]["layer"] == "0"


def test_outer_is_one_ccw_polyline_with_the_source_bulge(tmp_path):
    d = _digest(tmp_path)
    res = dxf_assemble.assemble(d, _full_plan(d))
    outer = next(e for e in res["entities"] if e["role"] == "outer")
    assert outer["type"] == "LWPOLYLINE" and outer["closed"] is True
    assert signed_poly_area(outer["vertices"]) > 0
    assert sorted(round(v[2], 9) for v in outer["vertices"])[-1] == pytest.approx(Q, abs=1e-9)
    assert signed_poly_area(outer["vertices"]) == pytest.approx(100 * 50 - (9 - math.pi * 9 / 4), abs=1e-6)
    xs = [v[0] for v in outer["vertices"]]
    assert min(xs) == 50.0 and max(xs) == 150.0


def test_slot_is_clockwise_and_hole_is_a_circle(tmp_path):
    d = _digest(tmp_path)
    res = dxf_assemble.assemble(d, _full_plan(d))
    slot = next(e for e in res["entities"] if e["role"] == "slot")
    assert signed_poly_area(slot["vertices"]) < 0
    assert next(e for e in res["entities"] if e["role"] == "hole")["type"] == "CIRCLE"


def test_unaccounted_pieces_block_the_assembly(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    plan["excluded"] = [x for x in plan["excluded"] if x.get("bucket") != "B_NOISE"]
    with pytest.raises(dxf_assemble.AssembleError) as e:
        dxf_assemble.assemble(d, plan)
    assert "UNACCOUNTED_PIECES" in str(e.value)


def test_a_piece_cannot_be_used_twice(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    plan["members"].append({"id": "H2", "role": "hole", "pieces": plan["members"][1]["pieces"]})
    with pytest.raises(dxf_assemble.AssembleError, match="PIECE_USED_TWICE"):
        dxf_assemble.assemble(d, plan)


def test_exclusion_needs_a_known_reason_and_other_needs_a_note(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    plan["excluded"][1]["reason"] = "BECAUSE"
    with pytest.raises(dxf_assemble.AssembleError, match="UNKNOWN_REASON"):
        dxf_assemble.assemble(d, plan)
    plan = _full_plan(d)
    del plan["excluded"][2]["note"]
    with pytest.raises(dxf_assemble.AssembleError, match="OTHER_NEEDS_NOTE"):
        dxf_assemble.assemble(d, plan)


def test_unsupported_curve_cannot_be_used(tmp_path):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_ellipse((0, 0), major_axis=(5, 0), ratio=0.5)
    p = tmp_path / "e.dxf"
    doc.saveas(p)
    d = dxf_digest.digest(str(p))
    plan = {"members": [{"id": "X", "role": "cutout", "pieces": ["U0001"]}], "excluded": []}
    with pytest.raises(dxf_assemble.AssembleError, match="UNSUPPORTED_PIECE_USED"):
        dxf_assemble.assemble(d, plan)


def test_open_chain_cannot_be_an_outer(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    dropped = plan["members"][0]["pieces"].pop()
    plan["excluded"].append({"reason": "OTHER", "note": "drop one edge on purpose", "pieces": [dropped]})
    with pytest.raises(dxf_assemble.AssembleError, match="CHAIN_NOT_CLOSED"):
        dxf_assemble.assemble(d, plan)


def test_scale_other_than_one_needs_evidence_and_is_applied_exactly(tmp_path):
    d = _digest(tmp_path)
    with pytest.raises(dxf_assemble.AssembleError, match="TRANSFORM_NEEDS_EVIDENCE"):
        dxf_assemble.assemble(d, _full_plan(d, {"scale": 2.0}))
    res = dxf_assemble.assemble(d, _full_plan(d, {"scale": 2.0, "translate": [-100, -200], "evidence": "p1 view 1:2"}))
    outer = next(e for e in res["entities"] if e["role"] == "outer")
    assert min(v[0] for v in outer["vertices"]) == pytest.approx(0.0) and max(v[0] for v in outer["vertices"]) == pytest.approx(200.0)
    hole = next(e for e in res["entities"] if e["role"] == "hole")
    assert hole["center"] == pytest.approx([40.0, 50.0]) and hole["radius"] == pytest.approx(6.6)
    assert res["invariance"]["ok"] is True


def test_mirror_and_rotation_keep_winding_and_pass_invariance(tmp_path):
    d = _digest(tmp_path)
    for tr in ({"mirror_x": True, "evidence": "mirror view"}, {"rotate_deg": 90, "evidence": "rotated view"},
               {"mirror_x": True, "rotate_deg": 37.5, "scale": 3, "evidence": "all three"}):
        res = dxf_assemble.assemble(d, _full_plan(d, tr))
        outer = next(e for e in res["entities"] if e["role"] == "outer")
        slot = next(e for e in res["entities"] if e["role"] == "slot")
        assert signed_poly_area(outer["vertices"]) > 0 and signed_poly_area(slot["vertices"]) < 0, tr
        assert res["invariance"]["ok"] is True and res["invariance"]["max_dev"] < 1e-6, tr


def test_invariance_check_catches_a_changed_number(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    res = dxf_assemble.assemble(d, plan)
    bad = copy.deepcopy(res)
    next(e for e in bad["entities"] if e["role"] == "outer")["vertices"][1][0] += 0.01
    chk = dxf_assemble.verify_invariance(d, plan, bad)
    assert chk["ok"] is False and chk["errors"]
    bad2 = copy.deepcopy(res)
    next(e for e in bad2["entities"] if e["role"] == "hole")["radius"] += 0.001
    assert dxf_assemble.verify_invariance(d, plan, bad2)["ok"] is False
    bad3 = copy.deepcopy(res)
    bad3["entities"] = [e for e in bad3["entities"] if e["role"] != "bend"]
    assert dxf_assemble.verify_invariance(d, plan, bad3)["ok"] is False


def test_only_layer_colour_linetype_may_change(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    plan["members"][3]["role"] = "kegaki"
    res = dxf_assemble.assemble(d, plan)
    line = next(e for e in res["entities"] if e["role"] == "kegaki")
    assert line["color"] == 1 and "linetype" not in line and line["layer"] == "0"
    assert line["start"] == pytest.approx([90, 100]) and line["end"] == pytest.approx([90, 150])


def test_result_feeds_the_canonical_entity_validator(tmp_path):
    from export_dxf import validate_entity
    d = _digest(tmp_path)
    res = dxf_assemble.assemble(d, _full_plan(d))
    for e in res["entities"]:
        validate_entity({k: v for k, v in e.items() if k not in ("source_piece_ids",)}, "T", False)


def test_digest_hash_mismatch_is_refused(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    plan["source_sha256"] = "0" * 64
    with pytest.raises(dxf_assemble.AssembleError, match="DIGEST_HASH_MISMATCH"):
        dxf_assemble.assemble(d, plan)


def test_cli_end_to_end(tmp_path):
    d = _digest(tmp_path)
    dp, pp, op = tmp_path / "d.json", tmp_path / "p.json", tmp_path / "o.json"
    dp.write_text(json.dumps(d), encoding="utf-8")
    pp.write_text(json.dumps(_full_plan(d)), encoding="utf-8")
    assert dxf_assemble.main([str(dp), str(pp), "--out", str(op)]) == 0
    assert json.loads(op.read_text(encoding="utf-8"))["invariance"]["ok"] is True
    pp.write_text(json.dumps({"members": [], "excluded": []}), encoding="utf-8")
    assert dxf_assemble.main([str(dp), str(pp), "--out", str(op)]) == 2


def test_exclusion_detail_is_one_row_per_reason_and_note(tmp_path):
    d = _digest(tmp_path)
    plan = _full_plan(d)
    iso = next(x for x in plan["excluded"] if x.get("bucket") == "B_ISOLATED")
    ids = next(v["piece_ids"] for v in d["views"] if v["id"] == "B_ISOLATED")
    plan["excluded"].remove(iso)
    plan["excluded"] += [{"reason": "OTHER", "note": "test fixture stray line", "pieces": [i]} for i in ids]
    res = dxf_assemble.assemble(d, plan)
    rows = [(r["reason"], r["note"]) for r in res["ledger"]["excluded_detail"]]
    assert len(rows) == len(set(rows))
    assert sum(r["pieces"] for r in res["ledger"]["excluded_detail"]) == res["ledger"]["excluded"]
