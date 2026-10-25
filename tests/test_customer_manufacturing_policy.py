"""Approved 2026-10-12 manufacturing and numeric customer-code routing."""
from pathlib import Path
import sys
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from resolve_rules import resolve_rules, ResolutionError  # noqa: E402

ROUTER = yaml.safe_load((ROOT / "rules/ROUTER.yaml").read_text(encoding="utf-8"))
CATALOG = yaml.safe_load((ROOT / "data/customers.yaml").read_text(encoding="utf-8"))


def census(customer=None, mode="FLAT_NO_BEND"):
    return {
        "customer_code": customer,
        "source_mode": "PDF_ONLY",
        "part_mode": mode,
        "reference_present": "NO",
        "features": {k: {"state": "NO"} for k in ROUTER["feature_routes"]},
    }


def test_missing_customer_code_uses_general_rules_without_review():
    data = resolve_rules(census())
    assert data["customer_code"] is None and data["customer_rules"] == {}


@pytest.mark.parametrize("bad", [True, "646A", "アイコクアルファ", -646, "829.0"])
def test_name_and_invalid_ids_are_not_auto_inferred(bad):
    with pytest.raises(ResolutionError, match="customer_code"):
        resolve_rules(census(bad))


def test_data_authority_override_is_explicit_and_hole_qa_is_retained():
    assert resolve_rules(census(829))["customer_rules"]["data_pdf_policy"] == "DATA_NO_DIM_COMPARE"
    assert resolve_rules(census(240))["customer_rules"]["data_pdf_policy"] == "DATA_NO_DIM_COMPARE"
    assert resolve_rules(census(395))["customer_rules"]["data_pdf_policy"] == "PDF_PRIORITY"


def test_catalog_has_no_management_or_contact_fields():
    assert CATALOG["scope"] == "CAD_ONLY"
    assert len(CATALOG["customers"]) >= 20
    for code, record in CATALOG["customers"].items():
        assert re.fullmatch(r"[0-9]+", code)
        assert set(record) <= {"source", "notes", "data_pdf_policy", "nobi_profile", "corner_policy", "hole_policy"}
        assert not any(k in record for k in ("name", "phone", "email", "staff", "contact"))

def test_customer_technical_note_census_partitions_all_codes():
    census = CATALOG["customer_note_census"]
    included = set(CATALOG["customers"])
    excluded = set(census["excluded_non_cad_codes"])
    obsolete = set(census["fully_obsolete_codes"])
    assert len(included) == 90
    assert len(excluded) == 16
    assert obsolete == {"880"}
    assert included.isdisjoint(excluded | obsolete)
    assert excluded.isdisjoint(obsolete)
    assert len(included | excluded | obsolete) == census["source_note_bearing_codes"] == 107
    assert census["active_note_bearing_codes"] == 106
    assert CATALOG["source_workbook_sha256"] == "67851a40fc2fdde09f3ba0692cece5054ca9759d074134d8e16a1774cf7bbddb"
    assert "891" in included and "610" in included and "621" in included
    assert "old" in " ".join(CATALOG["customers"]["891"]["notes"]).lower() or "obsolete" in " ".join(CATALOG["customers"]["891"]["notes"]).lower()
    assert "OBSOLETE" in " ".join(CATALOG["customers"]["610"]["notes"])
    assert "OBSOLETE" in " ".join(CATALOG["customers"]["621"]["notes"])



def test_646_customer_record_selects_its_own_nobi_profile():
    x = census(646, "BEND")
    result = resolve_rules(x)
    assert result["customer_code"] == "646"
    assert result["customer_rules"]["nobi_profile"] == "AIKOKU_646"
    assert resolve_rules(census(829, "BEND"))["customer_rules"].get("nobi_profile") is None
