"""Struck-out callouts (`cancelled:`): CANCELED ledger group, zero entities, no FLAG, report note (521030-16)."""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import run_job  # noqa: E402
from canonical_contract import validate_canonical_job  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from holistic_engineering_guard import canonical_job_anomalies  # noqa: E402


def part(**kw):
    p = {"code": "26-000021", "material": "SPHCP", "t": 6, "page": 2, "envelope": [100, 60],
         "outline": [[0, 0], [100, 0], [100, 60], [0, 60]],
         "holes": [{"id": "H1", "d": 16, "group": "D16", "qty": 1, "ev": "p2 4-Ø16",
                    "wx": [[50, "HOLE_CENTER", "50"]], "wy": [[30, "HOLE_CENTER", "30"]]}]}
    p.update(kw)
    return p


CANCEL = [{"id": "M8", "label": "2-M8 トオシ", "family": "HOLE", "qty": 2, "mark": "STRIKE_SIGNED",
           "ev": "p2 struck + circled 2"},
          {"id": "D7", "label": "8-Ø7 トオシ", "family": "HOLE", "qty": 8, "mark": "STRIKE", "ev": "p2 struck"}]


def build(**kw):
    return bc.build_part(part(**kw))


def test_cancelled_callout_is_a_ledger_row_with_no_geometry_and_no_flag():
    base, p = build(), build(cancelled=CANCEL)
    assert p["status"] == "PASS" and not p["flags"]
    assert len(p["entities"]) == len(base["entities"])          # nothing drawn for the struck holes
    groups = {g["group_id"]: g for g in p["source_groups"]}
    g = groups["26-000021_G_M8"]
    assert g["status"] == "CANCELED" and g["source_quantity"] == 2
    assert [m["status"] for m in g["members"]] == ["CANCELED"] * 2
    assert groups["26-000021_G_D7"]["source_quantity"] == 8
    owned = {m.get("source_member_id") for m in p["canonical_members"]}
    assert not any(str(s).startswith("26-000021_M8_") or str(s).startswith("26-000021_D7_") for s in owned)
    job = bc.build_job({"job_id": "T", "parts": [part(cancelled=CANCEL)]})
    validate_canonical_job(job)
    assert canonical_job_anomalies(job) == []


def test_cancelled_survives_export_and_is_reported(tmp_path, capsys):
    job = bc.build_job({"job_id": "T", "parts": [part(cancelled=CANCEL)]})
    export_canonical_job(job, tmp_path)
    spec = tmp_path / "s.yaml"
    spec.write_text(yaml.safe_dump({"job_id": "T", "parts": [part(cancelled=CANCEL)]}, allow_unicode=True),
                    encoding="utf-8")
    run_job.main([str(spec), str(tmp_path / "out")])
    assert "hủy theo bản vẽ: 2-M8 トオシ ×2 (gạch + ②), 8-Ø7 トオシ ×8 (gạch)" in capsys.readouterr().out


@pytest.mark.parametrize("bad", [
    {"id": "X", "family": "HOLE", "qty": 0, "mark": "STRIKE", "ev": "e"},
    {"id": "X", "family": "HOLE", "qty": 2, "mark": "MAYBE", "ev": "e"},
    {"id": "X", "family": "WELD", "qty": 2, "mark": "STRIKE", "ev": "e"},
    {"id": "X", "family": "HOLE", "qty": 2, "mark": "STRIKE"},
])
def test_cancelled_entry_needs_family_qty_mark_and_evidence(bad):
    with pytest.raises(bc.BuildError):
        build(cancelled=[bad])


def test_duplicate_group_id_is_refused():
    with pytest.raises(bc.BuildError):
        build(cancelled=[{**CANCEL[0], "id": "D16"}])
