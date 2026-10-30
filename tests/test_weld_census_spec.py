"""KH851 weld census reaches the canonical part from the spec or its census_<code>.json (no job-local inject script),
and a `kegaki` item with `flag:` stays a FLAGGED mark (Magenta estimate or no geometry)."""
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
from canonical_contract import CanonicalContractError, validate_canonical_job  # noqa: E402

CODE = "26-000851"


def host(**kw):
    p = {"code": CODE, "material": "SPHCP", "t": 6, "page": 2, "envelope": [325, 32],
         "outline": [[0, 0], [325, 0], [325, 32], [0, 32]],
         "kegaki": [{"id": "K1", "group": "KG_A", "qty": 1, "ev": "p2 bar A: 121..153",
                     "lines": [[121, 0, 121, 32], [153, 0, 153, 32]]}]}
    p.update(kw)
    return p


def site(wid, mids, status="PROVED"):
    s = {"weld_site_id": wid, "status": status, "parent_code": CODE, "child_part_id": "A",
         "assembly_view_id": "P2_PLAN", "source_evidence": "p2 plan: bar A lies on C", "weld_required_cue": True,
         "self_locating": False, "mark_status": status, "mark_member_ids": mids}
    if status == "PROVED":
        s.update(host_face="TOP", datum_evidence="p2 chain 121/32")
    else:
        s["unresolved_fields"] = ["footprint position"]
    return s


def census(*sites):
    return {"source_assembly_view_ids": ["P2_PLAN"],
            "weld_site_census": {"inspected_assembly_view_ids": ["P2_PLAN"],
                                 "source_evidence": "p2 plan read at 400 dpi", "sites": list(sites)}}


def job(*parts):
    return bc.build_job({"job_id": "521000-01", "customer_code": "851", "parts": list(parts)})


def test_spec_weld_census_short_ids_validate():
    j = job(host(**census(site("W1", ["K1"]))))
    p = j["parts"][0]
    assert p["source_weld_site_ids"] == ["W1"]
    assert p["weld_site_census"]["sites"][0]["mark_member_ids"] == [f"{CODE}_K1"]
    validate_canonical_job(j)


def test_census_file_next_to_spec_is_merged(tmp_path):
    spec = tmp_path / "make" / f"spec_{CODE}.yaml"
    spec.parent.mkdir()
    spec.write_text(yaml.safe_dump({"job_id": "521000-01", "customer_code": "851", "parts": [host()]}),
                    encoding="utf-8")
    (tmp_path / f"census_{CODE}.json").write_text(json.dumps({"part_code": CODE, **census(site("W1", ["K1"]))}),
                                                   encoding="utf-8")
    j = bc.build_from_files([spec])
    assert j["parts"][0]["weld_site_census"]["sites"][0]["weld_site_id"] == "W1"
    validate_canonical_job(j)


def test_missing_851_census_still_fails_export_contract():
    with pytest.raises(CanonicalContractError):
        validate_canonical_job(job(host()))


def test_flagged_mark_without_geometry():
    k = [{"id": "K1", "group": "KG_A", "qty": 1, "ev": "p3 C welded between A and B",
          "flag": "KEGAKI C chưa xác định vị trí - xác nhận"}]
    j = job(host(kegaki=k, **census(site("W1", ["K1"], status="FLAGGED"))))
    p = j["parts"][0]
    m = next(m for m in p["canonical_members"] if m.get("source_member_id") == f"{CODE}_K1")
    assert m["status"] == "FLAGGED_NO_GEOMETRY" and m["entity_ids"] == []
    assert p["status"] == "PREVIEW" and p["flags"]
    validate_canonical_job(j)


def test_flagged_mark_with_estimate_is_magenta():
    k = [{"id": "K1", "group": "KG_A", "qty": 1, "ev": "p3 B on the seat edge",
          "flag": "KEGAKI B ước lượng vị trí - xác nhận", "lines": [[100, 0, 100, 32]]}]
    j = job(host(kegaki=k, **census(site("W1", ["K1"], status="FLAGGED"))))
    ent = next(e for e in j["parts"][0]["entities"] if e["entity_id"] == f"E_{CODE}_K1")
    assert (ent["role"], ent["color"]) == ("estimated", 6)
    validate_canonical_job(j)
