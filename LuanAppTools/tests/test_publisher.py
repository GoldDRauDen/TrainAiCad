import os
from pathlib import Path

import pytest

from .conftest import write_dxf
from LuanAppTools.core.publisher import Publisher


def test_pass_to_review_archives_stale_owned_combined_and_parts(store, run, tmp_path):
    lease = store.claim_run(run['id'], 'worker')
    publisher = Publisher(store, tmp_path / 'history')
    first = write_dxf(tmp_path / 'stage' / 'combined.dxf')
    part = write_dxf(tmp_path / 'stage' / 'part.dxf')
    publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': first, 'parts_dxf/26-056522.dxf': part})
    folder = store.get_job(run['job_id'])['folder']
    latest = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    lease2 = store.claim_run(latest['id'], 'worker')
    result = publisher.publish(latest['id'], lease2, 'source-two', {'520318-15_ALL_REVIEW_ONLY.dxf': first})
    assert result['status'] == 'published'
    assert not (folder / '520318-15_ALL.dxf').exists()
    assert not (folder / 'parts_dxf' / '26-056522.dxf').exists()
    assert (folder / '520318-15_ALL_REVIEW_ONLY.dxf').exists()
    assert len(list((tmp_path / 'history').rglob('*.dxf'))) == 2
    assert len(store.outputs(latest['id'])) == 1


def test_unowned_destination_collision_is_never_overwritten(store, run, tmp_path):
    folder = store.get_job(run['job_id'])['folder']
    existing = folder / '520318-15_ALL.dxf'
    existing.write_bytes(b'customer owned')
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    with pytest.raises(FileExistsError):
        Publisher(store, tmp_path / 'history').publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    assert existing.read_bytes() == b'customer owned'
    assert store.get_run(run['id'])['status'] == 'publication_pending'


def test_interrupted_destination_install_retries_local_files_and_combined_last(store, run, tmp_path, monkeypatch):
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    publisher = Publisher(store, tmp_path / 'history')
    folder = store.get_job(run['job_id'])['folder']
    operation = 'rename' if os.name == 'nt' else 'link'
    original = getattr(os, operation)
    def offline(src, dst):
        if str(dst).endswith('_ALL.dxf'):
            raise OSError('LAN unavailable')
        return original(src, dst)
    monkeypatch.setattr(os, operation, offline)
    files = {'520318-15_ALL.dxf': stage, 'parts_dxf/26-056522.dxf': stage}
    with pytest.raises(OSError):
        publisher.publish(run['id'], lease, 'source-one', files)
    assert store.get_run(run['id'])['status'] == 'publication_pending'
    assert (folder / 'parts_dxf' / '26-056522.dxf').exists()
    assert not (folder / '520318-15_ALL.dxf').exists()
    monkeypatch.setattr(os, operation, original)
    from LuanAppTools.core.store import Store
    reopened = Publisher(Store(store.db_path), tmp_path / 'history')
    assert reopened.retry(run['id'], lease)['status'] == 'published'
    assert store.get_run(run['id'])['status'] == 'completed'


def test_obsolete_run_cannot_publish_or_retry(store, run, tmp_path):
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    store.create_run(run['job_id'], 'source-two', 'e2a4161')
    with pytest.raises(ValueError):
        Publisher(store, tmp_path / 'history').publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    assert list(store.get_job(run['job_id'])['folder'].glob('*.dxf')) == []


def test_replaced_owned_file_is_treated_as_unowned(store, run, tmp_path):
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    publisher = Publisher(store, tmp_path / 'history')
    publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    folder = store.get_job(run['job_id'])['folder']
    (folder / '520318-15_ALL.dxf').write_bytes(b'customer replacement')
    newer = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    lease2 = store.claim_run(newer['id'], 'worker')
    with pytest.raises(FileExistsError):
        publisher.publish(newer['id'], lease2, 'source-two', {'520318-15_ALL_REVIEW_ONLY.dxf': stage})
    assert (folder / '520318-15_ALL.dxf').read_bytes() == b'customer replacement'


