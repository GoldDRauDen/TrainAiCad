"""PASS-only manufacturing DXF regression tests (synthetic source). No JSON output."""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from canonical_contract import CanonicalContractError, validate_canonical_job  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from export_job_artifacts import _arc_from_bulge  # noqa: E402


CHECKS = dict.fromkeys((
    "contour_topology", "datum", "feature_count", "unfold",
    "containment", "bend_domain", "material_rules", "slot_semantics"
), "PASS")


def source_group(code, family, name, eids, state="PROVED", canon_state=None):
    gid = f"G_{code}_{name}"
    mid = f"M_{code}_{name}"
    group = {
        "group_id": gid, "family": family, "status": state,
        "source_quantity": 1,
        "evidence": "synthetic test source claim; not customer dimensions",
        "members": [{"member_id": mid, "status": state}],
    }
    canonical = {
        "canonical_member_id": f"CM_{code}_{name}",
        "origin": "SOURCE", "source_member_id": mid,
        "group_id": gid, "status": canon_state or state, "entity_ids": eids,
    }
    return group, canonical


def part(code, bent=True, slot=True, relief=True):
    entities = [{
        "entity_id": f"E_{code}_OUT", "type": "LWPOLYLINE", "role": "outer",
        "closed": True,
        "vertices": [[0, 0, 0], [40, 0, 0], [40, 30, 0], [0, 30, 0]],
    }, {
        "entity_id": f"E_{code}_HOLE", "type": "CIRCLE",
        "role": "hole", "center": [7, 8], "radius": 2.5,
    }]
    groups, canonical = [], []

    def add(family, name, eids):
        group, member = source_group(code, family, name, eids)
        groups.append(group)
        canonical.append(member)

    add("CUT", "OUT", [f"E_{code}_OUT"])
    add("HOLE", "HOLE", [f"E_{code}_HOLE"])
    if slot:
        # Clockwise interior contour with two analytic negative semicircle bulges.
        entities.append({
            "entity_id": f"E_{code}_SLOT", "type": "LWPOLYLINE",
            "role": "slot", "closed": True,
            "vertices": [[12, 23, 0], [21, 23, -1], [21, 19, 0], [12, 19, -1]],
        })
        add("SLOT", "SLOT", [f"E_{code}_SLOT"])
    if bent:
        ents = []
        for k, x in (("A", 27), ("B", 29)):
            eid = f"E_{code}_BEND_{k}"
            entities.append({
                "entity_id": eid, "type": "LINE", "role": "bend",
                "linetype": "DASHED", "start": [x, 2], "end": [x, 28],
            })
            ents.append(eid)
        add("BEND", "BEND", ents)
    if relief:
        ids = [f"E_{code}_RELIEF_{i}" for i in range(3)]
        entities.extend([
            {"entity_id": ids[0], "type": "LINE", "role": "relief", "color": 3,
             "start": [30, 3], "end": [32, 3]},
            {"entity_id": ids[1], "type": "ARC", "role": "relief", "color": 3,
             "center": [32, 3.5], "radius": .5, "start_angle": 270, "end_angle": 0},
            {"entity_id": ids[2], "type": "LINE", "role": "relief", "color": 3,
             "start": [32.5, 3.5], "end": [33.5, 3.5]},
        ])
        add("RELIEF", "RELIEF", ids)
    return {
        "code": code, "material": "SS", "thickness_mm": 2,
        "status": "PASS", "checks": dict(CHECKS),
        "entities": entities, "source_groups": groups, "canonical_members": canonical,
    }


def review_part(code):
    p = part(code, bent=False, slot=False, relief=False)
    p.update(status="PREVIEW", preview_reason="numeric_only_known_topology",
             flags=["customer confirmation pending"])
    eid = f"E_{code}_FLAG"
    p["entities"].extend([
        {"entity_id": eid, "type": "CIRCLE", "role": "estimated",
         "color": 6, "center": [27, 20], "radius": 2.25},
        {"entity_id": f"E_{code}_FLAG_NOTE", "type": "TEXT", "role": "estimated_note",
         "color": 6, "text": "CHECK DIAMETER", "insert": [27, 25]},
    ])
    g, c = source_group(code, "HOLE", "PENDING", [eid],
                        state="FLAGGED", canon_state="PREVIEW")
    p["source_groups"].append(g)
    p["canonical_members"].append(c)
    return p


def job(parts):
    return {
        "canonical_contract": "TrainAiCad-CANONICAL-V4.31",
        "job_id": "TESTJOB", "parts": parts,
    }


def _xdata(ent):
    return [x.value for x in ent.get_xdata("TRAINAICAD") if x.code == 1000]


