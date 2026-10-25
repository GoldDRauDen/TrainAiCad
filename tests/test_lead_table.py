"""Lead value (vòi dẫn) from workbook column G via data/lead_table.yaml (user-approved 2026-10-21)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from slit_geometry import LeadValueUnproved, connected_slit, lead_end_by_offset, lead_val  # noqa: E402


@pytest.mark.parametrize("material,t,expected", [
    ("SS400", 1.2, 3), ("SS400", 3.2, 3), ("SS400", 4, 6), ("SS400", 5, 6),       # 055958: t5 -> 6
    ("SS400", 6, 6), ("SS400", 9, 6), ("SS400", 10, 10), ("SS400", 12, 10), ("SS400", 16, 10),
    ("SUS304-2B", 1.5, 6), ("SUS304-2B", 5, 6), ("SUS304-2B", 8, 6), ("SUS304-2B", 9, 10),
    ("SUS304-2B", 14, 10), ("SUS304-2B", 16, 10),
    ("A5052", 0.5, 6), ("A5052", 6, 6), ("A5052", 8, 6), ("A5052", 9, 10), ("A5052", 16, 10), ("A5052", 18, 10),
    ("銅", 5, 6), ("銅", 5.5, 6), ("銅", 6, 6),                                    # 5<t<6 uses the t6 row (L10)
    ("チタン", 5, 6), ("チタン", 10, 10),                                           # 他 uses the SUS/他 rows
])
def test_column_g_values(material, t, expected):
    assert lead_val(material, t) == expected


@pytest.mark.parametrize("material,t", [
    ("SS400", 19), ("SS400", 25), ("SUS304-2B", 19), ("SUS304-2B", 20), ("A5052", 19),   # hook rows -> FLAG
    ("SS400", 3.5), ("SS400", 14), ("SS400", 17), ("SS400", 5.5), ("SS400", 9.5),         # gaps between rows -> FLAG
    ("SUS304-2B", 5.5), ("SUS304-2B", 13), ("SUS304-2B", 17), ("A5052", 6.5),
    ("銅", 6.5), ("銅", 8),                                                                 # no Cu/Brass row above t6
])
def test_hook_rows_and_gaps_are_flagged_not_guessed(material, t):
    with pytest.raises(LeadValueUnproved, match="LEAD_VALUE_UNPROVED"):
        lead_val(material, t)


def test_unknown_material_is_flagged():
    with pytest.raises(LeadValueUnproved, match="LEAD_VALUE_UNPROVED:MATERIAL"):
        lead_val("XYZ-UNKNOWN", 2.0)


def test_055958_slit_reproduces_user_dxf():
    """User reference DXF: B=(204.208,565), S=(1,0), lead 6 (t5), slit 5.2, R0.5."""
    lead = lead_val("SS400", 5.0)
    p = lead_end_by_offset((204.208, 565.0), (-1.0, 0.0), (0.0, 1.0), lead)
    assert p == pytest.approx((198.208, 571.0))
    slit = connected_slit((204.208, 565.0), (1.0, 0.0), (p[0] - 204.208, p[1] - 565.0), 5.0 + 0.2)
    assert slit["line1"][0] == pytest.approx((209.408, 565.0))
    assert slit["line1"][1] == pytest.approx((204.415, 565.0), abs=1e-3)
    assert slit["arc"]["center"] == pytest.approx((204.415, 565.5), abs=1e-3)
    assert slit["arc"]["start_angle"] == pytest.approx(225.0) and slit["arc"]["end_angle"] == pytest.approx(270.0)
    assert slit["line2"][0] == pytest.approx((204.062, 565.146), abs=1e-3)
    assert slit["line2"][1] == pytest.approx((198.208, 571.0))
