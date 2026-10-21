"""Rule-load budget and anti-supplement guard (approved 2026-10-15).

Purpose: a new lesson must EDIT the existing rule in place (or move evidence to
regression/), never append another dated/versioned supplement. Raising a budget
or the heading allowlist needs explicit user approval (DUYET).
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from benchmark_rule_routes import benchmark  # noqa: E402

# exact UTF-8 bytes of the unique rule files a job loads (all stages L0-L3)
SCENARIO_BUDGET = {  # tightened 2026-10-21 after JOB_CARD/lookup slimming
    "flat": (80_000, 150_000),
    "flat_tap": (80_000, 172_000),
    "bend_nobi": (80_000, 245_000),
    "data_holes": (95_000, 182_000),
    "unknown_complex": (110_000, 333_000),
}
FILE_BUDGET = {
    "JOB_CARD.md": 6_000,
    "AI_ENTRYPOINT.md": 9_000,
    "skills/lispcad/core/DRAWING_READING.md": 6_000,
    "skills/lispcad/core/VALIDATION.md": 13_800,
    "skills/lispcad/core/CAD_OUTPUT.md": 13_000,
    "skills/lispcad/core/DATUM_DIMENSION.md": 16_500,
    "references/MATERIAL_RULES.md": 9_000,
}
VERSIONED_HEADING = re.compile(r"^#{1,4} .*(?:V4\.\d+|20\d\d-\d\d-\d\d)", re.M)


def test_scenario_load_budget():
    for case in benchmark()["cases"]:
        first, full = SCENARIO_BUDGET[case["scenario"]]
        assert case["first_two_stages_bytes"] <= first, (case["scenario"], "L0+L1", case["first_two_stages_bytes"])
        assert case["all_stages_unique_bytes"] <= full, (case["scenario"], "all stages", case["all_stages_unique_bytes"])


def test_core_file_budget():
    for rel, cap in FILE_BUDGET.items():
        size = (ROOT / rel).stat().st_size
        assert size <= cap, f"{rel} is {size} bytes (> {cap}): tighten an existing rule or move evidence to regression/"


def _routed_files():
    router = yaml.safe_load((ROOT / "skills/lispcad/router/ROUTER.yaml").read_text(encoding="utf-8"))
    files = set(router["default_load"]) | {e["path"] for e in router["conditional_default_load"]}
    for group in ("stage_routes", "source_routes", "mode_routes", "feature_routes", "customer_routes"):
        for route in router[group].values():
            files |= set(route["load"])
    return sorted(files | {"AI_ENTRYPOINT.md"})


def test_no_new_versioned_or_dated_supplement_headings_in_routed_files():
    allow = json.loads((ROOT / "tests/rule_heading_allowlist.json").read_text(encoding="utf-8"))
    for rel in _routed_files():
        text = (ROOT / rel).read_text(encoding="utf-8")
        found = VERSIONED_HEADING.findall(text)
        extra = [h for h in found if h not in allow.get(rel, [])]
        assert not extra, (
            f"{rel}: new versioned/dated heading(s) {extra}. Edit the existing rule in place; "
            "put evidence in regression/qa and history in docs/RULE_HISTORY.md (docs/RULE_LESSON_INTAKE.md)."
        )
