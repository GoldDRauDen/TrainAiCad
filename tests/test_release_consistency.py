from tools.compact_rules import read_rule_text
"""Release and output-contract consistency between entrypoints, Router and CAD_OUTPUT."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _text(rel):
    return read_rule_text(rel, ROOT)


def test_entrypoint_release_matches_router_and_coverage():
    entry = _text("AI_ENTRYPOINT.md")
    router = yaml.safe_load(_text("skills/lispcad/router/ROUTER.yaml"))
    coverage = yaml.safe_load(_text("skills/lispcad/router/RULE_COVERAGE.yaml"))
    release = router["release"]
    assert f"Current production release is **{release}**." in entry
    assert coverage["release"] == release
    assert release in coverage["release_coverage"]


def test_latest_release_block_is_first_in_coverage():
    coverage = yaml.safe_load(_text("skills/lispcad/router/RULE_COVERAGE.yaml"))
    assert next(iter(coverage["release_coverage"])) == coverage["release"]


def test_geometry_json_scope_is_every_code_everywhere():
    for rel in ("AI_ENTRYPOINT.md", "SKILL.md", "skills/lispcad/core/CAD_OUTPUT.md"):
        text = _text(rel)
        assert "PASS/PREVIEW/VIEWS_ONLY code" not in text, rel
    assert "every code, including REVIEW/FLAG" in _text("AI_ENTRYPOINT.md")
    assert "every code, including REVIEW/FLAG" in _text("SKILL.md")


def test_new_jobs_use_v434_schema_not_v431_only():
    entry = _text("AI_ENTRYPOINT.md")
    assert "continue using `TrainAiCad-CANONICAL-V4.31`" not in entry
    assert "V4.32 still builds the V4.31 canonical contract" not in entry
    assert "TrainAiCad-CANONICAL-V4.34" in entry


def test_release_wiring_index_lives_in_docs_and_covers_latest():
    index = _text("docs/RELEASE_WIRING_INDEX.md")
    assert "- **V4.34:**" in index and "- **V4.33:**" in index
    assert "## 7. Release wiring index" not in _text("AI_ENTRYPOINT.md") or \
        "Moved to `docs/RELEASE_WIRING_INDEX.md`" in _text("AI_ENTRYPOINT.md")
    assert not re.search(r"^- \*\*V4\.\d+:\*\*", _text("AI_ENTRYPOINT.md"), re.M)


def test_census_extra_fields_do_not_pollute_feature_keys():
    text = _text("skills/lispcad/router/FEATURE_CENSUS.md")
    block = re.search(r"```yaml\nsource_manufacturing_notes:.*?\n```", text, re.S)
    assert block is None or "hairline_HL" not in block.group(0)
    assert "hairline_HL" in text and "grain_vector_part_relative" in text
