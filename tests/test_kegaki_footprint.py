"""KEGAKI contact-footprint rules derived from PDF dimensions (job 521021-03).

Numbers come from the source views of 521021-03; the DXF sample only served to
audit them. Geometry here is synthetic/derived, not a digitisation of the sample.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from canonical_contract import CanonicalContractError, validate_canonical_job
from kegaki_footprint import (contact_length, contact_width, single_line_offset,
                              slanted_edge_length, union_boundary_segments)
from test_weld_kegaki_guard import fixture_job, part_of


def segs(items):
    return sorted(tuple(sorted(((round(a, 3), round(b, 3)), (round(c, 3), round(d, 3)))))
                  for (a, b), (c, d) in items)


def test_062020_slanted_end_footprint_is_hypot_and_open_to_the_contour():
    width = contact_width(6, slant_delta=3.5)           # 117 vs 113.5
    assert width == pytest.approx(6.946, abs=1e-3)
    length = contact_length(35, 5)                       # 35 - 5
    assert length == 30
    got = union_boundary_segments([(0, 5.5, length, 5.5 + width)], [((0, 0), (0, 35))])
    assert segs(got) == segs([((0, 5.5), (30, 5.5)), ((0, 5.5 + width), (30, 5.5 + width)),
                              ((30, 5.5), (30, 5.5 + width))])   # left side NOT drawn
    assert len(got) == 3


def test_062023_tilted_child_width_and_slanted_contact_length():
    assert contact_width(6, tilt_deg=12) == pytest.approx(6.14, abs=0.01)
    slant = slanted_edge_length(20, 95.7, 90.3)          # shorter alternates only
    assert slant == pytest.approx(20.716, abs=1e-3)
    assert contact_length(slant, 5) == pytest.approx(15.716, abs=1e-3)   # 15.72


def test_062113_and_062024_single_line_offset_is_host_thickness_minus_k():
    assert single_line_offset(6, 4) == 2
    assert single_line_offset(6, 2) == 4
    with pytest.raises(ValueError):
        single_line_offset(6, 6)


def test_062027_tube_and_ribs_are_one_union_outline_of_ten_lines():
    plate = [((0, 0), (75, 0)), ((75, 0), (75, 100)), ((75, 100), (0, 100)), ((0, 100), (0, 0))]
    got = union_boundary_segments(
        [(12.5, 25, 62.5, 75), (37.5, 75, 43.5, 100), (37.5, 0, 43.5, 25)], plate)
    assert len(got) == 10
    assert segs(got) == segs([
        ((12.5, 25), (37.5, 25)), ((43.5, 25), (62.5, 25)), ((62.5, 25), (62.5, 75)),
        ((62.5, 75), (43.5, 75)), ((37.5, 75), (12.5, 75)), ((12.5, 75), (12.5, 25)),
        ((43.5, 75), (43.5, 100)), ((37.5, 100), (37.5, 75)),
        ((43.5, 0), (43.5, 25)), ((37.5, 25), (37.5, 0))])


def test_kegaki_overlapping_rectangles_are_blocked_by_the_guard():
    job = fixture_job()
    part = part_of(job)
    part["entities"].append({"entity_id": "E_MARK_C", "type": "LINE", "role": "kegaki",
                             "color": 1, "start": [10, 5], "end": [15, 5]})
    part["canonical_members"][1]["entity_ids"].append("E_MARK_C")
    with pytest.raises(CanonicalContractError, match="KEGAKI_DUPLICATE_SEGMENT"):
        validate_canonical_job(job)


def test_kegaki_line_on_the_part_contour_is_blocked_by_the_guard():
    job = fixture_job()
    part = part_of(job)
    part["entities"][2]["start"], part["entities"][2]["end"] = [0, 5], [0, 12]   # on x=0 edge
    with pytest.raises(CanonicalContractError, match="KEGAKI_ON_CONTOUR"):
        validate_canonical_job(job)


def test_062019_no_mark_part_must_name_laser_partners_in_chain_census():
    job = fixture_job(code="062019")
    part = part_of(job)
    part["source_weld_site_ids"] = []
    census = part["weld_site_census"]
    census["sites"] = []
    census["no_weld_evidence"] = "Assembly inspected: A end lands on B face; KEGAKI is on host B, none on A"
    census["assembly_laser_partner_codes"] = ["062020"]
    with pytest.raises(CanonicalContractError, match="CHAIN_CENSUS_EMPTY"):
        validate_canonical_job(job)                      # partner not named
    census["no_weld_evidence"] += " (062020 is the host)"
    assert validate_canonical_job(job)["parts"][0]["weld_kegaki_closure"]["required_site_ids"] == []
    census.pop("assembly_laser_partner_codes")
    with pytest.raises(CanonicalContractError, match="CHAIN_CENSUS_EMPTY"):
        validate_canonical_job(job)                      # silent empty census blocked
