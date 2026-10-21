"""Every `FILE.md §N` reference in a live rule file must point at an existing
file and heading. A dead reference sends the AI searching for a rule that is
not there (found 2026-10-21: BEND_UNFOLD §4.10, DRAWING_READING §2.1/§2.4)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = (
    list(ROOT.glob("skills/**/*.md")) + list(ROOT.glob("references/*.md"))
    + [ROOT / n for n in ("AI_ENTRYPOINT.md", "SKILL.md", "AI_BOOTSTRAP.md", "README.md", "AGENTS.md", "JOB_CARD.md")]
)
REF = re.compile(r"`?([A-Za-z_./0-9-]+\.md)`?\s*(?:§|section |Section )\s*([0-9][0-9.]*[a-z]?)")
MISSING_PATHS = ("services/trainaicad-mcp",)


def _target(name: str):
    hits = [p for p in ROOT.rglob(Path(name).name)
            if ".git" not in p.parts and "LuanAppTools" not in p.parts and "regression" not in p.parts]
    return hits[0] if hits else None


def test_section_references_resolve():
    dead = []
    for f in LIVE:
        if not f.exists():
            continue
        for m in REF.finditer(f.read_text(encoding="utf-8")):
            name, sec = m.group(1), m.group(2).rstrip(".")
            tgt = _target(name)
            if tgt is None:
                dead.append(f"{f.relative_to(ROOT)} -> missing {name}")
                continue
            heads = [ln for ln in tgt.read_text(encoding="utf-8").splitlines()
                     if ln.startswith("#") or re.match(r"^\d+\.\s", ln)]
            if not any(re.search(r"(^|[\s#])" + re.escape(sec) + r"([\s.:)]|$)", h) for h in heads):
                dead.append(f"{f.relative_to(ROOT)} -> {name} §{sec}")
    assert not dead, dead


def test_no_reference_to_removed_paths():
    for f in LIVE:
        if f.exists():
            text = f.read_text(encoding="utf-8")
            for path in MISSING_PATHS:
                assert path not in text, (f.relative_to(ROOT), path)
