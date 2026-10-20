"""Lead (voi dan): offset BOTH edges meeting at B toward the void by LeadVal; the lead ray is the bisector
of the void wedge, so it makes angle theta/2 with each edge (80 -> 40, 90 -> 45, 130 -> 65, 135 -> 67.5)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from slit_geometry import lead_end_by_offset, lead_val


def lead(theta_deg, value):
    t = math.radians(theta_deg)
    e1, e2 = (1.0, 0.0), (math.cos(t), math.sin(t))
    n1, n2 = (-e1[1], e1[0]), (e2[1], -e2[0])  # normals pointing into the void wedge
    return lead_end_by_offset((0, 0), n1, n2, value), e1, e2


@pytest.mark.parametrize("theta,half", [(80, 40), (90, 45), (100, 50), (130, 65), (135, 67.5)])
def test_lead_ray_is_the_bisector_of_the_void_wedge(theta, half):
    p, e1, e2 = lead(theta, 3.0)
    a1 = math.degrees(math.atan2(p[1], p[0]))
    assert a1 == pytest.approx(half) and theta - a1 == pytest.approx(half)
    assert math.hypot(*p) == pytest.approx(3.0 / math.sin(math.radians(theta) / 2))


def test_lead_point_is_exactly_lead_from_both_edges():
    for theta in (80, 90, 135):
        p, e1, e2 = lead(theta, 3.0)
        assert abs(p[1]) == pytest.approx(3.0)                                  # distance to edge 1 (x-axis)
        assert abs(p[0] * e2[1] - p[1] * e2[0]) == pytest.approx(3.0)           # distance to edge 2


def test_90_degree_lead_is_the_plain_diagonal():
    p, _, _ = lead(90, 3.0)
    assert p == pytest.approx((3.0, 3.0))
    assert lead_val("SPHCP", 3.2) == 3.0 and lead_val("SPHCP", 4.5) == 6.0