def test_publisher_rejects_traversal_and_symlink_output_parent(store, run, tmp_path):
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    publisher = Publisher(store, tmp_path / 'history')
    with pytest.raises(ValueError):
        publisher.publish(run['id'], lease, 'source-one', {'../escape.dxf': stage})
    outside = tmp_path / 'outside'
    outside.mkdir()
    (store.get_job(run['job_id'])['folder'] / 'parts_dxf').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage, 'parts_dxf/26-056522.dxf': stage})
    assert list(outside.iterdir()) == []


def test_publisher_rejects_replaced_job_directory_symlink(store, run, tmp_path):
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    folder = store.get_job(run['job_id'])['folder']
    folder.rmdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    folder.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='[Ss]ymlink'):
        Publisher(store, tmp_path / 'history').publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    assert list(outside.iterdir()) == []


def test_archive_collision_never_replaces_externally_changed_history(store, run, tmp_path, monkeypatch):
    stage = write_dxf(tmp_path / 'stage.dxf')
    publisher = Publisher(store, tmp_path / 'history')
    lease = store.claim_run(run['id'], 'worker')
    publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    newer = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    lease2 = store.claim_run(newer['id'], 'worker')
    # Interrupt real publication after journal reservation, before its archive copy.
    original_copy = publisher._copy_verified
    def interrupted_copy(source, target, digest):
        raise OSError('archive destination unavailable')
    monkeypatch.setattr(publisher, '_copy_verified', interrupted_copy)
    with pytest.raises(OSError):
        publisher.publish(newer['id'], lease2, 'source-two', {'520318-15_ALL_REVIEW_ONLY.dxf': stage})
    monkeypatch.setattr(publisher, '_copy_verified', original_copy)
    journal = store.get_run(newer['id'])['publication']
    archive = Path(journal['archives'][0]['archive_path'])
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b'external history')
    with pytest.raises(FileExistsError):
        publisher.retry(newer['id'], lease2)
    assert archive.read_bytes() == b'external history'


def test_current_files_are_archived_when_same_output_name_is_reused(store, run, tmp_path):
    first = write_dxf(tmp_path / 'first.dxf', length=10)
    second = write_dxf(tmp_path / 'second.dxf', length=20)
    publisher = Publisher(store, tmp_path / 'history')
    lease = store.claim_run(run['id'], 'worker')
    publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': first})
    newer = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    lease2 = store.claim_run(newer['id'], 'worker')
    publisher.publish(newer['id'], lease2, 'source-two', {'520318-15_ALL.dxf': second})
    folder = store.get_job(run['job_id'])['folder']
    assert (folder / '520318-15_ALL.dxf').read_bytes() == second.read_bytes()
    assert store.outputs(run['id'], current_only=False)[0]['status'] == 'archived'
    assert list((tmp_path / 'history').rglob('*.dxf'))[0].read_bytes() == first.read_bytes()


def test_publish_checks_actual_snapshot_source_even_before_watcher_requeues(store, tmp_path):
    from LuanAppTools.core.sources import discover_jobs, snapshot_job
    from .conftest import write_pdf
    folder = tmp_path / 'jobs' / 'job'
    write_pdf(folder / 'source.pdf')
    snapshot = snapshot_job(discover_jobs([tmp_path / 'jobs'])[0], tmp_path / 'cache', stable_seconds=0)
    job = store.register_job(folder)
    run = store.create_run(job['id'], snapshot.source_hash, 'e2a4161', snapshot_dir=snapshot.directory)
    lease = store.claim_run(run['id'], 'worker')
    (folder / 'source.pdf').write_bytes(b'changed source')
    stage = write_dxf(tmp_path / 'stage.dxf')
    with pytest.raises(ValueError, match='Source changed'):
        Publisher(store, tmp_path / 'history').publish(run['id'], lease, snapshot.source_hash, {'job_ALL.dxf': stage})
    assert not (folder / 'job_ALL.dxf').exists()


