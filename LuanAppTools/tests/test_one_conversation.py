"""One conversation for the whole job: the PDF (and DXF data) is read once and the agent works through every code.

The per-code mode (conversation="code") stays available and keeps its own tests in test_single_agent.py; the two
are compared on the same job with bench/run_metrics.py. Commit 72f6282 split the job conversation per code because
a real run (521016-23) re-read a growing history on every call, so this mode has to be measured, not assumed.
"""
import asyncio
import json

import pytest

from LuanAppTools.cad.contract import HOST_NEXT_CODE_NOTE
from LuanAppTools.cad.pipeline import CadPipeline, Paused, PipelineError
from LuanAppTools.core.settings import Settings
from LuanAppTools.tests.test_cache_prefix import MixedRunner
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner


def run_job(setup, runner, **options):  # noqa: F811
    repo, source, control = setup
    pipeline = CadPipeline(repo, runner, single_agent=True, conversation="job", **options)
    return asyncio.run(pipeline.run(source, control, job_name="JOB")), control


def two_codes():
    return {"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")}


def test_one_session_serves_the_intake_and_every_code(setup):  # noqa: F811
    runner = SingleRunner(two_codes())
    result, control = run_job(setup, runner)
    assert [p.status for p in result.parts] == ["PASS", "PASS"]
    assert len(runner.requests) == 3  # intake + one solve per code
    assert len({r.session_id for r in runner.requests}) == 1
    assert [r.resume_session for r in runner.requests] == [False, True, True]
    assert [len(r.images) for r in runner.requests] == [1, 0, 0]  # the pages are read once, at intake
    assert all((r.model, r.effort) == ("sonnet-5.5", "medium") for r in runner.requests)
    checkpoint = control.store.get_run(control.run_id)["checkpoint"]
    assert [key for key in checkpoint if key.startswith("agent")] == ["agent"]
    assert len(checkpoint["agent"]["turns"]) == 3


def test_each_code_gets_its_full_task_but_the_rules_are_not_sent_again(setup):  # noqa: F811
    runner = SingleRunner(two_codes())
    run_job(setup, runner)
    assert runner.requests[0].prompt.count("FILE AI_BOOTSTRAP.md") == 1
    for request, code in zip(runner.requests[1:], ("26-000001", "26-000002")):
        assert "Build the complete canonical part" in request.prompt  # the task of this code, not "Continue"
        assert code in request.prompt.rsplit("CONTEXT_JSON", 1)[1]
        assert "FILE AI_BOOTSTRAP.md" not in request.prompt  # already in the conversation
        assert HOST_NEXT_CODE_NOTE in request.prompt


def test_the_note_forbids_copying_geometry_between_codes():
    assert "never copy or mirror" in HOST_NEXT_CODE_NOTE
    assert "Never mirror every bent part by default" in HOST_NEXT_CODE_NOTE  # the repository's own sentence


def test_every_turn_uses_the_same_output_schema(setup):  # noqa: F811
    runner = SingleRunner(two_codes())
    run_job(setup, runner)
    schemas = {json.dumps(r.schema, sort_keys=True) for r in runner.requests}
    assert len(schemas) == 1  # a changed schema would rebuild the whole cached conversation
    properties = runner.requests[0].schema["properties"]
    assert {"pages", "codes", "part", "evidence_refs", "tool_requests"} <= set(properties)


def test_a_retried_code_stays_in_the_same_conversation(setup):  # noqa: F811
    runner = SingleRunner({"26-000001": synthetic_part(hole=True)})
    with pytest.raises(PipelineError, match="Some codes have no"):
        run_job(setup, runner)
    assert len(runner.requests) == 3
    assert len({r.session_id for r in runner.requests}) == 1
    assert [r.resume_session for r in runner.requests] == [False, True, True]
    assert "Build the complete canonical part" in runner.requests[2].prompt  # second attempt restates the task


def test_a_hard_code_cannot_change_the_effort_of_the_shared_conversation(setup):  # noqa: F811
    runner = MixedRunner(two_codes())
    run_job(setup, runner)
    assert {(r.model, r.effort) for r in runner.requests} == {("sonnet-5.5", "medium")}


def test_pause_and_resume_keep_the_one_session(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner(two_codes(), pause=control.pause)
    pipeline = CadPipeline(repo, runner, single_agent=True, conversation="job")
    with pytest.raises(Paused):
        asyncio.run(pipeline.run(source, control, job_name="JOB"))
    control.pause.clear()
    control.cancel = asyncio.Event()
    runner.pause = None
    result = asyncio.run(pipeline.run(source, control, job_name="JOB"))
    assert len(result.parts) == 2 and len(runner.requests) == 3
    assert len({r.session_id for r in runner.requests}) == 1


def test_the_pipeline_default_is_still_one_conversation_per_code(setup):  # noqa: F811
    repo, _, _ = setup
    assert CadPipeline(repo, SingleRunner({}), single_agent=True).one_conversation is False
    assert CadPipeline(repo, SingleRunner({}), single_agent=True, conversation="job").one_conversation is True
    with pytest.raises(ValueError, match="conversation"):
        CadPipeline(repo, SingleRunner({}), single_agent=True, conversation="all")


def test_settings_default_to_the_job_conversation_and_reject_other_values(tmp_path):
    settings = Settings(tmp_path, validate_roots=False)
    assert settings.conversation == "job" and settings.public_dict()["conversation"] == "job"
    Settings(tmp_path, validate_roots=False, conversation="code")
    with pytest.raises(ValueError, match="conversation"):
        Settings(tmp_path, validate_roots=False, conversation="agent")
