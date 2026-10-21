"""Everything before the shared rules in the provider's cache prefix must not depend on the code.

Measured (Haiku, two fresh sessions, same appended system prompt): a schema that differs per code
-> second session created 20,218 tokens and read 0; one identical schema -> created 0, read 20,162.
The output schema is a tool definition and sits before the system prompt in the cache prefix.
"""
import asyncio
import json
from pathlib import Path

import pytest

from LuanAppTools.cad.contract import (
    HOST_CANONICAL_NOTE, HOST_WELD_NOTE, solve_part_schema)
from LuanAppTools.cad.pipeline import CadPipeline
from LuanAppTools.tests.test_customer_code import CustomerRunner, kh851_part
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_shared_context import SharedRunner
from LuanAppTools.tests.test_single_agent import SingleRunner

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ["contour_topology", "datum", "feature_count", "unfold", "containment",
          "bend_domain", "material_rules", "slot_semantics"]


def run_pipeline(setup, runner, name="CACHE"):  # noqa: F811
    repo, source, control = setup
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name=name))
    return result, control


def test_part_schema_is_code_independent_unless_a_code_is_given():
    assert solve_part_schema(CHECKS) == solve_part_schema(CHECKS, None)
    generic = solve_part_schema(CHECKS)
    assert generic["properties"]["code"] == {"type": "string"}
    assert solve_part_schema(CHECKS, "26-000001")["properties"]["code"]["enum"] == ["26-000001"]


def test_solve_schema_is_identical_for_every_code(setup):  # noqa: F811
    runner = SharedRunner({"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")})
    run_pipeline(setup, runner)
    first, second = runner.requests[1].schema, runner.requests[2].schema
    assert first == second
    assert "enum" not in json.dumps(first["properties"]["evidence_refs"])


def test_wrong_evidence_refs_are_restated_by_the_host(setup):  # noqa: F811
    class WrongRefs(SingleRunner):
        async def complete(self, request, **kwargs):
            result = await super().complete(request, **kwargs)
            if "part" in result.data:
                result.data["evidence_refs"] = ["bogus:p9"]
            return result

    result, _ = run_pipeline(setup, WrongRefs({"26-000001": synthetic_part()}))
    assert [p.status for p in result.parts] == ["PASS"]


def test_a_part_for_another_code_is_still_rejected(setup):  # noqa: F811
    from LuanAppTools.cad.pipeline import PipelineError
    runner = SingleRunner({"26-000001": synthetic_part("26-000009")})
    with pytest.raises(PipelineError, match="Some codes have no"):
        run_pipeline(setup, runner)


class MixedRunner(SingleRunner):
    """Second code is a multi-face part; the first stays flat."""

    async def complete(self, request, **kwargs):
        result = await super().complete(request, **kwargs)
        if "codes" in result.data:
            result.data["codes"][1]["census"]["part_mode"] = "MULTI_FACE"
        return result


def test_hard_codes_get_one_effort_level_more(setup):  # noqa: F811
    runner = MixedRunner({"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")})
    run_pipeline(setup, runner)
    assert [(r.model, r.effort) for r in runner.requests] == [
        ("sonnet-5.5", "medium"), ("sonnet-5.5", "medium"), ("sonnet-5.5", "high")]


def test_weld_codes_are_hard_too(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": kh851_part()}, ["851"], weld_from=1)
    run_pipeline(setup, runner)
    assert runner.requests[-1].effort == "high"


def test_first_turn_carries_the_full_task_and_later_turns_a_short_reminder(setup):  # noqa: F811
    runner = SingleRunner({"26-000001": synthetic_part(hole=True)})
    with pytest.raises(Exception, match="Some codes have no"):
        run_pipeline(setup, runner)
    first, second = runner.requests[1], runner.requests[2]
    assert second.resume_session and "Build the complete canonical part" in first.prompt
    assert "Build the complete canonical part" not in second.prompt and "Continue" in second.prompt


def test_weld_note_reaches_only_codes_that_have_weld_sites(setup):  # noqa: F811
    plain = SharedRunner({"26-000001": synthetic_part()})
    run_pipeline(setup, plain)
    assert HOST_WELD_NOTE not in plain.requests[1].prompt
    assert HOST_CANONICAL_NOTE in plain.requests[1].prompt


def test_weld_note_is_added_for_a_kh851_code(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": kh851_part()}, ["851"], weld_from=1)
    run_pipeline(setup, runner)
    assert HOST_WELD_NOTE in runner.requests[-1].prompt


def test_host_note_keys_exist_in_the_repository_tools():
    sources = "".join((ROOT / "tools" / name).read_text(encoding="utf-8")
                      for name in ("weld_kegaki_guard.py", "canonical_contract.py"))
    for key in ("mark_member_ids", "FLAGGED_NO_GEOMETRY", "weld_site_census", "witness_required_feature_ids",
                "feature_witness_graph", "SOURCE_VIEW"):
        assert key in sources, key
    for key in ("mark_member_ids", "FLAGGED_NO_GEOMETRY"):
        assert key in HOST_WELD_NOTE
    for key in ("witness_required_feature_ids", "feature_witness_graph", "SOURCE_VIEW"):
        assert key in HOST_CANONICAL_NOTE
