"""tools/lookup.py reproduces every approved table regression (2026-10-21).

The tables live in their owning Markdown files; these tests prove the parser
reads them correctly and encodes the approved decisions:
- Nobi: handwritten > table; non-90° without handwritten, no J, t not
  tabulated, L out of range or 'Confirm' cell -> SPLIT_FLANGE_10MM + FLAG.
- SUS uses 2B by default, #1 only when the source states #1.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lookup  # noqa: E402


@pytest.mark.parametrize("material,t,L,expected", [
    ("SPCC", 1.6, 900, 2.64),
    ("SS400", 3.0, 1500, 5.28),
    ("SS400", 4.5, 2000, 8.48),
    ("SUS430", 6.0, 800, 10.22),           # L09: SUS430 uses SS/SUS430/BRASS Nobi
    ("真ちゅう", 1.0, 500, 1.90),             # brass shares table 1
    ("A5052", 4.0, 1800, 6.84),
    ("銅", 3.0, 1000, 5.10),
])
def test_nobi_table_values(material, t, L, expected):
    res = lookup.nobi(material, t, L)
    assert res["status"] == "OK" and res["nobi"] == expected and res["source"] == "TABLE"


def test_sus_default_2b_and_explicit_no1():
    assert lookup.nobi("SUS304", 3.0, 2000)["nobi"] == 7.84          # approved 2026-10-12 recalibration
    assert lookup.nobi("SUS304", 3.0, 2000)["surface_default"] is True
    assert lookup.nobi("SUS304", 3.0, 2000, surface="#1")["nobi"] == 7.80
    # #1 > 2B rows are genuine (different SUS finish), not swapped columns
    assert lookup.nobi("SUS304", 4.0, 1200, surface="#1")["nobi"] == 8.90


def test_open_bracket_follows_previous_row():
    # '~ 550' then '~ 750' means (550, 750]
    assert lookup.nobi("SUS304", 5.0, 500)["v_die"] == "V25"
    assert lookup.nobi("SUS304", 5.0, 600)["v_die"] == "V32"
    assert lookup.nobi("A5052", 3.0, 1500)["nobi"] == 4.78


@pytest.mark.parametrize("kwargs,reason", [
    ({"material": "SPCC", "t": 2.5, "L": 500}, "THICKNESS_NOT_TABULATED"),
    ({"material": "SPCC", "t": 3.0, "L": 2600}, "BEND_LENGTH_OUT_OF_TABLE"),
    ({"material": "A5052", "t": 3.0, "L": 2000}, "TABLE_CELL_CONFIRM"),
    ({"material": "SPCC", "t": 1.6, "L": 900, "angle": 135}, "NON_90_NO_HANDWRITTEN_NOBI"),
    ({"material": "SPCC", "t": 1.6, "L": 900, "j_symbol": False}, "NO_J_NO_HANDWRITTEN_NOBI"),
    ({"material": "SUS304", "t": 2.3, "L": 500, "customer_code": "646"}, "KH646_NO_MATCH"),
])
def test_missing_nobi_splits_flange_10mm_with_vietnamese_flag(kwargs, reason):
    res = lookup.nobi(**kwargs)
    assert res["status"] == "FLAG" and res["reason"] == reason
    assert res["action"] == lookup.SPLIT_FLANGE
    assert "tách bích cách 10 mm" in res["flag_vi"]


def test_handwritten_nobi_wins_even_for_non_90():
    res = lookup.nobi("SPCC", 0.8, 300, angle=147, handwritten=0.36)
    assert res["status"] == "OK" and res["nobi"] == 0.36 and res["source"] == "HANDWRITTEN"


def test_kh646_only_for_numeric_646():
    assert lookup.nobi("SPCC", 4.5, 900, customer_code="646")["nobi"] == 7.84
    assert lookup.nobi("SPCC", 4.5, 900)["nobi"] == 7.76
    assert lookup.nobi("SUS304", 5.0, 700, customer_code="646")["nobi"] == 9.58
    assert lookup.nobi("SUS304", 5.0, 900, customer_code="646")["nobi"] == 10.20


@pytest.mark.parametrize("material,t,r", [
    ("SS400", 9, "R2"), ("SPCC", 3.2, "R0.5"), ("SS400", 3.5, "R0.5"), ("SS400", 12, "NONE"),
    ("SS400", 19, "R3"), ("SS400", 25, "R3"), ("SUS430", 6, "R0.5"), ("SUS304", 8, "NONE"),
    ("A5052", 5, "R0.5"), ("A5052", 7, "NONE"),
    ("真ちゅう", 5.5, "R0.5"), ("真ちゅう", 6, "R0.5"), ("真ちゅう", 7, "NONE"),
])
def test_laser_r(material, t, r):
    assert lookup.laser_r(material, t)["laser_r"] == r


def test_ss_t19_r3_scope_is_outer_perimeter_only():
    assert "never holes/slots" in lookup.laser_r("SS400", 19)["corner_class"]


@pytest.mark.parametrize("material,t,dia,piercing,through,entity,color", [
    ("SS400", 9, 3.3, False, False, "POINT", "BYLAYER"),     # M4 pilot
    ("SS400", 9, 4.2, False, False, "POINT", "BYLAYER"),     # M5 pilot
    ("SS400", 9, 5.0, False, False, "CIRCLE", "BYLAYER"),    # M6 pilot
    ("SUS304", 15, 9.0, False, False, "POINT", "BYLAYER"),   # SUS t15-16 min Ø10
    ("A5052", 5, 3.0, False, False, "POINT", "BYLAYER"),     # AL min 0.8t, not < t/2
    ("SUS430", 6, 2.9, False, False, "POINT", "BYLAYER"),    # inherited t/2
    ("SS400", 3, 10, True, False, "POINT", "BYLAYER"),
    ("SS400", 3, 10, True, True, "POINT", 3),
])
def test_hole_point_or_circle(material, t, dia, piercing, through, entity, color):
    res = lookup.hole(material, t, dia, piercing, through)
    assert (res["entity"], res["color"]) == (entity, color)


@pytest.mark.parametrize("thread,dia,table", [
    ("M4", 3.3, "COARSE"), ("M6", 5.0, "COARSE"), ("M12", 10.3, "COARSE"), ("M8x1.25", 6.8, "COARSE"),
    ("M8x1", 7.0, "FINE"), ("M12×1.25", 10.8, "FINE"), ("M38x1.5", 36.6, "FINE"),
])
def test_thread_pilot(thread, dia, table):
    res = lookup.pilot(thread)
    assert res["pilot_dia"] == dia and res["table"] == table


def test_idod_rounds_offset_first_and_routes_acute():
    assert lookup.idod(3.0, 165)["offset"] == 0.39
    assert lookup.idod(3.0, 135)["offset"] == 1.24
    assert lookup.idod(2.0, 85)["action"] == "USE_ACUTE_BEND_LT85"


def test_unfold_062103():
    res = lookup.unfold([410.8, 20.8, 175.0], [1.68, 0.36])
    assert res["flat_length"] == 604.56
    assert (res["bend_lines"][0]["line1"], res["bend_lines"][0]["line2"]) == (409.12, 410.8)
    assert (res["bend_lines"][1]["line1"], res["bend_lines"][1]["line2"]) == (429.56, 429.92)


def test_cli_emits_json():
    out = subprocess.run([sys.executable, str(ROOT / "tools/lookup.py"), "nobi", "--material", "SPCC",
                          "--t", "2.5", "--L", "500"], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    assert data["status"] == "FLAG" and data["action"] == "SPLIT_FLANGE_10MM"


def test_countersink_through_hole_is_the_only_cut():
    res = lookup.countersink("M6")
    assert (res["through_hole"], res["counterbore"], res["countersink_mouth"]) == (6.6, 11.0, 12.5)
    assert lookup.countersink("M10")["status"] == "FLAG"


def test_tooling_lists_dies_for_the_material_family():
    dies = {d["v_die"]: d for d in lookup.tooling("SUS304", 3)["dies"]}
    assert dies["V40"]["L_min"] == 28.4 and dies["V40"]["Z_min"] == 29.6
    assert lookup.tooling("SPCC", 12)["dies"] == [{"v_die": "V80", "L_min": 57.0, "Z_min": None}]


@pytest.mark.parametrize("S,decision,depth", [(-2, "SLIT", 2.2), (0, "SLIT", 2.2), (1, "NO_SLIT", None),
                                              (1.5, "NO_SLIT", None), (2, "NO_SLIT", None)])
def test_slit_matrix_t2(S, decision, depth):
    res = lookup.slit("SPCC", 2, S)
    assert res["decision"] == decision and res.get("depth_from_actual_edge") == depth
    if S == -2:
        assert res["depth_from_reference"] == 4.2


def test_slit_over_90_and_unproved_step():
    assert lookup.slit("SUS304", 3.2, angle=130)["depth"] == 2.4513
    assert lookup.slit("SPCC", 2)["status"] == "FLAG"


def test_retreat_and_kegaki_wrappers():
    assert lookup.retreat(20, 30)["retreat"] == "A"
    assert lookup.kegaki(6, slant_delta=3.5)["width"] == pytest.approx(6.946, abs=1e-3)
    assert lookup.kegaki(6, tilt=12)["width"] == pytest.approx(6.134, abs=1e-3)
    assert lookup.kegaki(6, edge=35, offset=5)["contact_length"] == 30
    assert lookup.kegaki(6, host_t=6, k=4)["single_line_offset"] == 2
