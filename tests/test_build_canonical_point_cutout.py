"""build_canonical: POINT holes (piercing / below-minimum) and rectangular cut-outs (flat and face-relative)."""
import copy
import math
import sys
from pathlib import Path

import ezdxf
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from canonical_contract import validate_canonical_job  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from holistic_engineering_guard import canonical_job_anomalies  # noqa: E402

BEND = yaml.safe_load((ROOT / "examples/bend_minimal.yaml").read_text(encoding="utf-8"))


def plate(**kw):
    part = {"code": "26-000021", "material": "SUS304", "t": 3, "page": 1, "envelope": [100, 60],
            "outline": [[0, 0, {"SHARP": "t"}], [100, 0, {"SHARP": "t"}], [100, 60, {"SHARP": "t"}],
                        [0, 60, {"SHARP": "t"}]]}
    part.update(kw)
    return part


def hole(hid="H1", d=6, x=20, y=30, **kw):
    h = {"id": hid, "d": d, "ev": "Ø%g" % d, "wx": [[x, "HOLE_CENTER", "x"]], "wy": [[y, "HOLE_CENTER", "y"]]}
    h.update(kw)
    return h


def build(part):
    return bc.build_job({"job_id": "T", "parts": [part]})


def entity(job, suffix):
    return next(e for e in job["parts"][0]["entities"] if e["entity_id"].endswith(suffix))


def test_piercing_hole_becomes_bylayer_point_with_witness_chain():
    job = build(plate(holes=[hole(piercing=True)]))
    e = entity(job, "_H1")
    assert e["type"] == "POINT" and e["role"] == "ordinary_point" and "color" not in e
    assert e["point"] == [20.0, 30.0]
    validate_canonical_job(job)
    assert canonical_job_anomalies(job) == []


def test_hole_below_half_thickness_is_point_without_flag():
    job = build(plate(holes=[hole(d=1.2)]))
    assert entity(job, "_H1")["type"] == "POINT" and job["parts"][0]["flags"] == []


def test_through_piercing_is_green_point_with_authorization_record(tmp_path):
    stamp = "PIERCING (ピアス circled on M5) + THROUGH HOLE (red stamp)"
    job = build(plate(holes=[hole(piercing=True, through=True, stamp=stamp)]))
    e = entity(job, "_H1")
    assert e["type"] == "POINT" and e["role"] == "through_piercing" and e["color"] == 3
    rec = job["parts"][0]["piercing_authorizations"][0]
    assert rec["member_id"] == "26-000021_H1" and rec["entity_id"] == e["entity_id"]
    assert rec["stamp_text"] == stamp and rec["source_pdf_page"] == 1
    validate_canonical_job(job)
    manifest = export_canonical_job(job, tmp_path, require_slip_codes=True)
    doc = ezdxf.readfile(tmp_path / manifest["filename"])
    pts = [p for p in doc.modelspace() if p.dxftype() == "POINT" and p.dxf.layer == "0"]
    assert len(pts) == 1 and pts[0].dxf.color == 3
    assert not [c for c in doc.modelspace() if c.dxftype() == "CIRCLE"]


def test_through_piercing_needs_a_stamp_with_both_english_words():
    with pytest.raises(bc.BuildError, match="THROUGH_PIERCING_STAMP"):
        build(plate(holes=[hole(piercing=True, through=True)]))
    with pytest.raises(bc.BuildError, match="THROUGH_PIERCING_STAMP"):
        build(plate(holes=[hole(piercing=True, through=True, stamp="PIERCING only")]))
    with pytest.raises(bc.BuildError, match="through needs piercing"):
        build(plate(holes=[hole(through=True, stamp="PIERCING THROUGH HOLE")]))


def test_point_hole_survives_the_180_degree_turn():
    part = plate(envelope=[1200, 60], outline=[[0, 0, {"SHARP": "t"}], [1200, 0, {"SHARP": "t"}],
                                                 [1200, 60, {"SHARP": "t"}],
                                                 {"vnotch": {"start": 1100, "pitch": -200, "count": 5, "level": 60,
                                                             "depth": 10, "inward": -1, "qty": 5, "ev": "v"}},
                                                 [0, 60, {"SHARP": "t"}]],
                 holes=[hole(x=50, y=20, piercing=True)])
    job = build(part)
    p = job["parts"][0]
    assert p["canonical_rotation_deg"] == 180 and entity(job, "_H1")["point"] == [1150.0, 40.0]
    validate_canonical_job(job)
    assert canonical_job_anomalies(job) == []


