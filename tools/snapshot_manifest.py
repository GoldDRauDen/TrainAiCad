"""Hash-verified access to LISPCAD snapshots retired from the working tree.

Snapshots under skills/lispcad/versions/ and skills/lispcad/portable/ are read
from the pinned commit in docs/history/SNAPSHOT_MANIFEST.json and verified
against the recorded sha256. They are audit evidence only, never runtime input.
Reading needs the pinned commit reachable: use a full clone or
`git fetch --unshallow` (CI checks out with fetch-depth 0).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/history/SNAPSHOT_MANIFEST.json"


class SnapshotUnavailable(RuntimeError):
    """The pinned snapshot commit is not reachable from this checkout."""


def load_manifest(path: Path = MANIFEST) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Snapshot:
    """Minimal read-only stand-in for a Path: read_text, read_bytes, is_file."""

    def __init__(self, rel: str, root: Path = ROOT):
        self.rel = rel
        self.root = Path(root)
        self._manifest = load_manifest(self.root / "docs/history/SNAPSHOT_MANIFEST.json")
        self._entry = self._manifest["snapshots"].get(rel)

    def is_file(self) -> bool:
        return self._entry is not None

    def read_bytes(self) -> bytes:
        if self._entry is None:
            raise FileNotFoundError(f"not an archived snapshot: {self.rel}")
        commit = self._manifest["source_commit"]
        try:
            data = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{commit}:{self.rel}"],
                capture_output=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise SnapshotUnavailable(
                f"{self.rel}: pinned commit {commit} not reachable; "
                "use a full clone or `git fetch --unshallow`"
            ) from exc
        if hashlib.sha256(data).hexdigest() != self._entry["sha256"]:
            raise AssertionError(f"{self.rel}: sha256 differs from SNAPSHOT_MANIFEST.json")
        return data

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.read_bytes().decode(encoding)


def snapshot_text(rel: str, root: Path = ROOT) -> str:
    return Snapshot(rel, root).read_text()
