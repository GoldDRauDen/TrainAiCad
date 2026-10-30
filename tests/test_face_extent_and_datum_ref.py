"""A chamfer over the middle of a leg does not narrow the bend (521030-03 26-064602), and a round blank's features
chain from a hole centre (`datum_ref`, 521027-26 26-063851) - no job-local merge/patch script."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from canonical_contract import validate_canonical_job  # noqa: E402


def _leg_with_mid_chamfer():
    r5 = {"R": 5, "group": "R5", "ev": "p2 R5"}
    return {"code": "26-064602", "material": "SPHCP", "t": 4.5, "page": 2, "envelope": [453, 480],
            "bend": {"axis": "X", "width": 480, "width_ev": "p2 480",
                     "faces": [{"id": "F1", "od": 170, "ev": "p2 170"}, {"id": "F2", "od": 290, "ev": "p2 290"}],
                     "bends": [{"id": "B1", "angle": 90, "sign": 1, "nobi": 7, "ev": "p2 handwritten 453"}]},
            "outline": [[145, 0], [453, 0, r5], [453, 480, r5], [145, 480], [100, 435], [0, 435, r5], [0, 385, r5],
                        [75, 385, r5], [75, 95, r5], [0, 95, r5], [0, 45, r5], [100, 45]]}


def test_a_chamfer_in_the_middle_of_a_leg_keeps_the_bend_full_width():
    part = bc.build_part(_leg_with_mid_chamfer())
    bends = [e for e in part["entities"] if e["role"] == "bend"]
    assert bends and all(sorted((e["start"][1], e["end"][1])) == [0, 480] for e in bends)


def test_a_two_axis_flat_step_still_stops_the_bend_at_the_step():
    sys.path.insert(0, str(ROOT / "tests"))
    from test_bend_corner_samples import _hd
    part = bc.build_part(_hd(34.0))   # S = -2: the bottom bend stays between the tabs, no corner with the tab bends
    assert {tuple(s["corner_B"]) for s in part["bend_end_junctions"]} >= {(35.32, 28.32), (283.32, 28.32)}


def _ring(ref="ID66"):
    hole = lambda hid, x, d, **kw: {"id": hid, "d": d, "group": f"D{d}", "ev": f"p2 Ø{d}", "datum_x": 59.5,  # noqa: E731
                                    "datum_y": 59.5, "wx": [[x - 59.5, "HOLE_CENTER", "p2", "ORDINATE"]],
                                    "wy": [[0, "HOLE_CENTER", "p2", "ORDINATE"]], **kw}
    return {"job_id": "521027-26", "parts": [{
        "code": "26-063851", "material": "SPCC", "t": 0.5, "page": 2, "envelope": [119, 119],
        "outline": {"circle": {"center": [59.5, 59.5], "d": 119, "ev": "p2 Ø119"}},
        "holes": [hole("ID66", 59.5, 66), hole("H1", 9.5, 10, datum_ref=ref, qty=2), hole("H2", 109.5, 10, datum_ref=ref)]}]}


def test_datum_ref_chains_from_the_hole_centre():
    job = bc.build_job(_ring())
    targets = {t["feature_id"]: t["datum_entity_id"] for t in job["parts"][0]["feature_witness_graph"]["targets"]}
    assert targets["26-063851_H1"] == targets["26-063851_H2"] == "E_26-063851_ID66"
    validate_canonical_job(job)


def test_datum_ref_must_name_another_hole():
    with pytest.raises(bc.BuildError, match="datum_ref"):
        bc.build_job(_ring("NOPE"))