def cutout(**kw):
    c = {"id": "OP1", "rect": [20, 10, 80, 50], "R": 10, "group": "OPENING", "qty": 1, "ev": "p1 opening 60 x 40 R10"}
    c.update(kw)
    return c


def test_rect_cutout_is_one_clockwise_closed_contour_with_true_arcs(tmp_path):
    job = build(plate(cutouts=[cutout()]))
    e = entity(job, "_OP1")
    assert e["role"] == "cutout" and e["closed"] is True and len(e["vertices"]) == 8
    assert sum(1 for v in e["vertices"] if v[2]) == 4
    assert all(abs(abs(v[2]) - math.tan(math.pi / 8)) < 1e-9 for v in e["vertices"] if v[2])
    area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(e["vertices"], e["vertices"][1:] + e["vertices"][:1]))
    assert area2 < 0  # CW
    grp = next(g for g in job["parts"][0]["source_groups"] if g["family"] == "CUTOUT")
    assert grp["source_quantity"] == 1 and grp["members"][0]["member_id"] == "26-000021_OP1"
    validate_canonical_job(job)
    assert canonical_job_anomalies(job) == []
    manifest = export_canonical_job(job, tmp_path, require_slip_codes=True)
    doc = ezdxf.readfile(tmp_path / manifest["filename"])
    inner = [x for x in doc.modelspace() if x.dxf.layer == "0" and x.dxftype() in ("LINE", "ARC")
             and "_OP1:" in str(manifest["entity_map"][list(doc.modelspace()).index(x)])]
    assert len(inner) == 8 and sum(1 for x in inner if x.dxftype() == "ARC") == 4


def test_square_cutout_without_radius_has_no_bulges():
    e = entity(build(plate(cutouts=[cutout(R=0)])), "_OP1")
    assert len(e["vertices"]) == 4 and not any(v[2] for v in e["vertices"])


def test_cutout_group_quantity_is_closed():
    c2 = cutout(id="OP2", rect=[85, 10, 95, 20])
    c2.pop("R")
    with pytest.raises(bc.BuildError, match="GROUP_COUNT_CLOSURE"):
        build(plate(cutouts=[cutout(qty=1), c2 | {"qty": 1}]))
    job = build(plate(cutouts=[cutout(qty=2), c2 | {"qty": 2}]))
    assert len([g for g in job["parts"][0]["source_groups"] if g["family"] == "CUTOUT"]) == 1


@pytest.mark.parametrize("bad, match", [
    (cutout(rect=[20, 10, 120, 50]), "CONTAINMENT"),
    (cutout(rect=[20, 10, 30, 50], R=6), "R .* larger"),
    (cutout(rect=[50, 10, 20, 50]), "rect"),
    (cutout(ev=None), "needs ev"),
])
def test_bad_cutouts_are_refused(bad, match):
    with pytest.raises(bc.BuildError, match=match):
        build(plate(cutouts=[bad]))


def bent(**kw):
    part = copy.deepcopy(BEND["parts"][0])
    part["envelope"] = [228.64, 40]
    part["outline"] = "auto"
    part["holes"] = []
    part.update(kw)
    return part


def test_face_relative_cutout_maps_onto_the_flat_like_a_hole():
    # F3 starts at line1 of B1 (50 - 3.68 = 46.32 ... face start), u measured along the face, v across from the flat edge
    part = bent(cutouts=[{"id": "OP1", "face": "F3", "from": "start", "u": [30, 60], "v": [10, 30], "R": 5,
                          "group": "OPENING", "qty": 1, "ev": "p6 opening on F3"}])
    job = build(part)
    chain = job["parts"][0]["unfold"]["faces"]["F3"]
    e = entity(job, "_OP1")
    xs = [v[0] for v in e["vertices"]]
    assert min(xs) == pytest.approx(chain["start"] + 30) and max(xs) == pytest.approx(chain["start"] + 60)
    ys = [v[1] for v in e["vertices"]]
    assert min(ys) == pytest.approx(10) and max(ys) == pytest.approx(30)
    validate_canonical_job(job)


def test_cutout_across_a_bend_zone_is_refused():
    part = bent(cutouts=[{"id": "OP1", "rect": [30, 10, 80, 30], "R": 0, "group": "OPENING", "qty": 1, "ev": "x"}])
    with pytest.raises(bc.BuildError, match="overlaps bend"):
        build(part)
