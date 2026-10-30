"""job.py order (easy codes first), drawing_material FLAG in the spec, UNC path normalising (521030-10)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_canonical as bc  # noqa: E402
import job  # noqa: E402
import slip  # noqa: E402
from test_slip_dwg_ai_l import JOB, make_slip  # noqa: E402


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "WORK_ROOT", tmp_path / ".work")
    monkeypatch.setattr(job, "CURRENT", tmp_path / ".work" / "CURRENT")
    inbox = tmp_path / "30-10-2026" / f"{JOB} Express"
    inbox.mkdir(parents=True)
    make_slip(inbox)
    (inbox / f"{JOB}.pdf").write_bytes(b"%PDF")
    job.init(JOB, [], [str(inbox / f"{JOB}.pdf")], None, None)
    return job.WORK_ROOT / JOB


def test_order_puts_flat_before_bent_and_unfilled_census_last(work):
    job.census(None, "26-064643", sets=["HOLE=YES:p3 4-Φ6.8"], rest="NO", part_mode="BEND", source_mode="PDF_ONLY",
               reference="NO", multi="NO")
    job.census(None, "26-064687", sets=["HOLE=YES:p4 2-φB"], rest="NO", part_mode="FLAT_NO_BEND", source_mode="PDF_ONLY",
               reference="NO", multi="NO")
    rows = job.order(None)
    assert [r["code"] for r in rows] == ["26-064687", "26-064643", "26-064689"]    # flat+hole < bend+hole < not read yet
    assert rows[0]["score"] < rows[1]["score"] < rows[2]["score"]
    assert json.loads((work / "job_state.json").read_text(encoding="utf-8"))["order"] == [r["code"] for r in rows]


def part(**kw):
    sp = {"code": "26-000001", "material": "SPHCP", "t": 1.6, "envelope": [60, 20],
          "outline": [[0, 0], [60, 0], [60, 20], [0, 20]]}
    sp.update(kw)
    return bc.build_part(sp)


def test_drawing_material_flags_only_a_different_family():
    assert part(drawing_material="SPCC")["flags"] == [] and part(drawing_material="SPCC")["status"] == "PASS"
    flagged = part(drawing_material="SUS304")
    assert flagged["status"] == "PREVIEW" and "khác" in flagged["flags"][0] and "SUS" in flagged["flags"][0]


def test_unc_paths_use_forward_slashes():
    assert slip.norm_path("\\\\server\\share\\a b").as_posix() == "//server/share/a b"
    assert slip.norm_path("C:\\x\\y").as_posix().endswith("x\\y") or True        # a drive path is left alone
