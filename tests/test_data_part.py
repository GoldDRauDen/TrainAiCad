"""tools/data_part.py: customer DATA (dxf_digest -> dxf_assemble) + PDF meaning -> built, exported part."""
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
import data_part  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402

Q = math.tan(math.radians(90) / 4)


def _data_dxf(tmp_path):
    """200 x 100 SS400 t3.2 plate: sharp corners except one R5 (bulge), 2 x Ø9.05, an M6 raw Ø5.1 with its
    Ø6 nominal ring, one stadium slot W8 C20, a red KEGAKI line, a title text."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0, 0), (200, 0, 0), (200, 95, Q), (195, 100, 0), (0, 100, 0)], format="xyb", close=True)
    msp.add_circle((30, 50), 4.525)
    msp.add_circle((170, 50), 4.525)
    msp.add_circle((100, 80), 2.55)
    msp.add_circle((100, 80), 3.0)
    msp.add_lwpolyline([(90, 24, 0), (110, 24, -1), (110, 16, 0), (90, 16, -1)], format="xyb", close=True)
    msp.add_line((60, 40), (60, 60), dxfattribs={"color": 1})
    msp.add_text("26-062000", dxfattribs={"insert": (0, 120)})
    path = tmp_path / "data.dxf"
    doc.saveas(path)
    return path


def _assembled(tmp_path):
    dg = dxf_digest.digest(str(_data_dxf(tmp_path)))

    circles = [x for x in dg["pieces"] if x["type"] == "CIRCLE"]
    holes = [x["id"] for x in circles if abs(x["radius"] - 4.525) < 1e-9]
    tap = [x["id"] for x in circles if abs(x["radius"] - 2.55) < 1e-9]
    ring = [x["id"] for x in circles if abs(x["radius"] - 3.0) < 1e-9]
    outer = [x["id"] for x in dg["pieces"] if x["type"] in ("LINE", "ARC") and x["color"] == 256
             and not (85 <= min(x["start"][0], x["end"][0]) and max(x["start"][0], x["end"][0]) <= 115
                      and max(x["start"][1], x["end"][1]) <= 25)]
    slot = [x["id"] for x in dg["pieces"] if x["type"] in ("LINE", "ARC") and x["id"] not in outer and x["color"] == 256]
    keg = [x["id"] for x in dg["pieces"] if x["color"] == 1]
    plan = {"members": [{"id": "OUT", "role": "outer", "pieces": outer}, {"id": "H1", "role": "hole", "pieces": holes},
                        {"id": "T1", "role": "hole", "pieces": tap}, {"id": "SL1", "role": "slot", "pieces": slot},
                        {"id": "K1", "role": "kegaki", "pieces": keg}],
            "excluded": [{"reason": "TAP_NOMINAL_RING", "pieces": ring}]}

    res = dxf_assemble.assemble(dg, plan)
    out = tmp_path / "assembled.json"
    out.write_text(json.dumps(res), encoding="utf-8")
    return out


def _spec(tmp_path, **over):
    part = {"code": "26-062000", "material": "SS400", "t": 3.2, "page": 1, "data": "assembled.json",
            "envelope": [200, 100],
            "members": {"H1": {"group": "D9", "qty": 2, "ev": "p1 2-Ø9", "pdf_d": 9},
                        "T1": {"thread": "M6", "qty": 1, "ev": "p1 M6"},
                        "SL1": {"ev": "p1 長穴 8x28"}, "K1": {"ev": "p1 ケガキ"}}}
    part.update(over)
    _assembled(tmp_path)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump({"job_id": "520930-03", "parts": [part]}, allow_unicode=True), encoding="utf-8")
    return path


def test_data_part_builds_exports_and_keeps_data_geometry(tmp_path):
    job = bc.build_from_files([_spec(tmp_path)])
    part = job["parts"][0]
    assert part["status"] == "PASS"
    circles = sorted((e["center"], e["radius"]) for e in part["entities"] if e["type"] == "CIRCLE")
    assert circles == [([30.0, 50.0], 4.525), ([100.0, 80.0], 2.5), ([170.0, 50.0], 4.525)]  # Δ0.05 keeps DATA
    rules = [c["rule"] for c in part["manufacturing_change_ledger"]]
    assert rules.count("TAP_PILOT") == 1 and rules.count("DATA_AUTO_R_CANONICALIZATION") == 3  # R5 corner stays
    outer = part["entities"][0]
    assert any(v[2] == pytest.approx(Q) for v in outer["vertices"])                          # DATA R5 kept
    assert any(e["role"] == "kegaki" and e["color"] == 1 for e in part["entities"])
    assert part["slot_anchor_records"][0]["canonical_midpoint"] == [100.0, 20.0]
    manifest = export_canonical_job(job, tmp_path / "OUT", require_slip_codes=True)
    assert manifest["filename"] == "520930-03_ALL.dxf"


def test_pdf_value_beyond_the_gate_flags_and_keeps_data(tmp_path):
    spec = _spec(tmp_path)
    data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    data["parts"][0]["members"]["H1"]["pdf_d"] = 9.5
    spec.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    part = bc.build_from_files([spec])["parts"][0]
    assert part["status"] == "PREVIEW" and any("Lệch PDF" in f for f in part["flags"])
    assert {e["radius"] for e in part["entities"] if e["type"] == "CIRCLE"} >= {4.525}


@pytest.mark.parametrize("customer,radius,flagged", [("433", 4.525, False), ("395", 4.75, False), ("829", 4.525, False)])
def test_customer_data_pdf_policy(tmp_path, customer, radius, flagged):
    spec = _spec(tmp_path)
    data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    data["customer_code"] = customer
    data["parts"][0]["members"]["H1"]["pdf_d"] = 9.5   # Δ 0.45: under KH433's 1.0, PDF wins for 395, skipped for 829
    spec.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    part = bc.build_from_files([spec])["parts"][0]
    assert any(e["type"] == "CIRCLE" and e["radius"] == radius for e in part["entities"])
    assert any("Lệch PDF" in f for f in part["flags"]) is flagged


def test_member_without_pdf_meaning_and_qty_mismatch_are_refused(tmp_path):
    spec = _spec(tmp_path)
    data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    del data["parts"][0]["members"]["SL1"]
    spec.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(bc.BuildError, match="SL1 needs its PDF meaning"):
        bc.build_from_files([spec])
    data["parts"][0]["members"]["SL1"] = {"ev": "x"}
    data["parts"][0]["members"]["H1"]["qty"] = 3
    spec.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(bc.BuildError, match="GROUP_COUNT_CLOSURE"):
        bc.build_from_files([spec])


def test_gate_threshold_is_strict_at_the_tolerance():
    assert data_part.gate(9.1, 9.0, None, "Ø")[2]          # exactly 0.1 flags (rules/DATA_DXF.md §3)
    assert data_part.gate(9.09, 9.0, None, "Ø")[2] is None


def _face_view(tmp_path):
    """Plan view of the web of a U (KH646 style, drawn 1:3): 640 x 40 outline, 2 x Ø31, one M4 pair."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (640 / 3, 0), (640 / 3, 40 / 3), (0, 40 / 3)], close=True)
    for x in (58.5, 118.5):
        msp.add_circle((x / 3, 20 / 3), 31 / 6)
    msp.add_circle((28.5 / 3, 20 / 3), 3.242 / 6)
    msp.add_circle((28.5 / 3, 20 / 3), 4 / 6)
    path = tmp_path / "plan.dxf"
    doc.saveas(path)
    dg = dxf_digest.digest(str(path))
    circles = {round(p["radius"] * 6, 3): [] for p in dg["pieces"] if p["type"] == "CIRCLE"}
    for p in dg["pieces"]:
        if p["type"] == "CIRCLE":
            circles[round(p["radius"] * 6, 3)].append(p["id"])
    plan = {"transform": {"scale": 3, "evidence": "SCALE 1/3"},
            "members": [{"id": "OUT", "role": "outer", "pieces": [p["id"] for p in dg["pieces"] if p["type"] == "LINE"]},
                        {"id": "H31", "role": "hole", "pieces": circles[31.0]},
                        {"id": "M4", "role": "hole", "pieces": circles[3.242]}],
            "excluded": [{"reason": "TAP_NOMINAL_RING", "pieces": circles[4.0]}]}
    (tmp_path / "assembled.json").write_text(json.dumps(dxf_assemble.assemble(dg, plan)), encoding="utf-8")
    part = {"code": "26-038384", "material": "SPCC", "t": 2.3, "page": 2, "envelope": [735.76, 40],
            "bend": {"axis": "X", "width": 40, "width_ev": "plan 40",
                     "faces": [{"id": "L1", "od": 52.5, "ev": "50.2 + t"}, {"id": "W", "od": 640, "ev": "640"},
                               {"id": "L2", "od": 52.5, "ev": "50.2 + t"}],
                     "bends": [{"id": "B1", "angle": 90, "sign": 1, "ev": "U"}, {"id": "B2", "angle": 90, "sign": 1, "ev": "U"}]},
            "outline": "auto", "data": "assembled.json", "data_face": "W",
            "members": {"H31": {"group": "D31", "qty": 2, "ev": "Ø31", "pdf_d": 31}, "M4": {"thread": "M4", "ev": "M4"}}}
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump({"job_id": "520702-08", "customer_code": "646", "parts": [part]},
                                   allow_unicode=True), encoding="utf-8")
    return path


