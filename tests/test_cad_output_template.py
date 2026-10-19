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
    texts = _texts(ezdxf.readfile(TEMPLATE))
    code = next(e for e in texts if e.dxf.text == "00-000000")
    assert abs(code.dxf.insert.y - (100 + X.CODE_LABEL_OFFSET_MM)) < 1e-6  # sample part top y=100
    flags = sorted((e for e in texts if e.dxf.text.startswith("FLAG")), key=lambda e: -e.dxf.insert.y)
    assert [round(a.dxf.insert.y - b.dxf.insert.y, 3) for a, b in zip(flags, flags[1:])] == [X.FLAG_LINE_PITCH_MM] * 2
    assert abs((flags[0].dxf.insert.x - 100) - X.FLAG_LABEL_CLEARANCE_MM) < 1.0  # sample part right x=100
    long_marks = sorted((e for e in texts if e.dxf.text in ("J", "LJ")), key=lambda e: e.dxf.insert.x)
    x0 = 6.121059627732378  # sample long part left edge, L=1650
    xs = [e.dxf.insert.x - x0 for e in long_marks]
    assert [e.dxf.text for e in long_marks] == ["J", "J", "LJ"]
    assert abs(xs[0] - X.JLJ_FIRST_OFFSET_MM) < 1.0
    assert abs(1650 - xs[2] - X.JLJ_LAST_OFFSET_MM) < 1.0
    assert abs(xs[1] - (xs[0] + xs[2]) / 2) < 1.0
    points = [e for e in ezdxf.readfile(TEMPLATE).modelspace() if e.dxftype() == "POINT"]
    assert len(points) == 3  # one POINT per J/LJ text, at the text insert


def test_new_doc_strips_sample_entities():
    doc = X.new_doc()
    assert len(doc.modelspace()) == 0
    assert doc.header["$INSUNITS"] == 4 and doc.header["$MEASUREMENT"] == 1
