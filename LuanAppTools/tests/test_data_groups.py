"""Host-side expansion of model-assigned DATA groups into the exact entity inventory."""
import asyncio
import copy
import json

import ezdxf
import fitz
import pytest

from LuanAppTools.ai.protocol import AIResult, ProviderError
from LuanAppTools.cad.evidence import prepare_evidence
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError, expand_data_groups
from LuanAppTools.tests.test_pipeline import setup  # noqa: F401  (pytest fixture)


@pytest.fixture
def evidence(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    pdf = fitz.open()
    pdf.new_page(width=200, height=100)
    pdf.save(source / "drawing.pdf")
    pdf.close()
    d = ezdxf.new()
    msp = d.modelspace()
    msp.add_lwpolyline([(0, 0), (40, 0), (40, 20), (0, 20)], close=True)
    msp.add_circle((20, 10), 4)
    msp.add_line((200, 0), (240, 0))
    d.saveas(source / "data.dxf")
    return prepare_evidence(source, tmp_path / "work")


def _ids(ev):
    return {"data.dxf#" + e["id"] for e in ev.dxf[0]["entities"]}


def test_groups_expand_to_exact_entity_inventory(evidence):
    data = {"data_entities": [], "data_groups": [
        {"id": "data.dxf#G1", "codes": ["26-000001"], "disposition": "part"},
        {"id": "data.dxf#G2", "codes": [], "disposition": "drawing_only"},
    ]}
    result = expand_data_groups(copy.deepcopy(data), evidence)
    assert "data_groups" not in result
    assert {d["id"] for d in result["data_entities"]} == _ids(evidence)
    owner = {d["id"]: d for d in result["data_entities"]}
    first = evidence.dxf[0]["groups"][0]["entity_ids"]
    assert all(owner[i]["codes"] == ["26-000001"] and owner[i]["disposition"] == "part" for i in first)
    last = evidence.dxf[0]["groups"][1]["entity_ids"]
    assert all(owner[i]["codes"] == [] and owner[i]["disposition"] == "drawing_only" for i in last)


def test_entity_can_be_split_out_of_a_group_explicitly(evidence):
    circle = next(e["id"] for e in evidence.dxf[0]["entities"] if e["type"] == "CIRCLE")
    hole = "data.dxf#" + circle
    data = {"data_entities": [{"id": hole, "codes": ["26-000002"]}], "data_groups": [
        {"id": "data.dxf#G1", "codes": ["26-000001"], "exclude": [hole]},
        {"id": "data.dxf#G2", "codes": [], "disposition": "drawing_only"},
    ]}
    result = expand_data_groups(data, evidence)
    owner = {d["id"]: d for d in result["data_entities"]}
    assert owner[hole]["codes"] == ["26-000002"] and len(owner) == len(_ids(evidence))
    assert not any("exclude" in d for d in result["data_entities"])


@pytest.mark.parametrize("groups, explicit", [
    ([{"id": "data.dxf#G9", "codes": []}], False),  # unknown group
    ([{"id": "data.dxf#G1", "codes": []}, {"id": "data.dxf#G1", "codes": []}], False),  # group twice
    ([{"id": "data.dxf#G1", "codes": []}], True),  # explicit entity also inside a group
    ([{"id": "data.dxf#G1", "codes": [], "exclude": ["data.dxf#NOPE"]}], False),  # exclude outside group
])
def test_ambiguous_group_assignments_are_rejected(evidence, groups, explicit):
    entities = [{"id": evidence.dxf[0]["groups"][0]["entity_ids"][0], "codes": []}] if explicit else []
    with pytest.raises(PipelineError) as error:
        expand_data_groups({"data_entities": entities, "data_groups": groups}, evidence)
    assert error.value.kind == "inventory_invalid"


def test_payload_without_groups_is_unchanged(evidence):
    data = {"data_entities": [{"id": "x", "codes": []}]}
    assert expand_data_groups(copy.deepcopy(data), evidence) == data


class IntakeOnlyRunner:
    """Answers intake with DATA groups, then refuses the solve stage."""

    def __init__(self):
        self.requests = []

    async def complete(self, request, *, workspace, cancel, emit):
        self.requests.append(request)
        context = json.loads(request.prompt.split("\nCONTEXT_JSON\n", 1)[1])
        if context["stage"] != "intake":
            raise ProviderError("unavailable", "stop after intake")
        groups = context["evidence"]["dxf"][0]["groups"]
        data = {
            "pages": [{"page_id": "source.pdf:p1", "disposition": "inspected"}],
            "views": [{"id": "v1", "page_id": "source.pdf:p1", "rect": [0, 0, 300, 300], "codes": ["26-000001"]}],
            "notes": [],
            "data_entities": [],
            "data_groups": [{"id": g["id"], "codes": ["26-000001"]} for g in groups],
            "codes": [{
                "code": "26-000001", "page_ids": ["source.pdf:p1"], "view_ids": ["v1"], "note_ids": [],
                "data_ids": [],  # the host completes this from the expanded inventory
                "difficulty": "easy", "difficulty_evidence": ["source.pdf:p1"], "independent": False,
                "census": {"source_mode": "PDF_DATA_RAW", "part_mode": "FLAT_NO_BEND",
                           "reference_present": "NO", "multi_code_or_assembly": "NO",
                           "features": {k: "NO" for k in context["feature_families"]}},
            }],
        }
        return AIResult(data, {}, "fixture", request.model, request.effort)


def test_pipeline_sends_compact_evidence_and_stores_expanded_inventory(setup):  # noqa: F811
    repo, source, control = setup
    d = ezdxf.new()
    d.modelspace().add_lwpolyline([(0, 0), (40, 0), (40, 20), (0, 20)], close=True)
    d.modelspace().add_circle((20, 10), 4)
    d.saveas(source / "data.dxf")
    runner = IntakeOnlyRunner()
    with pytest.raises((PipelineError, ProviderError)):
        asyncio.run(CadPipeline(repo, runner).run(source, control, job_name="GROUPS"))
    assert '"attributes"' not in runner.requests[0].prompt
    assert '"vertices"' not in runner.requests[0].prompt  # intake sees group summaries only
    assert "data_group" in runner.requests[0].prompt
    inventory = control.store.get_run(control.run_id)["checkpoint"]["inventory"]
    assert len(inventory["data_entities"]) == 2 and "data_groups" not in inventory
    assert sorted(inventory["codes"][0]["data_ids"]) == sorted(d["id"] for d in inventory["data_entities"])


def _inventory(**overrides):
    inventory = {
        "pages": [{"page_id": "a.pdf:p1"}, {"page_id": "a.pdf:p2"}, {"page_id": "a.pdf:p3"}],
        "views": [
            {"id": "v1", "page_id": "a.pdf:p1", "codes": ["26-000001"]},
            {"id": "v2", "page_id": "a.pdf:p2", "codes": ["26-000001", "26-000002"]},
        ],
        "notes": [{"id": "n1", "page_id": "a.pdf:p2", "codes": ["26-000002"]}],
        "data_entities": [{"id": "d#1", "codes": ["26-000001"]}, {"id": "d#2", "codes": []}],
        "codes": [
            {"code": "26-000001", "page_ids": ["a.pdf:p1"], "view_ids": [], "note_ids": [], "data_ids": []},
            {"code": "26-000002", "page_ids": ["a.pdf:p3"], "view_ids": ["v2"], "note_ids": ["wrong"], "data_ids": ["d#2"]},
        ],
    }
    inventory.update(overrides)
    return inventory


def test_code_links_are_derived_from_item_ownership():
    from LuanAppTools.cad.pipeline import complete_code_links

    original = _inventory()
    snapshot = copy.deepcopy(original)
    result = complete_code_links(original)
    assert original == snapshot  # input is not mutated
    first, second = result["codes"]
    assert first["view_ids"] == ["v1", "v2"] and first["note_ids"] == [] and first["data_ids"] == ["d#1"]
    assert second["view_ids"] == ["v2"] and second["note_ids"] == ["n1"] and second["data_ids"] == []
    # Pages are the model's pages plus every page its views and notes sit on.
    assert first["page_ids"] == ["a.pdf:p1", "a.pdf:p2"]
    assert second["page_ids"] == ["a.pdf:p3", "a.pdf:p2"]


def test_code_links_leave_malformed_payloads_for_validation():
    from LuanAppTools.cad.pipeline import complete_code_links

    assert complete_code_links({"codes": "nope"}) == {"codes": "nope"}
    partial = {"codes": [{"code": "26-000001"}], "views": [{"id": "v", "codes": ["26-000001"]}]}
    assert complete_code_links(partial)["codes"][0]["view_ids"] == ["v"]  # missing page_id tolerated


def test_pipeline_accepts_an_intake_whose_code_lists_omit_pages(setup):  # noqa: F811
    repo, source, control = setup
    d = ezdxf.new()
    d.modelspace().add_circle((20, 10), 4)
    d.saveas(source / "data.dxf")

    class SparseRunner(IntakeOnlyRunner):
        async def complete(self, request, **kwargs):
            result = await super().complete(request, **kwargs)
            code = result.data["codes"][0]
            code.update(page_ids=[], view_ids=[], note_ids=[], data_ids=[])
            return result

    with pytest.raises((PipelineError, ProviderError)):
        asyncio.run(CadPipeline(repo, SparseRunner()).run(source, control, job_name="SPARSE"))
    inventory = control.store.get_run(control.run_id)["checkpoint"]["inventory"]
    code = inventory["codes"][0]
    assert code["page_ids"] == ["source.pdf:p1"] and code["view_ids"] == ["v1"] and len(code["data_ids"]) == 1


def test_source_mode_is_pinned_to_the_job_source_relationship():
    from LuanAppTools.cad.pipeline import pin_source_mode

    data = {"codes": [
        {"code": "26-000001", "census": {"source_mode": "PDF_ONLY", "reference_present": "NO"}},
        {"code": "26-000002", "census": {"source_mode": "PDF_DATA_RAW", "reference_present": "NO"}},
    ]}
    snapshot = copy.deepcopy(data)
    result = pin_source_mode(data, "PDF_DATA_RAW")
    assert data == snapshot
    assert [c["census"]["source_mode"] for c in result["codes"]] == ["PDF_DATA_RAW", "PDF_DATA_RAW"]
    # Only the source relationship is pinned: a claimed reference still fails validation.
    data["codes"][0]["census"]["reference_present"] = "YES"
    assert pin_source_mode(data, "PDF_DATA_RAW")["codes"][0]["census"]["reference_present"] == "YES"
    assert pin_source_mode({"codes": "nope"}, "PDF_ONLY") == {"codes": "nope"}


def test_pipeline_accepts_a_per_code_pdf_only_claim_when_the_job_has_data(setup):  # noqa: F811
    repo, source, control = setup
    d = ezdxf.new()
    d.modelspace().add_circle((20, 10), 4)
    d.saveas(source / "data.dxf")

    class WrongModeRunner(IntakeOnlyRunner):
        async def complete(self, request, **kwargs):
            result = await super().complete(request, **kwargs)
            result.data["codes"][0]["census"]["source_mode"] = "PDF_ONLY"
            return result

    with pytest.raises((PipelineError, ProviderError)):
        asyncio.run(CadPipeline(repo, WrongModeRunner()).run(source, control, job_name="MODE"))
    inventory = control.store.get_run(control.run_id)["checkpoint"]["inventory"]
    assert inventory["codes"][0]["census"]["source_mode"] == "PDF_DATA_RAW"
