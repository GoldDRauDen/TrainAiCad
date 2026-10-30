"""mirror_of partner (対称 / 本図の反対勝手), per-part customer and estimate: true (521030-10)."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_canonical as bc  # noqa: E402
import pair_consistency  # noqa: E402
from test_bend_end_collinear_tab import spec as hat_spec  # noqa: E402


def with_holes(sp):
    sp = copy.deepcopy(sp)
    sp["holes"] = [
        {"id": "H1", "d": 8, "group": "PhiB", "qty": 2, "face": "F1", "from": "start", "ev": "p4 2-φB",
         "wu": [[10, "HOLE_CENTER", "p4 10"]], "wv": [[60, "CONTOUR_EDGE", "p4 60"], [15, "HOLE_CENTER", "p4 15"]]},
        {"id": "H2", "d": 8, "group": "PhiB", "face": "F5", "from": "end", "ev": "p4 2-φB",
         "wu": [[10, "HOLE_CENTER", "p4 10"]],
         "wv": [[60, "CONTOUR_EDGE", "p4 60"], [15, "HOLE_CENTER", "p4 15"], [125, "HOLE_CENTER", "p4 125"]]}]
    return sp


def holes(part):
    return sorted((round(e["center"][0], 3), round(e["center"][1], 3)) for e in part["entities"] if e.get("role") == "hole")


def test_bent_partner_is_the_y_mirror_and_matches_the_hand_made_one():
    a = with_holes(hat_spec())
    b = {"code": "26-064688", "mirror_of": {"code": "26-064687", "axis": "y", "ev": "p4 B 本図の反対勝手"}}
    job = bc.build_job({"job_id": "521030-10", "parts": [a, b]})
    pa, pb = job["parts"]
    assert pb["code"] == "26-064688"
    assert holes(pa) == [(10.0, 75.0), (306.64, 200.0)] and holes(pb) == [(10.0, 200.0), (306.64, 75.0)]
    assert pair_consistency.check_pair(job, "26-064687", "26-064688", mirror="y")["differences"] == []
    assert len(pb["bend_end_junctions"]) == 8


def test_mirror_along_the_chain_is_refused():
    a = hat_spec()
    b = {"code": "26-064688", "mirror_of": {"code": "26-064687", "axis": "x"}}
    with pytest.raises(bc.BuildError, match="MIRROR_UNSUPPORTED"):
        bc.build_job({"job_id": "521030-10", "parts": [a, b]})


def test_flat_partner_flips_the_hole_chain_with_a_signed_witness():
    a = {"code": "26-000001", "material": "SPCC", "t": 1.6, "page": 1, "envelope": [300, 100],
         "outline": [[0, 0], [300, 0], [300, 100], [0, 100]],
         "holes": [{"id": "H1", "d": 6.6, "group": "G", "ev": "p1", "wx": [[20, "HOLE_CENTER", "p1 20"]],
                    "wy": [[30, "HOLE_CENTER", "p1 30"]]}]}
    b = {"code": "26-000002", "mirror_of": {"code": "26-000001", "axis": "x"}}
    job = bc.build_job({"job_id": "J", "parts": [a, b]})
    assert holes(job["parts"][0]) == [(20.0, 30.0)] and holes(job["parts"][1]) == [(280.0, 30.0)]


def test_customer_is_per_part_and_files_may_differ(tmp_path):
    import yaml
    mk = lambda code, cust: {"job_id": "J", "customer_code": cust, "parts": [{   # noqa: E731
        "code": code, "material": "SPCC", "t": 1.6, "envelope": [50, 20], "outline": [[0, 0], [50, 0], [50, 20], [0, 20]]}]}
    f1, f2 = tmp_path / "a.yaml", tmp_path / "b.yaml"
    f1.write_text(yaml.safe_dump(mk("26-000001", "639")), encoding="utf-8")
    f2.write_text(yaml.safe_dump(mk("26-000002", "824")), encoding="utf-8")
    job = bc.build_from_files([f1, f2])
    assert [p["customer_code"] for p in job["parts"]] == ["639", "824"] and "customer_code" not in job


def test_estimate_part_is_magenta_and_needs_a_flag():
    sp = {"code": "26-000003", "material": "SUS304", "t": 1.5, "envelope": [200, 96], "estimate": True,
          "outline": [[0, 0], [200, 0], [200, 96], [0, 96]]}
    with pytest.raises(bc.BuildError, match="estimate"):
        bc.build_part(copy.deepcopy(sp))
    part = bc.build_part({**sp, "flags": ["Kích thước ước lượng"]})
    assert part["status"] == "PREVIEW" and part["entities"][0]["color"] == 6