def test_pass_and_review_export_separation(tmp_path):
    a, b, r = part("A"), part("B", bent=False, slot=False, relief=False), review_part("REVIEW")
    src = job([a, r, b])
    assert validate_canonical_job(src)["contract"] == src["canonical_contract"]
    result = export_canonical_job(src, tmp_path, individual_dxf=True, write_manifest=True)
    assert result["filename"] == "TESTJOB_ALL_REVIEW_ONLY.dxf"
    assert not (tmp_path / "geometry_json").exists()
    assert not list((tmp_path / "parts_dxf").glob("*.json"))  # only the opt-in manifest may exist
    assert set(x.name for x in (tmp_path / "parts_dxf").glob("*.dxf")) == {"A.dxf", "B.dxf"}
    assert not (tmp_path / "TESTJOB_ALL.dxf").exists()
    assert (tmp_path / result["filename"]).is_file()
    assert result["artifacts"]["parts"][1]["cut_dxf"] is None
    assert result["artifacts"]["parts"][1]["cut_readback"] == "NOT_PRODUCTION"
    for cut in (tmp_path / "parts_dxf").glob("*.dxf"):
        d = ezdxf.readfile(cut)
        ents = list(d.modelspace())
        assert ents
        assert {e.dxftype() for e in ents} <= {"LINE", "ARC", "CIRCLE"}
        assert all(e.dxf.layer == "0" for e in ents)
        assert all(e.dxf.get("color", 256) != 6 for e in ents)
        assert all(any(v.startswith("SOURCE_ENTITY_ID=") for v in _xdata(e)) for e in ents)
    # Outline 4 lines, hole circle, slot 2 lines+2 arcs, relief 2 lines+1 arc.
    types = [e.dxftype() for e in ezdxf.readfile(tmp_path / "parts_dxf/A.dxf").modelspace()]
    assert types.count("LINE") == 8 and types.count("ARC") == 3 and types.count("CIRCLE") == 1
    assert len(types) == 12
    composite = ezdxf.readfile(tmp_path / result["filename"])
    # V4.35: the combined CUT file has no LWPOLYLINE; outlines are LINE/ARC pieces.
    composite_types = [e.dxftype() for e in composite.modelspace() if e.dxf.layer == "0"]
    assert "LWPOLYLINE" not in composite_types and "LINE" in composite_types
    assert any("NO CUT" in e.dxf.text for e in composite.modelspace() if e.dxftype() == "TEXT")


def test_all_pass_total_name_and_rebuild_without_json(tmp_path):
    src = job([part("A"), part("B", bent=False)])
    r1 = export_canonical_job(src, tmp_path, individual_dxf=True)
    assert r1["filename"] == "TESTJOB_ALL.dxf"
    assert not list(tmp_path.rglob("*.json"))
    assert all(p["cut_readback"] == "PASS" for p in r1["artifacts"]["parts"])
    r2 = export_canonical_job(src, tmp_path, individual_dxf=True)
    assert all(p["cut_readback"] == "PASS" for p in r2["artifacts"]["parts"])
    assert {p.name for p in (tmp_path / "parts_dxf").glob("*.dxf")} == {"A.dxf", "B.dxf"}
    assert not list((tmp_path / "parts_dxf").glob("*.pending"))


def test_status_downgrade_removes_stale_pass_cut(tmp_path):
    src = job([part("A"), part("B", bent=False)])
    export_canonical_job(src, tmp_path, individual_dxf=True)
    src["parts"][1] = review_part("B")
    result = export_canonical_job(src, tmp_path, individual_dxf=True)
    assert result["filename"] == "TESTJOB_ALL_REVIEW_ONLY.dxf"
    assert not (tmp_path / "parts_dxf/B.dxf").exists()
    assert (tmp_path / "parts_dxf/A.dxf").exists()
    assert not (tmp_path / "TESTJOB_ALL.dxf").exists()
    assert not (tmp_path / "geometry_json").exists()


@pytest.mark.parametrize("start,end,bulge", [
    ((0, 0), (10, 0), 1),
    ((0, 0), (10, 0), -1),
    ((0, 0), (10, 0), 0.5),
    ((0, 0), (10, 0), -2),
])
def test_bulge_arc_preserves_true_analytic_endpoints_and_sweep(start, end, bulge):
    center, radius, sa, ea = _arc_from_bulge(start, end, bulge)
    assert math.isclose((ea - sa) % 360, abs(math.degrees(4 * math.atan(bulge))), abs_tol=1e-6)
    def xy(angle):
        a = math.radians(angle)
        return center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)
    expect = (start, end) if bulge > 0 else (end, start)
    for actual, target in zip((xy(sa), xy(ea)), expect):
        assert math.dist(actual, target) < 1e-6


