"""521019-05 lessons: projection/notch census, OD-plane wall, C beside bend, stacked plates, bend-end relief."""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from slit_geometry import connected_slit, lead_val, slit_depth_from_actual_edge  # noqa: E402


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_notch_wall_at_own_od_plane():
    total = 450 + 275 - 2.6                      # 061138
    assert math.isclose(total, 722.4)
    assert math.isclose(total - 275, 447.4)      # last face wall = line1, not 450


def test_stacked_plate_bend_and_total():
    # 061137 on 061122: vertex of the lower contour offset by t=2, slanted edge (750,330)->(820,0)
    t = 2.0
    ux, uy = 330.0, 70.0
    n = math.hypot(ux, uy)
    nx, ny = ux / n * t, uy / n * t               # inward normal * t
    dx, dy = 70.0, -330.0
    # intersect offset slanted line with y = 330 + t
    px, py = 750 + nx, 330 + ny
    k = (330 + t - py) / (dy / math.hypot(dx, dy))
    vx = px + k * dx / math.hypot(dx, dy)
    assert math.isclose(vx, 751.62, abs_tol=0.01)
    end = (820 + nx, 0 + ny)
    flange = math.hypot(end[0] - vx, end[1] - (330 + t))
    assert math.isclose(flange, 338.97, abs_tol=0.02)
    assert math.isclose(vx + flange - 3.0, 1087.59, abs_tol=0.02)
    assert math.isclose(vx - 3.0, 748.62, abs_tol=0.01)


def test_connected_slit_reproduces_user_sample_061138():
    # SUS t1.5, B=(447.4,350), slit +x, lead (-6,6), depth T+0.2
    assert lead_val("SUS", 1.5) == 6.0
    depth = slit_depth_from_actual_edge(0, 1.5)
    assert math.isclose(depth, 1.7)
    r = connected_slit((447.4, 350.0), (1, 0), (-6, 6), depth, 0.5)
    (x0, y0), (x1, y1) = r["line1"]
    assert (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)) == (449.1, 350.0, 447.61, 350.0)
    (a0, b0), (a1, b1) = r["line2"]
    assert (round(a0, 2), round(b0, 2), round(a1, 2), round(b1, 2)) == (447.25, 350.15, 441.4, 356.0)
    assert (round(r["arc"]["center"][0], 2), round(r["arc"]["center"][1], 2)) == (447.61, 350.5)
    assert (r["arc"]["start_angle"], r["arc"]["end_angle"]) == (225.0, 270.0)


def test_positive_step_has_no_slit():
    assert slit_depth_from_actual_edge(50, 2) is None   # 061122 notch 50 from the bend end