def test_stale_owned_part_cannot_be_archived_through_replaced_parent_symlink(store, run, tmp_path):
    stage = write_dxf(tmp_path / 'stage.dxf')
    publisher = Publisher(store, tmp_path / 'history')
    lease = store.claim_run(run['id'], 'worker')
    publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage, 'parts_dxf/26-056522.dxf': stage})
    folder = store.get_job(run['job_id'])['folder']
    outside = tmp_path / 'outside'
    (folder / 'parts_dxf').rename(outside)
    (folder / 'parts_dxf').symlink_to(outside, target_is_directory=True)
    newer = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    lease2 = store.claim_run(newer['id'], 'worker')
    with pytest.raises(ValueError, match='[Ss]ymlink'):
        publisher.publish(newer['id'], lease2, 'source-two', {'520318-15_ALL_REVIEW_ONLY.dxf': stage})
    assert (outside / '26-056522.dxf').exists()


def test_customer_output_appearing_during_staging_is_preserved(store, run, tmp_path, monkeypatch):
    import shutil
    stage = write_dxf(tmp_path / 'stage.dxf')
    lease = store.claim_run(run['id'], 'worker')
    publisher = Publisher(store, tmp_path / 'history')
    target = store.get_job(run['job_id'])['folder'] / '520318-15_ALL.dxf'
    original_copy = shutil.copy2

    def customer_appears(source, staged, *args, **kwargs):
        result = original_copy(source, staged, *args, **kwargs)
        target.write_bytes(b'customer output arrived during staging')
        return result

    monkeypatch.setattr(shutil, 'copy2', customer_appears)
    with pytest.raises(FileExistsError):
        publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    assert target.read_bytes() == b'customer output arrived during staging'
    assert store.get_run(run['id'])['status'] == 'publication_pending'
    assert store.outputs(run['id'])[0]['status'] == 'pending'
    # Once the user resolves the collision, the saved journal can finish unchanged.
    monkeypatch.setattr(shutil, 'copy2', original_copy)
    target.unlink()
    assert publisher.retry(run['id'], lease)['status'] == 'published'


def test_customer_archive_appearing_during_staging_is_preserved(store, run, tmp_path, monkeypatch):
    import shutil
    stage = write_dxf(tmp_path / 'stage.dxf')
    publisher = Publisher(store, tmp_path / 'history')
    lease = store.claim_run(run['id'], 'worker')
    publisher.publish(run['id'], lease, 'source-one', {'520318-15_ALL.dxf': stage})
    newer = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    lease2 = store.claim_run(newer['id'], 'worker')
    original_copy = shutil.copy2
    appeared = []

    def customer_appears(source, staged, *args, **kwargs):
        result = original_copy(source, staged, *args, **kwargs)
        archive = Path(store.get_run(newer['id'])['publication']['archives'][0]['archive_path'])
        archive.write_bytes(b'customer history arrived during staging')
        appeared.append(archive)
        return result

    monkeypatch.setattr(shutil, 'copy2', customer_appears)
    with pytest.raises(FileExistsError):
        publisher.publish(newer['id'], lease2, 'source-two', {'520318-15_ALL_REVIEW_ONLY.dxf': stage})
    assert appeared[0].read_bytes() == b'customer history arrived during staging'
    assert store.get_run(newer['id'])['status'] == 'publication_pending'
    folder = store.get_job(run['job_id'])['folder']
    assert (folder / '520318-15_ALL.dxf').read_bytes() == stage.read_bytes()
    assert not (folder / '520318-15_ALL_REVIEW_ONLY.dxf').exists()
    monkeypatch.setattr(shutil, 'copy2', original_copy)
    appeared[0].unlink()
    assert publisher.retry(newer['id'], lease2)['status'] == 'published'


def test_copy_flush_uses_writable_file_descriptor(tmp_path, monkeypatch):
    from LuanAppTools.core.sources import file_hash
    source=write_dxf(tmp_path/'source.dxf')
    original=os.fsync
    flushed=[]
    def flush(fd):
        # Windows FlushFileBuffers requires write access. Zero-byte write checks
        # descriptor mode without altering the staged DXF on either platform.
        os.write(fd,b'')
        flushed.append(fd)
        original(fd)
    monkeypatch.setattr(os,'fsync',flush)
    target=tmp_path/'output.dxf'
    Publisher._copy_verified(source,target,file_hash(source))
    assert flushed and file_hash(source)==file_hash(target)
