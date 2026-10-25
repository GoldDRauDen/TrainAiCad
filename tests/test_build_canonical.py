"""tools/build_canonical.py, run_job.py, overlay_check.py: compact FLAT spec -> verified canonical DXF."""
import copy
import json
import math
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import overlay_check  # noqa: E402
import run_job  # noqa: E402
from canonical_contract import validate_canonical_job  # noqa: E402
from corner_guard import corner_errors  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from holistic_engineering_guard import canonical_job_anomalies  # noqa: E402

EXAMPLE = ROOT / "examples/flat_minimal.yaml"


def spec():
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def one(part):
    return {"job_id": "T", "parts": [part]}


def strip(**kw):
    part = {"code": "26-000009", "material": "A2017", "t": 5, "page": 1, "envelope": [1720, 70],
            "outline": [[0, 0], [1720, 0], [1720, 70],
                        {"vnotch": {"start": 1680, "pitch": -200, "count": 8, "level": 70, "depth": 25,
                                    "inward": -1, "qty": 8, "ev": "8-90 8-25"}},
                        [100, 70], [0, 65]]}
    part.update(kw)
    return part


def test_example_job_json_is_in_sync_with_spec():
    built = bc.build_job(spec())
    stored = json.loads((ROOT / "examples/flat_minimal.job.json").read_text(encoding="utf-8"))
    assert built == stored, "regenerate: python tools/build_canonical.py examples/flat_minimal.yaml -o examples/flat_minimal.job.json"


def test_example_passes_contract_guards_and_saved_dxf(tmp_path):
    job = bc.build_job(spec())
    validate_canonical_job(job)
    assert canonical_job_anomalies(job) == []
    manifest = export_canonical_job(job, tmp_path, require_slip_codes=True)
    assert manifest["filename"] == "EXAMPLE-FLAT_ALL.dxf"
    verify = run_job.verify_saved(tmp_path / manifest["filename"], job, manifest)
    assert not verify["audit_errors"] and all(r["closed"] for r in verify["parts"].values())


def test_auto_laser_r_only_on_convex_corners_up_to_90_degrees():
    part = bc.build_job(one(strip()))["parts"][0]
    inv = part["corner_inventory"]
    assert [r["decision"] for r in inv] == ["AUTO_R"] * 3      # (0,65) is 92.86 deg: no automatic R
    arcs = [v for v in part["entities"][0]["vertices"] if v[2]]
    assert len(arcs) == 3
    assert corner_errors(part) == []


def test_slope_reads_up_from_left_end_and_part_turns_for_jlj():
    part = bc.build_job(one(strip()))["parts"][0]
    assert part["canonical_rotation_deg"] == 180               # top edge has notches, bottom edge is straight
    marks = [e for e in part["entities"] if e["role"] == "mark" and e["type"] == "TEXT"]
    assert [m["text"] for m in marks] == ["J", "J", "LJ"]       # 1500 < L <= 2000
    assert {m["insert"][1] for m in marks} == {70.0}
    pts = {tuple(v[:2]) for v in part["entities"][0]["vertices"]}
    assert (1720.0, 5.0) in pts and (1620.0, 0.0) in pts       # left end at 65 rose to 70 at x=100, turned 180 deg
    assert (1440.0, 25.0) in pts                               # first V bottom: 70-25 = 45 from the old bottom


def test_unotch_radius_is_half_width_and_mouth_callout_covers_all_notches():
    part = spec()["parts"][0]
    part["outline"][1]["unotch"]["at"] = [[100, 0], [200, 0]]
    part["outline"][1]["unotch"]["qty"] = 2
    built = bc.build_job(one(part))["parts"][0]
    assert built["status"] == "PASS" and built["flags"] == []
    c1 = [r for r in built["corner_inventory"] if r["canonical_member_id"].endswith(tuple(f"C1_{i}" for i in range(1, 5)))]
    assert len(c1) == 4 and {r["decision"] for r in c1} == {"CALLED"}
    verts = built["entities"][0]["vertices"]
    semis = [(v, verts[(i + 1) % len(verts)]) for i, v in enumerate(verts) if abs(v[2]) == 1]
    assert len(semis) == 2 and all(abs(math.dist(a[:2], b[:2]) - 10) < 1e-9 for a, b in semis)


def test_hole_witness_survives_rotation():
    part = strip(outline=[[0, 0], [1720, 0], [1720, 70],
                          {"vnotch": {"start": 1680, "pitch": -200, "count": 8, "level": 70, "depth": 25,
                                      "inward": -1, "ev": "v"}}, [0, 70]],
                 holes=[{"id": "H1", "d": 10, "ev": "Ø10", "wx": [[50, "HOLE_CENTER", "50"]],
                         "wy": [[20, "HOLE_CENTER", "20"]]}])
    job = bc.build_job(one(part))
    p = job["parts"][0]
    hole = next(e for e in p["entities"] if e["type"] == "CIRCLE")
    assert p["canonical_rotation_deg"] == 180 and hole["center"] == [1670.0, 50.0]
    validate_canonical_job(job)
    assert canonical_job_anomalies(job) == []


