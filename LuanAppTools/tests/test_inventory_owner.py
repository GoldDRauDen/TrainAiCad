"""Printed flat arithmetic needs an owning code, and the views need their printed dimensions."""
import asyncio
from types import SimpleNamespace

import pytest

from LuanAppTools.cad.pipeline import CadPipeline, PipelineError, interaction_schema, validate_inventory
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner

EVIDENCE = SimpleNamespace(pages=[{"id": "p1"}], dxf=[])
ARITHMETIC = {"id": "n1", "page_id": "p1", "text": "80+60-9.78=130.22", "codes": ["26-000001"]}
VIEW = {"id": "v1", "page_id": "p1", "rect": [0, 0, 1, 1], "codes": ["26-000001"]}


def inventory(notes, views, **code):
    return {
        "pages": [{"page_id": "p1", "disposition": "inspected"}],
        "views": views, "notes": notes, "data_entities": [],
        "codes": [{"code": "26-000001", "page_ids": ["p1"], "view_ids": [v["id"] for v in views],
                   "note_ids": [n["id"] for n in notes if "26-000001" in n["codes"]], "data_ids": [],
                   "census": {"source_mode": "PDF_ONLY", "reference_present": "NO"}, **code}],
    }


def check(data, **kwargs):
    return validate_inventory(data, EVIDENCE, "PDF_ONLY", require_difficulty=False, **kwargs)


def test_flat_arithmetic_note_without_owner_is_rejected():
    note = {**ARITHMETIC, "codes": [], "disposition": "scope unresolved"}
    with pytest.raises(PipelineError, match="owning code.*n1"):
        check(inventory([note], [{**VIEW, "dimensions": [80, 60]}]))


def test_both_intake_problems_are_reported_in_one_error():
    note = {**ARITHMETIC, "codes": [], "disposition": "scope unresolved"}
    with pytest.raises(PipelineError) as raised:
        check(inventory([note], [VIEW]))  # no owner and no dimensions: one repair turn must be enough
    assert "owning code" in str(raised.value) and "printed dimensions" in str(raised.value)


def test_views_need_dimensions_when_arithmetic_exists():
    with pytest.raises(PipelineError, match="printed dimensions"):
        check(inventory([ARITHMETIC], [VIEW]))
    data = inventory([ARITHMETIC], [{**VIEW, "dimensions": []}])
    assert check(data) == data


def test_plain_unscoped_note_is_still_allowed():
    note = {"id": "n2", "page_id": "p1", "text": "2-M8", "codes": [], "disposition": "administrative"}
    data = inventory([note], [VIEW])
    assert check(data) == data


def test_multi_agent_intake_is_unaffected():
    note = {**ARITHMETIC, "codes": [], "disposition": "scope unresolved"}
    data = inventory([note], [VIEW], difficulty="easy", difficulty_evidence=["p1"])
    assert validate_inventory(data, EVIDENCE, "PDF_ONLY", require_difficulty=True) == data


def test_intake_schema_documents_dimensions():
    view = interaction_schema("intake", single_agent=True)["properties"]["views"]["items"]
    assert view["properties"]["dimensions"] == {"type": "array", "items": {"type": "number"}}
    assert "dimensions" not in view["required"]


class OwnerRunner(SingleRunner):
    """The first intake answer leaves the printed arithmetic ownerless; the repair turn assigns it."""

    intakes = 0

    async def complete(self, request, **kwargs):
        result = await super().complete(request, **kwargs)
        if "codes" in result.data:
            OwnerRunner.intakes += 1
            owners = [] if OwnerRunner.intakes == 1 else ["26-000001"]
            note = {"id": "n1", "page_id": "source.pdf:p1", "text": "80+60-9.78=130.22", "codes": owners}
            if not owners:
                note["disposition"] = "scope unresolved"
            result.data["notes"] = [note]
            for view in result.data["views"]:
                view["dimensions"] = [80, 60, 6]
        return result


def test_ownerless_note_is_repaired_in_the_same_conversation(setup):  # noqa: F811
    repo, source, control = setup
    OwnerRunner.intakes = 0
    runner = OwnerRunner({"26-000001": synthetic_part()})
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="OWNER"))
    assert result.staged_files and len(runner.requests) == 3  # intake, its repair, one solve
    assert "owning code" in runner.requests[1].prompt
    assert "owning code" in runner.requests[0].prompt  # the intake task itself names the owner rule
