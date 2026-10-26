"""Bend end whose web edge leaves the corner B slanted against the bend (521026-03 26-063194/26-063197).

U channel 30/120/30, SPHCP t3.2 (Nobi 5.5, lead 3): the web's bottom edge rises 48.4 over 103.7 from the flange end,
starting exactly on the flange-side bend line (S = 0). The lead end is the intersection of the flange side edge and the
slanted edge, each offset by LeadVal perpendicular to itself: 3 | 3 at the 115.02 degree corner.
"""
import copy
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from canonical_contract import CanonicalContractError  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from slit_geometry import connected_slit  # noqa: E402

RISE, RUN = 48.4, 103.7


def _spec(rise=RISE):
    return {"code": "26-063194", "material": "SPHCP", "t": 3.2, "page": 2, "envelope": [580, 169],
            "bend": {"axis": "Y", "width": 580, "width_ev": "p2 580",
                     "faces": [{"id": "FB", "od": 30, "ev": "30"}, {"id": "FW", "od": 120, "ev": "120"},
                               {"id": "FT", "od": 30, "ev": "30"}],
                     "bends": [{"id": "B1", "angle": 90, "sign": 1, "nobi": 5.5, "ev": "5.5"},
                               {"id": "B2", "angle": 90, "sign": 1, "nobi": 5.5, "ev": "5.5"}]},
            "outline": [[0, 0], [476.3, 0], [476.3, 24.5], [580, 24.5 + rise], [580, 169], [0, 169]]}


def _lead_distances(part):
    green = [e for e in part["entities"] if e.get("color") == 3 and e["type"] == "LINE"]
    tip = next(e["end"] for e in green if e["end"][1] < 24.5)           # lead end P inside the void
    ux, uy = RUN / math.hypot(RUN, RISE), RISE / math.hypot(RUN, RISE)
    to_side = tip[0] - 476.3                                              # side edge x = 476.3
    to_slant = abs((tip[0] - 476.3) * uy - (tip[1] - 24.5) * ux)         # slanted edge through B
    return tip, to_side, to_slant


def test_slanted_web_edge_is_accepted_and_the_lead_is_offset_3_from_both_edges():
    part = bc.build_part(_spec())
    (site,) = part["bend_end_junctions"]
    assert site["decision"] == "SLIT" and site["S_mm"] == pytest.approx(0.0) and site["corner_B"] == [476.3, 24.5]
    tip, to_side, to_slant = _lead_distances(part)
    assert to_side == pytest.approx(3.0, abs=1e-6) and to_slant == pytest.approx(3.0, abs=1e-6)   # not 3.99
    assert tip == pytest.approx([479.3, 22.589522], abs=1e-5)
    n_side, n_web = (1.0, 0.0), (RISE / math.hypot(RUN, RISE), -RUN / math.hypot(RUN, RISE))
    angle = 180 - math.degrees(math.acos(n_side[0] * n_web[0] + n_side[1] * n_web[1]))
    assert angle == pytest.approx(115.02, abs=0.01)
    slit_line = next(e for e in part["entities"] if e["entity_id"].endswith("_J1_L1"))
    assert slit_line["start"] == [476.3, 27.9]                              # T + 0.2 - S = 3.4 from B


def test_parallel_web_edge_keeps_the_old_lead():
    part = bc.build_part(_spec(rise=0.0))
    tip, to_side, _ = _lead_distances(part)
    assert tip == pytest.approx([479.3, 21.5], abs=1e-6) and to_side == pytest.approx(3.0)


def test_guard_remeasures_the_slanted_site_and_exports(tmp_path):
    job = {"canonical_contract": bc.CONTRACT, "job_id": "521026-03", "parts": [bc.build_part(_spec())]}
    assert export_canonical_job(job, tmp_path)["status"] == "PASS"


def test_guard_rejects_a_lead_offset_measured_as_if_the_edge_were_horizontal(tmp_path):
    part = bc.build_part(_spec())
    wrong = connected_slit((476.3, 24.5), (0.0, 1.0), (3.0, -3.0), 3.4)    # the 3.99 lead of the base variant
    by_id = {e["entity_id"]: e for e in part["entities"]}
    by_id["26-063194_J1_L1"].update(start=list(wrong["line1"][0]), end=list(wrong["line1"][1]))
    by_id["26-063194_J1_A"].update(center=list(wrong["arc"]["center"]), start_angle=wrong["arc"]["start_angle"],
                                   end_angle=wrong["arc"]["end_angle"])
    by_id["26-063194_J1_L2"].update(start=list(wrong["line2"][0]), end=list(wrong["line2"][1]))
    job = {"canonical_contract": bc.CONTRACT, "job_id": "521026-03", "parts": [part]}
    with pytest.raises(CanonicalContractError, match="BEND_END_SLIT_CONSTRUCTION_UNPROVED"):
        export_canonical_job(job, tmp_path)


def test_guard_rejects_a_slanted_edge_that_does_not_start_on_the_side_edge(tmp_path):
    job = {"canonical_contract": bc.CONTRACT, "job_id": "521026-03", "parts": [bc.build_part(_spec())]}
    part = copy.deepcopy(job["parts"][0])
    edges = part["bend_end_source_edges"]
    (site,) = part["bend_end_junctions"]
    edges[site["side_edge_id"]]["start"][0] += 5                             # side edge no longer meets the web edge
    edges[site["side_edge_id"]]["end"][0] += 5
    with pytest.raises(CanonicalContractError, match="BEND_END_MEASUREMENT_AXIS_INVALID"):
        export_canonical_job({**job, "parts": [part]}, tmp_path)
