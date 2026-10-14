#!/usr/bin/env python3
"""Read only routed, exact CAD rule sections from the compact V4.34 packs.

Usage:
  python tools/read_routed_rules.py --module-id skills/lispcad/features/SLIT_RELIEF.md
  python tools/read_routed_rules.py --census census.json --stage L2_GEOMETRY
  python tools/read_routed_rules.py --census census.json --output /tmp/job_rules.md
No source evidence is invented by this helper; resolve_rules validates the census.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from compact_rules import ROOT, CompactRuleError, read_rule_text
from resolve_rules import resolve_rules, ResolutionError

STAGES = ("L0_BOOTSTRAP", "L1_SOURCE_CENSUS", "L2_GEOMETRY", "L3_VALIDATE_EXPORT_QA")


def extract(paths: list[str], root: Path = ROOT) -> str:
    out = []
    seen = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        data = read_rule_text(path, root)
        out.append(f"<!-- BEGIN SELECTED RULE: {path} -->\n{data.rstrip()}\n"
                   f"<!-- END SELECTED RULE: {path} -->")
    return "\n\n---\n\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selectors = parser.add_mutually_exclusive_group(required=True)
    selectors.add_argument("--module-id", action="append", help="Stable logical module ID")
    selectors.add_argument("--census", type=Path, help="Complete source evidence census JSON")
    parser.add_argument("--stage", choices=STAGES, help="One mandatory execution stage")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Output file OUTSIDE repo (otherwise stdout)")
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        if args.census:
            census = json.loads(args.census.read_text(encoding="utf-8"))
            plan = resolve_rules(census, root)
            paths = (plan["stage_plans"][args.stage]["rule_paths"]
                     if args.stage else plan["rule_paths"])
        else:
            paths = args.module_id
        rendered = extract(paths, root)
        if args.output:
            target = args.output.expanduser().resolve()
            if target.is_relative_to(root):
                raise ValueError("Output is read-only and must be outside repository")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            print(json.dumps({"output": str(target), "sections": len(paths),
                              "utf8_bytes": len(rendered.encode("utf-8"))}))
        else:
            sys.stdout.write(rendered)
    except (CompactRuleError, ResolutionError, ValueError, OSError, KeyError) as exc:
        print(f"RULE_EXTRACT_FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
