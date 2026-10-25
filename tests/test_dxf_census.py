"""tools/dxf_census.py: bulges decode to arcs, parts cluster top-to-bottom, holes summarised by Ø."""
import math
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dxf_census  # noqa: E402

Q = math.tan(math.radians(90) / 4)  # quarter-circle bulge


def _dxf(tmp_path):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    # upper part: 100 x 50 plate, one R3 corner as a bulge, two Ø6.6 holes, a red KEGAKI line
    msp.add_lwpolyline([(0, 300, 0), (97, 300, Q), (100, 303, 0), (100, 350, 0), (0, 350, 0)],
                       format="xyb", close=True)
    msp.add_circle((20, 325), 3.3)
    msp.add_circle((80, 325), 3.3)
    msp.add_line((40, 310), (60, 310), dxfattribs={"color": 1})
    # lower part: 60 x 40, closing segment carries the bulge
    msp.add_lwpolyline([(0, 0, 0), (60, 0, 0), (60, 40, 0), (1, 40, Q), (0, 39, 0)], format="xyb", close=True)
    msp.add_text("26-000001", dxfattribs={"insert": (0, 360)})
    path = tmp_path / "data.dxf"
    doc.saveas(path)
    return str(path)


def test_bulges_are_arcs_and_parts_are_clustered_top_to_bottom(tmp_path):
    res = dxf_census.census(_dxf(tmp_path))
    layer = res["layers"]["0"]
    assert layer["bulged_polylines"] == 2 and layer["closed_polylines"] == 2
    assert layer["arc_radii"] == {"R3": 1, "R1": 1}
    assert layer["holes_by_dia"] == {"Ø6.6": 2}
    assert layer["annotations"] == {"TEXT": 1}
    top, bottom = res["clusters_top_to_bottom"]
    assert top["size"] == [100.0, 50.0] and top["holes_by_dia"] == {"Ø6.6": 2} and top["colors"]["1"] == 1
    assert bottom["size"] == [60.0, 40.0] and bottom["arc_radii"] == {"R1": 1}
    assert any(r.get("bulge_decoded") for r in res["_decoded"] if r["type"] == "ARC")


def test_cli_writes_decoded_pieces(tmp_path):
    out = tmp_path / "decoded.json"
    assert dxf_census.main([_dxf(tmp_path), "--out", str(out)]) == 0
    assert out.is_file() and '"ARC"' in out.read_text(encoding="utf-8")
