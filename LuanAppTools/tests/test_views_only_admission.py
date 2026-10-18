"""VIEWS_ONLY needs a failed, named flat attempt whenever printed flat arithmetic closes against the views."""
import asyncio
import json

import pytest

from LuanAppTools.ai.protocol import AIResult
from LuanAppTools.ai.tools import HostTools
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError
from LuanAppTools.tests.test_pipeline import ScriptedRunner, setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner
from LuanAppTools.tests.test_views_only_gate import NOTE, views_only_part

CITE = ("v1", "n_calc")


def views_only_for(code):
    part = synthetic_part(code)
    part.update(
        status="VIEWS_ONLY", preview_reason="separate_source_views", flags=["bend attachment unresolved"],
        source_exhausted=True, holistic_challenge_run=True, flat_attempted=True,
        face_graph_candidates=[{"candidate_id": "C1", "constraint_result": "attachment edge ambiguous",
                                "evidence_used": ["v1"]}],
        unresolved_objects=[{"object": "bend attachment edge"}],
    )
    part["entities"][0]["view_id"] = "FRONT"
    return part


def flat_attempt(width):
    """A flat the exporter's gates reject (hole without witness) whose outer polyline is `width` wide."""
    part = synthetic_part(hole=True)
    part["entities"][0]["vertices"] = [[0, 0, 0], [width, 0, 0], [width, 40, 0], [0, 40, 0]]
    return part


class TurnRunner(SingleRunner):
    """Asks the host to validate the scripted parts one per round, then answers with the scripted final part."""

    def __init__(self, parts, turns=(), *, dimensions=(80, 60, 6), notes=(NOTE,)):
        super().__init__(parts)
        self.turns, self.dimensions, self.notes, self.sent = list(turns), list(dimensions), list(notes), 0

    async def complete(self, request, **kwargs):
        context = json.loads(request.prompt.split("\nCONTEXT_JSON\n", 1)[1])
        if context["stage"] == "solve" and self.turns:
            self.requests.append(request)
            part = json.loads(json.dumps(self.turns.pop(0)))
            self.sent += 1
            if part["status"] == "VIEWS_ONLY":  # keep identical rounds distinct for the existing repeat guard
                part["flags"] = [*part["flags"], f"round {self.sent}"]
            data = {"tool_requests": [{"name": "validate", "arguments": {"part": part}}]}
            return AIResult(data, {}, request.session_id, request.model, request.effort)
        result = await super().complete(request, **kwargs)
        if "codes" in result.data:
            result.data["notes"] = [dict(n) for n in self.notes]
            for view in result.data["views"]:
                view["dimensions"] = list(self.dimensions)
        return result


def tool_results(request):
    return json.loads(request.prompt.rsplit("CONTEXT_JSON\n", 1)[1])["tool_results"]


def run(setup, runner, **kwargs):  # noqa: F811
    repo, source, control = setup
    return asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="ADMIT", **kwargs))


def test_views_only_is_rejected_until_a_flat_was_attempted(setup):  # noqa: F811
    held = views_only_part(record=True, cite=CITE)
    runner = TurnRunner({"26-000001": held}, [held, flat_attempt(130.22), held])
    result = run(setup, runner)
    first, second, third = (tool_results(runner.requests[i])[0]["result"] for i in (2, 3, 4))
    assert "VIEWS_ONLY_ADMISSION" in first["error"] and "80+60-9.78=130.22" in first["error"]
    assert "WITNESS_REQUIRED_FEATURE_MISSING" in second["error"]  # the attempt failed a named gate
    assert "error" not in third  # now the VIEWS_ONLY validates
    assert [p.status for p in result.parts] == ["VIEWS_ONLY"]


def test_attempt_that_does_not_reproduce_the_result_does_not_unlock(setup):  # noqa: F811
    held = views_only_part(record=True, cite=CITE)
    runner = TurnRunner({"26-000001": held}, [held, flat_attempt(100.0), held])
    with pytest.raises(PipelineError, match="Some codes have no"):
        run(setup, runner)
    assert "VIEWS_ONLY_ADMISSION" in tool_results(runner.requests[4])[0]["result"]["error"]


def test_skipping_validate_is_caught_on_the_final_answer(setup):  # noqa: F811
    runner = TurnRunner({"26-000001": views_only_part(record=True, cite=CITE)})
    with pytest.raises(PipelineError, match="Some codes have no"):
        run(setup, runner)
    control = setup[2]
    issues = control.store.get_run(control.run_id)["checkpoint"]["parts"]["26-000001"]["issues"]
    assert len(issues) == 2 and all("VIEWS_ONLY_ADMISSION" in issue for issue in issues)
    assert control.store.attempts(control.run_id, "26-000001") == 2


def test_unclosed_arithmetic_keeps_todays_behaviour(setup):  # noqa: F811
    runner = TurnRunner({"26-000001": views_only_part(record=True, cite=CITE)}, dimensions=())
    assert [p.status for p in run(setup, runner).parts] == ["VIEWS_ONLY"]


def test_other_code_is_untouched(setup):  # noqa: F811
    parts = {"26-000001": synthetic_part(), "26-000002": views_only_for("26-000002")}
    note = {**NOTE, "codes": ["26-000001"]}
    result = run(setup, TurnRunner(parts, notes=(note,)))
    assert [p.status for p in result.parts] == ["PASS", "VIEWS_ONLY"]


def record_closures(monkeypatch):
    seen = []
    original = HostTools.__init__

    def recording(self, *args, **kwargs):
        seen.append(kwargs.get("closure") is not None)
        original(self, *args, **kwargs)

    monkeypatch.setattr(HostTools, "__init__", recording)
    return seen


def test_single_agent_solve_tools_carry_a_closure(setup, monkeypatch):  # noqa: F811
    seen = record_closures(monkeypatch)
    run(setup, TurnRunner({"26-000001": synthetic_part()}))
    assert seen == [False, True]  # the intake tools have none; the solve tools do


def test_non_single_agent_mode_is_untouched(setup, monkeypatch):  # noqa: F811
    repo, source, control = setup
    seen = record_closures(monkeypatch)
    asyncio.run(CadPipeline(repo, ScriptedRunner({"26-000001": synthetic_part()})).run(source, control, job_name="PLAIN"))
    assert seen and not any(seen)
