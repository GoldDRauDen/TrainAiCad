"""Explicit source inventories and verified immutable local snapshots."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time


_EXCLUDED_DIRS = {'parts_dxf', 'history', 'cache', 'renders', 'render', '__pycache__', 'node_modules'}


def folder_identity(folder: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(Path(folder).resolve(strict=True))).encode('utf-8')).hexdigest()


def contained_path(root: Path, relative: str | Path) -> Path:
    """Reject traversal and symlinks, including symlinks which still point inside root."""
    root = Path(root).absolute()
    cursor = root
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ValueError('Symlink root is not allowed')
        cursor = cursor.parent
    root = root.resolve(strict=True)
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or '..' in relative.parts or '\\' in relative.as_posix() or ':' in str(relative):
        raise ValueError('Unsafe relative path')
    candidate = root.joinpath(relative)
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError('Symlink path is not allowed')
    if not candidate.resolve().is_relative_to(root):
        raise ValueError('Path escapes configured root')
    return candidate


@dataclass(frozen=True)
class SourceJob:
    id: str
    name: str
    folder: Path
    root: Path
    files: tuple[Path, ...]
    owned_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class SourceSnapshot:
    source_hash: str
    directory: Path
    files: tuple[Path, ...]
    manifest: tuple[dict, ...]


def _inventory(folder: Path, owned: set[Path]) -> tuple[Path, ...]:
    files = []
    candidates = list(folder.iterdir())
    for directory in folder.iterdir():
        if directory.name.casefold() == 'data' and directory.is_dir() and not directory.is_symlink():
            candidates.extend(directory.iterdir())
    for path in candidates:
        if path.is_symlink() or not path.is_file() or path.resolve() in owned:
            continue
        if path.suffix.casefold() not in {'.pdf', '.dxf'}:
            continue
        if path.name.startswith('.') or path.stem.upper().endswith(('_ALL', '_ALL_REVIEW_ONLY')):
            continue
        contained_path(folder, path.relative_to(folder))
        files.append(path)
    return tuple(sorted(files, key=lambda path: path.relative_to(folder).as_posix()))


def discover_jobs(roots, *, owned_paths=()) -> list[SourceJob]:
    owned = {Path(path).resolve() for path in owned_paths}
    result = {}
    for configured_root in roots:
        root = Path(configured_root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Source root must be a directory')
        def visit(folder):
            files = _inventory(folder, owned)
            if any(path.suffix.casefold() == '.pdf' and path.parent == folder for path in files):
                identity = folder_identity(folder)
                result[identity] = SourceJob(identity, folder.name, folder, root, files, tuple(owned))
                return
            for child in sorted(folder.iterdir()):
                if child.is_dir() and not child.is_symlink() and not child.name.startswith('.') and child.name.casefold() not in _EXCLUDED_DIRS:
                    visit(child)
        visit(root)
    return sorted(result.values(), key=lambda job: str(job.folder))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(job: SourceJob) -> tuple[dict, ...]:
    if job.folder.is_symlink() or not job.folder.resolve().is_relative_to(job.root):
        raise ValueError('Source folder escaped configured root')
    files = _inventory(job.folder, set(job.owned_paths))
    if not files or files != job.files:
        raise ValueError('Source file inventory changed; rediscover job')
    result = []
    for path in files:
        contained_path(job.root, path.relative_to(job.root))
        before = path.stat()
        digest = file_hash(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('Source changed while hashing')
        result.append({'path': path.relative_to(job.folder).as_posix(), 'sha256': digest, 'size': after.st_size})
    return tuple(result)


def validate_source(path: Path) -> None:
    if path.suffix.casefold() == '.pdf':
        import fitz
        try:
            with fitz.open(path) as document:
                if document.needs_pass or document.page_count < 1:
                    raise ValueError('PDF is encrypted or empty')
                for page in document:
                    page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
        except Exception as exc:
            raise ValueError(f'Invalid PDF: {path.name}') from exc
    elif path.suffix.casefold() == '.dxf':
        validate_dxf(path)


def validate_dxf(path: Path) -> None:
    import ezdxf
    try:
        document = ezdxf.readfile(path)
        if document.audit().has_errors:
            raise ValueError('DXF audit failed')
        # Materialize the saved-file modelspace, rather than trusting the suffix.
        list(document.modelspace())
    except Exception as exc:
        raise ValueError(f'Invalid DXF: {path.name}') from exc


def snapshot_job(job: SourceJob, cache_dir: Path, *, stable_seconds: float = 10.0) -> SourceSnapshot:
    if stable_seconds < 0:
        raise ValueError('stable_seconds cannot be negative')
    initial = _manifest(job)
    if stable_seconds:
        time.sleep(stable_seconds)
    if _manifest(job) != initial:
        raise ValueError('Source changed during stability interval')
    cache = Path(cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.snapshot-', dir=cache))
    try:
        for entry in initial:
            source = contained_path(job.folder, entry['path'])
            target = temporary / entry['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if file_hash(target) != entry['sha256']:
                raise ValueError('Source changed during copy')
            validate_source(target)
        if _manifest(job) != initial:
            raise ValueError('Source changed during copy')
        source_hash = hashlib.sha256(json.dumps(initial, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        directory = cache / job.id / source_hash
        directory.parent.mkdir(parents=True, exist_ok=True)
        (temporary / 'manifest.json').write_text(json.dumps(initial, indent=2), encoding='utf-8')
        if directory.exists():
            # A previous local snapshot must still match before it can be reused.
            for entry in initial:
                if file_hash(contained_path(directory, entry['path'])) != entry['sha256']:
                    raise ValueError('Cached snapshot content changed')
        else:
            os.replace(temporary, directory)
        return SourceSnapshot(source_hash, directory, tuple(directory / entry['path'] for entry in initial), initial)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
