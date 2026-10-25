"""VIEWS_ONLY must earn the exhaustion record the repository's own guard defines."""
import asyncio
from pathlib import Path

import pytest

from LuanAppTools.cad.contract import (
    HOST_VIEWS_ONLY_NOTE, ContractError, check_flat_attempt, flat_arithmetic_notes, prepare_part)
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError
from LuanAppTools.cad.repository import CadError
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner

ROOT = Path(__file__).resolve().parents[2]
NOTE = {"id": "n_calc", "page_id": "source.pdf:p1", "text": "Handwritten 80+60-9.78=130.22", "codes": ["26-000001"]}
OTHER = {"id": "n_misc", "page_id": "source.pdf:p1", "text": "2-M8; A+B+C (reference)", "codes": ["26-000001"]}


def views_only_part(*, record=False, cite=("v1",)):
    part = synthetic_part()
    part.update(status="VIEWS_ONLY", preview_reason="separate_source_views", flags=["bend attachment unresolved"])
    part["entities"][0]["view_id"] = "FRONT"
    if record:
        part.update(
            source_exhausted=True, holistic_challenge_run=True, flat_attempted=True,
            face_graph_candidates=[{"candidate_id": "C1", "constraint_result": "attachment edge ambiguous",
                                    "evidence_used": list(cite)}],
            unresolved_objects=[{"object": "bend attachment edge"}],
        )
    return part


def test_flat_arithmetic_notes_recognise_printed_sums_only():
    assert [n["id"] for n in flat_arithmetic_notes([NOTE, OTHER])] == ["n_calc"]
    assert flat_arithmetic_notes([{"id": "x", "text": "161+41-9.78=192.22 ; 73+71-9.78=134.22"}])
    assert flat_arithmetic_notes([]) == []


def test_prepare_part_sets_host_owned_flags_only_when_arithmetic_exists():
    flat = prepare_part(synthetic_part(), [NOTE])
    assert flat["high_source_evidence"] is True and flat["flat_attempted"] is True
    views = prepare_part(views_only_part(), [NOTE])
    assert views["high_source_evidence"] is True and "flat_attempted" not in views
    plain = synthetic_part()
    assert prepare_part(plain, [OTHER]) == plain
    explicit = synthetic_part()
    explicit["flat_attempted"] = False
    assert prepare_part(explicit, [NOTE])["flat_attempted"] is False  # never overrides the model


def test_views_only_must_cite_flat_arithmetic_notes():
    with pytest.raises(ContractError, match=r"FLAT_ARITHMETIC_NOT_TESTED.*n_calc.*80\+60-9\.78=130\.22"):
        check_flat_attempt(views_only_part(record=True), [NOTE])
    check_flat_attempt(views_only_part(record=True, cite=("v1", "n_calc")), [NOTE])
    check_flat_attempt(views_only_part(record=True), [OTHER])  # no arithmetic, nothing to cite
    check_flat_attempt(synthetic_part(), [NOTE])  # only VIEWS_ONLY is gated here


def test_views_only_passes_only_with_the_full_exhaustion_record(setup, tmp_path):  # noqa: F811
    repo = setup[0]

    def validate(part):
        job = {"canonical_contract": repo.contract, "job_id": "T", "parts": [part]}
        return asyncio.run(repo.validate(job, tmp_path / "validate", asyncio.Event()))

    with pytest.raises(CadError) as bare:
        validate(views_only_part())
    assert "VIEWS_ONLY_BEFORE_SOURCE_EXHAUSTION" in str(bare.value)
    assert "VIEWS_ONLY_BEFORE_HOLISTIC_CHALLENGE" in str(bare.value)

    claimed = views_only_part()
    claimed.update(source_exhausted=True, holistic_challenge_run=True)
    with pytest.raises(CadError, match="VIEWS_ONLY_SOURCE_EXHAUSTION_UNPROVED"):
        validate(claimed)

    assert validate(views_only_part(record=True))["parts"]


class NotedRunner(SingleRunner):
    def __init__(self, parts):
        super().__init__(parts)

    async def complete(self, request, **kwargs):
        result = await super().complete(request, **kwargs)
        if "codes" in result.data:  # intake: the drawing carries printed flat arithmetic
            result.data["notes"] = [dict(NOTE)]
            for view in result.data["views"]:  # the intake now records the printed dimensions of every view
                view["dimensions"] = []
        return result


def test_pipeline_rejects_views_only_that_ignores_flat_arithmetic(setup):  # noqa: F811
    repo, source, control = setup
    runner = NotedRunner({"26-000001": views_only_part(record=True)})
    with pytest.raises(PipelineError, match="Some codes have no"):
        asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="GATE"))
    issues = control.store.get_run(control.run_id)["checkpoint"]["parts"]["26-000001"]["issues"]
    assert issues and all("FLAT_ARITHMETIC_NOT_TESTED" in issue for issue in issues)


def test_pipeline_accepts_views_only_that_tested_the_arithmetic(setup):  # noqa: F811
    repo, source, control = setup
    runner = NotedRunner({"26-000001": views_only_part(record=True, cite=("v1", "n_calc"))})
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="GATE"))
    assert [p.status for p in result.parts] == ["VIEWS_ONLY"]
    assert "GATE_ALL_REVIEW_ONLY.dxf" in result.staged_files


def test_solve_prompt_explains_views_only_requirements(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part()})
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="GATE"))
    prompt = runner.requests[1].prompt
    assert "face_graph_candidates" in prompt and "separate_source_views" in prompt


def test_host_note_keys_exist_in_the_guard_source():
    guard = (ROOT / "tools" / "holistic_engineering_guard.py").read_text(encoding="utf-8")
    for key in ("source_exhausted", "holistic_challenge_run", "face_graph_candidates", "unresolved_objects",
                "proved_source_view_member_ids", "views_only_canonical_member_ids", "flat_attempted",
                "high_source_evidence"):
        assert key in HOST_VIEWS_ONLY_NOTE and key in guard, key
