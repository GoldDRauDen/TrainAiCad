"""Open SPLINE / ELLIPSE contour segments of customer DATA stay that entity from digest to the saved DXF (rules/DATA_DXF.md)."""
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import curves  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from geometry_containment import _loop  # noqa: E402


def _digest(tmp_path, draw):
    doc = ezdxf.new("R2010")
    draw(doc.modelspace())
    path = tmp_path / "data.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def _spline_plate(m):
    m.add_line((0, 0), (30, 0))
    m.add_spline(fit_points=[(30, 0, 0), (40, 1.5, 0), (50, 3, 0)], degree=3)
    for a, b in (((50, 3), (100, 3)), ((100, 3), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))):
        m.add_line(a, b)
    m.add_circle((20, 25), 4)


def _ellipse_plate(m):
    m.add_ellipse((50, 0), major_axis=(50, 0), ratio=0.2, start_param=math.pi, end_param=2 * math.pi)   # (0,0) -> (100,0) via y=-10
    for a, b in (((100, 0), (100, 40)), ((100, 40), (0, 40)), ((0, 40), (0, 0))):
        m.add_line(a, b)


def _plan(d):
    return {"members": [{"id": "OUT", "role": "outer",
                         "pieces": [p["id"] for p in d["pieces"] if p["type"] == "LINE"] + [u["id"] for u in d["unsupported"] if u.get("curve")]},
                        *([{"id": "H", "role": "hole", "pieces": [p["id"] for p in d["pieces"] if p["type"] == "CIRCLE"]}]
                          if any(p["type"] == "CIRCLE" for p in d["pieces"]) else [])],
            "excluded": []}


def _build(tmp_path, d, envelope, members=None):
    res = dxf_assemble.assemble(d, _plan(d))
    (tmp_path / "asm.json").write_text(json.dumps(res), encoding="utf-8")
    part = {"code": "26-062010", "material": "SS400", "t": 3.2, "page": 1, "data": "asm.json", "envelope": envelope}
    if members:
        part["members"] = members
    (tmp_path / "spec.yaml").write_text(yaml.safe_dump({"job_id": "520930-03", "parts": [part]}, allow_unicode=True), encoding="utf-8")
    return res, bc.build_from_files([tmp_path / "spec.yaml"])


def test_digest_decodes_open_curves_and_leaves_a_whole_ellipse_unsupported(tmp_path):
    d = _digest(tmp_path, _spline_plate)
    (u,) = d["unsupported"]
    assert u["curve"]["kind"] == "SPLINE" and u["curve"]["fit_points"] == [[30.0, 0.0], [40.0, 1.5], [50.0, 3.0]]
    assert u["curve"]["start"] == [30.0, 0.0] and u["curve"]["end"] == [50.0, 3.0]
    whole = _digest(tmp_path, lambda m: m.add_ellipse((0, 0), major_axis=(5, 0), ratio=0.5))
    assert "curve" not in whole["unsupported"][0]


def test_spline_contour_segment_is_kept_exactly_to_the_saved_dxf(tmp_path):
    d = _digest(tmp_path, _spline_plate)
    res, job = _build(tmp_path, d, [100, 50], {"H": {"group": "D8", "qty": 1, "ev": "p1 Ø8", "pdf_d": 8}})
    assert res["invariance"]["ok"] and len(res["entities"][0]["curves"]) == 1
    outer = job["parts"][0]["entities"][0]
    assert [c["kind"] for c in outer["curves"]] == ["SPLINE"]
    manifest = export_canonical_job(job, tmp_path / "OUT", require_slip_codes=True)
    saved = ezdxf.readfile(tmp_path / "OUT" / manifest["filename"])
    (sp,) = [e for e in saved.modelspace() if e.dxftype() == "SPLINE"]
    assert [(round(p[0], 6), round(p[1], 6)) for p in sp.fit_points] == [(30.0, 0.0), (40.0, 1.5), (50.0, 3.0)]
    assert sp.dxf.degree == 3 and not any(e.dxftype() == "LWPOLYLINE" for e in saved.modelspace())


def test_ellipse_contour_segment_is_kept_exactly_to_the_saved_dxf(tmp_path):
    d = _digest(tmp_path, _ellipse_plate)
    res, job = _build(tmp_path, d, [100, 50])
    assert res["invariance"]["ok"]
    manifest = export_canonical_job(job, tmp_path / "OUT", require_slip_codes=True)
    saved = ezdxf.readfile(tmp_path / "OUT" / manifest["filename"])
    (el,) = [e for e in saved.modelspace() if e.dxftype() == "ELLIPSE"]
    assert el.dxf.ratio == pytest.approx(0.2) and el.dxf.major_axis.x == pytest.approx(50.0)
    assert el.dxf.start_param == pytest.approx(math.pi) and el.dxf.end_param == pytest.approx(2 * math.pi)


def test_a_mirrored_ellipse_is_refused_not_approximated(tmp_path):
    d = _digest(tmp_path, _ellipse_plate)
    plan = _plan(d)
    plan["transform"] = {"mirror_x": True, "evidence": "test"}
    with pytest.raises(dxf_assemble.AssembleError, match="ELLIPSE_MIRROR_NOT_SUPPORTED"):
        dxf_assemble.assemble(d, plan)


def test_a_curve_cannot_sit_in_a_cutout_or_slot(tmp_path):
    d = _digest(tmp_path, _ellipse_plate)
    plan = _plan(d)
    plan["members"][0]["role"] = "cutout"
    with pytest.raises(dxf_assemble.AssembleError, match="CURVE_IN_CUTOUT"):
        dxf_assemble.assemble(d, plan)


def test_containment_follows_the_curve_not_its_chord():
    # the chord of a deep elliptical sag lies far above the real edge: a hole between them is OUTSIDE the chord polygon
    c = {"kind": "ELLIPSE", "center": [50.0, 0.0], "major_axis": [50.0, 0.0], "ratio": 0.2, "start_param": math.pi,
         "end_param": 2 * math.pi, "start": [0.0, 0.0], "end": [100.0, 0.0]}
    verts = [[0, 0, 0], [100, 0, 0], [100, 40, 0], [0, 40, 0]]
    chord = _loop(verts)
    real = _loop(verts, curves=[{**c, "seg": 0}])
    assert len(real) > len(chord) + 10 and min(p[1] for p in real) < -9.9
    assert min(p[1] for p in chord) == 0


def test_curve_points_survive_the_j_lj_turn_exactly():
    c = {"kind": "SPLINE", "degree": 3, "fit_points": [[30.0, 0.0], [40.0, 1.5], [50.0, 3.0]], "control_points": [], "knots": [],
         "weights": [], "start_tangent": [1.0, 0.0], "end_tangent": [1.0, 0.5], "start": [30.0, 0.0], "end": [50.0, 3.0]}
    t = curves.transform(c, lambda q: [1100 - q[0], 90 - q[1]])
    assert t["fit_points"] == [[1070.0, 90.0], [1060.0, 88.5], [1050.0, 87.0]]
    assert t["start_tangent"] == [-1.0, -0.0] or t["start_tangent"] == [-1.0, 0.0]
