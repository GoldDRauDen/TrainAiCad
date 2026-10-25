"""Customer corner / hole policies (data/customers.yaml) applied by the tools, not by memory.

User-confirmed 2026-10-25: KH768/KH859 keep uncalled OUTER convex corners sharp (no Laser R);
drawn R/C is still drawn; KH859 t>=19 corners and holes < t/2 need customer confirmation (FLAG).
"""
import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import lookup  # noqa: E402

SPEC = yaml.safe_load((ROOT / "examples/flat_minimal.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("customer,t,expected", [
    (None, 4.5, "R0.5"), ("768", 4.5, "NONE"), ("859", 9, "NONE"), ("325", 2, "NONE"),
    ("765", 2, "R3"), ("775", 3.2, "R0.3"), ("775", 6, "NONE"), ("712", 6, "C5"), ("999", 4.5, "R0.5"),
])
def test_laser_r_applies_the_customer_corner_rule(customer, t, expected):
    res = lookup.laser_r("SS400", t, customer)
    assert res["status"] == "OK" and res["laser_r"] == expected


@pytest.mark.parametrize("customer,t,reason", [("859", 19, "CUSTOMER_CORNER_CONFIRM"), ("775", 4.8, "CUSTOMER_CORNER_GAP")])
def test_customer_corner_confirmation_is_a_flag(customer, t, reason):
    res = lookup.laser_r("SS400", t, customer)
    assert res["status"] == "FLAG" and res["reason"] == reason and res["flag_vi"].startswith("KH")


def test_kh859_hole_below_half_t_needs_confirmation():
    assert lookup.hole("SS400", 6, 2)["entity"] == "POINT"
    res = lookup.hole("SS400", 6, 2, customer="859")
    assert res["status"] == "FLAG" and res["action"] == "MAGENTA_CIRCLE"
    assert lookup.hole("SS400", 6, 2, piercing=True, customer="859")["entity"] == "POINT"
    assert lookup.hole("SS400", 6, 4, customer="859")["entity"] == "CIRCLE"


def _part(spec, customer, t=None):
    ps = copy.deepcopy(spec["parts"][0])
    ps["material"] = "SS400"
    if t is not None:
        ps["t"] = t
        ps.pop("holes", None), ps.pop("slots", None)  # thick plate: Ø6.6 / slot 8 would become POINTs
    return bc.build_part(ps, customer)


def _decisions(part):
    return [c["decision"] for c in part["corner_inventory"]]


def test_flat_builder_keeps_outer_corners_sharp_for_kh768_but_draws_called_rc():
    general = _part(SPEC, None)
    kh768 = _part(SPEC, "768")
    assert "AUTO_R" in _decisions(general)
    assert "AUTO_R" not in _decisions(kh768) and "SHARP" in _decisions(kh768)
    assert _decisions(kh768).count("CALLED") == _decisions(general).count("CALLED")
    sharp = [c for c in kh768["corner_inventory"] if c["decision"] == "SHARP"]
    assert all("KH768" in c["no_auto_r_reason"] for c in sharp)
    assert kh768["status"] == "PASS"


def test_flat_builder_flags_kh859_thick_plate_corners_once():
    part = _part(SPEC, "859", t=19)
    assert part["status"] == "PREVIEW"
    assert "AUTO_R" not in _decisions(part) and "FLAG" in _decisions(part)
    assert sum("KH859" in f for f in part["flags"]) == 1


def test_flat_builder_uses_customer_chamfer_for_kh712():
    part = _part(SPEC, "712", t=6)
    members = [m for m in part["canonical_members"] if m.get("controlling_rule") == "MATERIAL_AUTO_R"]
    assert members and all(m["laser_r"] == "C5" and m["customer_rule"] == "KH712" for m in members)


def test_job_level_customer_reaches_every_part():
    spec = copy.deepcopy(SPEC)
    spec["customer_code"] = "768"
    job = bc.build_job(spec)
    assert all(p["laser_r_lookup"]["rule"] == "KH768" for p in job["parts"])
