"""customer_code from the job statistics reaches the resolver and the job; KH851 carries its weld census."""
import asyncio
import json
from pathlib import Path

import pytest

from LuanAppTools.cad.contract import WELD_SITE_PROPERTIES, prepare_part
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError, pin_customer
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner
from LuanAppTools.tests.test_views_only_gate import views_only_part

ROOT = Path(__file__).resolve().parents[2]


class CustomerRunner(SingleRunner):
    """Intake reports `customers[n]` on its n-th call (the last one repeats); optional weld census."""

    def __init__(self, parts, customers, weld_from=None):
        super().__init__(parts)
        self.customers, self.weld_from, self.intakes = customers, weld_from, 0

    async def complete(self, request, **kwargs):
        result = await super().complete(request, **kwargs)
        if "codes" in result.data:
            customer = self.customers[min(self.intakes, len(self.customers) - 1)]
            self.intakes += 1
            result.data["customer_code"] = customer
            result.data["customer_code_evidence"] = "slip header"
            if customer == "851" and self.weld_from is not None and self.intakes >= self.weld_from:
                for code in result.data["codes"]:
                    code["census"]["features"]["KEGAKI"] = "YES"
                    code["weld"] = weld(code["code"])
        return result


def weld(code):
    return {
        "source_assembly_view_ids": ["v1"],
        "source_weld_site_ids": ["W1"],
        "weld_site_census": {
            "inspected_assembly_view_ids": ["v1"],
            "source_evidence": "assembly view v1 shows plate C1 welded to the main plate",
            "sites": [{"weld_site_id": "W1", "status": "FLAGGED", "child_part_id": "C1", "assembly_view_id": "v1",
                       "source_evidence": "plate C1 contact line in view v1", "mark_member_ids": ["MK1"],
                       "unresolved_fields": ["host face"]}],
        },
    }


def census_of(control, code="26-000001"):
    return json.loads((control.workspace / "routing" / code / "census.json").read_text(encoding="utf-8"))


def run_pipeline(setup, runner):  # noqa: F811
    repo, source, control = setup
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="CUSTOMER"))
    return result, control


