"""Printed flat arithmetic must close against the views before a part may fall back to VIEWS_ONLY."""
import json

import pytest

from LuanAppTools.cad.closure import (
    Attempt, ClosureContext, ViewsOnlyRejected, admit_views_only, attempt_log, closed_equations,
    match_terms, parse_equations)

DIMS_056152 = [155, 50, 6, 22, 70, 3, 38, 25, 30, 10, 15, 65, 88, 33]
NOTE = {"id": "N7", "text": "Handwritten '161+41−9.78=192.22' and '73+71-9.78=134.22'"}


def test_parse_two_equations_unicode_minus():
    equations = parse_equations("N7", NOTE["text"])
    assert [(e.positive, e.negative, e.result) for e in equations] == [
        ((161.0, 41.0), (9.78,), 192.22), ((73.0, 71.0), (9.78,), 134.22)]
    assert all(e.note_id == "N7" for e in equations)


def test_en_dash_parses_like_a_minus():
    (equation,) = parse_equations("n", "80+60–9.78=130.22")
    assert (equation.positive, equation.negative, equation.result) == ((80.0, 60.0), (9.78,), 130.22)


def test_wrong_arithmetic_is_dropped():
    assert parse_equations("n", "161+41-9.78=192.23") == []
    assert parse_equations("n", "2-M8 and A+B+C") == []


def test_terms_close_by_pair_sum_and_thickness():
    assert match_terms([161, 41, 73, 71], DIMS_056152, 6) == ("161=155+6", "41=38+3", "73=70+3", "71=65+6")
    assert match_terms([161, 999], DIMS_056152, 6) is None
    assert match_terms([161], [155], 6) == ("161=155+t",)
    assert match_terms([149], [155], 6) == ("149=155-t",)
    assert match_terms([155], [155], 6) == ("155",)
    assert match_terms([161], [155], None) is None  # no thickness: no +-t matching
    assert match_terms([161], [155], "six") is None  # not a number: never crashes
    assert match_terms([161], [], 6) is None


def test_closed_equations_need_every_term():
    two = closed_equations([NOTE], [{"dimensions": DIMS_056152}], 6)
    assert [c.equation.result for c in two] == [192.22, 134.22]
    assert two[0].matches == ("161=155+6", "41=38+3")
    assert closed_equations([NOTE], [{"dimensions": [155, 6]}], 6) == []
    assert closed_equations([NOTE], [{"id": "v"}], 6) == []  # view without "dimensions"
    pooled = closed_equations([NOTE], [{"dimensions": DIMS_056152[:7]}, {"dimensions": DIMS_056152[7:]}], 6)
    assert len(pooled) == 2  # dimensions of all the code's views are pooled


def outer(width, height, bulge=0):
    return {"entity_id": "E", "type": "LWPOLYLINE", "role": "outer", "closed": True,
            "vertices": [[0, 0, 0], [width, 0, bulge], [width, height, 0], [0, height, 0]]}


def validate_entry(status, entities, result):
    return {"request": {"name": "validate", "arguments": {"part": {"status": status, "entities": entities}}},
            "result": result}


def test_attempt_log_names_the_gate_and_extents():
    history = [
        validate_entry("PASS", [outer(192.22, 134.22)],
                       {"error": "x", "gates": [{"gate": "tools/canonical_contract.py:331"}]}),
        validate_entry("PASS", [outer(1, 2)], {"error": "canonical: WITNESS_REQUIRED_FEATURE_MISSING:['M']"}),
        validate_entry("PASS", [outer(1, 2)], {"error": "oops"}),
        validate_entry("PASS", [outer(3, 4)], {"parts": []}),
        validate_entry("VIEWS_ONLY", [outer(5, 6)], {"error": "A_B_C"}),
        validate_entry("PASS", [{"type": "CIRCLE", "role": "hole"}], {"error": "A_B_C"}),
        validate_entry("PASS", [outer(7, 8, bulge=0.4)], {"error": "A_B_C"}),
        {"request": {"name": "crop", "arguments": {}}, "result": {}},
    ]
    assert attempt_log(history) == [
        Attempt(True, "tools/canonical_contract.py:331", (192.22, 134.22)),
        Attempt(True, "WITNESS_REQUIRED_FEATURE_MISSING", (1.0, 2.0)),
        Attempt(True, None, (1.0, 2.0)),  # unnamed failure does not unlock
        Attempt(False, None, (3.0, 4.0)),  # validate passed
        Attempt(True, "A_B_C", None),  # no outer polyline
        Attempt(True, "A_B_C", (7.0, 8.0)),  # extents from vertices only
    ]  # a VIEWS_ONLY validate and non-validate calls are skipped
    assert attempt_log(json.loads(json.dumps(history))) == attempt_log(history)


def test_admit_views_only():
    closed = closed_equations([NOTE], [{"dimensions": DIMS_056152}], 6)
    views_only = {"status": "VIEWS_ONLY", "thickness_mm": 6}
    with pytest.raises(ViewsOnlyRejected, match=r"VIEWS_ONLY_ADMISSION.*161=155\+6.*192\.22.*HOLISTIC_ENGINEERING_CHALLENGE"):
        admit_views_only(views_only, closed, [])
    admit_views_only(views_only, closed, [Attempt(True, "WITNESS_REQUIRED_FEATURE_MISSING", (192.22, 134.22))])
    admit_views_only(views_only, closed, [Attempt(True, "G", (50.0, 134.221))])  # either axis, within 0.011
    for attempt in (Attempt(True, "G", (100.0, 40.0)),  # extent does not reproduce a result
                    Attempt(True, "G", None),  # nothing to measure
                    Attempt(True, None, (192.22, 134.22)),  # unnamed failure
                    Attempt(False, None, (192.22, 134.22))):  # validate passed: the flat should be submitted instead
        with pytest.raises(ViewsOnlyRejected):
            admit_views_only(views_only, closed, [attempt])
    admit_views_only({"status": "PASS"}, closed, [])  # only VIEWS_ONLY is gated
    admit_views_only(views_only, [], [])  # nothing closed: accepted as before


def test_context_uses_the_parts_thickness_and_the_history():
    context = ClosureContext(notes=(NOTE,), views=({"dimensions": [155, 6, 38, 3, 70, 65]},))
    history = [validate_entry("PASS", [outer(192.22, 134.22)], {"error": "canonical: A_B_C"})]
    with pytest.raises(ViewsOnlyRejected):
        context.admit({"status": "VIEWS_ONLY", "thickness_mm": 6}, [])
    context.admit({"status": "VIEWS_ONLY", "thickness_mm": 6}, history)
    context.admit({"status": "VIEWS_ONLY"}, history)  # no thickness: pair sums alone still close these terms
    with pytest.raises(ViewsOnlyRejected):
        context.admit({"status": "VIEWS_ONLY"}, [])
    context.admit({"status": "VIEWS_ONLY", "thickness_mm": "six"}, history)  # junk thickness never crashes
