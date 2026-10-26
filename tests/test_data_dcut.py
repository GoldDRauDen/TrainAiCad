"""D-shaped cut-out (半月 hole: arc + flat chord = a closed loop of TWO vertices) harvested from customer DATA.

The DATA arc/line are never retyped; the PDF size (Ø12.1 / flat 10.1) is only a same-parameter gate.
"""
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import data_part  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402
from canonical_contract import validate_canonical_job  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402

CHORD_HALF = math.sqrt(36 - 16)
CAP = math.degrees(math.atan2(4, CHORD_HALF))      # 41.81 deg


def _dxf(tmp_path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((0, 0), (100, 0)), ((100, 0), (100, 60)), ((100, 60), (0, 60)), ((0, 60), (0, 0))):
        msp.add_line(a, b)
    for cx in (30, 70):
        msp.add_arc((cx, 30), 6, 180 - CAP, CAP)                      # the big arc, CCW from 138.19 to 41.81
        msp.add_line((cx - CHORD_HALF, 34), (cx + CHORD_HALF, 34))    # the flat, 4 above the centre
    path = tmp_path / "d.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def _spec(tmp_path, pdf_size=(12.1, 10.1)):
    dg = _dxf(tmp_path)
    lines = [p["id"] for p in dg["pieces"] if p["type"] == "LINE"]
    arcs = sorted((p for p in dg["pieces"] if p["type"] == "ARC"), key=lambda p: p["center"][0])
    chords = sorted((p for p in dg["pieces"] if p["type"] == "LINE" and abs(p["start"][1] - 34) < 1e-6),
                    key=lambda p: p["start"][0])
    outer = [p["id"] for p in dg["pieces"] if p["type"] == "LINE" and p["id"] not in {c["id"] for c in chords}]
    plan = {"members": [{"id": "OUT", "role": "outer", "pieces": outer},
                        {"id": "D1", "role": "cutout", "pieces": [arcs[0]["id"], chords[0]["id"]]},
                        {"id": "D2", "role": "cutout", "pieces": [arcs[1]["id"], chords[1]["id"]]}]}
    path = tmp_path / "assembled.json"
    path.write_text(json.dumps(dxf_assemble.assemble(dg, plan)), encoding="utf-8")
    meaning = {m: {"group": "DCUT", "ev": "8箇所 半月部 Ø12.1 / 10.1", "pdf_size": list(pdf_size), "pdf_label": "lỗ bán nguyệt"}
               for m in ("D1", "D2")}
    return {"code": "26-000910", "material": "SPCC", "t": 2, "page": 1, "data": str(path), "envelope": [100, 60],
            "members": meaning}


def test_two_vertex_loop_with_an_arc_is_a_valid_clockwise_cutout(tmp_path):
    part = bc.build_part(_spec(tmp_path, pdf_size=(12, 10)))
    cuts = [e for e in part["entities"] if e["role"] == "cutout"]
    assert len(cuts) == 2 and all(len(c["vertices"]) == 2 for c in cuts)
    assert sorted(round(c["vertices"][0][0] + CHORD_HALF, 6) for c in cuts) == [30, 70]
    assert part["status"] == "PASS" and not part["flags"]
    job = {"canonical_contract": bc.CONTRACT, "job_id": "T", "parts": [part]}
    validate_canonical_job(job)
    assert export_canonical_job(job, tmp_path / "out")["status"] == "PASS"   # the saved DXF reopens with both D loops


def test_pdf_size_is_a_same_parameter_gate_flagged_once(tmp_path):
    part = bc.build_part(_spec(tmp_path))            # PDF 12.1 / 10.1 against DATA 12 / 10 (delta 0.1 flags)
    assert part["status"] == "PREVIEW"
    assert sum("DATA_PDF_DIM_DIFF" in f and "lỗ bán nguyệt X" in f for f in part["flags"]) == 1
    assert sum("DATA_PDF_DIM_DIFF" in f and "lỗ bán nguyệt Y" in f for f in part["flags"]) == 1
    cuts = [e for e in part["entities"] if e["role"] == "cutout"]
    assert data_part._bbox(cuts[0]["vertices"]) == pytest.approx((12.0, 10.0), abs=1e-6)      # DATA kept


def test_a_straight_two_vertex_loop_is_still_refused(tmp_path):
    spec = _spec(tmp_path, pdf_size=(12, 10))
    spec["cutouts"] = [{"id": "X", "ev": "x", "vertices": [[10, 10, 0], [20, 10, 0]]}]
    with pytest.raises(bc.BuildError, match="closed clockwise loop"):
        bc.build_part({k: v for k, v in spec.items() if k not in ("data", "members")} |
                      {"outline": [[0, 0], [100, 0], [100, 60], [0, 60]]})
