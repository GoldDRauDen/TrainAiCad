"""Non-90 bend with narrow tabs (521026-13, 26-063295 / 26-062885 type): OD from the outer-face intersection,
the step S gates the relief at every angle (S>0: none; S<=0: t·sin θ past the flange-side bend line)."""
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc
import lookup
from export_canonical_dxf import export_canonical_job

LEG = lookup.leg(35, 65, 6, 120, nobi=4.92)          # 31.536 / 71.928 -> flat 98.544, lines 67.008 / 71.928


def tab_part(web_y):
    """A (820 wide, free edge at y=0) with a 38 mm tab at each end bent 120° out of its top edge at web_y."""
    top = LEG["flat_length"]
    return {
        "code": "26-000099", "material": "SS400", "t": 6, "page": 2, "envelope": [820, top],
        "bend": {"axis": "Y", "width": 38, "width_ev": "tab 38",
                 "faces": [{"id": "F1", "od": LEG["od2"], "ev": "A 65 + t/cos30"},
                           {"id": "F2", "od": LEG["od1"], "ev": "tab 35 - t tan30"}],
                 "bends": [{"id": "B1", "angle": 120, "sign": 1, "nobi": 4.92, "L": 38, "ev": "handwritten 120° N4.92"}]},
        "outline": [[0, 0, {"C": 20, "group": "C20", "qty": 2, "ev": "2-C20"}], [820, 0, {"C": 20, "group": "C20", "ev": "2-C20"}],
                    [820, top], [782, top], [782, web_y], [38, web_y], [38, top], [0, top]],
    }


def build(web_y):
    return bc.build_part(tab_part(web_y))


def test_od_and_flat_of_the_hd_sample():
    part = build(65)
    assert part["envelope_mm"] == [820.0, 98.544]
    lines = sorted(e["start"][1] for e in part["entities"] if e["role"] == "bend")
    assert lines == [67.01, 67.01, 71.93, 71.93]            # the builder rounds bend lines to 0.01 (HD 67.01 / 71.93)


def test_web_edge_before_the_zone_is_a_positive_step_without_relief():
    part = build(65)                                   # B at y65, flange-side line y71.928: S = +6.928
    assert part["bend_end_junctions"] == [] or all(s["decision"] == "NO_RELIEF" for s in part["bend_end_junctions"])
    assert not any(e["role"] == "slit" for e in part["entities"])


def test_flush_web_edge_gets_the_t_sin_theta_slit_and_exports(tmp_path):
    part = build(71.93)                                # web edge on the flange-side bend line (rounded 0.01): S = 0
    sites = [s for s in part["bend_end_junctions"] if s["decision"] == "SLIT"]
    assert sites, part["bend_end_junctions"]
    site = sites[0]
    assert site["mechanism"] == "NON_90_RELIEF" and site["included_angle_deg"] == 120
    slit = [e for e in part["entities"] if e["role"] == "slit"]
    assert sorted(e["type"] for e in slit) == ["ARC"] * 2 + ["LINE"] * 4          # one LINE+ARC+LINE slit per tab corner
    ys = [e["start"][1] for e in slit if e["type"] == "LINE" and abs(e["start"][0] - e["end"][0]) < 1e-9]
    assert min(ys) == pytest.approx(71.93 - 6 * math.sin(math.radians(120)), abs=1e-4)
    job = {"canonical_contract": bc.CONTRACT, "job_id": "TEST-NON90", "parts": [part]}
    manifest = export_canonical_job(job, tmp_path, require_slip_codes=False)
    assert ezdxf.readfile(tmp_path / manifest["filename"]).audit().has_errors is False
