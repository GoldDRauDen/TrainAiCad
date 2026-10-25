"""Rule-route byte benchmark and duplicate-paragraph audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from benchmark_rule_routes import benchmark  # noqa: E402


def test_benchmark_measures_real_file_bytes_without_claiming_total_token_savings():
    b = benchmark()
    assert b["metric"] == "EXACT_UTF8_BYTES_NOT_LLM_TOKENS"
    assert b["stage_invariant"] == "L0_L1_L2_L3_ALL_MANDATORY"
    assert len(b["cases"]) == 5
    for case in b["cases"]:
        assert case["first_two_stages_bytes"] < case["all_stages_unique_bytes"]
        assert sum(case["stage_breakdown"].values()) == case["all_stages_unique_bytes"]
        assert case["route_count"] > 0
    # Gate for the planned optimization: startup/context reading of ordinary
    # flat and bend jobs must be at least 30% smaller than eager L0–L3 loads.
    ordinary = [c for c in b["cases"] if c["scenario"] in {"flat", "bend_nobi"}]
    assert all(c["initial_context_reduction_pct_vs_eager_load"] >= 30 for c in ordinary)


def test_no_exact_cross_module_rule_paragraph_duplicates():
    """The current approved canonical modules have no repeated long paragraphs.

    This does not prove the absence of semantic contradictions or short
    repeated policy wording; those still need human/source rule review.
    """
    from audit_rule_duplicates import scan
    report = scan(min_chars=170)
    assert report["repeated_cross_module_paragraphs"] == 0
