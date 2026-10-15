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


# Approved by the user (2026-10-14): these identifiers are gates even though
# their names do not end with a gate suffix. Keep this list explicit so the
# index stays reproducible. DATA_NO_DIM_COMPARE is a customer policy value and
# stays out of this list.
APPROVED_GATES = (
    "BEND_ATTACHMENT_EDGE_LOCKED", "BEND_DOMAIN_LOCKED", "BEND_SIGN_LOCKED",
    "FACE_ORDER_LOCKED", "FEATURE_OWNERSHIP_LOCKED", "TOPOLOGY_LOCKED",
    "DIMENSION_WITNESS_LOCKED", "SOURCE_PHYSICAL_TO_CANONICAL",
    "CANONICAL_TO_SOURCE_PHYSICAL", "SOURCE_EXHAUSTED_BEFORE_VIEWS_ONLY",
    "CONSTRAINTS_CLOSED", "FINAL_ENGINEERING_SANITY_REVIEW",
    "ENGINEERING_ANOMALY_DETECTED", "SOURCE_ONLY_SNAPSHOT",
    "SAME_PHYSICAL_PARAMETER_BEFORE_REFERENCE_CONFLICT",
    "POST_REFERENCE_SOURCE_REWRITE", "SAME_FACE_FIRST", "RAW_DATA_SNAPSHOT",
    "PHYSICAL_DATA_BASELINE", "THICKNESS_SINGLE_USE", "PART_IDENTITY_COLLISION",
    "DATA_PDF_DIM_DIFF", "SAVED_DXF_LAYER0_ENTITY_IDS",
    "FOLD_BACK_SOURCE_REPROJECTION", "NEAREST_VIEW_EDGE", "FOLD_BACK_MATCH",
)

# Historical Groups B and C (decision preserved in docs/RULE_HISTORY.md): status labels, blocking labels,
# geometry/mechanism/file names. Explicitly NOT gates. Listing them here keeps
# review_candidates limited to identifiers nobody has classified yet.
REVIEWED_NON_GATES = (
    "ASSEMBLY_DATUM_GRAPH", "BEND_EDGE", "BEND_END_OFFSET_90", "CANONICAL_ENTITY_IDS",
    "CONFIRM_CONFLICT", "CONTOUR_EDGE", "CUSTOMER_CONFIRMATION_PENDING", "DATA_NO_DIM_COMPARE",
    "DATA_REQUIRED_MISSING", "DETAILED_SOURCE_BUNDLE", "DIMENSION_HELPER_OR_CONSTRUCTION",
    "DUPLICATE_COINCIDENT", "ENTITY_ID", "FACE_GRAPH", "FEATURE_FAMILY", "FLAGGED_NO_GEOMETRY",
    "FREE_EDGE", "GEOMETRY_DECODE_GAP", "HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE",
    "HIDDEN_OR_PROJECTION_ONLY", "HOLE_CENTER", "INSIDE_VIEW", "IRRELEVANT_TO_MANUFACTURING",
    "LEFT_EDGE", "LEGACY_COMPATIBILITY_TEXT", "MANUFACTURING_CANONICAL",
    "MEASUREMENT_CONSTRUCTION_VIEW", "NEW_PDF_TO_DXF", "OUTER_EDGE", "PART_IDENTITY_GAP",
    "PASS_CODE", "PDF_PRIORITY", "PHYSICAL_CUT_OR_FACE_EDGE", "PHYSICAL_HOLE_SLOT_OR_FEATURE",
    "REFERENCE_ANOMALY", "REFERENCE_ASSISTED_UNDERSTANDING", "REVIEW_ONLY", "RIGHT_EDGE",
    "ROUTING_COVERAGE_GAP", "SKILL_LISPCAD_CURRENT", "SLOT_MIDPOINT", "SOURCE_CONFLICT",
    "SOURCE_FEATURE_GROUP", "SOURCE_MEMBER_CENSUS_GAP", "SOURCE_UNIT_CONFLICT", "SOURCE_VIEW",
    "THICKNESS_REPRESENTATION", "THREAD_NOMINAL_REFERENCE", "THREAD_PREHOLE_SOURCE",
    "TRUE_SOURCE_AMBIGUITY", "VIEWS_ONLY", "WELD_REQUIRED_CUE",
    "BEND_SUPPORT", "FOLD_BACK", "PHYSICAL_DATA_BASELINE_COMPLETE",
    "RAW_DATA_SNAPSHOT_COMPLETE",
)
assert not set(REVIEWED_NON_GATES) & set(APPROVED_GATES)

CANDIDATE = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]{2,})+\b")


def _file_stems() -> set:
    stems = set()
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            stems.add(path.stem.upper())
    return stems


def build() -> str:
    mentions = {}
    candidates = {}
    for rel in source_files():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for gate in set(PATTERN.findall(text)):
            mentions.setdefault(gate, set()).add(rel)
        for token in set(CANDIDATE.findall(text)):
            candidates.setdefault(token, set()).add(rel)
    for gate in APPROVED_GATES:
        if gate not in candidates:
            raise ValueError(f"approved gate not found in sources: {gate}")
        mentions.setdefault(gate, set()).update(candidates[gate])
    router_text = ROUTER.read_text(encoding="utf-8")
    router_tokens = set(CANDIDATE.findall(router_text))
    stems = _file_stems()
    review = {
        t: sorted(f) for t, f in candidates.items()
        if t not in mentions and len(f) >= 2 and t not in router_tokens and t not in stems
        and t not in REVIEWED_NON_GATES
    }
    router = yaml.safe_load(router_text)
    doc = {
        "release": router["release"],
        "generated_by": "tools/build_gate_index.py",
        "note": "Derived lookup only. Routed rule files stay authoritative; this index defines no gate. "
                "'gates' match a gate suffix. 'review_candidates' are other upper-case identifiers in 2+ "
                "sources, excluding file names and Router route names; a human decides which are gates.",
        "post_route_checks": list(router["post_route_checks"]),
        "gates": [{"id": g, "files": sorted(mentions[g])} for g in sorted(mentions)],
        "review_candidates": [{"id": t, "files": review[t]} for t in sorted(review)],
        "reviewed_non_gates": sorted(REVIEWED_NON_GATES),
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
    target.write_text(build(), encoding="utf-8")
    print(target)