def test_gates_refuse_wrong_input():
    bad = strip(envelope=[1720, 75])
    with pytest.raises(bc.BuildError, match="ENVELOPE_MISMATCH"):
        bc.build_job(one(bad))
    bad = strip()
    bad["outline"][3]["vnotch"]["qty"] = 7
    with pytest.raises(bc.BuildError, match="GROUP_COUNT_CLOSURE"):
        bc.build_job(one(bad))
    bad = strip(outline=list(reversed(strip()["outline"][:3])) + [[0, 70]])
    with pytest.raises(bc.BuildError, match="counter-clockwise"):
        bc.build_job(one(bad))
    bad = spec()["parts"][0]
    bad["holes"][1]["at"] = [261, 50]
    with pytest.raises(bc.BuildError, match="DIMENSION_CHAIN_MISMATCH"):
        bc.build_job(one(bad))


def test_flagged_corner_makes_magenta_preview_without_auto_r():
    part = spec()["parts"][0]
    part["outline"][0] = [0, 0, {"FLAG": "Góc trái dưới chưa rõ R hay C"}]
    built = bc.build_job(one(part))["parts"][0]
    assert built["status"] == "PREVIEW" and built["entities"][0]["color"] == 6
    assert any(r["decision"] == "FLAG" for r in built["corner_inventory"])
    assert built["flags"] == ["Góc trái dưới chưa rõ R hay C"]


def test_overlay_fit_reports_residual(tmp_path):
    from pdf_views import fitz
    if fitz is None:
        pytest.skip("PyMuPDF not installed")
    img = tmp_path / "c.png"
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 400, 200), False)
    pix.set_rect(pix.irect, (255, 255, 255))
    pix.save(str(img))
    job = bc.build_job(spec())
    # scale 1 px/mm, y down, origin at (50, 150): exact anchors -> zero residual
    anchors = [overlay_check.parse_anchor(t) for t in ("0,0=50,150", "300,0=350,150", "300,100=350,50")]
    res = overlay_check.overlay(job, "26-000001", img, anchors, tmp_path / "o.png")
    assert res["max_residual_mm"] < 1e-9 and abs(res["scale_px_per_mm"] - 1) < 1e-9
    drawn = fitz.Pixmap(str(tmp_path / "o.png"))
    assert (drawn.width, drawn.height) == (400, 200)
    assert drawn.pixel(100, 150)[0] > 150 and drawn.pixel(100, 150)[1] < 100   # red outline on the bottom edge (x=50 mm)
    off = [overlay_check.parse_anchor(t) for t in ("0,0=50,150", "300,0=350,150", "300,100=350,45")]
    assert overlay_check.overlay(job, "26-000001", img, off, tmp_path / "o2.png")["max_residual_mm"] > 1


def test_run_job_cli_writes_only_dxf_to_out(tmp_path):
    out, work = tmp_path / "OUT", tmp_path / "work"
    assert run_job.main([str(EXAMPLE), str(out), "--work", str(work)]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["EXAMPLE-FLAT_ALL.dxf"]
    report = (work / "EXAMPLE-FLAT_report.md").read_text(encoding="utf-8")
    assert "| 26-000002 |" in report and "xoay 180°" in report


def test_run_job_default_work_dir_is_outside_the_spec_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(run_job.job_state, "WORK_ROOT", tmp_path / ".work")
    monkeypatch.setattr(run_job.job_state, "CURRENT", tmp_path / ".work" / "CURRENT")
    before = sorted(p.name for p in EXAMPLE.parent.iterdir())
    assert run_job.main([str(EXAMPLE), str(tmp_path / "OUT")]) == 0
    assert sorted(p.name for p in EXAMPLE.parent.iterdir()) == before
    assert (tmp_path / ".work" / "EXAMPLE-FLAT" / "EXAMPLE-FLAT_report.md").is_file()


def _split_spec(tmp_path, code, job_id="J-MULTI"):
    spec = copy.deepcopy(yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")))
    spec["job_id"] = job_id
    spec["parts"] = [dict(spec["parts"][0], code=code)]
    path = tmp_path / f"spec_{code}.yaml"
    path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    return path


def test_run_job_merges_specs_and_hand_canonical_json_in_order(tmp_path):
    import boxmet_job
    a, b = _split_spec(tmp_path, "26-000101"), _split_spec(tmp_path, "26-000102")
    box = tmp_path / "box.job.json"
    box.write_text(json.dumps(boxmet_job.build_job("26-000103", 200, 150, [30, 30, 30, 30], 1.5, "SS", 2.54,
                                                   job_id="J-MULTI")), encoding="utf-8")
    out, work = tmp_path / "OUT", tmp_path / "work"
    assert run_job.main([str(a), str(box), str(b), str(out), "--work", str(work)]) == 0
    job = json.loads((work / "J-MULTI_job.json").read_text(encoding="utf-8"))
    assert [p["code"] for p in job["parts"]] == ["26-000101", "26-000103", "26-000102"]
    assert sorted(p.name for p in out.iterdir()) == ["J-MULTI_ALL.dxf"]
    report = (work / "J-MULTI_report.md").read_text(encoding="utf-8")
    assert all(f"| {c} |" in report for c in ("26-000101", "26-000102", "26-000103"))


@pytest.mark.parametrize("second,match", [("26-000101", "duplicate part code"), ("26-000102", "job_id")])
def test_build_from_files_refuses_duplicates_and_mixed_jobs(tmp_path, second, match):
    a = _split_spec(tmp_path, "26-000101")
    b = _split_spec(tmp_path, second, job_id="J-MULTI" if second == "26-000101" else "J-OTHER")
    with pytest.raises(bc.BuildError, match=match):
        bc.build_from_files([a, b])
