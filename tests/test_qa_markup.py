"""tools/qa_markup.py: <JOB>_AI_QA.dxf = failing profiles copied out with red circle + leader + note (QA_REVERSE)."""
import json
import subprocess
import sys
from pathlib import Path

import ezdxf
import pytest
from ezdxf import bbox

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import qa_markup  # noqa: E402


def _rect(msp, x, y, w, h, layer="0"):
    return msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True,
                              dxfattribs={"layer": layer})


def _src(tmp_path, name, fill):
    doc = ezdxf.new("R2010")
    fill(doc, doc.modelspace())
    p = tmp_path / name
    doc.saveas(p)
    return p


def _run(tmp_path, items, job="J1"):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps({"job": job, "items": items}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out" / f"{job}_AI_QA.dxf"
    assert qa_markup.main([str(issues), str(out)]) == 0
    doc = ezdxf.readfile(out)
    auditor = doc.audit()
    assert not auditor.has_errors, auditor.errors
    return doc


def _texts(msp):
    return [t.dxf.text for t in msp.query("TEXT")]


def test_per_code_profile_with_mark(tmp_path, capsys):
    def fill(doc, msp):
        doc.layers.add("CUT", color=3)
        _rect(msp, 100, 200, 80, 40, layer="CUT")
        msp.add_line((100, 220), (180, 220), dxfattribs={"layer": "CUT"})
    src = _src(tmp_path, "26-063784.dxf", fill)
    doc = _run(tmp_path, [{"code": "26-063784", "src": str(src), "note": "thiếu R5",
                           "marks": [{"x": 180, "y": 240, "note": "R5 thiếu"}]}])
    msp = doc.modelspace()
    pl = msp.query("LWPOLYLINE").first
    assert pl.dxf.layer == "CUT" and doc.layers.get("CUT").color == 3
    ext = bbox.extents([pl])
    assert ext.extmin.isclose((0, 0, 0)) and ext.extmax.isclose((80, 40, 0))
    assert len(msp.query("LINE")) == 1
    circle = msp.query("CIRCLE").first
    assert circle.dxf.layer == "AI_QA" and circle.dxf.color == 1
    assert circle.dxf.center.isclose((80, 40, 0)) and circle.dxf.radius == pytest.approx(3.2)
    leader = msp.query("LEADER").first
    assert leader.dxf.layer == "AI_QA"
    texts = _texts(msp)
    assert any("26-063784" in t and "thiếu R5" in t for t in texts) and "R5 thiếu" in texts
    out = capsys.readouterr().out
    assert "ok 26-063784" in out and "wrote:" in out


def test_bbox_cuts_one_code_from_composite(tmp_path):
    def fill(doc, msp):
        _rect(msp, 0, 0, 50, 50)
        msp.add_circle((25, 25), 5)
        _rect(msp, 200, 0, 30, 90)
    src = _src(tmp_path, "composite.dxf", fill)
    doc = _run(tmp_path, [{"code": "B", "src": str(src), "bbox": [195, -5, 235, 95], "note": ""}])
    msp = doc.modelspace()
    pls = msp.query("LWPOLYLINE")
    assert len(pls) == 1 and not msp.query("CIRCLE")
    assert bbox.extents(pls).size.isclose((30, 90, 0))


def test_items_without_usable_src_are_notes(tmp_path, capsys):
    good = _src(tmp_path, "a.dxf", lambda doc, msp: _rect(msp, 0, 0, 10, 10))
    doc = _run(tmp_path, [
        {"code": "26-000001", "note": "không tìm thấy profile", "marks": [{"x": 1, "y": 2, "note": "lỗ sai"}]},
        {"code": "26-000002", "src": str(tmp_path / "missing.dxf"), "note": "src hỏng"},
        {"code": "26-000003", "src": str(good), "bbox": [500, 500, 600, 600], "note": "bbox rỗng"},
        {"code": "26-000004", "src": str(good), "note": "ok"},
    ])
    msp = doc.modelspace()
    texts = _texts(msp)
    for code in ("26-000001", "26-000002", "26-000003"):
        assert any(t.startswith(code) for t in texts)
    assert any("lỗ sai" in t for t in texts)
    assert len(msp.query("LWPOLYLINE")) == 1 and not msp.query("CIRCLE")
    out = capsys.readouterr().out
    assert out.count("note-only") == 3 and "ok 26-000004" in out


def test_insert_brings_block_definition(tmp_path):
    def fill(doc, msp):
        blk = doc.blocks.new("HOLE_PAT")
        blk.add_circle((0, 0), 2)
        blk.add_line((-3, 0), (3, 0))
        _rect(msp, 0, 0, 60, 30)
        msp.add_blockref("HOLE_PAT", (10, 10))
        msp.add_blockref("HOLE_PAT", (50, 20))
    src = _src(tmp_path, "blk.dxf", fill)
    doc = _run(tmp_path, [{"code": "C", "src": str(src), "note": "x"},
                          {"code": "D", "src": str(src), "note": "y"}])
    msp = doc.modelspace()
    inserts = msp.query("INSERT")
    assert len(inserts) == 4
    for ins in inserts:
        blk = doc.blocks.get(ins.dxf.name)
        assert blk is not None and len(blk.query("CIRCLE")) == 1
    xs = sorted(round(i.dxf.insert.x, 6) for i in inserts)
    assert xs[:2] == [10, 50] and xs[2] > 60


def test_dimension_is_copied_as_its_drawn_geometry(tmp_path):
    def fill(doc, msp):
        doc.layers.add("DIM", color=4)
        _rect(msp, 0, 0, 100, 50)
        msp.add_linear_dim(base=(0, 60), p1=(0, 50), p2=(100, 50), dxfattribs={"layer": "DIM"}).render()
    src = _src(tmp_path, "dim.dxf", fill)
    doc = _run(tmp_path, [{"code": "E", "src": str(src), "note": ""}])
    msp = doc.modelspace()
    assert not msp.query("DIMENSION")
    assert any("100" in m.text for m in msp.query("MTEXT"))
    assert msp.query("LINE[layer=='DIM']")


@pytest.mark.parametrize("content", ["{not json", json.dumps({"job": "J", "items": []}), json.dumps([1])])
def test_bad_input_exits_nonzero(tmp_path, content):
    issues = tmp_path / "issues.json"
    issues.write_text(content, encoding="utf-8")
    out = tmp_path / "o.dxf"
    r = subprocess.run([sys.executable, "tools/qa_markup.py", str(issues), str(out)],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode != 0 and r.stderr.strip() and not out.exists()


def test_missing_issues_file_and_usage(tmp_path):
    assert qa_markup.main([str(tmp_path / "nope.json"), str(tmp_path / "o.dxf")]) == 1
    assert qa_markup.main([]) == 2
