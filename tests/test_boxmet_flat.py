"""tools/boxmet_flat.py against the MM.dxf reference, transpose symmetry, closed contour, unequal heights."""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from boxmet_flat import BoxMetError, box_flat, laser_r
from slit_geometry import connected_slit

REF = json.loads((ROOT / "regression/boxmet/MM_L200_W150_H30_T1.5_N2.54.json").read_text(encoding="utf-8"))
r5 = lambda p: (round(p[0], 5), round(p[1], 5))
key = lambda a, b: tuple(sorted((r5(a), r5(b))))


def cut_lines(g):
    return [(e["start"], e["end"]) for e in g["lines"] if not e["dashed"]]


def test_matches_MM_dxf_exactly_except_long_outside_dashes():
    p = REF["params"]
    g = box_flat(p["L"], p["W"], *p["H"], p["T"], p["material"], p["N"])
    ref = {(key(e["start"], e["end"]), 3 if e["color"] == 3 else 256, e["dashed"]) for e in REF["lines"]}
    mine = {(key(e["start"], e["end"]), 256, e["dashed"]) for e in g["lines"]}
    for s in g["slits"]:
        mine |= {(key(*s["line1"]), 3, False), (key(*s["line2"]), 3, False)}
    only_ref, only_mine = ref - mine, mine - ref
    # known, documented difference: the two long outside dashed lines are shortened by T at both ends
    assert {k for k, _, _ in only_ref} == {key((27.46, 27.46), (227.46, 27.46)), key((27.46, 177.46), (227.46, 177.46))}
    assert {k for k, _, _ in only_mine} == {key((28.96, 27.46), (225.96, 27.46)), key((28.96, 177.46), (225.96, 177.46))}
    ref_arcs = {(r5(a["center"]), a["radius"], round(a["start_angle"], 3) % 360, round(a["end_angle"], 3) % 360,
                 3 if a["color"] == 3 else 256) for a in REF["arcs"]}
    mine_arcs = {(r5(a["center"]), a["radius"], round(a["start_angle"], 3) % 360, round(a["end_angle"], 3) % 360, 256)
                 for a in g["arcs"]}
    mine_arcs |= {(r5(s["arc"]["center"]), s["arc"]["radius"], round(s["arc"]["start_angle"], 3) % 360,
                   round(s["arc"]["end_angle"], 3) % 360, 3) for s in g["slits"]}
    assert ref_arcs == mine_arcs


def loop_is_closed(g):
    """Every cut-contour endpoint (lines + outer arcs) is shared by exactly two entities."""
    deg = Counter()
    for a, b in cut_lines(g):
        deg[r5(a)] += 1
        deg[r5(b)] += 1
    for a in g["arcs"]:
        for ang in (a["start_angle"], a["end_angle"]):
            t = math.radians(ang)
            deg[r5((a["center"][0] + a["radius"] * math.cos(t), a["center"][1] + a["radius"] * math.sin(t)))] += 1
    return all(v == 2 for v in deg.values())


@pytest.mark.parametrize("args", [
    (200, 150, 30, 30, 30, 30, 1.5, "SS", 2.54),
    (150, 200, 30, 30, 30, 30, 1.5, "SS", 2.54),
    (120, 120, 25, 25, 25, 25, 1.6, "SPHC", 2.2),
    (300, 100, 60, 30, 30, 30, 2.3, "SPCC", 2.6),      # unequal heights
    (180, 140, 20, 45, 35, 50, 3.0, "SECC", 3.5),      # all different
    (200, 150, 30, 30, 30, 30, 2.0, "SUS304-2B", 3.0),
])
def test_cut_contour_is_one_closed_chain(args):
    g = box_flat(*args)
    assert loop_is_closed(g)
    assert g["bbox"][0] == pytest.approx(0) and g["bbox"][1] == pytest.approx(0)
    L, W, H1, H2, H3, H4, T, _, N = args
    assert g["bbox"][2] == pytest.approx(L + H2 + H4 - 2 * N)
    assert g["bbox"][3] == pytest.approx(W + H1 + H3 - 2 * N)


def reflect(p):
    return (p[1], p[0])


def merged(segments):
    """Merge touching collinear axis-parallel segments (entity splitting is not geometry)."""
    groups = {}
    for a, b in segments:
        a, b = r5(a), r5(b)
        if a[0] == b[0]:
            groups.setdefault(("v", a[0]), []).append(sorted((a[1], b[1])))
        else:
            assert a[1] == b[1]
            groups.setdefault(("h", a[1]), []).append(sorted((a[0], b[0])))
    out = set()
    for k, spans in groups.items():
        spans.sort()
        cur = spans[0][:]
        for lo, hi in spans[1:]:
            if lo <= cur[1] + 1e-6:
                cur[1] = max(cur[1], hi)
            else:
                out.add((k, round(cur[0], 5), round(cur[1], 5)))
                cur = [lo, hi]
        out.add((k, round(cur[0], 5), round(cur[1], 5)))
    return out


