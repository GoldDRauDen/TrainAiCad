"""Approved numeric cases (former regression/tools/check_*.py), run against the real tools.

Each case is a user-approved job value; the tool must reproduce it exactly.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import acute_bend  # noqa: E402
import lookup  # noqa: E402
import slit_geometry as sg  # noqa: E402

UNFOLD = [  # (job, OD list, Nobi list, flat length, [(line1, line2) per bend])
    ("056942", [150.0, 23.2], [4.4], 168.8, [(145.6, 150.0)]),
    ("056956", [106.0, 222.0, 106.0], [3.8, 3.8], 426.4, [(102.2, 106.0), (320.4, 324.2)]),
    ("057042", [39.8, 128.8, 21.3], [4.62, 4.62], 180.66, [(35.18, 39.8), (159.36, 163.98)]),
    ("057042-Y", [15.0, 35.0, 15.0], [4.62, 4.62], 55.76, [(10.38, 15.0), (40.76, 45.38)]),
    ("058155", [70.0, 110.0, 70.0], [7.6, 7.6], 234.8, [(62.4, 70.0), (164.8, 172.4)]),
    ("058653", [25.60, 22.92, 68.00], [1.32, 2.64], 112.56, None),
    ("058655", [60.51, 52.81, 32.30], [0.68, 3.80], 141.14, None),
    ("044812", [28.0, 21.0], [3.68], 45.32, None),
    ("018300", [797.26, 24.26], [0.37], 821.15, None),
    ("056911", [40.0, 906.0, 40.0], [2.64, 2.64], 980.72, None),
]


@pytest.mark.parametrize("job,od,nobi,flat,pairs", UNFOLD, ids=[c[0] for c in UNFOLD])
def test_unfold_matches_approved_jobs(job, od, nobi, flat, pairs):
    res = lookup.unfold(od, nobi)
    assert res["status"] == "OK"
    assert res["flat_length"] == pytest.approx(flat, abs=1e-9)
    if pairs:
        got = [(b["line1"], b["line2"]) for b in res["bend_lines"]]
        assert got == pytest.approx(pairs, abs=1e-9)


def test_same_total_does_not_mean_same_face_order():
    a = lookup.unfold([150.0, 23.2], [4.4])
    b = lookup.unfold([23.2, 150.0], [4.4])
    assert a["flat_length"] == b["flat_length"]
    assert a["bend_lines"] != b["bend_lines"]


@pytest.mark.parametrize("t,angle,offset", [(3.0, 165, 0.39), (3.0, 135, 1.24)])
def test_id_to_od_offset_is_rounded_first(t, angle, offset):
    assert lookup.idod(t, angle)["offset"] == offset


@pytest.mark.parametrize("thread,pilot", [("M4", 3.3), ("M5", 4.2), ("M6", 5.0), ("M8", 6.8)])
def test_pilot_holes(thread, pilot):
    assert lookup.pilot(thread)["pilot_dia"] == pilot


def test_bend_end_relief_90_matrix_t2():
    assert sg.slit_depth_from_actual_edge(-2.0, 2.0) == pytest.approx(2.2)
    assert sg.slit_depth_from_reference(-2.0, 2.0) == pytest.approx(4.2)
    assert sg.slit_depth_from_actual_edge(0.0, 2.0) == pytest.approx(2.2)
    assert sg.slit_depth_from_reference(0.0, 2.0) == pytest.approx(2.2)
    for s in (1.0, 1.5, 2.0):
        assert sg.slit_depth_from_actual_edge(s, 2.0) is None


@pytest.mark.parametrize("theta,depth", [(150, 1.6), (130, 2.45134221798073), (110, 3.007016386514907)])
def test_slit_depth_above_90_is_t_sin_theta(theta, depth):
    assert sg.slit_depth_gt90(3.2, theta) == pytest.approx(depth, abs=1e-12)


def test_slit_depth_above_90_rejects_90():
    with pytest.raises(ValueError):
        sg.slit_depth_gt90(3.2, 90)


def test_acute_bend_fixture_reproduces_approved_od():
    fixture = ROOT / "regression/fixtures/acute_bend_lt85/ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf"
    r = acute_bend.solve_fixture(fixture)
    assert r["t"] == pytest.approx(3.0)
    assert r["angle_deg"] == pytest.approx(75.0)
    assert r["OD1"] == pytest.approx(182.01421719900188, abs=0.01)
    assert r["OD2"] == pytest.approx(49.71223623506498, abs=0.01)
    para = acute_bend.od_from_inside(*r["inside"], r["t"], r["angle_deg"], 0.6)
    assert para["OD1"] == pytest.approx(r["OD1"], abs=1e-9)
    assert para["OD2"] == pytest.approx(r["OD2"], abs=1e-9)


def test_acute_bend_rejects_non_acute():
    with pytest.raises(ValueError):
        acute_bend.od_from_inside(100, 50, 3, 90, 0.6)
