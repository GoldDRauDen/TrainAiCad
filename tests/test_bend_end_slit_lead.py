"""BEND_END_OFFSET_90 slit decision + connected slit with lead (521016-17 lesson)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from slit_geometry import connected_slit, lead_val, slit_depth_from_actual_edge, slit_depth_from_reference


def test_signed_offset_matrix():
    assert slit_depth_from_actual_edge(5.1, 1.2) is None      # 060722 upper step: no slit
    assert slit_depth_from_actual_edge(1.6, 1.2) is None      # 060722 lower step: no slit
    assert slit_depth_from_actual_edge(0, 2.5) == 2.7
    assert slit_depth_from_actual_edge(-2, 2) == 2.2
    assert slit_depth_from_reference(-2, 2) == 4.2


def test_lead_val_by_material():
    assert lead_val("SS", 1.5) == 3.0
    assert lead_val("SS", 3.2) == 3.0
    assert lead_val("SPCC", 1.2) == 3.0
    assert lead_val("SPCC", 3.2) == 3.0
    assert lead_val("SPCC", 3.3) == 6.0
    assert lead_val("SS", 6.0) == 6.0
    assert lead_val("AL", 2.5) == 6.0
    assert lead_val("SUS", 1.5) == 6.0


def test_connected_slit_is_tangent_135_degrees():
    # 060730 near-edge left junction: B=(45,11.12), S=(0,+1), D=(-6,-6), T=2.5
    g = connected_slit((45, 11.12), (0, 1), (-6, -6), 2.7)
    assert math.isclose(g["theta_deg"], 135.0, abs_tol=1e-9)
    assert math.isclose(g["tangent_dist"], 0.5 / math.tan(math.radians(67.5)), abs_tol=1e-12)
    (e1, t1), (t2, e2) = g["line1"], g["line2"]
    assert math.dist(e1, (45, 13.82)) < 1e-9 and math.dist(e2, (39, 5.12)) < 1e-9
    c, r = g["arc"]["center"], g["arc"]["radius"]
    assert math.isclose(math.dist(c, t1), r, abs_tol=1e-9) and math.isclose(math.dist(c, t2), r, abs_tol=1e-9)
    # arc is tangent to both rays: radius vector perpendicular to each ray
    assert abs((t1[0]-c[0])*0 + (t1[1]-c[1])*1) < 1e-9
    assert abs((t2[0]-c[0])*(-1) + (t2[1]-c[1])*(-1)) < 1e-9
    sweep = (g["arc"]["end_angle"] - g["arc"]["start_angle"]) % 360
    assert math.isclose(sweep, 45.0, abs_tol=1e-9)
