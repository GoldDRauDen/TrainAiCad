"""Single job conversation, host validation and durable continuation."""
import asyncio
import json
import pytest
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError, Paused
from LuanAppTools.tests.test_pipeline import setup, ScriptedRunner, synthetic_part
from LuanAppTools.ai.claude import ClaudeRunner
from LuanAppTools.ai.gateway import GatewayRunner
from LuanAppTools.ai.protocol import AIRequest


class SingleRunner(ScriptedRunner):
    async def complete(self, request, **kwargs):
        result = await super().complete(request, **kwargs)
        if "codes" in result.data:
            for code in result.data["codes"]:
                for key in ("difficulty", "difficulty_evidence", "independent"):
                    code.pop(key, None)
        return result


def test_single_agent_exports_two_codes_without_qa_or_repeated_images(setup):
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")})
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="SINGLE", individual=True))
    assert len(result.parts) == 2 and len(result.staged_files) == 3
    assert len(runner.requests) == 3  # intake + one solve per code; no QA call
    # Intake and every code own a conversation, so cost stays linear in the number of codes.
    assert len({r.session_id for r in runner.requests}) == 3
    assert [r.resume_session for r in runner.requests] == [False, False, False]
    assert [len(r.images) for r in runner.requests] == [1, 1, 1]  # each code gets only its own pages
    assert all(r.model == "sonnet-5.5" and r.effort == "medium" for r in runner.requests)
    assert all(p.qa["independent"] is False for p in result.parts)
    assert [r.prompt.count("FILE AI_BOOTSTRAP.md") for r in runner.requests] == [1, 1, 1]
    assert "26-000001" in runner.requests[1].prompt.rsplit("CONTEXT_JSON", 1)[1]
    assert "validate tool" in runner.requests[1].prompt  # validate before answering


def test_single_agent_pause_resume_keeps_session_and_finished_candidate(setup):
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")}, pause=control.pause)
    pipeline = CadPipeline(repo, runner, single_agent=True)
    with pytest.raises(Paused):
        asyncio.run(pipeline.run(source, control, job_name="SINGLE"))
    control.pause.clear()
    control.cancel = asyncio.Event()
    runner.pause = None
    result = asyncio.run(pipeline.run(source, control, job_name="SINGLE"))
    assert len(result.parts) == 2 and len(runner.requests) == 3
    assert len({r.session_id for r in runner.requests}) == 3


def test_single_agent_still_rejects_invalid_geometry_and_bounds_retries(setup):
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part(hole=True)})
    with pytest.raises(PipelineError, match="Some codes have no"):
        asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="SINGLE"))
    assert len(runner.requests) == 3
    # Both attempts for a code share that code's conversation; intake is separate.
    assert len({r.session_id for r in runner.requests}) == 2
    assert runner.requests[1].session_id == runner.requests[2].session_id
    assert [r.resume_session for r in runner.requests] == [False, False, True]
    assert not list((control.workspace / "aggregate").rglob("*.dxf"))


def test_claude_explicit_session_and_resume_arguments(tmp_path, monkeypatch):
    runner = ClaudeRunner()
    monkeypatch.setattr(runner, "executable", lambda: ["claude"])
    first = AIRequest("sonnet-5.5", "medium", "first", session_id="job-session")
    second = AIRequest("sonnet-5.5", "medium", "second", session_id="job-session", resume_session=True)
    assert "--session-id" in runner.argv(first, tmp_path)
    assert "--resume" in runner.argv(second, tmp_path)
    assert "--no-session-persistence" not in runner.argv(second, tmp_path)


def test_gateway_preserves_one_conversation_without_duplicate_images(tmp_path):
    image = tmp_path / "page.png"
    image.write_bytes(b"synthetic")
    runner = GatewayRunner("http://localhost:20128/v1")
    request = AIRequest("model", "medium", "solve", gateway_authorized=True,
        history=({"prompt": "inventory", "images": [str(image)], "answer": {"codes": []}},))
    body = runner._body(request, tmp_path)
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    assert body["messages"][1]["content"] == '{"codes":[]}'
    assert sum(len([c for c in m["content"] if isinstance(c, dict) and c["type"] == "image_url"])
               for m in body["messages"] if isinstance(m["content"], list)) == 1


