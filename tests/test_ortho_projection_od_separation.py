"""26-062103 (job 521021-06): OD measured from DXF, cut by projection, rotated and joined."""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_chain_flat_and_bend_lines_062103():
    od = [410.8, 20.8, 175.0]
    nobi = [1.68, 0.36]
    flat = sum(od) - sum(nobi)
    assert math.isclose(flat, 604.56, abs_tol=1e-9)
    line1_1 = od[0] - nobi[0]
    line2_1 = od[0]
    line1_2 = od[0] + od[1] - sum(nobi)
    line2_2 = od[0] + od[1] - nobi[0]
    assert (round(line1_1, 2), round(line2_1, 2)) == (409.12, 410.8)
    assert (round(line1_2, 2), round(line2_2, 2)) == (429.56, 429.92)
    assert math.isclose(line1_2 + 175.0, flat, abs_tol=1e-9)         # u maps to flat X = line1 + u
    assert math.isclose(flat - 120.0, line1_2 + 55.0, abs_tol=1e-9)  # R10 notch bottom: 120 from the free edge


def test_tab_outer_plane_and_flat_tip():
    t, rin, nobi = 0.8, 1.0, 1.68
    assert math.isclose(305.8 - t - rin, 304.0)                     # tangent line of the neck
    assert math.isclose(rin + t, 1.8)
    assert math.isclose(305.8 + 19.0 - nobi, 323.12, abs_tol=1e-9)
    assert math.isclose(323.12 - 7.08, 316.04, abs_tol=1e-9)         # Phi7 centre from the tip
