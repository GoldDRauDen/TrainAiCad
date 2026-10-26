"""A slot on a bent face: its `axis` is the slot direction in the flat; it must not be read as the chain selector."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_canonical as bc  # noqa: E402


def _spec(**slot):
    return {"code": "26-000920", "material": "SPCC", "t": 2.3, "page": 1, "envelope": [142, 182.7],
            "bend": {"axis": "X", "width": 182.7, "width_ev": "length 182.7",
                     "faces": [{"id": "FL1", "od": 22, "ev": "22"}, {"id": "FW", "od": 105.6, "ev": "105.6"},
                               {"id": "FL2", "od": 22, "ev": "22"}],
                     "bends": [{"id": "B1", "angle": 90, "sign": 1, "nobi": 3.8, "ev": "h"},
                               {"id": "B2", "angle": 90, "sign": 1, "nobi": 3.8, "ev": "h"}]},
            "outline": "auto",
            "slots": [{"id": "S1", "w": 9, "cd": 100, "axis": [0, 1], "ev": "長穴 W9 C100", "face": "FW", "from": "start",
                       "wu": [[52.8, "SLOT_MIDPOINT", "52.8 from the left outer plane"]],
                       "wv": [[70, "SLOT_MIDPOINT", "70 from the free end"]], **slot}]}


def test_slot_on_a_face_keeps_its_direction_vector():
    part = bc.build_part(_spec())
    (slot,) = [e for e in part["entities"] if e["role"] == "slot"]
    assert part["slot_anchor_records"][0]["canonical_midpoint"] == pytest.approx([18.2 + 52.8, 70])   # web centre, 142/2
    assert part["slot_anchor_records"][0]["axis_unit"] == pytest.approx([0, 1])
    ys = [v[1] for v in slot["vertices"]]
    assert max(ys) - min(ys) == pytest.approx(100)                     # the straight part runs along flat Y
    assert part["status"] == "PASS"


def test_chain_key_still_selects_the_chain_of_a_two_axis_part():
    assert bc._chain_key({"axis": "X"}) == "X" and bc._chain_key({"chain": "Y", "axis": [1, 0]}) == "Y"
    assert bc._chain_key({"axis": [0, 1]}) is None
