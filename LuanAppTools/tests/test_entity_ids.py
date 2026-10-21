"""Every code is solved in its own conversation, so two codes can both call their outline E_OUTER.

Recorded in run 18798d71 (job 520925-07): 26-056159 and 26-056160 both passed validation alone, then the
composite export stopped with "entity_id must be globally unique across the composite job" after ~23 model calls.
The host namespaces the colliding ids when it builds the composite job.
"""
import asyncio
import copy
import json

from LuanAppTools.cad.contract import ENTITY_ID_FORMAT, namespace_entity_ids
from LuanAppTools.cad.pipeline import CadPipeline
from LuanAppTools.tests.test_pipeline import setup, synthetic_part  # noqa: F401  (pytest fixture)
from LuanAppTools.tests.test_single_agent import SingleRunner


def part(code, ids=("E_OUTER", "E_HOLE")):
    return {
        "code": code,
        "entities": [{"entity_id": i, "type": "LINE"} for i in ids],
        "canonical_members": [{"canonical_member_id": "CM_1", "entity_ids": list(ids)}],
        "feature_witness_graph": {"targets": [{"entity_id": ids[0], "datum_entity_id": ids[-1]}]},
        "face_graph": {"bends": [{"material_domain": {"entity_ids": [ids[0]]}}]},
        "flags": ["E_OUTER is only mentioned in this text"],
    }


def all_ids(parts):
    return [e["entity_id"] for p in parts for e in p["entities"]]


def test_colliding_ids_of_a_later_part_get_the_work_number_and_every_reference_follows():
    first, second = part("26-056159"), part("26-056160")
    result = namespace_entity_ids([first, second])
    assert result[0] == first  # the first owner keeps its ids
    ids = all_ids(result)
    assert len(ids) == len(set(ids)) == 4
    renamed = result[1]
    new_outer, new_hole = (e["entity_id"] for e in renamed["entities"])
    assert new_outer == "26056160_E_OUTER" and new_hole == "26056160_E_HOLE"
    assert renamed["canonical_members"][0]["entity_ids"] == [new_outer, new_hole]
    assert renamed["feature_witness_graph"]["targets"][0] == {"entity_id": new_outer, "datum_entity_id": new_hole}
    assert renamed["face_graph"]["bends"][0]["material_domain"]["entity_ids"] == [new_outer]
    assert renamed["flags"] == ["E_OUTER is only mentioned in this text"]  # text is not a reference


def test_input_is_not_modified_and_the_rename_is_stable():
    parts = [part("26-056159"), part("26-056160")]
    before = copy.deepcopy(parts)
    once = namespace_entity_ids(parts)
    assert parts == before
    assert namespace_entity_ids(once) == once  # nothing collides any more


def test_parts_without_a_collision_are_returned_unchanged():
    parts = [part("26-056159", ("A1", "A2")), part("26-056160", ("B1", "B2"))]
    assert namespace_entity_ids(parts) == parts


def test_only_colliding_ids_are_renamed():
    result = namespace_entity_ids([part("26-056159", ("E_OUTER", "E_A")), part("26-056160", ("E_OUTER", "E_B"))])
    assert [e["entity_id"] for e in result[1]["entities"]] == ["26056160_E_OUTER", "E_B"]


def test_a_rename_never_lands_on_an_id_that_is_already_taken():
    taken = part("26-056161", ("26056160_E_OUTER", "X"))
    result = namespace_entity_ids([part("26-056159"), taken, part("26-056160")])
    ids = all_ids(result)
    assert len(ids) == len(set(ids))


def test_dictionary_keys_that_are_entity_ids_follow_too():
    second = part("26-056160")
    second["witness"] = {"E_OUTER": {"ref": "E_HOLE"}}
    result = namespace_entity_ids([part("26-056159"), second])
    assert result[1]["witness"] == {"26056160_E_OUTER": {"ref": "26056160_E_HOLE"}}


def test_new_ids_fit_the_exporter_id_format_even_for_long_ids():
    long_id = "E_" + "X" * 60
    result = namespace_entity_ids([part("26-056159", (long_id, "A")), part("26-056160", (long_id, "B"))])
    for entity in result[1]["entities"]:
        assert ENTITY_ID_FORMAT.fullmatch(entity["entity_id"])
    ids = all_ids(result)
    assert len(ids) == len(set(ids))


def test_id_format_is_the_stricter_of_the_two_repository_rules():
    from pathlib import Path
    tools = Path(__file__).resolve().parents[2] / "tools"
    text = (tools / "export_dxf.py").read_text(encoding="utf-8")
    assert r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}' in text  # export_dxf's per-id rule
    assert ENTITY_ID_FORMAT.pattern == r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"


def colliding(code):
    value = synthetic_part(code)
    text = json.dumps(value).replace("E_" + code, "E_SHARED")
    return json.loads(text)


def test_pipeline_exports_two_codes_that_both_called_their_outline_the_same(setup):  # noqa: F811
    repo, source, control = setup
    runner = SingleRunner({"26-000001": colliding("26-000001"), "26-000002": colliding("26-000002")})
    result = asyncio.run(CadPipeline(repo, runner, single_agent=True).run(source, control, job_name="IDS"))
    assert [p.status for p in result.parts] == ["PASS", "PASS"]
    assert result.staged_files
    canonical = json.loads(result.canonical_path.read_text(encoding="utf-8"))
    ids = [e["entity_id"] for p in canonical["parts"] for e in p["entities"]]
    assert len(ids) == len(set(ids)) == 2
    # the per-code results kept in the run are what the model produced
    stored = {p["code"]: p["data"]["canonical"] for p in control.store.parts(control.run_id)}
    assert [e["entity_id"] for e in stored["26-000002"]["entities"]] == ["E_SHARED"]