def test_customer_code_reaches_the_resolver_the_prompt_and_the_job(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": synthetic_part()}, ["859"])
    _, control = run_pipeline(setup, runner)
    assert census_of(control)["customer_code"] == "859"
    context = json.loads(runner.requests[1].prompt.rsplit("CONTEXT_JSON\n", 1)[1])
    assert context["code"]["census"]["customer_code"] == "859"
    job = json.loads((control.workspace / "aggregate" / "canonical.json").read_text(encoding="utf-8"))
    assert job["customer_code"] == "859"


def test_no_customer_code_keeps_the_current_behaviour(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": synthetic_part()}, [None])
    _, control = run_pipeline(setup, runner)
    assert "customer_code" not in census_of(control)
    assert "customer_code" not in json.loads((control.workspace / "aggregate" / "canonical.json").read_text())


def test_non_numeric_customer_code_is_repaired_inside_the_intake_conversation(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": synthetic_part()}, ["KH-851", None])
    run_pipeline(setup, runner)
    assert len(runner.requests) == 3 and runner.requests[0].session_id == runner.requests[1].session_id
    assert "customer_code" in runner.requests[1].prompt.rsplit("CONTEXT_JSON\n", 1)[1]


def test_pin_customer_defaults_and_validation():
    data = {"customer_code": " 0851 ", "views": [{"id": "v1"}], "codes": [{"code": "26-000001", "census": {"features": {}}, "weld": {
        "source_assembly_view_ids": ["v1"], "source_weld_site_ids": ["W1"],
        "weld_site_census": {"sites": [{"weld_site_id": "W1"}]}}}]}
    pinned = pin_customer(data)
    census = pinned["codes"][0]["census"]
    assert pinned["customer_code"] == "851" and census["customer_code"] == "851"
    assert census["part_code"] == "26-000001"
    site = census["weld_site_census"]["sites"][0]
    assert site["parent_code"] == "26-000001" and site["mark_status"] == "FLAGGED" and site["unresolved_fields"]
    with pytest.raises(PipelineError, match="customer_code"):
        pin_customer({"customer_code": "KH851", "codes": []})


def test_prepare_part_copies_the_weld_census_without_overriding_the_model():
    census = {"source_assembly_view_ids": ["v1"], "source_weld_site_ids": ["W1"], "weld_site_census": {"sites": []}}
    part = prepare_part(synthetic_part(), [], census)
    assert part["source_assembly_view_ids"] == ["v1"]
    assert part["weld_site_census"] == {"sites": [], "inspected_assembly_view_ids": ["v1"]}
    own = synthetic_part()
    own["source_weld_site_ids"] = ["MINE"]
    assert prepare_part(own, [], census)["source_weld_site_ids"] == ["MINE"]
    census["weld_site_census"]["sites"].append("x")  # the copy is independent of the census
    assert part["weld_site_census"]["sites"] == []


def test_weld_schema_covers_every_site_key_the_repository_reads():
    import ast
    tree = ast.parse((ROOT / "tools" / "weld_kegaki_guard.py").read_text(encoding="utf-8"))
    read = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "site"
                and isinstance(node.args[0], ast.Constant)):
            read.add(node.args[0].value)
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "site"
                and isinstance(node.slice, ast.Constant)):
            read.add(node.slice.value)
    assert read - set(WELD_SITE_PROPERTIES) == set()


def kh851_part():
    part = views_only_part(record=True)
    part["source_groups"].append({"group_id": "GK", "family": "KEGAKI", "status": "FLAGGED", "source_quantity": 1,
                                  "members": [{"member_id": "MK1", "status": "FLAGGED"}]})
    part["canonical_members"].append({"canonical_member_id": "CMK", "origin": "SOURCE", "source_member_id": "MK1",
                                      "group_id": "GK", "status": "FLAGGED_NO_GEOMETRY", "entity_ids": []})
    return part


def test_kh851_without_a_weld_census_is_repaired_once_then_flows_to_export(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": kh851_part()}, ["851"], weld_from=2)
    result, control = run_pipeline(setup, runner)
    assert len(runner.requests) == 3  # intake, intake repair, solve
    assert "weld_site_census" in runner.requests[1].prompt.rsplit("CONTEXT_JSON\n", 1)[1]
    census = census_of(control)
    assert census["customer_code"] == "851" and census["source_weld_site_ids"] == ["W1"]
    job = json.loads((control.workspace / "aggregate" / "canonical.json").read_text(encoding="utf-8"))
    part = job["parts"][0]
    assert job["customer_code"] == "851" and part["source_weld_site_ids"] == ["W1"]
    assert [p.status for p in result.parts] == ["VIEWS_ONLY"]


def test_kh851_that_never_supplies_the_weld_census_stops_with_the_repository_message(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": synthetic_part()}, ["851"])
    with pytest.raises(PipelineError) as stopped:
        run_pipeline(setup, runner)
    assert stopped.value.kind == "inventory_invalid" and "weld_site_census" in str(stopped.value)
    assert len(runner.requests) == 2  # intake and exactly one repair; no solve was paid for


def test_resolver_survives_customer_notes_with_non_ascii_text(setup, tmp_path):  # noqa: F811
    # Customer 859's catalog note contains a '>=' sign; a Windows pipe used to crash the tool on it.
    repo = setup[0]
    census = {"source_mode": "PDF_ONLY", "part_mode": "FLAT_NO_BEND", "reference_present": "NO",
              "multi_code_or_assembly": "NO", "customer_code": "859",
              "features": {name: "NO" for name in repo.router["feature_routes"]}}
    route = asyncio.run(repo.resolve(census, tmp_path / "route", asyncio.Event()))
    assert any(ord(ch) > 127 for note in route["customer_rules"]["notes"] for ch in note)


def weld_data(assembly, inspected, views=("v1",)):
    return {"customer_code": "851", "views": [{"id": v} for v in views], "codes": [
        {"code": "26-000001", "census": {"features": {}}, "weld": {
            "source_assembly_view_ids": list(assembly), "source_weld_site_ids": [],
            "weld_site_census": {"inspected_assembly_view_ids": list(inspected), "source_evidence": "x" * 10,
                                 "no_weld_evidence": "no weld symbol in any view", "sites": []}}}]}


def test_inspected_views_are_derived_from_the_assembly_views():
    # Every original page is already proved inspected, so the model's second list is a pure echo.
    # It once listed all four inspected views next to an empty assembly list and failed the repository gate.
    pinned = pin_customer(weld_data([], ["v1", "v2", "v3"], views=("v1", "v2", "v3")))
    assert pinned["codes"][0]["census"]["weld_site_census"]["inspected_assembly_view_ids"] == []
    pinned = pin_customer(weld_data(["v1", "v2"], ["v1"], views=("v1", "v2")))
    assert pinned["codes"][0]["census"]["weld_site_census"]["inspected_assembly_view_ids"] == ["v1", "v2"]


def test_unknown_assembly_view_is_rejected_at_intake():
    with pytest.raises(PipelineError, match=r"26-000001.*unknown view.*ghost"):
        pin_customer(weld_data(["ghost"], [], views=("v1",)))


def test_every_failing_code_is_reported_in_one_repair_message(setup):  # noqa: F811
    runner = CustomerRunner({"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")}, ["851"])
    with pytest.raises(PipelineError) as stopped:
        run_pipeline(setup, runner)
    assert "26-000001" in str(stopped.value) and "26-000002" in str(stopped.value)
    repair = runner.requests[1].prompt.rsplit("CONTEXT_JSON\n", 1)[1]
    assert "26-000001" in json.loads(repair)["validation_error"] and "26-000002" in json.loads(repair)["validation_error"]


def test_prepare_part_fills_inspected_views_from_the_assembly_list():
    part = synthetic_part()
    part["source_assembly_view_ids"] = ["v1", "v2"]
    part["weld_site_census"] = {"source_evidence": "x" * 10, "sites": []}
    assert prepare_part(part, [])["weld_site_census"]["inspected_assembly_view_ids"] == ["v1", "v2"]
