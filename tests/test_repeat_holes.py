"""`repeat` on a hole: P75*7 as one entry with the same witness chains and group closure as eight written holes."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_canonical as bc  # noqa: E402


def _spec(**hole):
    base = {"id": "H", "d": 12, "group": "D12", "ev": "8-Ø12 P75*7", "wx": [[30, "HOLE_CENTER", "30 from the left end"]],
            "wy": [[40, "HOLE_CENTER", "40 from the bottom"]], "repeat": {"n": 8, "step": 75, "along": "wx"}}
    base.update(hole)
    return {"code": "26-000940", "material": "SPCC", "t": 2, "page": 1, "envelope": [600, 100],
            "outline": [[0, 0], [600, 0], [600, 100], [0, 100]], "holes": [base]}


def _centres(part):
    return sorted(e["center"][0] for e in part["entities"] if e["type"] == "CIRCLE")


def test_repeat_expands_to_the_pitch_chain():
    spec = _spec()
    part = bc.build_part(spec)
    assert _centres(part) == [30 + 75 * k for k in range(8)]               # 30 .. 555
    assert part["status"] == "PASS" and "repeat" in spec["holes"][0]       # the caller's spec is not rewritten
    group = next(g for g in part["source_groups"] if g["group_id"].endswith("D12"))
    assert group["source_quantity"] == 8 and len(group["members"]) == 8
    edges = [e for e in part["feature_witness_graph"]["edges"] if e["axis"] == "X"]
    assert sum(e["value_mm"] for e in edges if e["to_node"].startswith("26-000940_H_8_X")) == pytest.approx(555)


def test_repeat_closes_against_a_printed_quantity():
    with pytest.raises(bc.BuildError, match="GROUP_COUNT_CLOSURE"):
        bc.build_part(_spec(qty=7))


def test_repeat_needs_a_valid_pitch_definition():
    with pytest.raises(bc.BuildError, match="repeat needs"):
        bc.build_part(_spec(repeat={"n": 1, "step": 75, "along": "wx"}))
    with pytest.raises(bc.BuildError, match="repeat needs"):
        bc.build_part(_spec(repeat={"n": 8, "step": 75, "along": "x"}))
