"""Same-direction box-corner retreat choice (depth first, longer bend edge on ties)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from corner_retreat import DEPTH_TOL, choose_retreat, retreat_violation


def test_061247_equal_depth_prefers_longer_bend_edge_either_ok():
    # top F4 265x30 vs right F5 83.2x30: both depth 30 -> either, prefer longer bend (F4 = A)
    r = choose_retreat(30, 30, 265, 83.2)
    assert r["retreat"] == "A" and r["either_ok"] and r["basis"] == "EQUAL_DEPTH_LONGER_BEND"
    assert choose_retreat(30, 30, 83.2, 265)["retreat"] == "B"


def test_khuyet_t_example_shallower_flange_retreats():
    # user's khyetT example: top 70 deep vs right 30 deep -> right (shallower) retreats
    r = choose_retreat(70, 30, 265, 83.2)
    assert r["retreat"] == "B" and not r["either_ok"] and r["khuyet_t_if_other"]


def test_061248_bottom_right_corner():
    # bottom flange depth 50 vs right flange 28.2 -> right retreats
    assert choose_retreat(50, 28.2, 54, 103)["retreat"] == "B"


def test_tolerance_is_0_1():
    assert DEPTH_TOL == 0.1
    assert choose_retreat(30.0, 30.09, 10, 20)["basis"] == "EQUAL_DEPTH_LONGER_BEND"
    assert choose_retreat(30.0, 30.1, 10, 20)["basis"] == "SHALLOWER_DEPTH"


@pytest.mark.parametrize("bad", [0, -1, float("nan"), True, "30"])
def test_invalid_depth_rejected(bad):
    with pytest.raises(ValueError):
        choose_retreat(bad, 30)


def test_violation_codes():
    w = {"flange_ids": ["A", "B"], "depth_mm": {"A": 70, "B": 30}, "retreated_flange_id": "A", "evidence_ref": "x"}
    assert retreat_violation(w) == "BEND_END_CORNER_RETREAT_KHUYET_T"
    w["retreated_flange_id"] = "B"
    assert retreat_violation(w) is None
    assert retreat_violation({}) == "BEND_END_CORNER_RETREAT_UNPROVED"