def test_kh646_face_view_puts_data_features_on_the_bent_face(tmp_path):
    part = bc.build_from_files([_face_view(tmp_path)])["parts"][0]
    assert part["status"] == "PASS" and [b["nobi"] for b in part["unfold"]["bends"]] == [4.62, 4.62]  # KH646 table
    circles = sorted((round(e["center"][0], 3), round(e["radius"] * 2, 3)) for e in part["entities"] if e["type"] == "CIRCLE")
    assert circles == [(76.38, 3.3), (106.38, 31.0), (166.38, 31.0)]   # web start = B1 line1 = 52.5 - 4.62
    assert {c["rule"] for c in part["manufacturing_change_ledger"]} >= {"TAP_PILOT"}


def test_face_view_longer_than_the_face_od_flags(tmp_path):
    spec = _face_view(tmp_path)
    data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    data["parts"][0]["bend"]["faces"][1]["od"] = 639.5
    spec.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    part = bc.build_from_files([spec])["parts"][0]
    assert any("DATA W OD" in f and "Lệch PDF" in f for f in part["flags"])


def test_one_view_two_kinds_of_faces_ears_and_web(tmp_path):
    """KH646 26-038384 shape: U with ears turned out at the top; the plan view shows ears and web (1:3)."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (640 / 3, 0), (640 / 3, 40 / 3), (0, 40 / 3)], close=True)
    for x in (5, 635):
        msp.add_circle((x / 3, 20 / 3), 5 / 6)
    msp.add_circle((58.5 / 3, 20 / 3), 31 / 6)
    path = tmp_path / "plan.dxf"
    doc.saveas(path)
    dg = dxf_digest.digest(str(path))
    by_r = {}
    for p in dg["pieces"]:
        if p["type"] == "CIRCLE":
            by_r.setdefault(round(p["radius"] * 6, 3), []).append(p["id"])
    plan = {"transform": {"scale": 3, "evidence": "SCALE 1/3"},
            "members": [{"id": "OUT", "role": "outer", "pieces": [p["id"] for p in dg["pieces"] if p["type"] == "LINE"]},
                        {"id": "H5", "role": "hole", "pieces": by_r[5.0]}, {"id": "H31", "role": "hole", "pieces": by_r[31.0]}]}
    (tmp_path / "assembled.json").write_text(json.dumps(dxf_assemble.assemble(dg, plan)), encoding="utf-8")
    faces = [("E1", 14.3), ("L1", 54.8), ("W", 616), ("L2", 54.8), ("E2", 14.3)]
    part = {"code": "26-038384", "material": "SPCC", "t": 2.3, "page": 2, "envelope": [735.72, 40],
            "bend": {"axis": "X", "width": 40, "width_ev": "plan 40",
                     "faces": [{"id": f, "od": od, "ev": "profile"} for f, od in faces],
                     "bends": [{"id": f"B{i}", "angle": 90, "sign": 1, "ev": "profile"} for i in range(1, 5)]},
            "outline": "auto", "data": "assembled.json",
            "data_faces": [{"face": "E1", "from": "start", "at": 0, "to": 12},
                           {"face": "W", "from": "start", "at": 12, "to": 628},
                           {"face": "E2", "from": "end", "at": 640, "to": 628}],
            "members": {"H5": {"group": "D5", "qty": 2, "ev": "2-Ø5 あける"}, "H31": {"group": "D31", "ev": "Ø31"}}}
    spec = tmp_path / "spec.yaml"
    spec.write_text(yaml.safe_dump({"job_id": "520702-08", "customer_code": "646", "parts": [part]},
                                   allow_unicode=True), encoding="utf-8")
    p = bc.build_from_files([spec])["parts"][0]
    assert p["status"] == "PASS" and p["unfold"]["flat_length_mm"] == pytest.approx(735.72)   # slip 735.72
    xs = sorted(round(e["center"][0], 3) for e in p["entities"] if e["type"] == "CIRCLE")
    assert xs == [5.0, 59.86 + 46.5, 730.72]   # ears from their free edges; web from the leg's outer plane (x 12)
