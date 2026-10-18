"""Replay the VIEWS_ONLY decision recorded in run 48cf0b85 through the admission gate (no AI call)."""
import json
from pathlib import Path

import pytest

from LuanAppTools.cad.closure import ClosureContext, ViewsOnlyRejected, closed_equations

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "weld_pair.json").read_text(encoding="utf-8"))
PAIR, CONTROL = FIXTURE["weld_pair"], FIXTURE["control"]


def context(case):
    return ClosureContext(notes=(case["note"],), views=tuple(case["views"]))


def flat_attempt_entry(width, height, error):
    outer = {"type": "LWPOLYLINE", "role": "outer", "vertices": [[0, 0, 0], [width, 0, 0], [width, height, 0], [0, height, 0]]}
    return {"request": {"name": "validate", "arguments": {"part": {"status": "PREVIEW", "entities": [outer]}}},
            "result": {"error": error}}


@pytest.mark.parametrize("candidate", ["candidate", "other_hand_candidate"])
def test_recorded_candidates_of_both_codes_are_rejected(candidate):
    # The drawing is shared by 056152 and 056153: the same arithmetic, views and VIEWS_ONLY decision.
    assert PAIR["note"]["codes"] == ["26-056152", "26-056153"]
    with pytest.raises(ViewsOnlyRejected) as rejected:
        context(PAIR).admit(PAIR[candidate], [])
    message = str(rejected.value)
    assert "192.22" in message and "134.22" in message
    assert "161=155+6" in message and "73=70+3" in message


def test_056159_control_closes_but_is_not_gated_when_not_views_only():
    (closed,) = closed_equations([CONTROL["note"]], CONTROL["views"], CONTROL["thickness_mm"])
    assert closed.equation.result == 130.22 and closed.matches == ("80", "60")
    context(CONTROL).admit({"status": "PASS", "thickness_mm": 6}, [])


def test_recorded_candidate_passes_after_a_matching_failed_attempt():
    history = [flat_attempt_entry(192.22, 134.22, "canonical: BEND_OD_NOBI_CLOSURE_FAIL:B1")]
    context(PAIR).admit(PAIR["candidate"], history)
    unrelated = [flat_attempt_entry(155, 70, "canonical: BEND_OD_NOBI_CLOSURE_FAIL:B1")]  # the slip size: not the printed result
    with pytest.raises(ViewsOnlyRejected):
        context(PAIR).admit(PAIR["candidate"], unrelated)
