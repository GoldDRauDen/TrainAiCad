import json
import zipfile

from luan_app import archive


def test_archive_named_job(tmp_path):
    slot = tmp_path / "slot"
    (slot / ".work" / "J1" / "make").mkdir(parents=True)
    (slot / ".work" / "J1" / "job_state.json").write_text("{}")
    (slot / ".work" / "J1" / "make" / "spec.yaml").write_text("a: 1")
    (slot / ".work" / "J2").mkdir()
    (slot / ".work" / "J2" / "x").write_text("x")
    dest = tmp_path / "run"
    assert archive.archive_work(slot, "J1", dest) == 2
    assert (dest / "work" / "J1" / "make" / "spec.yaml").is_file()
    assert not (dest / "work" / "J2").exists()


def test_archive_fallback_all_work(tmp_path):
    slot = tmp_path / "slot"
    for d in ("A", "render"):
        (slot / ".work" / d).mkdir(parents=True)
        (slot / ".work" / d / "f.txt").write_text("1")
    (slot / ".work" / "CURRENT").write_text("x")
    dest = tmp_path / "run"
    assert archive.archive_work(slot, "NOPE", dest) == 1
    assert (dest / "work" / "A" / "f.txt").is_file()
    assert archive.archive_work(tmp_path / "empty", "J", tmp_path / "run2") == 0


def test_bundle_contains_transcript_and_out(tmp_path, paths):
    rd = archive.run_dir(paths, 7)
    assert rd.name == "000007"
    od = archive.out_dir(paths, 7)
    (od / "report.md").write_text("# r")
    (rd / "transcript.jsonl").write_text("{}\n")
    archive.write_meta(rd, {"id": 7, "job": "J"}, {"commit": "abc"})
    z = archive.bundle_zip(rd)
    names = zipfile.ZipFile(z).namelist()
    assert "000007/transcript.jsonl" in names and "000007/out/report.md" in names and "000007/meta.json" in names
    assert json.loads((rd / "meta.json").read_text(encoding="utf-8"))["commit"] == "abc"


def test_csv_has_bom_and_header():
    text = archive.runs_csv([{"id": 1, "kind": "RUN", "job": "J", "path": "p", "user_name": "Hùng", "status": "DONE",
                              "summary": "4/4 PASS", "queued_at": "t", "started_at": "t", "ended_at": "t", "commit": "c"}])
    assert text.startswith("﻿id,kind,job,path,user,status,summary")
    assert "Hùng" in text


def test_csv_neutralizes_formula_cells():
    text = archive.runs_csv([{"id": 2, "kind": "RUN", "job": "=HYPERLINK(\"x\")", "path": "+1", "user_name": "@me",
                              "status": "DONE", "summary": "-2", "queued_at": "	t", "started_at": "t", "ended_at": "t",
                              "commit": "c"}])
    row = text.splitlines()[1]
    assert "'=HYPERLINK" in row and "'+1" in row and "'@me" in row and "'-2" in row and "'	t" in row
    assert row.startswith("2,RUN,")  # numbers stay numbers
