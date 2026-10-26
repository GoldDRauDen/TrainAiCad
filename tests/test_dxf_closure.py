"""Whole-file census closure over several assemble plans: VIEW_NOT_USED alone never closes a piece."""
import json
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import dxf_closure  # noqa: E402
import dxf_digest  # noqa: E402


def _digest(tmp_path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    msp.add_circle((10, 10), 2)                   # harvested by plan A
    msp.add_circle((50, 10), 3)                   # harvested by plan B
    msp.add_line((0, 0), (100, 0))                # judged by nobody
    msp.add_line((0, 5), (100, 5), dxfattribs={"linetype": "DASHED"})
    path = tmp_path / "c.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def _ids(dg, typ):
    return [p["id"] for p in dg["pieces"] if p["type"] == typ]


def _plans(dg, line_reason):
    c1, c2 = sorted(_ids(dg, "CIRCLE"), key=lambda i: next(p["center"][0] for p in dg["pieces"] if p["id"] == i))
    lines = _ids(dg, "LINE")
    plan_a = {"members": [{"id": "H1", "role": "hole", "pieces": [c1]}],
              "excluded": [{"reason": "VIEW_NOT_USED", "pieces": [c2] + lines}]}
    plan_b = {"members": [{"id": "H2", "role": "hole", "pieces": [c2]}],
              "excluded": [{"reason": line_reason, **({"note": "silhouette"} if line_reason == "OTHER" else {}),
                            "pieces": [c1] + lines}]}
    return plan_a, plan_b


def test_pieces_only_marked_view_not_used_are_unclosed(tmp_path):
    dg = _digest(tmp_path)
    res = dxf_closure.closure(dg, list(_plans(dg, "VIEW_NOT_USED")))
    assert not res["closed"] and len(res["unclosed"]) == 2
    assert {u["suggest"] for u in res["unclosed"]} == {"OTHER", "HIDDEN_OR_PROJECTION_ONLY"}   # the light fix to apply


def test_a_real_reason_in_any_plan_closes_the_file(tmp_path):
    dg = _digest(tmp_path)
    res = dxf_closure.closure(dg, list(_plans(dg, "OTHER")))
    assert res["closed"] and res["by_reason"]["USED"] == 2 and res["by_reason"]["OTHER"] == 2


def test_cli_exit_code_follows_closure(tmp_path):
    dg = _digest(tmp_path)
    (tmp_path / "d.json").write_text(json.dumps(dg), encoding="utf-8")
    for name, reason in (("open", "VIEW_NOT_USED"), ("closed", "OTHER")):
        a, b = _plans(dg, reason)
        (tmp_path / f"{name}_a.json").write_text(json.dumps(a), encoding="utf-8")
        (tmp_path / f"{name}_b.json").write_text(json.dumps(b), encoding="utf-8")
    assert dxf_closure.main([str(tmp_path / "d.json"), str(tmp_path / "open_a.json"), str(tmp_path / "open_b.json")]) == 2
    assert dxf_closure.main([str(tmp_path / "d.json"), str(tmp_path / "closed_a.json"), str(tmp_path / "closed_b.json")]) == 0