@pytest.mark.parametrize("H", [(30, 30, 30, 30), (20, 45, 35, 50), (60, 30, 30, 30)])
def test_transpose_symmetry(H):
    # reflecting across y=x: bottom<->left, right<->top ; L<->W.  Needs L != W (tie-break is directional).
    L, W, T, N = 200, 150, 1.5, 2.54
    a = box_flat(L, W, *H, T, "SS", N)
    h1, h2, h3, h4 = H
    b = box_flat(W, L, h4, h3, h2, h1, T, "SS", N)
    la = merged([(reflect(s), reflect(e)) for s, e in cut_lines(a)])
    lb = merged(cut_lines(b))
    assert la == lb
    assert {r5(reflect(x["center"])) for x in a["arcs"]} == {r5(x["center"]) for x in b["arcs"]}
    sa = {key(reflect(s["base"]), reflect(s["base"])) for s in a["slits"]}
    sb = {key(s["base"], s["base"]) for s in b["slits"]}
    assert sa == sb


def test_unequal_height_shallower_flap_retreats_at_each_corner():
    # L>=W would retreat Bottom/Top, but depth decides: bottom 60 deep -> Left/Right (30 deep) retreat at its corners
    g = box_flat(300, 100, 60, 30, 30, 30, 2.3, "SPCC", 2.6)
    assert g["retreat"] == {"BL": "V", "BR": "V", "TR": "H", "TL": "H"}
    # no khuyet_t: every retreating flap is no deeper than the flap it yields to
    depth = {"BL": (60, 30), "BR": (60, 30), "TR": (30, 30), "TL": (30, 30)}
    for c, side in g["retreat"].items():
        dh, dv = depth[c]
        assert (dh <= dv) if side == "H" else (dv <= dh)


def test_equal_heights_reproduce_boxmet_choice():
    assert set(box_flat(200, 150, 30, 30, 30, 30, 1.5, "SS", 2.54)["retreat"].values()) == {"H"}
    assert set(box_flat(150, 200, 30, 30, 30, 30, 1.5, "SS", 2.54)["retreat"].values()) == {"V"}
    assert set(box_flat(150, 150, 30, 30, 30, 30, 1.5, "SS", 2.54)["retreat"].values()) == {"H"}  # L>=W


def test_slit_depth_lead_and_construction():
    g = box_flat(200, 150, 30, 30, 30, 30, 1.5, "SS", 2.54)
    assert g["lead"] == 3.0 and g["slit_depth"] == pytest.approx(1.7)
    for s in g["slits"]:
        exp = connected_slit(s["base"], s["direction"], s["lead_delta"], 1.7)
        assert s["line1"] == exp["line1"] and s["line2"] == exp["line2"]
    assert box_flat(200, 150, 30, 30, 30, 30, 2.0, "SUS304-2B", 3.0)["lead"] == 6.0


def test_laser_r_follows_material_table():
    assert laser_r("SPHCP", 2.3) == 0.5 and laser_r("SS", 6) == 2.0 and laser_r("SUS304", 6) == 0.5
    assert laser_r("SS", 10) is None and laser_r("SS", 3.5) is None


def test_no_approved_r_leaves_corners_sharp_and_is_reported():
    g = box_flat(200, 150, 30, 30, 30, 30, 10, "SS", 12)
    assert g["R"] == 0.0 and g["R_sharp_flag"] is True and g["arcs"] == []


@pytest.mark.parametrize("bad", [
    dict(L=0), dict(L=float("nan")), dict(T=-1), dict(N=-1), dict(L=2.0), dict(H1=1.0), dict(H2=True)])
def test_invalid_inputs_rejected(bad):
    args = dict(L=200, W=150, H1=30, H2=30, H3=30, H4=30, T=1.5, material="SS", N=2.54)
    args.update(bad)
    with pytest.raises(BoxMetError):
        box_flat(**args)


def test_boxmet_flags_unproved_lead():
    import pytest as _pytest
    from boxmet_flat import BoxMetError as _Err, box_geometry as _bg
    with _pytest.raises(_Err, match="LEAD_VALUE_UNPROVED"):
        _bg(400, 300, 80, 80, 80, 80, 19, "SS400", 30)
