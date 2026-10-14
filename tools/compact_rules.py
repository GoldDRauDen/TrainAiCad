#!/usr/bin/env python3
"""Resolve stable logical CAD module IDs into compact production rule packs.

The retired per-feature Markdown paths remain logical module IDs in ROUTER.yaml.
Physical contents live in rules/*.md and are selected by exact BEGIN/END markers.
No heuristic matching, fallback to history or silent loss of rules is allowed.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = "config/RULE_MODULES.yaml"


class CompactRuleError(ValueError):
    """Broken, missing or inconsistent rule pack."""


@lru_cache(maxsize=16)
def _load_map(root_string: str) -> dict[str, str]:
    root = Path(root_string)
    manifest = yaml.safe_load((root / MAP_PATH).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise CompactRuleError("Unsupported compact-rule manifest")
    modules = manifest.get("modules")
    if not isinstance(modules, dict) or not modules:
        raise CompactRuleError("Empty compact-rule manifest")
    for logical, physical in modules.items():
        if (not isinstance(logical, str) or not isinstance(physical, str)
                or not physical.startswith("rules/") or not physical.endswith(".md")
                or logical.startswith("/") or ".." in Path(logical).parts
                or physical.startswith("/") or ".." in Path(physical).parts):
            raise CompactRuleError("Invalid compact-rule module mapping")
    return modules


def rule_module_map(root: Path = ROOT) -> dict[str, str]:
    return _load_map(str(Path(root).resolve()))


def resolve_rule_path(path: str, root: Path = ROOT) -> Path:
    root = Path(root).resolve()
    logical = rule_module_map(root)
    physical = logical.get(path, path)
    target = (root / physical).resolve()
    if (path.startswith("/") or "\\" in path or ".." in Path(path).parts
            or not target.is_relative_to(root) or not target.is_file()):
        raise CompactRuleError(f"Missing or unsafe rule path: {path}")
    return target


def read_rule_text(path: str, root: Path = ROOT) -> str:
    """Return exactly the specified module, not its entire large pack."""
    root = Path(root).resolve()
    real = resolve_rule_path(path, root)
    content = real.read_text(encoding="utf-8")
    if path not in rule_module_map(root):
        return content
    start = f"<!-- BEGIN MODULE: {path} -->"
    end = f"<!-- END MODULE: {path} -->"
    if content.count(start) != 1 or content.count(end) != 1:
        raise CompactRuleError(f"Missing/duplicate exact section markers: {path}")
    after_start = content.index(start) + len(start)
    before_end = content.index(end, after_start)
    return content[after_start:before_end].strip() + "\n"


def rule_physical_paths(logical_paths: list[str], root: Path = ROOT) -> list[str]:
    """Stable distinct physical file paths for loading/inspection."""
    root = Path(root).resolve()
    mapping = rule_module_map(root)
    seen = set()
    result = []
    for logical in logical_paths:
        resolved = mapping.get(logical, logical)
        resolve_rule_path(logical, root)
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return result


def validate_rule_manifest(root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    mapping = rule_module_map(root)
    physical = set(mapping.values())
    if physical != {p.relative_to(root).as_posix() for p in (root / "rules").glob("*.md")}:
        raise CompactRuleError("Unindexed active rule-pack file")
    for logical in mapping:
        if (root / logical).exists():
            raise CompactRuleError(f"Duplicated legacy source still active: {logical}")
        read_rule_text(logical, root)
    return {"logical_modules": len(mapping), "physical_rule_files": len(physical)}




class RuleView:
    """Path-like test/consumer view of exactly ONE logical module, not the pack."""

    def __init__(self, module_id: str, root: Path = ROOT):
        self.module_id = module_id
        self.root = Path(root).resolve()

    def read_text(self, encoding: str = "utf-8") -> str:
        if encoding.lower().replace("-", "") != "utf8":
            raise CompactRuleError("Only UTF-8 rule views are supported")
        return read_rule_text(self.module_id, self.root)

    def read_bytes(self) -> bytes:
        return self.read_text().encode("utf-8")

    def is_file(self) -> bool:
        try:
            read_rule_text(self.module_id, self.root)
            return True
        except (CompactRuleError, OSError):
            return False

    def exists(self) -> bool:
        return self.is_file()


def module_view(module_id: str, root: Path = ROOT) -> RuleView:
    return RuleView(module_id, root)

if __name__ == "__main__":
    import json
    print(json.dumps(validate_rule_manifest(), indent=2))
