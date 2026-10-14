"""Build docs/GATE_INDEX.yaml: a derived lookup of gate identifiers.

The index is NOT authority. It lists where each gate-like identifier is
mentioned in routed sources, so reviewers can check coverage. Rules stay in
the routed files named by the Router.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "skills/lispcad/router/ROUTER.yaml"
OUTPUT = ROOT / "docs/GATE_INDEX.yaml"
PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{6,}_(?:FAIL|CHECK|GATE|GUARD|LOCK|LEDGER|QA|PASS|CLOSURE|CONTRACT|COMPLETENESS)\b")
GLOBS = ("AI_ENTRYPOINT.md", "SKILL.md", "skills/lispcad/**/*.md", "references/**/*.md")
EXCLUDED = ("versions/", "portable/", "docs/history/")


def source_files():
    found = set()
    for pattern in GLOBS:
        for path in ROOT.glob(pattern):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and not any(part in rel for part in EXCLUDED):
                found.add(rel)
    return sorted(found)


def build() -> str:
    mentions = {}
    for rel in source_files():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for gate in set(PATTERN.findall(text)):
            mentions.setdefault(gate, set()).add(rel)
    router = yaml.safe_load(ROUTER.read_text(encoding="utf-8"))
    doc = {
        "release": router["release"],
        "generated_by": "tools/build_gate_index.py",
        "note": "Derived lookup only. Routed rule files stay authoritative; this index defines no gate.",
        "post_route_checks": list(router["post_route_checks"]),
        "gates": [{"id": g, "files": sorted(mentions[g])} for g in sorted(mentions)],
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
    target.write_text(build(), encoding="utf-8")
    print(target)
