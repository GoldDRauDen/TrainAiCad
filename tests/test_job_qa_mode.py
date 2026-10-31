"""`job.py init --qa`: a QA-only job keeps its census in QA/, never creates make/, and refuses to deliver (QA_REVERSE)."""
import json
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dwg_to_dxf  # noqa: E402
import job  # noqa: E402

JOB = "521031-03"
CODES = ["26-065001", "26-065002"]


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "WORK_ROOT", tmp_path / ".work")
    monkeypatch.setattr(job, "CURRENT", tmp_path / ".work" / "CURRENT")
    folder = tmp_path / "31-10-2026" / f"{JOB} hom nay"
    folder.mkdir(parents=True)
    (folder / f"{JOB}.pdf").write_bytes(b"%PDF")
    return folder


def _init_qa(inbox):
    return job.init(JOB, CODES, [str(inbox / f"{JOB}.pdf")], "843", None, qa=True)


def test_init_qa_writes_census_under_qa_and_no_make(inbox):
    state = _init_qa(inbox)
    d = job.WORK_ROOT / JOB
    assert state["mode"] == "QA" and json.loads((d / "job_state.json").read_text(encoding="utf-8"))["mode"] == "QA"
    assert not (d / "make").exists()
    for code in CODES:
        c = json.loads((d / "QA" / f"census_{code}.json").read_text(encoding="utf-8"))
        assert c["part_code"] == code and c["customer_code"] == "843"
        assert state["codes"][code]["files"]["census"] == f"QA/census_{code}.json"
    assert job.CURRENT.read_text().strip() == str(d.resolve())


def test_status_says_qa_job_without_make_or_deliver_steps(inbox):
    _init_qa(inbox)
    text = job.summary()
    assert "QA JOB" in text and "QA_REVERSE" in text and "AI_QA" in text
    assert "Re-read JOB_CARD.md" not in text and "deliver-code" not in text
    assert "next: L1" not in text and "next: QA:" in text


def test_census_order_and_batch_work_on_the_qa_census(inbox, tmp_path):
    _init_qa(inbox)
    d = job.WORK_ROOT / JOB
    out = job.census(None, CODES[0], sets=["HOLE=YES:p2 2-Ø10"], rest="NO", source_mode="PDF_ONLY",
                     part_mode="BEND", reference="NO", multi="NO")
    assert "rules/HOLE_TAP.md" in out["cards"]["L2_GEOMETRY"]
    assert json.loads((d / "QA" / f"census_{CODES[0]}.json").read_text(encoding="utf-8"))["part_mode"] == "BEND"
    f = tmp_path / "c.yaml"
    f.write_text("defaults: {source_mode: PDF_ONLY, part_mode: FLAT_NO_BEND, reference: 'NO', multi: 'NO', rest: 'NO'}\n"
                 f"codes:\n  {CODES[1]}: {{}}\n", encoding="utf-8")
    job.census_batch(None, str(f))
    rows = job.order()
    assert [r["code"] for r in rows] == [CODES[1], CODES[0]] and all(r["why"] != ["no census"] for r in rows)
    text = job.summary()
    assert f"{CODES[0]}: L1" in text and "cards now:" in text and "QA JOB" in text
    assert not (d / "make").exists()


def test_qa_prepare_still_fills_qa_and_deliver_is_refused(inbox, monkeypatch):
    (inbox / f"{JOB}_Quyen.dwg").write_bytes(b"AC1032 fake")
    _init_qa(inbox)

    def fake_convert(dwg, out, **kw):
        doc = ezdxf.new()
        doc.modelspace().add_line((0, 0), (10, 0))
        doc.saveas(out)
        return Path(out)
    monkeypatch.setattr(dwg_to_dxf, "convert", fake_convert)
    roles = job.qa_prepare(None)
    qa = job.WORK_ROOT / JOB / "QA"
    assert Path(roles["qa_target"]).name == f"{JOB}_Quyen.dwg"
    assert (qa / f"{JOB}_Quyen.dxf").is_file() and (qa / f"census_{CODES[0]}.json").is_file()
    assert not (job.WORK_ROOT / JOB / "make").exists()
    with pytest.raises(SystemExit, match="QA-only"):
        job.deliver(None)
    with pytest.raises(SystemExit, match="QA-only"):
        job.deliver_code(None, CODES[0])


def test_cli_init_qa_and_plain_init_unchanged(inbox, tmp_path, capsys):
    work = tmp_path / "w_qa"
    assert job.main(["init", JOB, "--codes", *CODES, "--source", str(inbox / f"{JOB}.pdf"), "--work", str(work),
                     "--qa"]) == 0
    assert "QA JOB" in capsys.readouterr().out and (work / "QA").is_dir() and not (work / "make").exists()
    assert job.main(["status"]) == 0 and "QA JOB" in capsys.readouterr().out
    plain = tmp_path / "w_make"
    state = job.init(JOB, CODES, [], None, str(plain))
    assert "mode" not in state and (plain / "make" / f"census_{CODES[0]}.json").is_file()
    assert not (plain / "QA").exists() and "QA JOB" not in job.summary()
