import shutil

import pytest

from .conftest import write_dxf, write_pdf
from LuanAppTools.core.sources import discover_jobs, snapshot_job
from LuanAppTools.core.settings import Settings


def test_same_named_jobs_under_distinct_roots_have_distinct_identity(tmp_path):
    write_pdf(tmp_path / 'a' / '520318-15' / 'source.pdf')
    write_pdf(tmp_path / 'b' / '520318-15' / 'source.pdf')
    jobs = discover_jobs([tmp_path / 'a', tmp_path / 'b'])
    assert [j.name for j in jobs] == ['520318-15', '520318-15']
    assert len({j.id for j in jobs}) == 2


def test_multiple_pdf_and_explicit_data_excludes_generated_and_unrelated(tmp_path):
    folder = tmp_path / 'root' / 'job'
    write_pdf(folder / 'a.pdf')
    write_pdf(folder / 'b.PDF')
    write_dxf(folder / 'data.dxf')
    write_dxf(folder / 'DATA' / 'customer.dxf')
    write_dxf(folder / 'job_ALL.dxf')
    write_dxf(folder / 'job_ALL_REVIEW_ONLY.dxf')
    write_dxf(folder / 'parts_dxf' / '26-056522.dxf')
    write_dxf(folder / 'unrelated' / 'other.dxf')
    write_dxf(folder / 'previous.dxf')
    jobs = discover_jobs([tmp_path / 'root'], owned_paths=[folder / 'previous.dxf'])
    assert [p.relative_to(folder).as_posix() for p in jobs[0].files] == [
        'DATA/customer.dxf', 'a.pdf', 'b.PDF', 'data.dxf']
    snap = snapshot_job(jobs[0], tmp_path / 'cache', stable_seconds=0)
    assert len(snap.source_hash) == 64
    assert [p.relative_to(snap.directory).as_posix() for p in snap.files] == [
        'DATA/customer.dxf', 'a.pdf', 'b.PDF', 'data.dxf']


def test_source_change_during_copy_rejects_snapshot(tmp_path, monkeypatch):
    source = write_pdf(tmp_path / 'root' / 'job' / 'source.pdf')
    job = discover_jobs([tmp_path / 'root'])[0]
    original = shutil.copy2
    def changing_copy(src, dst, *args, **kwargs):
        result = original(src, dst, *args, **kwargs)
        source.write_bytes(source.read_bytes() + b'changed')
        return result
    monkeypatch.setattr(shutil, 'copy2', changing_copy)
    with pytest.raises(ValueError, match='changed'):
        snapshot_job(job, tmp_path / 'cache', stable_seconds=0)
    assert list((tmp_path / 'cache').glob('*/manifest.json')) == []


def test_snapshot_rejects_invalid_pdf_and_symlink_escape(tmp_path):
    folder = tmp_path / 'root' / 'job'
    folder.mkdir(parents=True)
    (folder / 'bad.pdf').write_bytes(b'not pdf')
    with pytest.raises(ValueError, match='PDF'):
        snapshot_job(discover_jobs([tmp_path / 'root'])[0], tmp_path / 'cache', stable_seconds=0)
    (folder / 'bad.pdf').unlink()
    outside = write_pdf(tmp_path / 'outside.pdf')
    (folder / 'escape.pdf').symlink_to(outside)
    assert discover_jobs([tmp_path / 'root']) == []


def test_settings_validate_limits_roots_and_atomically_roundtrip(tmp_path):
    root = tmp_path / 'jobs'
    root.mkdir()
    settings = Settings(data_dir=tmp_path / 'app', roots=[root])
    settings.save()
    assert Settings.load(tmp_path / 'app').roots == (root.resolve(),)
    assert settings.public_dict()['max_ai_calls'] == 2
    assert 'token' not in settings.public_dict()
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path / 'app', roots=[root], max_ai_calls=4)
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path / 'app', roots=[tmp_path / 'missing'])
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path / 'app', roots=[root], models={'easy': {'model': 'invented', 'effort': 'medium'}})


def test_snapshot_detects_added_source(tmp_path):
    folder = tmp_path / 'root' / 'job'
    write_pdf(folder / 'a.pdf')
    job = discover_jobs([tmp_path / 'root'])[0]
    snapshot_job(job, tmp_path / 'cache', stable_seconds=0)
    write_dxf(folder / 'data.dxf', length=10)
    with pytest.raises(ValueError, match='changed'):
        snapshot_job(job, tmp_path / 'cache', stable_seconds=0)


def test_snapshot_hash_detects_same_size_content_change(tmp_path):
    folder = tmp_path / 'root' / 'job'
    write_pdf(folder / 'a.pdf')
    data = write_dxf(folder / 'data.dxf', length=10)
    job = discover_jobs([tmp_path / 'root'])[0]
    first = snapshot_job(job, tmp_path / 'cache', stable_seconds=0)
    before = data.read_bytes()
    after = before.replace(b'\n10.0\n', b'\n11.0\n')
    assert len(before) == len(after)
    assert before != after
    data.write_bytes(after)
    second = snapshot_job(job, tmp_path / 'cache', stable_seconds=0)
    assert first.source_hash != second.source_hash
