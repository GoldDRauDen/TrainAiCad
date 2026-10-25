"""tools/geom.py: one bulge implementation for every tool."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import geom  # noqa: E402

Q = math.tan(math.radians(90) / 4)


def test_quarter_circle_bulge_gives_the_radius_and_centre():
    cx, cy, r, theta = geom.bulge_circle((97, 0), (100, 3), Q)
    assert (round(cx, 9), round(cy, 9), round(r, 9)) == (97, 3, 3) and math.isclose(theta, math.pi / 2)


def test_negative_bulge_puts_the_centre_on_the_right_and_arc_stays_ccw():
    (cx, cy), r, sa, ea = geom.arc_from_bulge((0, 0), (10, 0), -1)
    assert (round(cx, 9), round(cy, 9), r) == (5, 0, 5) and (round(sa), round(ea)) == (0, 180)


def test_points_lie_on_the_arc_between_the_ends():
    pts = geom.bulge_points((0, 0), (10, 0), 1, 8)
    assert len(pts) == 7 and all(math.isclose(math.hypot(x - 5, y), 5) and y <= 1e-9 for x, y in pts)


@pytest.mark.parametrize("p1,b", [((0, 0), 1), ((10, 0), 0), ((10, 0), float("nan"))])
def test_degenerate_segments_are_refused(p1, b):
    with pytest.raises(geom.GeometryError):
        geom.bulge_circle((0, 0), p1, b)
