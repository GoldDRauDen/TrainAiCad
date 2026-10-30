"""A tab edge flush with the web edge (same line across the flat) must not steal the bend-end corner of another bend.

521030-10 26-064687 (hat with 30 wide ear tabs at the web edges): four bends, flanges 275 wide, web 155, tab edges at Y=60/215
collinear with the web edges. All 8 bend ends have S=0 (flange edges at the formed outer plane = the narrow face's side line)
and every one carries a slit at its own corner B.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_canonical as bc  # noqa: E402

N = 2.64
L1 = {1: 26.6 - N, 2: 85.96 - N, 3: 233.32 - N, 4: 292.68 - N}    # 23.96, 83.32, 230.68, 290.04


def spec(mirror=False):
    c = lambda g, q: {"C": 2, "group": g, "qty": q, "ev": "p4 C2"}   # noqa: E731
    pts = [[0, 90, c("T", 4)], [0, 60, c("T", 4)], [23.96, 60], [23.96, 0, c("A", 4)], [85.96, 0, c("A", 4)], [85.96, 60],
           [230.68, 60], [230.68, 0, c("B", 4)], [292.68, 0, c("B", 4)], [292.68, 107.5, c("N", 2)], [267.68, 107.5],
           [267.68, 167.5], [292.68, 167.5, c("N", 2)], [292.68, 185], [316.64, 185, c("T", 4)], [316.64, 215, c("T", 4)],
           [292.68, 215], [292.68, 275, c("B", 4)], [230.68, 275, c("B", 4)], [230.68, 215], [85.96, 215],
           [85.96, 275, c("A", 4)], [23.96, 275, c("A", 4)], [23.96, 90]]
    if mirror:
        pts = [[p[0], 275 - p[1], *p[2:]] for p in pts][::-1]
    faces = [("F1", 26.6), ("F2", 62), ("F3", 150), ("F4", 62), ("F5", 26.6)]
    return {"code": "26-064687", "material": "SPHCP", "t": 1.6, "page": 4, "envelope": [316.64, 275],
            "bend": {"axis": "X", "width": 155, "width_ev": "p4 web 155",
                     "faces": [{"id": f, "od": od, "ev": "p4"} for f, od in faces],
                     "bends": [{"id": f"B{i}", "angle": 90, "sign": 1 if i in (1, 4) else -1, "nobi": N,
                                "L": 30 if i in (1, 4) else 155, "ev": "p4 hand 2.64x4"} for i in (1, 2, 3, 4)]},
            "outline": pts}


@pytest.mark.parametrize("mirror", [False, True])
def test_every_bend_end_has_its_own_slit_corner(mirror):
    part = bc.build_part(spec(mirror))
    sites = part["bend_end_junctions"]
    assert len(sites) == 8 and all(s["decision"] == "SLIT" and abs(s["S_mm"]) < 1e-6 for s in sites)
    ys = (60.0, 215.0) if not mirror else (60.0, 215.0)
    want = {(23.96, 60.0), (23.96, 90.0), (85.96, 60.0), (85.96, 215.0), (230.68, 60.0), (230.68, 215.0),
            (292.68, 185.0), (292.68, 215.0)}
    if mirror:
        want = {(x, 275 - y) for x, y in want}
    assert {tuple(s["corner_B"]) for s in sites} == want
    assert len([e for e in part["entities"] if e.get("color") == 3]) == 8 * 3 and ys
