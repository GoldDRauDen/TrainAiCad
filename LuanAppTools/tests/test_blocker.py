"""The model records why a part is not PASS in a host-owned `blocker`; the repository never sees it."""
import asyncio
import json
from types import SimpleNamespace

from LuanAppTools.ai.tools import HostTools
from LuanAppTools.cad.contract import BLOCKER_CLASSES, HOST_BLOCKER_NOTE, solve_part_schema, split_blocker
from LuanAppTools.cad.pipeline import CadPipeline
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner

CHECKS = ["contour_topology", "datum", "feature_count", "unfold", "containment",
          "bend_domain", "material_rules", "slot_semantics"]
BLOCKER = {"class": "PART_IDENTITY_GAP", "rule": "references/PART_IDENTITY_GRAPH.md", "evidence": "N6_HW_AB"}


def test_split_blocker_removes_the_host_key_and_keeps_the_rest():
    part = {"code": "c", "blocker": dict(BLOCKER)}
    rest, blocker = split_blocker(part)
    assert rest == {"code": "c"} and blocker == BLOCKER
    assert "blocker" in part  # the input is not modified
    assert split_blocker({"code": "c"}) == ({"code": "c"}, None)
    assert split_blocker("not a dict") == ("not a dict", None)


def test_schema_offers_the_blocker_classes():
    blocker = solve_part_schema(CHECKS, "26-000001")["properties"]["blocker"]
    assert BLOCKER_CLASSES == [
        "TRUE_SOURCE_AMBIGUITY", "AI_INTERPRETATION_GAP", "SOURCE_MEMBER_CENSUS_GAP", "PART_IDENTITY_GAP",
        "GEOMETRY_DECODE_GAP", "ROUTING_COVERAGE_GAP", "CUSTOMER_CONFIRMATION_PENDING"]
    assert blocker["properties"]["class"]["enum"] == BLOCKER_CLASSES
    assert blocker["required"] == ["class", "rule"]
    assert all(name in HOST_BLOCKER_NOTE for name in BLOCKER_CLASSES)


class BlockerRunner(SingleRunner):
    async def complete(self, request, **kwargs):
        result = await super().complete(request, **kwargs)
        if "part" in result.data:
            result.data["part"]["blocker"] = dict(BLOCKER)
        return result


def test_pipeline_records_blocker_and_keeps_it_out_of_the_export(setup):  # noqa: F811
    repo, source, control = setup
    runner = BlockerRunner({"26-000001": synthetic_part()})
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="BLOCK"))
    events = [e["payload"] for e in control.store.events_since(control.run_id, 0) if e["kind"] == "blocker_recorded"]
    assert [(e["code"], e["blocker"]) for e in events] == [("26-000001", BLOCKER)]
    state = control.store.get_run(control.run_id)["checkpoint"]["parts"]["26-000001"]
    assert state["blocker"] == BLOCKER and "blocker" not in state["candidate"]
    canonical = json.loads((control.workspace / "aggregate" / "canonical.json").read_text(encoding="utf-8"))
    assert all("blocker" not in part for part in canonical["parts"])


def test_solve_prompt_asks_for_a_blocker_when_the_part_is_not_pass(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner({"26-000001": synthetic_part()})
    asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="BLOCK"))
    prompt = runner.requests[1].prompt
    assert "blocker" in prompt and "HOLISTIC_ENGINEERING_CHALLENGE" in prompt


def test_validate_tool_strips_the_blocker_before_the_repository_sees_the_part(tmp_path):
    seen = {}

    class Repo:
        contract = "TrainAiCad-CANONICAL-V4.34"

        async def validate(self, job, workspace, cancel, *, timeout):
            seen["parts"] = job["parts"]
            return {"ok": True}

    tools = HostTools(Repo(), SimpleNamespace(workspace=tmp_path), [], "JOB", asyncio.Event())
    call = {"name": "validate", "arguments": {"part": {"code": "c", "status": "PASS", "blocker": dict(BLOCKER)}}}
    assert asyncio.run(tools.execute(call))[0] == {"ok": True}
    assert "blocker" not in seen["parts"][0]