def test_unclassified_potential_cut_does_not_disappear_silently(tmp_path):
    src = job([part("A")])
    extra = {"entity_id": "E_A_STRANGE", "type": "LINE",
             "role": "unknown_cut_family", "start": [2, 2], "end": [3, 2]}
    src["parts"][0]["entities"].append(extra)
    g, c = source_group("A", "UNKNOWN", "STRANGE", [extra["entity_id"]])
    src["parts"][0]["source_groups"].append(g)
    src["parts"][0]["canonical_members"].append(c)
    with pytest.raises(CanonicalContractError, match="unclassified entity role"):
        export_canonical_job(src, tmp_path, individual_dxf=True)


def test_corrupt_pass_dxf_is_regenerated_after_read_back(tmp_path):
    src = job([part("A")])
    export_canonical_job(src, tmp_path, individual_dxf=True)
    cut = tmp_path / "parts_dxf/A.dxf"
    cut.write_bytes(b"definitely not a DXF")
    output = export_canonical_job(src, tmp_path, individual_dxf=True)
    assert output["artifacts"]["parts"][0]["cut_readback"] == "PASS"
    assert ezdxf.readfile(cut).audit().has_errors is False


def test_v431_multi_code_regression_keeps_every_proved_hole_and_bend_non_cut(tmp_path):
    """Existing approved source-member regression fixture, not a fresh PDF read."""
    import importlib.util
    module_path = ROOT / "regression/tools/check_521005_05_v431.py"
    spec = importlib.util.spec_from_file_location("v431_source_fixture", module_path)
    fixture = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(fixture)
    source = fixture.build_job()
    result = export_canonical_job(source, tmp_path, individual_dxf=True)
    assert result["status"] == "REVIEW_ONLY"
    assert result["filename"].endswith("_ALL_REVIEW_ONLY.dxf")
    assert not list(tmp_path.rglob("*.json"))
    assert {p.name for p in (tmp_path / "parts_dxf").glob("*.dxf")} == {
        "057862.dxf", "057873.dxf",
    }
    assert not (tmp_path / "parts_dxf/057864.dxf").exists()
    for code, hole_quantity in (("057862", 16), ("057873", 4)):
        d = ezdxf.readfile(tmp_path / "parts_dxf" / f"{code}.dxf")
        geometry = list(d.modelspace())
        assert all(e.dxftype() in {"LINE", "ARC", "CIRCLE"} for e in geometry)
        assert len([e for e in geometry if e.dxftype() == "CIRCLE"]) == hole_quantity
        assert not any(e.dxf.get("linetype", "") == "DASHED" for e in geometry)
    flagged = source["parts"][1]
    assert flagged["flags"] and flagged["status"] == "PREVIEW"


def test_cli_rejects_non_slip_codes_and_accepts_slip_work_numbers(tmp_path):
    from export_canonical_dxf import check_slip_codes
    check_slip_codes({"parts": [{"code": "26-056522"}, {"code": "27-1000001"}]})
    for bad in ("056522", "A", "26_056522", "26-05"):
        with pytest.raises(CanonicalContractError, match="SLIP_WORK_NO_FORMAT"):
            check_slip_codes({"parts": [{"code": bad}]})
    with pytest.raises(CanonicalContractError, match="SLIP_WORK_NO_FORMAT"):
        export_canonical_job(job([part("A")]), tmp_path, require_slip_codes=True)
    assert not list(tmp_path.glob("*.dxf"))


def test_individual_dxf_is_named_by_slip_work_number(tmp_path):
    src = job([part("26-056522", relief=False)])
    result = export_canonical_job(src, tmp_path, individual_dxf=True, require_slip_codes=True)
    assert (tmp_path / "parts_dxf/26-056522.dxf").is_file()
    assert result["artifacts"]["parts"][0]["cut_dxf"] == "parts_dxf/26-056522.dxf"
    assert not list(tmp_path.rglob("*.json"))


def test_default_output_is_combined_dxf_only(tmp_path):
    src = job([part("A"), part("B", bent=False)])
    result = export_canonical_job(src, tmp_path)
    assert result["filename"] == "TESTJOB_ALL.dxf"
    assert (tmp_path / "TESTJOB_ALL.dxf").is_file()
    assert not (tmp_path / "parts_dxf").exists()
    assert all(p["cut_dxf"] is None and p["cut_readback"] == "COMPOSITE_ONLY"
               for p in result["artifacts"]["parts"])
    assert not list(tmp_path.rglob("*.json"))
    export_canonical_job(src, tmp_path, individual_dxf=True)  # explicit request only
    assert {p.name for p in (tmp_path / "parts_dxf").glob("*.dxf")} == {"A.dxf", "B.dxf"}
