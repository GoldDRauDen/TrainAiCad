"""Identical validation errors must not be allowed to burn a conversation."""
import asyncio
import json

import pytest

from LuanAppTools.ai.protocol import AIResult
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError
from LuanAppTools.tests.test_gates import bad_views_only_part
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner


class RepeatingRunner(SingleRunner):
    """Asks the host to validate `bad` the first `times` rounds for `code`, then answers normally."""

    def __init__(self, parts, code, bad, times):
        super().__init__(parts)
        self.code, self.bad, self.times, self.asked = code, bad, times, 0

    async def complete(self, request, **kwargs):
        context = json.loads(request.prompt.split("\nCONTEXT_JSON\n", 1)[1])
        if context["stage"] == "solve" and context["code"]["code"] == self.code and self.asked < self.times:
            self.asked += 1
            self.requests.append(request)
            # A different request each round (like the model reshuffling fields) so the
            # existing identical-request guard does not fire; the error stays the same.
            part = json.loads(json.dumps(self.bad))
            part["flags"] = [f"unresolved {self.asked}"]
            data = {"tool_requests": [{"name": "validate", "arguments": {"part": part}}]}
            return AIResult(data, {}, request.session_id, request.model, request.effort)
        return await super().complete(request, **kwargs)


def tool_results(request):
    return json.loads(request.prompt.rsplit("CONTEXT_JSON\n", 1)[1])["tool_results"]


def test_second_identical_error_adds_an_instruction(setup):  # noqa: F811
    repo, source, control = setup
    runner = RepeatingRunner({"26-000001": synthetic_part()}, "26-000001", bad_views_only_part(), times=2)
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="STALL"))
    # Each follow-up prompt carries only the newest tool results.
    (first,), (second,) = tool_results(runner.requests[2]), tool_results(runner.requests[3])
    assert "repeated" not in first["result"] and "repeated" in second["result"]
    # The model's own attempt to open the gate's source failed in the real run; point it at the host tool.
    assert "read_rule" in second["result"]["repeated"] and "start" in second["result"]["repeated"]


def test_third_identical_error_ends_the_attempt_not_the_job(setup):  # noqa: F811
    repo, source, control = setup
    parts = {"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")}
    runner = RepeatingRunner(parts, "26-000001", bad_views_only_part(), times=99)
    with pytest.raises(PipelineError, match="Some codes have no"):
        asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="STALL"))
    statuses = {p["code"]: p["status"] for p in control.store.parts(control.run_id)}
    assert statuses == {"26-000001": "UNRESOLVED", "26-000002": "PASS"}
    assert runner.asked == 6  # three identical rounds in each of the two attempts, then it stops
    issues = control.store.get_run(control.run_id)["checkpoint"]["parts"]["26-000001"]["issues"]
    assert len(issues) == 2 and all("same error 3 times" in issue for issue in issues)
    stalls = [e for e in control.store.events_since(control.run_id, 0) if e["kind"] == "validation_error"]
    assert [e["payload"]["count"] for e in stalls][:3] == [1, 2, 3]


def test_a_different_error_resets_the_count(setup):  # noqa: F811
    repo, source, control = setup
    other = bad_views_only_part()
    other["thickness_mm"] = -1  # a different failure from the missing preview_reason
    runner = RepeatingRunner({"26-000001": synthetic_part()}, "26-000001", bad_views_only_part(), times=2)
    runner.bad_cycle = [bad_views_only_part(), other, bad_views_only_part()]
    original = runner.complete

    async def cycling(request, **kwargs):
        runner.bad = runner.bad_cycle[min(runner.asked, 2)]
        return await original(request, **kwargs)

    runner.complete = cycling
    runner.times = 3
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="STALL"))
    counts = [e["payload"]["count"] for e in control.store.events_since(control.run_id, 0)
              if e["kind"] == "validation_error"]
    assert counts == [1, 1, 1]
