"""tools/pdf_views.py: exact vector dimension text with grid cells, renders and crops."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
pdf_views = pytest.importorskip("pdf_views")
if pdf_views.fitz is None:
    pytest.skip("PyMuPDF not installed", allow_module_level=True)
fitz = pdf_views.fitz


@pytest.fixture()
def drawing(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)  # A4 landscape
    page.draw_rect(fitz.Rect(100, 100, 500, 400))
    page.insert_text((280, 90), "380", fontsize=10)          # top dimension, cell D2
    page.insert_text((520, 250), "2-Ø6.6", fontsize=10)       # leader note, cell G5
    page.insert_text((120, 450), "M8x1.25", fontsize=10)
    page.insert_text((700, 560), "SPCC t1.6", fontsize=8)     # title block
    path = tmp_path / "d.pdf"
    doc.save(path)
    return str(path)


def test_info_detects_vector_page(drawing):
    res = pdf_views.info(drawing)
    assert res["pages"][0]["kind"] == "VECTOR" and res["pages"][0]["vector_words"] >= 4


def test_text_returns_exact_values_with_cells(drawing):
    spans = {s["text"]: s for s in pdf_views.text(drawing, 1, dims_only=True)["spans"]}
    assert spans["380"]["cell"] == "D2"
    assert "2-Ø6.6" in spans and spans["2-Ø6.6"]["cell"] == "G5"
    assert "M8x1.25" in spans


def test_cells_filter_and_crop(drawing, tmp_path):
    only = pdf_views.text(drawing, 1, cells="G4:H6")["spans"]
    assert [s["text"] for s in only] == ["2-Ø6.6"]
    out = tmp_path / "c.png"
    res = pdf_views.crop(drawing, 1, "C1:E3", str(out), dpi=300)
    assert out.exists() and res["px"][0] > 300


def test_render_with_grid(drawing, tmp_path):
    out = tmp_path / "p.png"
    assert pdf_views.render(drawing, 1, str(out), dpi=72)["grid"] and out.exists()


def test_rotated_page_cells_match_render(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "R5", fontsize=12)
    page.set_rotation(90)
    path = tmp_path / "r.pdf"
    doc.save(path)
    span = pdf_views.text(str(path), 1)["spans"][0]
    assert span["text"] == "R5" and span["cell"] == "J1"
    assert [s["text"] for s in pdf_views.text(str(path), 1, cells="J1:J2")["spans"]] == ["R5"]


def test_pairs_flags_close_same_axis_dimensions(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)
    page.insert_text((60, 300), "70", fontsize=10)
    page.insert_text((80, 300), "65", fontsize=10)    # 20 pt away, same direction: must be cropped
    page.insert_text((400, 300), "1720", fontsize=10)
    path = tmp_path / "p.pdf"
    doc.save(path)
    res = pdf_views.pairs(str(path), 1, 25.0, str(tmp_path / "crops"), dpi=150)
    assert res["kind"] == "VECTOR"
    assert [sorted(p["values"]) for p in res["pairs"]] == [["65", "70"]]
    assert Path(res["pairs"][0]["out"]).exists()


def test_pairs_on_scan_returns_manual_note(tmp_path):
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    path = tmp_path / "s.pdf"
    doc.save(path)
    res = pdf_views.pairs(str(path), 1)
    assert res["pairs"] == [] and res["kind"] == "SCANNED_IMAGE"
