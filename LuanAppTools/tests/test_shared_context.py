"""Rules shared by every code travel in an appended system prompt file, so fresh sessions reuse the cache."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

from LuanAppTools.ai.claude import ClaudeRunner
from LuanAppTools.ai.protocol import AIRequest
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError, expand_shared_history
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner


class SharedRunner(SingleRunner):
    supports_shared_context = True

    def __init__(self, parts):
        super().__init__(parts)
        self.shared = []

    async def complete(self, request, **kwargs):
        file = request.shared_context_file
        self.shared.append(Path(file).read_text(encoding="utf-8") if file else None)
        return await super().complete(request, **kwargs)


def has_rules(prompt):
    return prompt.startswith("FILE ") or "\nFILE " in prompt


def run_pipeline(setup, runner, name="SHARED"):  # noqa: F811
    repo, source, control = setup
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name=name))
    return result, control


def test_rules_move_into_the_shared_file_and_out_of_the_prompt(setup):  # noqa: F811
    runner = SharedRunner({"26-000001": synthetic_part()})
    run_pipeline(setup, runner)
    intake, solve = runner.requests
    assert "FILE AI_BOOTSTRAP.md" in runner.shared[0] and "You are the CAD agent" in runner.shared[0]
    assert "Optional tool_requests" in runner.shared[1]
    assert "FILE skills/lispcad/core/VALIDATION.md" in runner.shared[1]
    assert "separate_source_views" in runner.shared[1]  # quoted part contract
    assert not has_rules(intake.prompt) and not has_rules(solve.prompt)
    assert "Build the complete canonical part" in solve.prompt and "CONTEXT_JSON" in solve.prompt


def test_codes_on_the_same_route_share_one_identical_file(setup):  # noqa: F811
    runner = SharedRunner({"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")})
    run_pipeline(setup, runner)
    assert runner.shared[1] == runner.shared[2] != runner.shared[0]
    assert runner.requests[1].shared_context_file == runner.requests[2].shared_context_file
    assert "26-000001" not in runner.shared[1]  # nothing code-specific may leak into the shared prefix


def test_resume_turn_reuses_the_file_and_sends_no_rules(setup):  # noqa: F811
    runner = SharedRunner({"26-000001": synthetic_part(hole=True)})
    with pytest.raises(PipelineError, match="Some codes have no"):
        run_pipeline(setup, runner)
    first, second = runner.requests[1], runner.requests[2]
    assert second.resume_session and not first.resume_session
    assert first.shared_context_file == second.shared_context_file
    assert not has_rules(second.prompt)


def test_checkpoint_keeps_a_reference_not_the_rules(setup):  # noqa: F811
    runner = SharedRunner({"26-000001": synthetic_part()})
    _, control = run_pipeline(setup, runner)
    turn = control.store.get_run(control.run_id)["checkpoint"]["agent:26-000001"]["turns"][0]
    assert len(turn["prompt"]) < 20000
    assert Path(turn["shared_context_file"]).read_text(encoding="utf-8") == runner.shared[1]


def test_metrics_event_records_the_shared_context_size(setup):  # noqa: F811
    runner = SharedRunner({"26-000001": synthetic_part()})
    _, control = run_pipeline(setup, runner)
    sizes = [e["payload"]["shared_context_characters"] for e in control.store.events_since(control.run_id, 0)
             if e["kind"] == "request_prepared"]
    assert sizes == [len(runner.shared[0]), len(runner.shared[1])]


def test_runner_without_support_keeps_rules_inline(setup):  # noqa: F811
    runner = SingleRunner({"26-000001": synthetic_part()})
    run_pipeline(setup, runner)
    assert all(r.shared_context_file is None for r in runner.requests)
    assert "FILE AI_BOOTSTRAP.md" in runner.requests[1].prompt


def test_gateway_history_gets_the_shared_rules_back(tmp_path):
    shared = tmp_path / "shared.txt"
    shared.write_text("FILE rules\nbody", encoding="utf-8")
    turns = [{"prompt": "task", "images": [], "answer": {}, "shared_context_file": str(shared)},
             {"prompt": "next", "images": [], "answer": {}}]
    expanded = expand_shared_history(turns)
    assert expanded[0]["prompt"] == "FILE rules\nbody\ntask" and "shared_context_file" not in expanded[0]
    assert expanded[1] == turns[1]


def fake_cli(tmp_path, version):
    script = tmp_path / f"cli_{version.replace('.', '_')}.py"
    script.write_text(f"""import json, sys
if '--version' in sys.argv: print('{version} (Claude Code)'); sys.exit()
if 'auth' in sys.argv: print(json.dumps({{'loggedIn': True, 'authMethod': 'claude.ai'}})); sys.exit()
payload = json.loads(sys.stdin.readline())
open(r'{tmp_path}/argv.json', 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))
open(r'{tmp_path}/prompt.txt', 'w', encoding='utf-8').write(payload['message']['content'][0]['text'])
print(json.dumps({{'type': 'system', 'subtype': 'init', 'session_id': 's1', 'model': 'claude-sonnet-5-5', 'effort': 'high'}}), flush=True)
print(json.dumps({{'type': 'result', 'subtype': 'success', 'is_error': False, 'result': '{{"answer":42}}',
                   'structured_output': {{'answer': 42}}, 'session_id': 's1', 'usage': {{'input_tokens': 1, 'output_tokens': 1}}}}), flush=True)
""", encoding="utf-8")
    return ClaudeRunner(command=(sys.executable, str(script)))


def shared_request(file):
    return AIRequest("sonnet-5.5", "high", "TASK", shared_context_file=file, timeout=10)


async def emit(event):
    pass


def call(runner, workspace, request):
    return asyncio.run(runner.complete(request, workspace=workspace, cancel=asyncio.Event(), emit=emit))


def test_new_cli_gets_the_file_as_an_appended_system_prompt(tmp_path):
    workspace = tmp_path / "work space ü"
    (workspace / "prompts").mkdir(parents=True)
    shared = workspace / "prompts" / "shared-1.txt"
    shared.write_text("SHARED RULES ü", encoding="utf-8")
    call(fake_cli(tmp_path, "2.1.301"), workspace, shared_request(shared))
    argv = json.loads((tmp_path / "argv.json").read_text(encoding="utf-8"))
    assert argv[argv.index("--append-system-prompt-file") + 1] == str(shared.resolve())
    assert (tmp_path / "prompt.txt").read_text(encoding="utf-8") == "TASK"


def test_old_cli_falls_back_to_putting_the_rules_in_the_prompt(tmp_path):
    workspace = tmp_path / "ws"
    (workspace / "prompts").mkdir(parents=True)
    shared = workspace / "prompts" / "shared-1.txt"
    shared.write_text("SHARED RULES", encoding="utf-8")
    call(fake_cli(tmp_path, "2.1.300"), workspace, shared_request(shared))
    assert "--append-system-prompt-file" not in json.loads((tmp_path / "argv.json").read_text(encoding="utf-8"))
    assert (tmp_path / "prompt.txt").read_text(encoding="utf-8") == "SHARED RULES\nTASK"


def test_shared_file_outside_the_workspace_is_refused(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="inside the isolated run workspace"):
        call(fake_cli(tmp_path, "2.1.301"), workspace, shared_request(outside))
