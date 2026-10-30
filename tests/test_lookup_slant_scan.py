"""lookup unfold face ranges + slant (521030-10) and scan_measure circle fit."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import lookup  # noqa: E402
import scan_measure  # noqa: E402


def test_unfold_faces_span_their_od_and_free_edges_sit_on_the_neighbour_line():
    res = lookup.unfold([26.6, 62, 150, 62, 26.6], [2.64] * 4)
    assert res["flat_length"] == 316.64
    faces = {f["face"]: f for f in res["faces"]}
    assert [round(f["end"] - f["start"], 2) for f in res["faces"]] == [26.6, 62, 150, 62, 26.6]
    assert faces[2]["start"] == res["bend_lines"][0]["line1"] == 23.96       # flange back edge = the tab's side line (S=0)
    assert faces[2]["end"] == res["bend_lines"][1]["line2"] == 85.96


def test_slant_matches_the_checked_sample():
    res = lookup.slant(70, 70, 5, 1.5)
    assert res["x_outer_tip"] == pytest.approx(7.62, abs=0.005) and res["outer_length"] == pytest.approx(93.76, abs=0.01)
    assert res["included_angle"] == pytest.approx(138.29, abs=0.01) and res["tip_offset_x"] == pytest.approx(1.12, abs=0.005)


def test_scan_measure_fits_a_ring_and_scales_it(tmp_path):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    h = w = 400
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - 210.0, yy - 190.0)
    img = np.where(np.abs(r - 60) < 2.0, 0, 255).astype(np.uint8)           # ring of radius 60 px
    path = tmp_path / "c.png"
    fitz.Pixmap(fitz.csGRAY, w, h, img.tobytes(), False).save(str(path))
    res = scan_measure.circle(path, (200, 200), 40, 80, scale_px=146.0, scale_mm=100.0)    # 1.46 px/mm
    assert res["center_px"] == pytest.approx([210, 190], abs=0.5) and res["radius_px"] == pytest.approx(60, abs=0.5)
    assert res["diameter_mm"] == pytest.approx(82.2, abs=0.6) and res["estimate_mm"] == 82
    assert scan_measure.px_per_mm(dpi=600)[0] == pytest.approx(23.622, abs=0.001)
