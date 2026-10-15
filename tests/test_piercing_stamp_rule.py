from pathlib import Path


def test_green_piercing_requires_english_through_hole_stamp():
    text = (Path(__file__).resolve().parents[1] / "skills/lispcad/features/HOLES_TAPS.md").read_text(encoding="utf-8")
    rule = next(line for line in text.splitlines() if line.startswith("1. PIERCING +"))
    assert "English `THROUGH HOLE` stamp on the same hole family" in rule
    assert "color 3 (Green)" in rule
    assert "Japanese `通シ`/`貫通` does not qualify" in rule
    assert "PIERCING alone stays ByLayer" in rule
