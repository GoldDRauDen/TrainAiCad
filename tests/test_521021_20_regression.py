"""521021-20: hole-family chains, KEGAKI across the bend (closed union), dx on back-face KEGAKI (rule text)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import pytest

from weld_kegaki_guard import WeldKegakiError, check_kegaki_drawing_form


def test_hole_family_chains_are_independent():
    assert 230 - 200 - 15 == 15      # 2-M8 left axis
    assert 230 - 15 == 215           # 2-M8 right axis
    assert 230 - 204 - 13 == 13      # 4-M5 left axis (NOT 15)
    assert 230 - 13 == 217           # 4-M5 right axis
    assert (65 + 259) - (450 - 115 - 25) == 14     # D plate M5 row below its top edge
    assert 25 - 14 == 11


def test_kegaki_union_rectangle_across_the_bend_values():
    line1, flange_inner, rib_base, rib_web, flange_t = 84.38, 90, 65, 150, 9
    assert flange_inner - rib_base == 25
    assert round(line1 + flange_t + rib_web, 2) == 243.38
    assert round(99 + 230 - 14.62, 2) == 314.38


def _part(lines):
    return {"code": "26-062288", "entities": [
        {"entity_id": "OUT", "type": "LWPOLYLINE", "role": "outer", "closed": True,
         "vertices": [[0, 0, 0], [75, 0, 0], [75, 314.38, 0], [0, 314.38, 0]]}] + [
        {"entity_id": f"K{i}", "type": "LINE", "role": "kegaki", "color": 1, "start": a, "end": b}
        for i, (a, b) in enumerate(lines)]}


def test_closed_union_rectangle_is_valid_drawing_form():
    y0, y1 = 314.38 - 243.38, 314.38 - 25.0
    check_kegaki_drawing_form(_part([
        ([34.5, y0], [40.5, y0]), ([40.5, y0], [40.5, y1]),
        ([40.5, y1], [34.5, y1]), ([34.5, y1], [34.5, y0])]))


def test_kegaki_line_on_contour_still_rejected():
    with pytest.raises(WeldKegakiError):
        check_kegaki_drawing_form(_part([([0, 10], [0, 100])]))


def test_rule_text_present():
    out = (ROOT / "tools/DXF_INPUT_SCHEMA.md").read_text(encoding="utf-8")
    assert "KEGAKI on the BACK face of the drawn view" in out and "dx_label: true" in out
    datum = (ROOT / "skills/lispcad/core/DATUM_DIMENSION.md").read_text(encoding="utf-8")
    assert "Each hole family has its OWN dimension string" in datum
    fp = (ROOT / "references/KEGAKI_FOOTPRINT_FROM_PDF.md").read_text(encoding="utf-8")
    assert "Child standing on two faces of a bent host" in fp and "243.38" in fp
    assert "canonical flat frame" in (ROOT / "skills/lispcad/modes/BEND_UNFOLD.md").read_text(encoding="utf-8").lower()
