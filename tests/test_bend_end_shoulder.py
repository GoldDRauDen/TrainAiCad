"""A wider flange ear behind a narrower neck: the shoulder past the bend zone is a recorded step (S > 0, no slit).

521028-17 26-063995: web 44 (59 flat at the neck), ear 30 from the free end; OD2 40.4 and Nobi 9.35 put line1 at 206.95,
so S = shoulder - line1 = 217.35 - 206.95 = +10.4 (the shoulder stands back from the neck).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402


def _ear(root_x):
    c10 = {"C": 10, "group": "C10", "ev": "p2 3-C10"}
    return {"code": "26-063995", "material": "SPHCP", "t": 6, "page": 2, "envelope": [247.35, 74],
            "bend": {"axis": "X", "width": 59, "width_ev": "p2 plan flange 59",
                     "faces": [{"id": "F1", "od": 216.3, "ev": "p2 216.3"}, {"id": "F2", "od": 40.4, "ev": "p2 40.4"}],
                     "bends": [{"id": "B1", "angle": 88, "sign": 1, "nobi": 9.35, "L": 29, "ev": "p2 88 deg, hand Nobi 9.35"}]},
            "outline": [[0, 30], [root_x, 30], [root_x, 0, c10], [247.35, 0, c10], [247.35, 59, c10], [178.9, 59],
                        [163.9, 74], [0, 74]]}


@pytest.mark.parametrize("root_x,S", [(217.35, 10.4), (216.3, 9.35)])
def test_shoulder_past_the_zone_is_a_step_without_slit(tmp_path, root_x, S):
    part = bc.build_part(_ear(root_x))
    sites = [s for s in part["bend_end_junctions"] if s["corner_B"] == [root_x, 30.0]]
    assert len(sites) == 1 and sites[0]["decision"] == "NO_RELIEF" and sites[0]["S_mm"] == pytest.approx(S)
    assert not [e for e in part["entities"] if e.get("color") == 3]
    job = {"canonical_contract": bc.CONTRACT, "job_id": "521028-17", "parts": [part]}
    assert export_canonical_job(job, tmp_path)["status"] in ("PASS", "PREVIEW")
