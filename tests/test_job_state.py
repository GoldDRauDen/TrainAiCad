"""tools/job.py: the job lives in files so a compacted session resumes without re-reading everything."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import job  # noqa: E402


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "WORK_ROOT", tmp_path / ".work")
    monkeypatch.setattr(job, "CURRENT", tmp_path / ".work" / "CURRENT")
    return tmp_path


def test_init_writes_state_census_templates_and_current_pointer(isolated):
    state = job.init("521019-05", ["26-061247", "26-061248"], ["521019-05.pdf"], "843", None)
    d = isolated / ".work" / "521019-05"
    assert (d / "job_state.json").is_file() and job.CURRENT.read_text().strip() == str(d.resolve())
    census = json.loads((d / "census_26-061247.json").read_text(encoding="utf-8"))
    assert census["part_code"] == "26-061247" and census["customer_code"] == "843"
    assert all(v["state"] == "UNKNOWN" for v in census["features"].values())
    assert set(state["codes"]) == {"26-061247", "26-061248"}
    with pytest.raises(SystemExit):
        job.init("521019-05", ["26-061247"], [], None, None)


def test_census_records_cards_and_advances_to_l1(isolated):
    job.init("J1", ["26-000001"], [], None, None)
    d = isolated / ".work" / "J1"
    c = json.loads((d / "census_26-000001.json").read_text(encoding="utf-8"))
    c.update(source_mode="PDF_ONLY", part_mode="BEND", reference_present="NO", multi_code_or_assembly="NO")
    for k in c["features"]:
        c["features"][k]["state"] = "NO"
    c["features"]["HOLE"]["state"] = "YES"
    (d / "census_26-000001.json").write_text(json.dumps(c), encoding="utf-8")
    out = job.census(None, "26-000001")
    assert "rules/BEND.md" in out["cards"]["L2_GEOMETRY"] and "rules/HOLE_TAP.md" in out["cards"]["L2_GEOMETRY"]
    text = job.summary()
    assert "26-000001: L1" in text and "next: L2" in text


def test_set_and_summary_keep_flags_files_and_next_step(isolated):
    job.init("J2", ["26-000002"], [], None, None)
    job.set_code(None, "26-000002", stage="L3", status="PREVIEW", flags=["Thiếu Nobi: tách bích 10 mm"],
                 files=["spec=spec_26-000002.yaml"], notes=["bend 2 split"])
    job.set_code(None, "26-000002", flags=["Thiếu Nobi: tách bích 10 mm"])  # no duplicate
    text = job.summary("J2")
    assert text.count("FLAG: Thiếu Nobi") == 1
    assert "spec=spec_26-000002.yaml" in text and "next: Report" in text
    with pytest.raises(SystemExit):
        job.set_code(None, "26-999999", stage="L1")


def test_status_warns_when_the_pinned_commit_moved(isolated, monkeypatch):
    job.init("J3", ["26-000003"], [], None, None)
    monkeypatch.setattr(job, "_head", lambda: "f" * 40)
    assert "WARNING: repo HEAD" in job.summary()
