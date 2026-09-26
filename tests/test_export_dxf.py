"""Structural DXF dual-export tests; NOT a substitute for drawing regression cases."""
import copy
import json
import sys
from pathlib import Path

import ezdxf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_dxf import export_job  # noqa: E402


CHECKS = dict.fromkeys(("contour_topology", "datum", "feature_count", "unfold",
                        "containment", "bend_domain", "material_rules", "slot_semantics"), "PASS")


def part(code, size=(30, 20)):
    x, y = size
    return {"code": code, "material": "SS", "thickness_mm": 2,
            "status": "PASS", "checks": dict(CHECKS), "entities": [
                {"type": "LWPOLYLINE", "role": "outer", "closed": True,
                 "vertices": [[0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0]]},
                {"type": "CIRCLE", "role": "hole", "center": [x/2, y/2], "radius": 2},
                {"type": "POINT", "role": "ordinary_point", "point": [6, 6]},
                {"type": "POINT", "role": "through_piercing", "color": 3, "point": [12, 6]},
                {"type": "LINE", "role": "bend", "linetype": "DASHED", "start": [5, 0], "end": [5, y]},
                {"type": "LINE", "role": "bend", "linetype": "DASHED", "start": [8, 0], "end": [8, y]},
            ]}


def test_two_part_dxf_and_manifest(tmp_path):
    job = {"job_id": "520924-19", "parts": [part("000001"), part("000002", (40, 15))]}
    manifest = export_job(job, tmp_path)
    assert [p["code"] for p in manifest["parts"]] == ["000001", "000002"]
    assert len(manifest["combined"]["PASS"]["parts"]) == 2
    assert manifest["combined"]["PASS"]["parts"][0]["combined_bbox_mm"][1] >= 25
    assert manifest["combined"]["PASS"]["parts"][1]["combined_bbox_mm"][3] == 15
    for filename, count in [("520924-19_000001.dxf", 6), ("520924-19_000002.dxf", 6), ("520924-19_ALL.dxf", 12)]:
        doc = ezdxf.readfile(tmp_path / filename)
        assert len(list(doc.modelspace())) == count
        assert doc.header["$INSUNITS"] == 4
        assert all(e.dxf.layer == "0" for e in doc.modelspace())
    assert (tmp_path / "520924-19_MANIFEST.json").is_file()
    assert json.loads((tmp_path / "520924-19_MANIFEST.json").read_text())["contract"] == "TrainAiCad-DXF-V4.7"


def test_preview_is_isolated_from_production(tmp_path):
    good = part("000001")
    review = part("000002")
    review.update(status="PREVIEW", flags=["unreadable numeric X"], preview_reason="numeric_only_known_topology")
    review["entities"].append({"type": "POINT", "role": "estimated", "color": 6, "point": [15, 15]})
    review["entities"].append({"type": "TEXT", "role": "estimated_note", "color": 6, "insert": [15, 16], "text": "ESTIMATED - CHECK DRAWING"})
    manifest = export_job({"job_id": "JOB", "parts": [good, review]}, tmp_path)
    assert (tmp_path / "JOB_ALL.dxf").is_file()
    assert (tmp_path / "JOB_PREVIEW_ALL.dxf").is_file()
    assert [p["code"] for p in manifest["combined"]["PASS"]["parts"]] == ["000001"]
    assert [p["code"] for p in manifest["combined"]["PREVIEW"]["parts"]] == ["000002"]
    with pytest.raises(ValueError):
        bad = copy.deepcopy(review)
        bad["entities"] = bad["entities"][:-1]
        export_job({"job_id": "JOB", "parts": [bad]}, tmp_path)


def test_rejects_unvalidated_or_wrong_layers(tmp_path):
    good = part("000001")
    del good["checks"]["datum"]
    with pytest.raises(ValueError, match="eight upstream"):
        export_job({"job_id": "JOB", "parts": [good]}, tmp_path)
    good = part("000001")
    good["entities"][1]["layer"] = "HOLES"
    with pytest.raises(ValueError, match="Layer 0"):
        export_job({"job_id": "JOB", "parts": [good]}, tmp_path)


def test_rejects_magenta_and_wrong_point_semantics(tmp_path):
    good = part("000001")
    good["entities"][2]["color"] = 3
    with pytest.raises(ValueError, match="ordinary POINT"):
        export_job({"job_id": "JOB", "parts": [good]}, tmp_path)
    good = part("000001")
    good["entities"][1]["color"] = 6
    with pytest.raises(ValueError, match="Magenta"):
        export_job({"job_id": "JOB", "parts": [good]}, tmp_path)
