"""A source DATA gap can warn in composite without downgrading proved CUT."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from canonical_contract import CanonicalContractError, validate_canonical_job
from export_canonical_dxf import export_canonical_job
from test_export_artifacts import part, job, review_part


def gap_flag(kind="NONCUT_SOURCE_OPEN"):
    flag = {
        "gap_id": "GAP_FROM_DATA_A",
        "classification": kind,
        "source_view_id": "CUSTOMER_DATA_FRONT",
        "source_entity_ids": ["RAW_SOURCE_ENTITY_01", "RAW_SOURCE_ENTITY_02"],
        "source_endpoints": [[4.0, 5.0], [4.2, 5.0]],
        "source_evidence": "Customer DXF physical source: two open endpoints, decoded and counted",
        "disposition_evidence": "PDF manufacturing witness and physical family census separately checked",
        "raw_data_snapshot_ref": "RAW_SNAPSHOT_CAD_JOB",
        "physical_data_baseline_ref": "PHYSICAL_CURVE_LEDGER_2026",
        "bidirectional_qa_ref": "SOURCE_PHYSICAL_TO_CANONICAL and inverse saved-DXF QA",
        "source_to_part_transform": [1, 0, 0, 1, 0, 0],
        "transform_evidence": "Identity transform proved by customer DATA front view",
        "source_role": "PROJECTION_ONLY",
        "canonical_entity_ids": [],
    }
    return flag


def valid_job():
    src = job([part("GAP", bent=False, slot=False, relief=False)])
    src["source_mode"] = "PDF_DATA_RAW"
    src["parts"][0]["data_gap_flags"] = [gap_flag()]
    return src


def _text_labels(doc):
    return [e.dxf.text for e in doc.modelspace()
            if e.dxftype() == "TEXT" and e.dxf.layer == "AI_META"]


def test_noncut_data_open_warnings_only_in_composite_pass_individual(tmp_path):
    src = valid_job()
    check = validate_canonical_job(src)
    assert len(check["parts"][0]["data_gap_advisories"]) == 1
    result = export_canonical_job(src, tmp_path, write_manifest=True)
    assert result["status"] == "PASS"
    assert result["filename"] == "TESTJOB_ALL.dxf"
    assert result["nonblocking_data_gap_flag_count"] == 1
    assert result["artifacts"]["parts"][0]["cut_readback"] == "PASS"
    assert (tmp_path / "parts_dxf/GAP.dxf").exists()
    assert not (tmp_path / "TESTJOB_ALL_REVIEW_ONLY.dxf").exists()
    assert validate_canonical_job(json.loads((tmp_path / "geometry_json/GAP.json").read_text()))
    cut = ezdxf.readfile(tmp_path / "parts_dxf/GAP.dxf")
    assert set(e.dxftype() for e in cut.modelspace()) <= {"LINE", "ARC", "CIRCLE"}
    assert not any(e.dxf.layer == "AI_META" for e in cut.modelspace())
    composite = ezdxf.readfile(tmp_path / "TESTJOB_ALL.dxf")
    assert not any(e.dxftype() in {"LWPOLYLINE", "POLYLINE"} for e in composite.modelspace())
    label = [l for l in _text_labels(composite) if "DATA GAP FLAG" in l]
    assert len(label) == 1 and "SOURCE ONLY; CUT PASS" in label[0]
    marker = [e for e in composite.modelspace()
              if e.dxf.layer == "AI_META" and e.dxftype() == "CIRCLE"]
    assert len(marker) == 1
    assert abs(marker[0].dxf.center.x - 4.1) < 1e-6
    assert marker[0].dxf.get("color") == 6
    assert not any("NO CUT" in l for l in _text_labels(composite))


def test_gap_warning_remains_local_with_unrelated_review(tmp_path):
    src = valid_job()
    src["parts"].append(review_part("REVIEW"))
    result = export_canonical_job(src, tmp_path)
    assert result["filename"] == "TESTJOB_ALL_REVIEW_ONLY.dxf"
    assert (tmp_path / "parts_dxf/GAP.dxf").exists()
    assert not (tmp_path / "parts_dxf/REVIEW.dxf").exists()
    assert any("DATA GAP FLAG" in t for t in _text_labels(
        ezdxf.readfile(tmp_path / result["filename"])))


@pytest.mark.parametrize("mutation,expected", [
    (lambda x: x.pop("source_mode"), "PDF_DATA_RAW"),
    (lambda x: x["parts"][0]["data_gap_flags"][0].pop("raw_data_snapshot_ref"),
     "RAW_DATA_SNAPSHOT"),
    (lambda x: x["parts"][0]["data_gap_flags"][0].update(source_endpoints=[[4, 5], [4, 5]]),
     "no measurable source gap"),
    (lambda x: x["parts"][0]["data_gap_flags"][0].update(source_role="CUT"),
     "noncut provenance"),
    (lambda x: x["parts"][0]["data_gap_flags"][0].update(canonical_entity_ids=["E_GAP_OUT"]),
     "NONCUT source gap"),
    (lambda x: x["parts"][0]["data_gap_flags"][0].update(source_to_part_transform=[1, 0, 1, 1, 0, 0]),
     "source transforms"),
    (lambda x: x["parts"][0].update(flags=["UNRESOLVED TOPOLOGY"]), "verified manufacturing PASS"),
    (lambda x: x["parts"][0]["checks"].update(contour_topology="N/A"), "cannot bypass"),
    (lambda x: x["parts"][0]["data_gap_flags"][0].update(classification="UNKNOWN_CUT_GAP"),
     "unknown/non-proved"),
])
def test_no_silent_downgrade_or_fake_pass(mutation, expected):
    src = valid_job()
    mutation(src)
    with pytest.raises(CanonicalContractError, match=expected):
        validate_canonical_job(src)


def test_intentional_open_relief_line_arc_keeps_manufacturing_pass(tmp_path):
    src = job([part("RELIEF", bent=False, slot=False, relief=True)])
    src["source_mode"] = "PDF_DATA_RAW"
    flag = gap_flag("INTENTIONAL_OPEN_CUT")
    flag["source_role"] = "CUT"
    flag["canonical_entity_ids"] = ["E_RELIEF_RELIEF_0", "E_RELIEF_RELIEF_1"]
    flag["manufacturing_instruction"] = "PDF explicit slit relief opens to material edge"
    src["parts"][0]["data_gap_flags"] = [flag]
    result = export_canonical_job(src, tmp_path)
    assert result["status"] == "PASS"
    assert (tmp_path / "parts_dxf/RELIEF.dxf").exists()


def test_raw_cut_missing_segment_not_pass_without_scope_witness(tmp_path):
    src = valid_job()
    flag = src["parts"][0]["data_gap_flags"][0]
    flag["classification"] = "PROVED_MANUFACTURING_CLOSURE"
    flag["source_role"] = "CUT"
    flag["canonical_entity_ids"] = ["E_GAP_OUT"]
    with pytest.raises(CanonicalContractError, match="manufacturing change"):
        validate_canonical_job(src)

    flag["manufacturing_change_ledger_ref"] = "MC_CLOSURE_2026"
    flag["closure_witness"] = "PDF source dimensions independently prove a continuous outside contour"
    with pytest.raises(CanonicalContractError, match="manufacturing_change_ledger scope"):
        validate_canonical_job(src)

    src["parts"][0]["manufacturing_change_ledger"] = [{
        "change_id": "MC_CLOSURE_2026",
        "status": "PROVED",
        "controlling_rule": "PDF_PROVED_OUTER_CORRECTION",
        "canonical_entity_ids": ["E_GAP_OUT"],
        "source_entity_ids": list(flag["source_entity_ids"]),
    }]
    assert validate_canonical_job(src)["parts"][0]["data_gap_advisories"][0]["classification"] == "PROVED_MANUFACTURING_CLOSURE"
    out = export_canonical_job(src, tmp_path)
    assert out["status"] == "PASS" and out["nonblocking_data_gap_flag_count"] == 1