def test_invalid_inventory_shape_is_corrected_in_same_conversation(setup):
    repo, source, control = setup
    class RepairRunner(SingleRunner):
        async def complete(self, request, **kwargs):
            result = await super().complete(request, **kwargs)
            if len(self.requests) == 1:
                result.data["pages"][0]["id"] = result.data["pages"][0].pop("page_id")
            return result
    runner = RepairRunner({"26-000001": synthetic_part()})
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="REPAIR"))
    assert result.staged_files and len(runner.requests) == 3
    # The inventory correction stays in the intake conversation; the code starts its own.
    assert len({r.session_id for r in runner.requests}) == 2
    assert runner.requests[0].session_id == runner.requests[1].session_id
    assert [len(r.images) for r in runner.requests] == [1, 0, 1]
    assert "response_format" in runner.requests[1].prompt


def test_error_resume_retains_session_budgets_and_never_resumes_cancelled(setup):
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part()})
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="RESUME"))
    store = control.store
    current = store.get_run(control.run_id)
    store.set_run_config(control.run_id, {**current["config"], "single_agent": True})
    store.set_run_status(control.run_id, "error", error="host failure")
    resumed = store.resume_run(control.run_id)
    assert resumed["status"] == "queued" and resumed["error"] is None
    assert resumed["checkpoint"] == current["checkpoint"]
    assert store.attempts(control.run_id, "26-000001") == 1
    store.set_run_status(control.run_id, "cancelled")
    with pytest.raises(ValueError):
        store.resume_run(control.run_id)


def test_partial_census_keeps_source_role_without_wasting_an_attempt(setup):
    repo, source, control = setup
    class PartialRunner(SingleRunner):
        async def complete(self, request, **kwargs):
            result = await super().complete(request, **kwargs)
            if "part" in result.data:
                result.data["census"] = {"features": {"HOLE": "NO"}}
            return result
    runner = PartialRunner({"26-000001": synthetic_part()})
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="PARTIAL"))
    assert result.staged_files and len(runner.requests) == 2
    assert control.store.attempts(control.run_id, "26-000001") == 1


def test_job_stops_after_consecutive_failed_codes_instead_of_spending_on_the_rest(setup):
    repo, source, control = setup
    runner = SingleRunner({
        "26-000001": synthetic_part(hole=True),
        "26-000002": synthetic_part("26-000002", hole=True),
        "26-000003": synthetic_part("26-000003"),
    })
    pipeline = CadPipeline(repo, runner, single_agent=True)
    with pytest.raises(PipelineError) as stopped:
        asyncio.run(pipeline.run(source, control, job_name="STOP"))
    assert stopped.value.kind == "no_progress" and "26-000001" in str(stopped.value)
    assert len(runner.requests) == 5  # intake + two attempts for each failing code; third code untouched
    assert control.store.attempts(control.run_id, "26-000003") == 0
    # Resuming never re-counts codes that already failed; it continues with the untouched code.
    control.cancel = asyncio.Event()  # a new event loop needs a fresh event
    control.pause = asyncio.Event()
    with pytest.raises(PipelineError, match="Some codes have no"):
        asyncio.run(pipeline.run(source, control, job_name="STOP"))
    assert len(runner.requests) == 6
    assert control.store.attempts(control.run_id, "26-000003") == 1


def test_a_single_failed_code_does_not_stop_the_job(setup):
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part(hole=True), "26-000002": synthetic_part("26-000002")})
    with pytest.raises(PipelineError, match="Some codes have no"):
        asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="ONE"))
    assert control.store.attempts(control.run_id, "26-000002") == 1
