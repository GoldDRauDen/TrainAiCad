"""An exporter/guard error must lead the model to the exact condition that raised it."""
import asyncio
import json
from pathlib import Path

import pytest

from LuanAppTools.ai.protocol import AIResult
from LuanAppTools.cad.gates import GateIndex, describe_failure, summarize_error
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {f"tools/{p.name}": p.read_text(encoding="utf-8") for p in (ROOT / "tools").glob("*.py")}


def index():
    return GateIndex.from_sources(SOURCES)


def test_views_only_error_names_the_fields_the_model_used_to_guess():
    error = ("export: 26-056152: VIEWS_ONLY requires independently proved source views, "
             "reason and unresolved flags")
    gates = index().advise(error)
    hit = next(g for g in gates if g["gate"].startswith("tools/export_dxf.py:"))
    assert "preview_reason" in hit["fires_when"] and "separate_source_views" in hit["fires_when"]
    assert "flags" in hit["fires_when"]


def test_canonical_contract_error_is_indexed():
    gates = index().advise("canonical: 26-000001: canonical entities required")
    assert any(g["gate"].startswith("tools/canonical_contract.py:") and "entities" in g["fires_when"] for g in gates)


def test_guard_anomaly_code_is_indexed():
    gates = index().advise("26-056152:VIEWS_ONLY_BEFORE_SOURCE_EXHAUSTION")
    assert any("source_exhausted" in g["fires_when"] for g in gates)


def test_error_without_a_matching_gate_returns_nothing():
    assert index().advise("Claude could not be reached") == []
    assert index().advise("") == []


def test_summarize_error_keeps_the_last_traceback_line_only():
    text = 'Traceback (most recent call last):\r\n  File "<string>", line 15, in <module>\r\nValueError: export: x\r\n'
    assert summarize_error(text) == "ValueError: export: x"
    assert summarize_error("plain message") == "plain message"


def test_describe_failure_appends_the_gate_condition():
    error = "ValueError: export: 26-056152: VIEWS_ONLY requires independently proved source views, reason and unresolved flags"
    described = describe_failure(error, index())
    assert described.startswith(error) and "preview_reason" in described
    assert describe_failure("boom", index()) == "boom"


def bad_views_only_part(code="26-000001"):
    part = synthetic_part(code)
    part["status"] = "VIEWS_ONLY"
    part["flags"] = ["unresolved"]
    return part  # missing preview_reason: the exporter rejects it


class ValidateFirstRunner(SingleRunner):
    def __init__(self, parts, bad):
        super().__init__(parts)
        self.bad, self.asked = bad, False

    async def complete(self, request, **kwargs):
        context = json.loads(request.prompt.split("\nCONTEXT_JSON\n", 1)[1])
        if context["stage"] == "solve" and not self.asked:
            self.asked = True
            self.requests.append(request)
            data = {"tool_requests": [{"name": "validate", "arguments": {"part": self.bad}}]}
            return AIResult(data, {}, request.session_id, request.model, request.effort)
        return await super().complete(request, **kwargs)


def test_validate_tool_result_carries_the_gate_condition(setup):  # noqa: F811
    repo, source, control = setup
    runner = ValidateFirstRunner({"26-000001": synthetic_part()}, bad_views_only_part())
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="GATES"))
    follow_up = runner.requests[2].prompt.rsplit("CONTEXT_JSON\n", 1)[1]
    result = json.loads(follow_up)["tool_results"][0]["result"]
    assert "VIEWS_ONLY requires" in result["error"]
    gate = next(g for g in result["gates"] if g["gate"].startswith("tools/export_dxf.py:"))
    assert "preview_reason" in gate["fires_when"]


def test_failed_attempt_issue_is_summarised_with_its_gate(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner({"26-000001": bad_views_only_part()})
    with pytest.raises(PipelineError, match="Some codes have no"):
        asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="GATES"))
    issues = control.store.get_run(control.run_id)["checkpoint"]["parts"]["26-000001"]["issues"]
    assert issues and all("Traceback" not in issue for issue in issues)
    assert "preview_reason" in issues[0]
