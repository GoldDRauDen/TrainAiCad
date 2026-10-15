"""V4.21 customer DATA geometry-preservation hard gate."""
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "tools"))
from snapshot_manifest import Snapshot  # noqa: E402
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CURRENT=Snapshot("skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md")
RELEASE=Snapshot("skills/lispcad/versions/V4.21/SKILL_LISPCAD_V4_21_PORTABLE.md")
BASE=Snapshot("skills/lispcad/versions/V4.20/SKILL_LISPCAD_V4_20_PORTABLE.md")

def test_v421_historical_release_and_inheritance():
    entry=((ROOT/"AI_ENTRYPOINT.md").read_text(encoding="utf-8") + (ROOT/"docs/RELEASE_WIRING_INDEX.md").read_text(encoding="utf-8"))
    skill=CURRENT.read_text(encoding="utf-8")
    release=RELEASE.read_text(encoding="utf-8")
    assert release.startswith("# SKILL_LISPCAD V4.21 PORTABLE")
    assert skill.startswith("# SKILL_LISPCAD V4.24 PORTABLE")
    assert "V4.21 direct approval / PUSH" in skill
    assert "- **V4.21:**" in entry
    assert BASE.read_text(encoding="utf-8").startswith("# SKILL_LISPCAD V4.20 PORTABLE")
    for token in [
        "DATA_RAW_TO_MANUFACTURING_CONTRACT.md",
        "520930-03_V4_21_APPROVED.md",
        "DATA_REQUIRED_MISSING",
        "source reprojection",
    ]:
        assert token in (entry + "\n" + skill)

def test_v421_source_classification_hard_gate():
    s=((ROOT/"references/SOURCE_DATA_CLASSIFICATION.md").read_text(encoding="utf-8") + (ROOT/"references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md").read_text(encoding="utf-8")).lower()
    for token in [
        "complete harvest/classification",
        "do not redraw",
        "data_required_missing",
        "646",
        "not a redraw tolerance",
    ]:
        assert token in s

def test_v421_reference_and_regression_present():
    ref=(ROOT/"references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md").read_text(encoding="utf-8")
    qa=(ROOT/"regression/qa/520930-03_V4_21_APPROVED.md").read_text(encoding="utf-8")
    assert "every `PDF_DATA_RAW` job" in ref
    assert "geometry/provenance authority" in ref
    assert "057088 DATA page scale 1:2" in qa
    assert "Same bbox with source-derived internal drift is still FAIL" in qa
