import os

from luan_app import staging


def _job(tmp_path):
    job = tmp_path / "share" / "521028-04 cuoi ngay"
    (job / "gui" / "521028-04").mkdir(parents=True)
    (job / "521028-04.pdf").write_bytes(b"%PDF-1.4\n")
    (job / "521028-04_依頼.xlsx").write_bytes(b"x")
    (job / "a.bak").write_bytes(b"junk")
    (job / "Thumbs.db").write_bytes(b"junk")
    (job / "~$521028-04_依頼.xlsx").write_bytes(b"lock")
    (job / "gui" / "521028-04" / "26-063784.dxf").write_text("0\nEOF\n")
    return job


def test_stage_in_copies_job_into_work_skipping_junk(tmp_path):
    job = _job(tmp_path)
    slot = tmp_path / "slot1"
    st = staging.stage_in(str(job), str(job), slot, "521028-04")
    assert st.local_dir == slot / ".work" / "521028-04" / "source"
    assert (st.local_dir / "521028-04.pdf").is_file() and (st.local_dir / "gui" / "521028-04" / "26-063784.dxf").is_file()
    assert not any((st.local_dir / n).exists() for n in ("a.bak", "Thumbs.db", "~$521028-04_依頼.xlsx"))
    assert st.local_target == str(st.local_dir)


def test_stage_in_maps_a_dxf_target_to_its_copy(tmp_path):
    job = _job(tmp_path)
    f = job / "gui" / "521028-04" / "26-063784.dxf"
    st = staging.stage_in(str(job), str(f), tmp_path / "slot1", "521028-04")
    assert os.path.normcase(st.local_target) == os.path.normcase(str(st.local_dir / "gui" / "521028-04" / "26-063784.dxf"))


def test_stage_out_copies_new_deliveries_never_overwrites(tmp_path):
    job = _job(tmp_path)
    (job / "AI_L").mkdir()
    (job / "AI_L" / "521028-04_ALL.dxf").write_text("old\n")
    st = staging.stage_in(str(job), str(job), tmp_path / "slot1", "521028-04")
    ai_l = st.local_dir / "AI_L"
    (ai_l / "521028-04_ALL_v2.dxf").write_text("new\n")       # job.py deliver made _v2 next to the copied old one
    (ai_l / "26-063784.dxf").write_text("code\n")
    out = staging.stage_out(st)
    names = sorted(os.path.basename(p) for p in out)
    assert names == ["26-063784.dxf", "521028-04_ALL_v2.dxf"]
    assert (job / "AI_L" / "521028-04_ALL.dxf").read_text() == "old\n"
    assert staging.stage_out(st) == []                          # second call: identical content is not copied again


def test_stage_out_renames_when_share_got_a_different_file_meanwhile(tmp_path):
    job = _job(tmp_path)
    st = staging.stage_in(str(job), str(job), tmp_path / "slot1", "521028-04")
    (st.local_dir / "AI_L").mkdir()
    (st.local_dir / "AI_L" / "521028-04_ALL.dxf").write_text("mine\n")
    (job / "AI_L").mkdir()
    (job / "AI_L" / "521028-04_ALL.dxf").write_text("someone else\n")
    out = staging.stage_out(st)
    assert [os.path.basename(p) for p in out] == ["521028-04_ALL_v2.dxf"]
    assert (job / "AI_L" / "521028-04_ALL.dxf").read_text() == "someone else\n"
