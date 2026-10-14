"""docs/GATE_INDEX.yaml must be the current output of its generator and cover the Router."""
import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_gate_index", ROOT / "tools/build_gate_index.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def test_index_is_current_output_of_generator():
    assert (ROOT / "docs/GATE_INDEX.yaml").read_text(encoding="utf-8") == builder.build()


def test_index_lists_every_router_post_route_check():
    index = yaml.safe_load((ROOT / "docs/GATE_INDEX.yaml").read_text(encoding="utf-8"))
    router = yaml.safe_load((ROOT / "skills/lispcad/router/ROUTER.yaml").read_text(encoding="utf-8"))
    assert index["post_route_checks"] == router["post_route_checks"]


def test_every_indexed_gate_is_mentioned_in_a_cited_source():
    index = yaml.safe_load((ROOT / "docs/GATE_INDEX.yaml").read_text(encoding="utf-8"))
    assert index["gates"], "index must not be empty"
    for gate in index["gates"]:
        for rel in gate["files"]:
            assert gate["id"] in (ROOT / rel).read_text(encoding="utf-8"), (gate["id"], rel)


def test_review_candidates_catch_names_the_suffix_rule_misses():
    index = yaml.safe_load((ROOT / "docs/GATE_INDEX.yaml").read_text(encoding="utf-8"))
    candidates = {c["id"]: c["files"] for c in index["review_candidates"]}
    assert "DATA_NO_DIM_COMPARE" not in candidates
    assert "DATA_NO_DIM_COMPARE" in index["reviewed_non_gates"]
    gate_ids = {g["id"] for g in index["gates"]}
    assert not (gate_ids & set(candidates)), "a token must be either a gate or a review candidate"
    for token, files in candidates.items():
        assert len(files) >= 2
        for rel in files:
            assert token in (ROOT / rel).read_text(encoding="utf-8"), (token, rel)


def test_approved_gates_are_listed_as_gates_not_candidates():
    index = yaml.safe_load((ROOT / "docs/GATE_INDEX.yaml").read_text(encoding="utf-8"))
    gate_ids = {g["id"] for g in index["gates"]}
    candidate_ids = {c["id"] for c in index["review_candidates"]}
    for gate in builder.APPROVED_GATES:
        assert gate in gate_ids, gate
        assert gate not in candidate_ids, gate
    assert "DATA_NO_DIM_COMPARE" not in gate_ids
    assert "DATA_NO_DIM_COMPARE" not in candidate_ids
