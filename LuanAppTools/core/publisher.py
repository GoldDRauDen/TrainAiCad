"""Journaled DXF publication; file copies never invoke CAD or providers."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time

from .sources import contained_path, file_hash, validate_dxf
from .store import Store


class Publisher:
    def __init__(self, store: Store, archive_dir: Path):
        self.store = store
        self.archive_dir = Path(archive_dir).resolve()
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _verify_source(self, run, folder):
        if not run['snapshot_dir']:
            return
        manifest = json.loads((run['snapshot_dir'] / 'manifest.json').read_text(encoding='utf-8'))
        digest = hashlib.sha256(json.dumps(tuple(manifest), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if digest != run['source_hash']:
            raise ValueError('Snapshot manifest hash does not match source generation')
        # Rediscovery checks both changed content and additions/deletions.
        from .sources import _inventory
        owned = {Path(output['path']).resolve() for output in self.store.outputs(job_id=run['job_id'], current_only=False)}
        inventory = _inventory(folder, owned)
        if [path.relative_to(folder).as_posix() for path in inventory] != [entry['path'] for entry in manifest]:
            raise ValueError('Source inventory changed before publication')
        for entry in manifest:
            if file_hash(contained_path(folder, entry['path'])) != entry['sha256']:
                raise ValueError('Source changed before publication')

    @staticmethod
    def _destination_root(destination):
        """An output root outside the job folder: no symlink components, created if missing."""
        root = Path(destination).expanduser().absolute()
        # Resolve only after rejecting symlink components in the supplied destination.
        cursor = root
        while cursor != cursor.parent:
            if cursor.is_symlink():
                raise ValueError('Symlink output destination is not allowed')
            cursor = cursor.parent
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve(strict=True)

    def _prepare(self, run, lease, files, parts_destination, combined_destination=None):
        job = self.store.get_job(run['job_id'])
        folder = job['folder']
        allowed_combined = {f"{job['name']}_ALL.dxf", f"{job['name']}_ALL_REVIEW_ONLY.dxf"}
        if len(set(files) & allowed_combined) != 1:
            raise ValueError('Exactly one canonical combined DXF is required')
        entries = []
        for name, stage in files.items():
            relative = Path(name)
            if name in allowed_combined:
                if combined_destination is None:
                    root, relative_target = folder, relative
                else:
                    root, relative_target = self._destination_root(combined_destination), Path(relative.name)
                combined = True
            elif len(relative.parts) == 2 and relative.parts[0] == 'parts_dxf' and re.fullmatch(r'[A-Za-z0-9_-]+\.dxf', relative.name):
                if parts_destination is None:
                    root, relative_target = folder, relative
                else:
                    root, relative_target = self._destination_root(parts_destination), Path(relative.name)
                combined = False
            else:
                raise ValueError('Unsupported output name or unsafe path')
            target = contained_path(root, relative_target)
            stage = Path(stage).resolve(strict=True)
            validate_dxf(stage)
            import ezdxf
            if not len(ezdxf.readfile(stage).modelspace()):
                raise ValueError('Empty DXF cannot be published')
            entries.append({'name': name, 'root': str(root), 'relative': relative_target.as_posix(), 'path': str(target), 'staged': str(stage), 'sha256': file_hash(stage), 'combined': combined})
        entries.sort(key=lambda entry: (entry['combined'], entry['name']))
        journal = {'files': entries, 'source_hash': run['source_hash'], 'archives': []}
        self._verify_source(run, folder)
        with self.store.publication_guard(run['id'], lease, run['source_hash']) as db:
            old = [dict(row) for row in db.execute("SELECT * FROM outputs WHERE job_id=? AND status IN ('current','pending','archiving')", (run['job_id'],))]
            # No filesystem mutation occurs until ALL collisions have been checked.
            for target in {entry['path'] for entry in entries} | {row['path'] for row in old}:
                path = Path(target)
                if path.is_symlink():
                    raise ValueError('Symlink output is not allowed')
                if path.exists():
                    contained_path(path.parent, path.name)
                    owners = [row for row in old if row['path'] == target]
                    digest = file_hash(path)
                    if not any(owner['sha256'] == digest for owner in owners):
                        raise FileExistsError(f'Unowned or externally modified output: {target}')
            for row in old:
                if row['run_id'] == run['id']:
                    # A same-run retry must use the persisted immutable manifest.
                    matching = next((entry for entry in entries if entry['path'] == row['path']), None)
                    if matching is None or matching['sha256'] != row['sha256']:
                        raise ValueError('Run publication manifest cannot change during retry')
                    continue
                suffix = hashlib.sha256(row['path'].encode()).hexdigest()[:16]
                relative_archive = Path(run['job_id']) / row['run_id'] / suffix / Path(row['path']).name
                archive = contained_path(self.archive_dir, relative_archive)
                row['archive_path'] = str(archive)
                journal['archives'].append(row)
                db.execute("UPDATE outputs SET status='archiving',archive_path=? WHERE path=? AND run_id=?", (str(archive), row['path'], row['run_id']))
            for entry in entries:
                db.execute("INSERT INTO outputs(path,job_id,run_id,sha256,status) VALUES(?,?,?,?,'pending') ON CONFLICT(path,run_id) DO NOTHING", (entry['path'], run['job_id'], run['id'], entry['sha256']))
            db.execute("UPDATE runs SET publication=?,status='publication_pending',error=NULL,updated=? WHERE id=?", (json.dumps(journal), time.time(), run['id']))
        return journal

    def _archive(self, run, lease, entry):
        source = Path(entry['path'])
        archive = Path(entry['archive_path'])
        with self.store.publication_guard(run['id'], lease, run['source_hash']) as db:
            archive = contained_path(self.archive_dir, archive.relative_to(self.archive_dir))
            if source.exists():
                contained_path(source.parent, source.name)
                # Ownership needs matching bytes; a filename or SQLite row alone is insufficient.
                if source.is_symlink() or file_hash(source) != entry['sha256']:
                    raise FileExistsError(f'Owned output was externally replaced: {source}')
                archive.parent.mkdir(parents=True, exist_ok=True)
                if archive.exists() and file_hash(archive) != entry['sha256']:
                    raise FileExistsError(f'Archive was externally modified: {archive}')
                if not archive.exists():
                    self._copy_verified(source, archive, entry['sha256'])
                if file_hash(source) != entry['sha256']:
                    raise FileExistsError('Output changed while archiving')
                source.unlink()
            elif not archive.exists() or file_hash(archive) != entry['sha256']:
                # A missing output needs no destructive operation and is preserved as history metadata.
                db.execute("UPDATE outputs SET status='missing' WHERE path=? AND run_id=?", (entry['path'], entry['run_id']))
                return
            db.execute("UPDATE outputs SET status='archived' WHERE path=? AND run_id=?", (entry['path'], entry['run_id']))

    @staticmethod
    def _copy_verified(source, target, expected_hash):
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix='.luanapp-', suffix='.tmp', dir=target.parent)
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            shutil.copy2(source, temporary)
            with temporary.open('r+b') as stream:
                os.fsync(stream.fileno())
            if file_hash(temporary) != expected_hash:
                raise ValueError('Staged output changed during copy')
            # Install only if the destination is still absent. A pre-copy check
            # cannot protect another LAN user's file created while staging.
            if os.name == 'nt':
                # Windows rename fails when the destination already exists.
                os.rename(temporary, target)
            else:
                # POSIX rename replaces existing files; hard-link creation is
                # atomic and exclusive. Both paths share the destination volume.
                # Unsupported filesystems fail closed and retain the retry journal.
                os.link(temporary, target)
            if file_hash(target) != expected_hash:
                raise OSError('Final destination hash verification failed')
            validate_dxf(target)
        finally:
            temporary.unlink(missing_ok=True)

    def _execute(self, run, lease, journal):
        folder = self.store.get_job(run['job_id'])['folder']
        for entry in journal['archives']:
            # Completed archives must not consume this run's already-written replacement on retry.
            with self.store._connect() as db:
                row = db.execute('SELECT status FROM outputs WHERE path=? AND run_id=?', (entry['path'], entry['run_id'])).fetchone()
            if row['status'] == 'archiving':
                self._archive(run, lease, entry)
        for entry in journal['files']:
            self._verify_source(run, folder)
            with self.store.publication_guard(run['id'], lease, run['source_hash']) as db:
                target = contained_path(Path(entry['root']), entry['relative'])
                source = Path(entry['staged'])
                if file_hash(source) != entry['sha256']:
                    raise ValueError('Local validated output changed before publication')
                if target.exists() and file_hash(target) != entry['sha256']:
                    raise FileExistsError(f'Destination changed after ownership reservation: {target}')
                if not target.exists():
                    self._copy_verified(source, target, entry['sha256'])
                else:
                    validate_dxf(target)
                db.execute("UPDATE outputs SET status='current' WHERE path=? AND run_id=?", (entry['path'], run['id']))
        self._verify_source(run, folder)
        with self.store.publication_guard(run['id'], lease, run['source_hash']) as db:
            for entry in journal['files']:
                target = contained_path(Path(entry['root']), entry['relative'])
                if file_hash(target) != entry['sha256']:
                    raise OSError('Destination changed before publication completed')
                validate_dxf(target)
            db.execute("UPDATE runs SET status='completed',lease=NULL,error=NULL,updated=? WHERE id=?", (time.time(), run['id']))
        return {'status': 'published', 'files': [entry['path'] for entry in journal['files']], 'source_hash': run['source_hash']}

    def _pending(self, run_id, lease, source_hash, exc):
        # Never resurrect a cancelled or superseded run while handling an I/O failure.
        try:
            with self.store.publication_guard(run_id, lease, source_hash) as db:
                db.execute("UPDATE runs SET status='publication_pending',error=?,updated=? WHERE id=?", (str(exc), time.time(), run_id))
        except (ValueError, KeyError):
            pass

    def publish(self, run_id: str, lease: str, source_hash: str, staged_files: dict[str, Path], *, parts_destination: Path | None = None, combined_destination: Path | None = None) -> dict:
        run = self.store.assert_lease(run_id, lease, source_hash)
        try:
            if run['publication']:
                raise ValueError('Publication is already prepared; use retry to reuse its local files')
            journal = self._prepare(run, lease, staged_files, parts_destination, combined_destination)
            return self._execute(run, lease, journal)
        except Exception as exc:
            self._pending(run_id, lease, source_hash, exc)
            raise

    def retry(self, run_id: str, lease: str) -> dict:
        run = self.store.get_run(run_id)
        self.store.assert_lease(run_id, lease, run['source_hash'])
        if not run['publication']:
            raise ValueError('No saved publication exists; prepare validated outputs first')
        try:
            return self._execute(run, lease, run['publication'])
        except Exception as exc:
            self._pending(run_id, lease, run['source_hash'], exc)
            raise
