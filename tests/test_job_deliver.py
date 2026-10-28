"""Delivery of the composite DXF to the job's input folder (OUTPUT.md §2): no overwrite, _v2, 52xxxx-xx folder match."""
import json
import sys
from pathlib import Path

import ezdxf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import job as jobmod  # noqa: E402

JOB = "521028-22"


def make_dxf(path, radius):
    doc = ezdxf.new()
    doc.modelspace().add_circle((0, 0), radius)
    doc.saveas(path)


@pytest.fixture
def setup(tmp_path):
    day = tmp_path / "28-10-2026"
    inbox = day / f"{JOB} とても急ぎます"
    inbox.mkdir(parents=True)
    work = tmp_path / "work"
    (work / "out").mkdir(parents=True)
    (work / "job_state.json").write_text(
        json.dumps({"job": JOB, "sources": [str(inbox / f"{JOB}.pdf")], "codes": {}}), encoding="utf-8")
    return day, inbox, work


def test_delivers_to_the_folder_named_after_the_job_then_versions(setup):
    _, inbox, work = setup
    make_dxf(work / "out" / f"{JOB}_ALL.dxf", 5)
    assert jobmod.deliver(str(work)) == inbox / f"{JOB}_ALL.dxf"
    assert jobmod.deliver(str(work)) is None                     # identical content: nothing new
    make_dxf(work / "out" / f"{JOB}_ALL.dxf", 6)
    assert jobmod.deliver(str(work)) == inbox / f"{JOB}_ALL_v2.dxf"
    make_dxf(work / "out" / f"{JOB}_ALL.dxf", 7)
    assert jobmod.deliver(str(work)) == inbox / f"{JOB}_ALL_v3.dxf"
    assert ezdxf.readfile(inbox / f"{JOB}_ALL.dxf").modelspace()[0].dxf.radius == 5   # first delivery untouched


def test_source_path_without_the_tail_finds_the_unique_sibling_folder(setup):
    day, inbox, work = setup
    state = json.loads((work / "job_state.json").read_text(encoding="utf-8"))
    state["sources"] = [str(day / JOB / f"{JOB}.pdf")]             # tail missing in the given path
    (work / "job_state.json").write_text(json.dumps(state), encoding="utf-8")
    make_dxf(work / "out" / f"{JOB}_ALL_REVIEW_ONLY.dxf", 5)
    assert jobmod.deliver(str(work)) == inbox / f"{JOB}_ALL_REVIEW_ONLY.dxf"


def test_other_job_folder_is_not_a_match_and_unclear_destination_stops(setup):
    day, inbox, work = setup
    (day / f"{JOB}1 other").mkdir()                                # 521028-221 is another job number
    assert jobmod._is_job_dir(f"{JOB} x", JOB) and not jobmod._is_job_dir(f"{JOB}1 x", JOB)
    (day / f"{JOB} duplicate").mkdir()
    state = json.loads((work / "job_state.json").read_text(encoding="utf-8"))
    state["sources"] = [str(day / JOB / f"{JOB}.pdf")]
    (work / "job_state.json").write_text(json.dumps(state), encoding="utf-8")
    make_dxf(work / "out" / f"{JOB}_ALL.dxf", 5)
    with pytest.raises(SystemExit, match="unclear"):
        jobmod.deliver(str(work))


def test_only_the_composite_name_is_delivered(setup):
    _, _, work = setup
    make_dxf(work / "out" / "other.dxf", 5)
    with pytest.raises(SystemExit):
        jobmod.deliver(str(work), dxf=str(work / "out" / "other.dxf"))
