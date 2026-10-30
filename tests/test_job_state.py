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
    census = json.loads((d / "make" / "census_26-061247.json").read_text(encoding="utf-8"))
    assert census["part_code"] == "26-061247" and census["customer_code"] == "843"
    assert all(v["state"] == "UNKNOWN" for v in census["features"].values())
    assert set(state["codes"]) == {"26-061247", "26-061248"}
    with pytest.raises(SystemExit):
        job.init("521019-05", ["26-061247"], [], None, None)


def test_census_records_cards_and_advances_to_l1(isolated):
    job.init("J1", ["26-000001"], [], None, None)
    d = isolated / ".work" / "J1"
    c = json.loads((d / "make" / "census_26-000001.json").read_text(encoding="utf-8"))
    c.update(source_mode="PDF_ONLY", part_mode="BEND", reference_present="NO", multi_code_or_assembly="NO")
    for k in c["features"]:
        c["features"][k]["state"] = "NO"
    c["features"]["HOLE"]["state"] = "YES"
    (d / "make" / "census_26-000001.json").write_text(json.dumps(c), encoding="utf-8")
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


def test_hook_is_silent_without_an_open_job_and_prints_it_otherwise(isolated):
    assert job.hook_text() == ""
    job.init("J4", ["26-000004"], [], None, None)
    assert "26-000004: L0" in job.hook_text() and "Re-read JOB_CARD.md" in job.hook_text()
    job.set_code(None, "26-000004", stage="DONE")
    assert job.hook_text() == ""


def test_census_from_one_file_sets_every_code_and_keeps_an_explicit_unknown(isolated):
    job.init("J9", ["26-000001", "26-000002"], [], None, None)
    d = isolated / ".work" / "J9"
    f = isolated / "c.yaml"
    f.write_text("defaults: {source_mode: PDF_ONLY, part_mode: FLAT_NO_BEND, reference: 'NO', multi: 'NO', rest: 'NO'}\n"
                 "codes:\n"
                 "  26-000001: {set: {HOLE: 'YES:p2 2-Ø10'}}\n"
                 "  26-000002: {part_mode: BEND, set: {HOLE: 'YES:p3', SLIT_RELIEF: 'UNKNOWN:p3 bend end'},\n"
                 "              material_and_grain: {printed_grade: SPCC}}\n", encoding="utf-8")
    out = job.census_batch("J9", str(f))
    assert [r["code"] for r in out] == ["26-000001", "26-000002"]
    c2 = json.loads((d / "make" / "census_26-000002.json").read_text(encoding="utf-8"))
    assert c2["part_mode"] == "BEND" and c2["features"]["SLIT_RELIEF"]["state"] == "UNKNOWN"
    assert c2["features"]["TAP"]["state"] == "NO" and c2["material_and_grain"] == {"printed_grade": "SPCC"}
    assert "rules/SLIT_RELIEF.md" in out[1]["cards"]["L2_GEOMETRY"]
    f.write_text("codes: {26-000001: {colour: red}}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="unknown keys"):
        job.census_batch("J9", str(f))


def test_clean_keeps_the_record_and_drops_scratch(isolated):
    job.init("J8", ["26-000001"], [], None, None)
    d = isolated / ".work" / "J8"
    (d / "make" / "ledger_26-000001.md").write_text("| crop | c1.png |\n", encoding="utf-8")
    for name in ("make/c1.png", "make/c2.png", "make/mk.py", "make/out_t2/x.dxf", "make/spec_26-000001.yaml",
                 "make/J8_ALL.dxf"):
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text("x", encoding="utf-8")
    dry = job.clean("J8")
    assert dry["files"] == 3 and (d / "make" / "mk.py").is_file()
    job.clean("J8", apply=True)
    left = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()}
    assert {"make/c1.png", "make/spec_26-000001.yaml", "make/J8_ALL.dxf", "job_state.json"} <= left
    assert not {"make/c2.png", "make/mk.py", "make/out_t2/x.dxf"} & left and not (d / "make" / "out_t2").exists()
