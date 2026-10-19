"""templates/CAD_OUTPUT_TEMPLATE.dxf sample layout stays in sync with export_dxf constants."""
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import export_dxf as X

TEMPLATE = ROOT / "templates" / "CAD_OUTPUT_TEMPLATE.dxf"


def _texts(doc):
    return [e for e in doc.modelspace() if e.dxftype() == "TEXT"]


def test_template_text_style_layers_and_header():
    doc = ezdxf.readfile(TEMPLATE)
    assert {"0", "Defpoints", "DIM"} <= {l.dxf.name for l in doc.layers}
    assert "Standard" in doc.styles and "DASHED" in doc.linetypes
    assert doc.header["$PDMODE"] == 3 and doc.header["$PDSIZE"] == 5
    assert doc.header["$TEXTSIZE"] == 10
    assert all(e.dxf.style == "Standard" for e in _texts(doc))


def test_template_sample_text_sizes_match_exporter():
    heights = {}
    for e in _texts(ezdxf.readfile(TEMPLATE)):
        key = "flag" if e.dxf.text.startswith("FLAG") else e.dxf.text if e.dxf.text in ("dx", "J", "LJ") else "code"
        heights.setdefault(key, set()).add(e.dxf.height)
    assert heights == {"code": {X.CODE_LABEL_HEIGHT_MM}, "dx": {X.DX_LABEL_HEIGHT_MM},
                       "flag": {X.FLAG_LABEL_HEIGHT_MM}, "J": {X.JLJ_TEXT_HEIGHT_MM},
                       "LJ": {X.JLJ_TEXT_HEIGHT_MM}}


def test_template_sample_positions_match_exporter():
    doc = ezdxf.readfile(TEMPLATE)
    texts = _texts(doc)
    code = next(e for e in texts if e.dxf.text == "00-000000")
    assert abs(code.dxf.insert.y - (100 + X.CODE_LABEL_OFFSET_MM)) < 1e-6  # sample part top y=100
    flags = sorted((e for e in texts if e.dxf.text.startswith("FLAG")), key=lambda e: -e.dxf.insert.y)
    assert [round(a.dxf.insert.y - b.dxf.insert.y, 3) for a, b in zip(flags, flags[1:])] == [X.FLAG_LINE_PITCH_MM] * 2
    assert abs((flags[0].dxf.insert.x - 100) - X.FLAG_LABEL_CLEARANCE_MM) < 1.0  # sample part right x=100
    long_marks = sorted((e for e in texts if e.dxf.text in ("J", "LJ")), key=lambda e: e.dxf.insert.x)
    assert [e.dxf.text for e in long_marks] == ["J", "J", "LJ"]
    assert all(e.dxf.layer == "0" for e in long_marks)  # J/LJ stay on layer 0 (labels use AI_META)
    # sample long part: C5 chamfer left, C2 chamfer right -> marks at X1+30 and X2-30 of the max-Y edge
    top_lines = [e for e in doc.modelspace() if e.dxftype() == "LINE" and not e.dxf.linetype == "DASHED"
                 and abs(e.dxf.start.y - 292.875) < 0.01 and abs(e.dxf.end.y - 292.875) < 0.01]
    x1 = min(min(e.dxf.start.x, e.dxf.end.x) for e in top_lines)
    x2 = max(max(e.dxf.start.x, e.dxf.end.x) for e in top_lines)
    xs = [e.dxf.insert.x for e in long_marks]
    assert abs(xs[0] - (x1 + X.JLJ_INSET_MM)) < 0.01
    assert abs(xs[2] - (x2 - X.JLJ_INSET_MM)) < 0.01
    assert abs(xs[1] - (xs[0] + xs[2]) / 2) < 0.01
    points = [e for e in doc.modelspace() if e.dxftype() == "POINT"]
    assert len(points) == 3  # one POINT per J/LJ text, at the text insert


def test_new_doc_strips_sample_entities():
    doc = X.new_doc()
    assert len(doc.modelspace()) == 0
    assert doc.header["$INSUNITS"] == 4 and doc.header["$MEASUREMENT"] == 1
