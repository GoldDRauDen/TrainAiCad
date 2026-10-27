"""tools/dxf_partition.py: geometry-only member proposal for one part of a customer-DATA digest."""
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dxf_digest  # noqa: E402
import dxf_partition  # noqa: E402


def _digest(tmp_path):
    doc = ezdxf.new("R2010")
    m = doc.modelspace()
    m.add_lwpolyline([(0, 0), (400, 0), (400, 200), (0, 200)], close=True)                       # outer
    m.add_lwpolyline([(50, 50), (100, 50), (100, 90), (50, 90)], close=True)                     # pocket 1
    m.add_lwpolyline([(150, 50), (200, 50), (200, 90), (150, 90)], close=True)                   # pocket 2
    m.add_lwpolyline([(250, 100, 0), (300, 100, 1), (300, 120, 0), (250, 120, 1)], format="xyb", close=True)   # stadium slot
    for x in (20, 60, 100):
        m.add_circle((x, 160), 3.3)
    m.add_circle((350, 160), 4.5)
    m.add_circle((350, 160), 5.0)                                                                # nominal ring (concentric)
    m.add_line((0, 100), (400, 100), dxfattribs={"linetype": "DASHED"})                          # hidden / centre style
    m.add_line((10, 10), (30, 10), dxfattribs={"layer": "0", "color": 0})                        # dimension-style piece
    m.add_line((200, 0), (200, -10))                                                             # stub touching the edge (T)
    path = tmp_path / "d.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def test_members_come_from_geometry(tmp_path):
    d = _digest(tmp_path)
    res = dxf_partition.partition(d, [-20, -20, 420, 220])
    roles = {m["id"]: (m["role"], len(m["pieces"])) for m in res["members"]}
    assert roles["OUT"] == ("outer", 4)
    assert roles["PK01"] == ("cutout", 4) and roles["PK02"] == ("cutout", 4)
    assert roles["SL1"] == ("slot", 4)
    assert roles["HD6_6"] == ("hole", 3) and roles["HD9"] == ("hole", 1) and roles["HD10"] == ("hole", 1)
    assert res["tap_candidates"] == [{"centre": [350.0, 160.0], "dia": [9.0, 10.0]}]


def test_anything_not_a_simple_loop_is_left_to_the_ai(tmp_path):
    res = dxf_partition.partition(_digest(tmp_path), [-20, -20, 420, 220])
    assert any(len(u["pieces"]) == 1 for u in res["unresolved"])                                # the stub
    assert res["other"]["0|0|CONTINUOUS|LINE"] == 1                                             # dimension-style piece: counted, never a contour
    assert any(k.endswith("DASHED|LINE") for k in res["other"])                                 # counted, reason left to the AI


def test_a_spline_edge_stays_in_the_outer_loop(tmp_path):
    doc = ezdxf.new("R2010")
    m = doc.modelspace()
    m.add_line((0, 0), (30, 0))
    m.add_spline(fit_points=[(30, 0, 0), (40, 1.5, 0), (50, 3, 0)], degree=3)
    for a, b in (((50, 3), (100, 3)), ((100, 3), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))):
        m.add_line(a, b)
    path = tmp_path / "s.dxf"
    doc.saveas(path)
    d = dxf_digest.digest(str(path))
    res = dxf_partition.partition(d, [-5, -5, 105, 55])
    (out,) = [x for x in res["members"] if x["role"] == "outer"]
    assert "U0001" in out["pieces"] and len(out["pieces"]) == 6 and not res["unresolved"]


def test_an_altered_digest_is_refused(tmp_path):
    d = _digest(tmp_path)
    d["pieces"][0]["start"][0] += 1
    with pytest.raises(ValueError, match="DIGEST_PIECES_ALTERED"):
        dxf_partition.partition(d, [-20, -20, 420, 220])
