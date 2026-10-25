"""tools/bend_corner.py against the user's approved sample DXFs (coordinates copied from the samples).

HD (slit-relief-HD.dxf, SUS t2, lead 6): one web, a narrower bottom flange, two side tabs; S = 0 / -2 / +6.
061248 (061247,061248.dxf lower view, SS t3.2, lead 3): two-axis box corner pair, same fold, retreated flange.
"""
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402


def _hd(f1_od, code="26-000301"):
    w_od = 108.32 - f1_od + 3.68
    r10 = {"R": 10, "group": "R10", "ev": "HD R10"}
    r5 = {"R": 5, "group": "R5", "ev": "HD R5"}
    return {"code": code, "material": "SUS304", "t": 2, "page": 1, "envelope": [318.64, 108.32],
            "bend": {"chains": [
                {"axis": "Y", "width": 248, "faces": [{"id": "F1", "od": f1_od, "ev": "bottom flange OD"},
                                                  {"id": "W", "od": w_od, "ev": "web OD"}],
                 "bends": [{"id": "BB", "angle": 90, "sign": 1, "nobi": 3.68, "ev": "bottom bend"}]},
                {"axis": "X", "width": 50, "faces": [{"id": "TL", "od": 27, "ev": "left tab OD"},
                                                 {"id": "W", "od": 272, "ev": "web OD"},
                                                 {"id": "TR", "od": 27, "ev": "right tab OD"}],
                 "bends": [{"id": "BL", "angle": 90, "sign": 1, "nobi": 3.68, "ev": "left tab bend"},
                           {"id": "BR", "angle": 90, "sign": 1, "nobi": 3.68, "ev": "right tab bend"}]}]},
            "outline": [[35.32, 0, r10], [283.32, 0, r10], [283.32, 28.32], [318.64, 28.32, r10],
                        [318.64, 78.32, r10], [293.32, 78.32], [293.32, 108.32, r5], [25.32, 108.32, r5],
                        [25.32, 78.32], [0, 78.32, r10], [0, 28.32, r10], [35.32, 28.32]]}


def _green(part):
    return [e for e in part["entities"] if e.get("color") == 3]


def _close(a, b, tol=1e-3):
    return math.dist(a, b) <= tol


@pytest.mark.parametrize("f1_od,S,slit_end", [(32.0, 0.0, 30.52), (34.0, -2.0, 32.52), (26.0, 6.0, None)])
def test_hd_flat_step_matches_the_sample(tmp_path, f1_od, S, slit_end):
    part = bc.build_part(_hd(f1_od))
    sites = {tuple(s["corner_B"]): s for s in part["bend_end_junctions"]}
    if slit_end is None:
        assert not _green(part) and all(s["decision"] == "NO_RELIEF" for s in sites.values())
    else:
        left, right = sites[(35.32, 28.32)], sites[(283.32, 28.32)]
        assert left["S_mm"] == pytest.approx(S) and left["decision"] == "SLIT" and right["decision"] == "SLIT"
        green = _green(part)
        assert len(green) == 6
        lines = [(e["start"], e["end"]) for e in green if e["type"] == "LINE"]
        assert any(_close(a, [35.32, slit_end]) and _close(b, [35.32, 28.527]) for a, b in lines)
        assert any(_close(a, [35.174, 28.174]) and _close(b, [29.32, 22.32]) for a, b in lines)   # lead 6
        assert any(_close(a, [283.32, slit_end]) for a, _ in lines)
        arc = next(e for e in green if e["type"] == "ARC" and e["center"][0] < 100)
        assert _close(arc["center"], [34.82, 28.527]) and arc["radius"] == 0.5
    bottom = sorted((e["start"], e["end"]) for e in part["entities"] if e.get("role") == "bend"
                    and e["start"][1] == e["end"][1])
    assert [b[0][0] for b in bottom] == [35.32, 35.32] and [b[1][0] for b in bottom] == [283.32, 283.32]
    job = {"canonical_contract": bc.CONTRACT, "job_id": "HD", "parts": [part]}
    assert export_canonical_job(job, tmp_path)["status"] == "PASS"   # the guard re-measures every site


def _box_061248(code="26-061248"):
    c5 = {"C": 5, "group": "C5", "ev": "C5"}
    return {"code": code, "material": "SS400", "t": 3.2, "page": 2, "envelope": [127, 170.8],
            "bend": {"chains": [
                {"axis": "Y", "faces": [{"id": "FB", "od": 50, "ev": "bottom flange"}, {"id": "W", "od": 103, "ev": "web"},
                                        {"id": "FT", "od": 28.2, "ev": "top flange"}],
                 "bends": [{"id": "BB", "angle": 90, "sign": 1, "nobi": 5.2, "L": 54, "fold": "toward", "ev": "bottom"},
                           {"id": "BT", "angle": 90, "sign": 1, "nobi": 5.2, "L": 104, "fold": "toward", "ev": "top"}]},
                {"axis": "X", "faces": [{"id": "W", "od": 104, "ev": "web"}, {"id": "FR", "od": 28.2, "ev": "right"}],
                 "bends": [{"id": "BR", "angle": 90, "sign": 1, "nobi": 5.2, "L": 96.6, "fold": "toward",
                            "ev": "right"}]}]},
            "outline": [[50, 0, c5], [104, 0, c5], [104, 48], [127, 48], [127, 144.6], [104, 144.6], [104, 170.8],
                        [0, 170.8, c5], [0, 94.8, c5], [50, 94.8]]}


