"""BOXMET canonical job -> normal exporter (all guards) -> saved DXF read-back vs the MM.dxf reference."""
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from boxmet_flat import BoxMetError
from boxmet_job import build_job, _main
from canonical_contract import CanonicalContractError
from export_canonical_dxf import export_canonical_job
from holistic_engineering_guard import canonical_job_anomalies

REF = json.loads((ROOT / "regression/fixtures/boxmet_MM_L200_W150_H30_T1.5_N2.54.json").read_text(encoding="utf-8"))
r4 = lambda p: (round(p[0], 4), round(p[1], 4))


def exported(tmp_path, job):
    export_canonical_job(job, tmp_path)
    files = list(tmp_path.glob("*_ALL.dxf"))  # `_ALL_REVIEW_ONLY.dxf` would mean a PREVIEW/FLAG part
    assert len(files) == 1
    return ezdxf.readfile(str(files[0]))


def test_mm_parameters_export_and_match_reference_geometry(tmp_path):
    p = REF["params"]
    job = build_job("26-000001", p["L"], p["W"], tuple(p["H"]), p["T"], p["material"], p["N"])
    assert canonical_job_anomalies(job) == []
    msp = exported(tmp_path, job).modelspace()
    key = lambda a, b: tuple(sorted((r4(a), r4(b))))
    got_lines = {(key(e.dxf.start, e.dxf.end), 3 if e.dxf.color == 3 else 256, e.dxf.linetype == "DASHED")
                 for e in msp if e.dxftype() == "LINE"}
    ref_lines = {(key(l["start"], l["end"]), 3 if l["color"] == 3 else 256, l["dashed"]) for l in REF["lines"]}
    # documented difference: the two long outside dashed lines are shortened by T at both ends
    assert {k for k, _, _ in ref_lines - got_lines} == {key((27.46, 27.46), (227.46, 27.46)),
                                                         key((27.46, 177.46), (227.46, 177.46))}
    assert {k for k, _, _ in got_lines - ref_lines} == {key((28.96, 27.46), (225.96, 27.46)),
                                                         key((28.96, 177.46), (225.96, 177.46))}
    got_arcs = {(r4(e.dxf.center), round(e.dxf.radius, 4), round(e.dxf.start_angle, 3) % 360,
                 round(e.dxf.end_angle, 3) % 360, 3 if e.dxf.color == 3 else 256)
                for e in msp if e.dxftype() == "ARC"}
    ref_arcs = {(r4(a["center"]), round(a["radius"], 4), round(a["start_angle"], 3) % 360,
                 round(a["end_angle"], 3) % 360, 3 if a["color"] == 3 else 256) for a in REF["arcs"]}
    assert got_arcs == ref_arcs


def test_unequal_heights_box_exports(tmp_path):
    job = build_job("26-000002", 300, 100, (60, 30, 30, 30), 2.3, "SPCC", 2.6)
    assert canonical_job_anomalies(job) == []
    exported(tmp_path, job)


def test_holes_get_witnesses_and_export(tmp_path):
    job = build_job("26-000003", 200, 150, (30, 30, 30, 30), 1.5, "SS", 2.54,
                    holes=[(100.0, 100.0, 6.0, "synthetic hole evidence")])
    assert canonical_job_anomalies(job) == []
    exported(tmp_path, job)


def test_corner_drawn_rounded_is_flagged_not_rounded():
    with pytest.raises(BoxMetError, match="BOXMET_CORNER_DRAWN_SHAPE_NOT_SHARP_FLAG"):
        build_job("26-000004", 200, 150, (30, 30, 30, 30), 1.5, "SS", 2.54, drawn_corners="ROUNDED")


def test_auto_r_without_corner_inventory_is_blocked():
    job = build_job("26-000005", 200, 150, (30, 30, 30, 30), 1.5, "SS", 2.54)
    job["parts"][0].pop("corner_inventory")
    assert any("CORNER_INVENTORY_MISSING" in e for e in canonical_job_anomalies(job))


def test_no_approved_r_row_keeps_sharp_corners_with_reason(tmp_path):
    job = build_job("26-000006", 200, 150, (40, 40, 40, 40), 10, "SS", 12)
    assert canonical_job_anomalies(job) == []
    assert all(r["decision"] == "SHARP" and r["no_auto_r_reason"] for r in job["parts"][0]["corner_inventory"])


def test_cli_writes_job(tmp_path):
    out = tmp_path / "j.json"
    assert _main(["--code", "26-000007", "--L", "200", "--W", "150", "--H", "30", "30", "30", "30",
                  "--T", "1.5", "--material", "SS", "--N", "2.54", "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["parts"][0]["code"] == "26-000007"
