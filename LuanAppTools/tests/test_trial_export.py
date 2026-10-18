"""validate must run the repository's real exporter, not only its contract checks.

Recorded in run 18798d71 (job 520925-07): 26-056152 and 26-056153 passed every host validation, were accepted as
VIEWS_ONLY, and only the final export refused them ("source views F_OUT/F_H1 must be separated by >=10 mm") after
all four codes had been paid for. That gate lives in tools/export_dxf.py::export_single_job, which validate skipped.
"""
import asyncio
import json

import pytest

from LuanAppTools.cad.pipeline import CadPipeline
from LuanAppTools.cad.repository import CadError
from LuanAppTools.tests.test_gates import ValidateFirstRunner
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_views_only_gate import views_only_part


def two_views(offset):
    """A VIEWS_ONLY part with a FRONT view (x 0..12, y 0..40) and a BACK view `offset` mm to the right."""
    part = views_only_part(record=True)
    x = offset
    part["entities"].append({
        "entity_id": "E_BACK", "type": "LWPOLYLINE", "role": "outer", "closed": True, "view_id": "BACK",
        "vertices": [[x + 2, 2, 0], [x + 8, 2, 0], [x + 8, 30, 0], [x + 2, 30, 0]],
    })
    part["canonical_members"][0]["entity_ids"].append("E_BACK")
    return part


def validate(repo, tmp_path, part):
    job = {"canonical_contract": repo.contract, "job_id": "TRIAL", "parts": [part]}
    return asyncio.run(repo.validate(job, tmp_path / "validate", asyncio.Event()))


def test_views_that_overlap_are_refused_by_validate(setup, tmp_path):  # noqa: F811
    repo = setup[0]
    with pytest.raises(CadError, match=r"source views FRONT/BACK must be separated by >=10 mm"):
        validate(repo, tmp_path, two_views(offset=0))


def test_separated_views_pass_validate_and_leave_nothing_behind_but_the_trial_folder(setup, tmp_path):  # noqa: F811
    repo = setup[0]
    assert validate(repo, tmp_path, two_views(offset=60))["parts"]
    assert validate(repo, tmp_path, two_views(offset=60))["parts"]  # the same workspace can be reused
    assert not list((tmp_path / "validate").glob("*.dxf"))


def test_the_model_sees_the_exporter_gate_in_its_own_validate_round(setup):  # noqa: F811
    repo, source, control = setup
    runner = ValidateFirstRunner({"26-000001": views_only_part(record=True)}, two_views(offset=0))
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="TRIAL"))
    follow_up = runner.requests[2].prompt.rsplit("CONTEXT_JSON\n", 1)[1]
    result = json.loads(follow_up)["tool_results"][0]["result"]
    assert "must be separated by >=10 mm" in result["error"]
    assert any(g["gate"].startswith("tools/export_dxf.py:") for g in result["gates"])


def test_a_part_the_exporter_accepts_costs_nothing_extra(setup, tmp_path):  # noqa: F811
    repo = setup[0]
    assert validate(repo, tmp_path, synthetic_part())["parts"]
