"""The minimal prompt names the role, the rules to read and the deliverable; everything else is the repository's."""
import asyncio

import pytest

from LuanAppTools.cad.contract import HOST_VIEWS_ONLY_NOTE
from LuanAppTools.cad.pipeline import CadPipeline
from LuanAppTools.cad.prompts import MINIMAL_PREAMBLE, minimal_task
from LuanAppTools.core.settings import Settings
from LuanAppTools.service.controller import ApplicationService
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_settings_default_to_the_minimal_prompt_and_reject_unknown_styles(tmp_path):
    settings = Settings(data_dir=tmp_path, validate_roots=False)
    assert settings.prompt_style == "minimal" and settings.public_dict()["prompt_style"] == "minimal"
    with pytest.raises(ValueError, match="prompt style"):
        Settings(data_dir=tmp_path, validate_roots=False, prompt_style="verbose")
    assert Settings(data_dir=tmp_path, validate_roots=False, prompt_style="full").prompt_style == "full"


def test_minimal_task_states_role_rules_and_deliverable():
    assert "sheet-metal mechanical engineer" in MINIMAL_PREAMBLE
    intake = minimal_task("intake", individual=False, output_folder=None)
    for name in ("AI_BOOTSTRAP", "AI_ENTRYPOINT", "FEATURE_CENSUS", "ROUTER.yaml"):
        assert name in intake
    assert "dimensions" in intake and "owner" in intake  # the two fields the host's checks need
    solve = minimal_task("solve", individual=False, output_folder=None)
    assert "validate tool" in solve
    assert "one combined DXF" in solve and "input folder" in solve and "individual" not in solve.replace("no individual", "")
    both = minimal_task("solve", individual=True, output_folder="D:\\OUT")
    assert "D:\\OUT" in both and "individual part DXFs" in both and "no individual" not in both


def test_minimal_style_replaces_the_long_host_notes(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part()})
    asyncio.run(CadPipeline(repo, runner, single_agent=True, prompt_style="minimal").run(
        source, control, job_name="MIN", individual=True, output_folder="D:\\OUT"))
    intake, solve = runner.requests[0].prompt, runner.requests[1].prompt
    assert MINIMAL_PREAMBLE in intake and "sheet-metal mechanical engineer" in solve
    assert "individual part DXFs" in solve and "D:\\OUT" in solve
    assert HOST_VIEWS_ONLY_NOTE[:60] not in solve  # the rules themselves still carry their own wording
    assert "Set source_exhausted=true and holistic_challenge_run=true only after" not in solve


def test_full_style_keeps_the_pre_migration_prompt(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part()})
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="FULL"))
    assert HOST_VIEWS_ONLY_NOTE[:60] in runner.requests[1].prompt
    assert "sheet-metal mechanical engineer" not in runner.requests[1].prompt


def test_new_runs_carry_the_prompt_style_and_the_output_folder(tmp_path):
    service = ApplicationService(tmp_path / "app", ROOT)
    assert service._config({})["prompt_style"] == "minimal"
    service.update_settings({"prompt_style": "full"})
    assert service._config({})["prompt_style"] == "full"