def test_061248_corner_pair_matches_the_sample(tmp_path):
    part = bc.build_part(_box_061248())
    bends = {(tuple(e["start"]), tuple(e["end"])) for e in part["entities"] if e.get("role") == "bend"}
    for seg in (((0, 142.6), (98.8, 142.6)), ((0, 147.8), (98.8, 147.8)), ((98.8, 50), (98.8, 142.6)),
                ((104, 50), (104, 142.6)), ((50, 44.8), (98.8, 44.8)), ((50, 50), (98.8, 50))):
        assert seg in bends or seg[::-1] in bends, seg
    slits = {tuple(s["corner_B"]): s for s in part["bend_end_junctions"] if s["decision"] == "SLIT"}
    assert set(slits) == {(104.0, 144.6), (104.0, 48.0)}
    assert all(s["steps_mm"] == {"BR": 0.0, "BT" if s["corner_B"][1] > 100 else "BB": 3.2} for s in slits.values())
    lines = [(e["start"], e["end"]) for e in _green(part) if e["type"] == "LINE"]
    for a, b in (([100.6, 144.6], [103.793, 144.6]), ([104.146, 144.746], [107, 147.6]),
                 ([100.6, 48], [103.793, 48]), ([104.146, 47.854], [107, 45])):
        assert any((_close(p, a) and _close(q, b)) or (_close(p, b) and _close(q, a)) for p, q in lines), (a, b)
    job = {"canonical_contract": bc.CONTRACT, "job_id": "521019-05", "parts": [part]}
    assert export_canonical_job(job, tmp_path)["status"] == "PASS"


def test_perpendicular_corner_needs_fold_directions():
    spec = _box_061248()
    del spec["bend"]["chains"][1]["bends"][0]["fold"]
    with pytest.raises(bc.BuildError, match="fold: toward"):
        bc.build_part(spec)


def _box_061247(code="26-061247"):
    c5 = {"C": 5, "group": "C5", "ev": "C5"}
    return {"code": code, "material": "SS400", "t": 3.2, "page": 1, "envelope": [289.5, 186.3],
            "bend": {"chains": [
                {"axis": "Y", "faces": [{"id": "F1", "od": 43.2, "ev": "F1"}, {"id": "F2", "od": 46.4, "ev": "F2"},
                                        {"id": "W", "od": 83.2, "ev": "web"}, {"id": "F4", "od": 30, "ev": "top"}],
                 "bends": [{"id": "B1", "angle": 90, "sign": 1, "L": 202, "fold": "toward", "ev": "B1"},
                           {"id": "B2", "angle": 90, "sign": 1, "L": 265, "fold": "away", "ev": "B2"},
                           {"id": "B3", "angle": 90, "sign": 1, "L": 259.5, "fold": "toward", "ev": "B3"}]},
                {"axis": "X", "faces": [{"id": "W", "od": 265, "ev": "web"}, {"id": "F5", "od": 30, "ev": "right"}],
                 "bends": [{"id": "B4", "angle": 90, "sign": 1, "L": 72.2, "fold": "toward", "ev": "B4"}]}]},
            "outline": [[0, 0, c5], [202, 0, c5], [202, 52.7], [265, 52.7, c5], [265, 78.6], [289.5, 78.6, c5],
                        [289.5, 158.6], [265, 158.6], [265, 186.3], [0, 186.3, c5]]}


def test_061247_opposite_fold_r_t_relief_and_slit_match_the_sample(tmp_path):
    part = bc.build_part(_box_061247())   # SS t3.2: table Nobi 5.5
    outer = part["entities"][0]["vertices"]
    from geom import bulge_circle
    arcs = [bulge_circle(a[:2], outer[(i + 1) % len(outer)][:2], a[2]) for i, a in enumerate(outer) if a[2]]
    for c, r in (((265, 78.6), 3.2), ((268.666, 79.1), 0.5), ((264.5, 74.934), 0.5)):
        assert any(_close(a[:2], c) and abs(a[2] - r) < 1e-6 for a in arcs), (c, r)
    bends = {(tuple(e["start"]), tuple(e["end"])) for e in part["entities"] if e.get("role") == "bend"}
    for seg in (((0, 78.6), (265, 78.6)), ((0, 84.1), (259.5, 84.1)), ((259.5, 84.1), (259.5, 156.3)),
                ((265, 78.6), (265, 156.3)), ((0, 156.3), (259.5, 156.3)), ((0, 161.8), (259.5, 161.8)),
                ((0, 37.7), (202, 37.7)), ((0, 43.2), (202, 43.2))):
        assert seg in bends or seg[::-1] in bends, seg
    mech = sorted(s["mechanism"] + ":" + s["decision"] for s in part["bend_end_junctions"])
    assert mech == ["BEND_END_OFFSET_90:SLIT", "OPPOSITE_FOLD_R_T:SEPARATE_RULE"]
    lines = [(e["start"], e["end"]) for e in _green(part) if e["type"] == "LINE"]
    assert any(_close(p, [261.6, 158.6]) or _close(q, [261.6, 158.6]) for p, q in lines)
    assert any(_close(p, [268, 161.6]) or _close(q, [268, 161.6]) for p, q in lines)
    job = {"canonical_contract": bc.CONTRACT, "job_id": "521019-05", "parts": [part]}
    assert export_canonical_job(job, tmp_path)["status"] == "PASS"
