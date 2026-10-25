"""Rule-card contract: routed, small, every path real, every lesson pointed to.

Raising a budget needs explicit user approval (DUYỆT). A new lesson edits its one owning card
in place and adds a line to that card's Lessons; history lives in git.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from benchmark_rule_routes import benchmark  # noqa: E402

RULES = ROOT / "rules"
CARDS = sorted(RULES.glob("*.md"))
ROUTER = yaml.safe_load((RULES / "ROUTER.yaml").read_text(encoding="utf-8"))
NOT_ROUTED = {"QA_REVERSE.md"}  # explicit QA role only, never part of E2E
ENTRY = [ROOT / "JOB_CARD.md", ROOT / "CLAUDE.md", ROOT / "README.md"]

CARD_BUDGET = 9_500       # bytes per card
ENTRY_BUDGET = {"JOB_CARD.md": 6_000, "CLAUDE.md": 4_000}
SCENARIO_BUDGET = {       # (L0+L1, all stages) bytes; measured V5.0: 13.8k/32k .. 22k/66k
    "flat": (16_000, 37_000),
    "flat_tap": (16_000, 41_000),
    "bend_nobi": (16_000, 57_000),
    "data_holes": (20_000, 45_000),
    "unknown_complex": (26_000, 75_000),
}


def _routed():
    paths = set(ROUTER["default_load"]) | {e["path"] for e in ROUTER["conditional_default_load"]}
    for group in ("stage_routes", "source_routes", "mode_routes", "feature_routes"):
        for route in ROUTER[group].values():
            paths |= set(route["load"])
    return paths


def test_every_card_is_routed_and_every_route_exists():
    routed = _routed()
    for rel in routed:
        assert (ROOT / rel).is_file(), rel
    cards = {f"rules/{p.name}" for p in CARDS}
    assert cards - routed == {f"rules/{n}" for n in NOT_ROUTED}


@pytest.mark.parametrize("card", CARDS, ids=[p.name for p in CARDS])
def test_card_is_small_and_titled(card):
    text = card.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) <= CARD_BUDGET, f"{card.name}: tighten the card or move evidence to regression/lessons"
    assert text.startswith(f"# {card.stem} — "), card.name
    assert not re.search(r"^#{1,4} .*(?:V4\.\d+|20\d\d-\d\d-\d\d)", text, re.M), "no versioned/dated headings"


def test_entry_files_are_small():
    for name, cap in ENTRY_BUDGET.items():
        assert len((ROOT / name).read_bytes()) <= cap, name


def test_scenario_load_budget():
    for case in benchmark()["cases"]:
        first, full = SCENARIO_BUDGET[case["scenario"]]
        assert case["first_two_stages_bytes"] <= first, case
        assert case["all_stages_unique_bytes"] <= full, case


PATH = re.compile(r"(?<![\w/.])((?:rules|data|tools|templates|examples|regression)/[\w./-]*[\w/])")


@pytest.mark.parametrize("doc", CARDS + ENTRY, ids=[p.name for p in CARDS + ENTRY])
def test_every_referenced_path_exists(doc):
    text = doc.read_text(encoding="utf-8")
    missing = [m for m in PATH.findall(text) if "<" not in m and not (ROOT / m).exists()]
    assert not missing, (doc.name, missing)
    cards = {p.name for p in CARDS}
    named = set(re.findall(r"`(?:rules/)?([A-Z_]+\.md)`", text)) - {"JOB_CARD.md", "CLAUDE.md", "README.md"}
    assert named <= cards, (doc.name, named - cards)


SECTION = re.compile(r"`(?:rules/)?([A-Z_]+)\.md`\s*§\s*(\d+)")


@pytest.mark.parametrize("doc", CARDS + ENTRY, ids=[p.name for p in CARDS + ENTRY])
def test_section_references_resolve(doc):
    for name, sec in SECTION.findall(doc.read_text(encoding="utf-8")):
        target = (RULES / f"{name}.md").read_text(encoding="utf-8")
        assert re.search(rf"^## {sec}\.", target, re.M), (doc.name, name, sec)


def test_every_lesson_is_pointed_to_by_its_card():
    lessons = ROOT / "regression/lessons"
    for folder in sorted(p for p in lessons.iterdir() if p.is_dir()):
        card = RULES / f"{folder.name}.md"
        assert card.is_file(), f"lesson folder without card: {folder.name}"
        text = card.read_text(encoding="utf-8")
        assert f"regression/lessons/{folder.name}/" in text
        for f in folder.glob("*.md"):
            key = f.stem.split("_")[0]
            assert key in text, f"{folder.name}: {f.name} is not listed in the card's Lessons"


def test_no_paragraph_repeated_across_cards():
    seen = {}
    for card in CARDS:
        for para in re.split(r"\n\s*\n", card.read_text(encoding="utf-8")):
            norm = re.sub(r"\s+", " ", para).strip().casefold()
            if len(norm) >= 170:
                assert norm not in seen, (card.name, seen.get(norm))
                seen[norm] = card.name


def test_census_template_families_match_the_router():
    from resolve_rules import census_template
    assert set(census_template()["features"]) == set(ROUTER["feature_routes"])
