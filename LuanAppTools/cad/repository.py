"""Pin and execute the real repository authority. No engineering rules live here."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import yaml
from LuanAppTools.ai.protocol import cancellable, ProviderError


# The repository tools print customer notes (for example '>=19 mm') as UTF-8; a Windows pipe defaults to cp1252.
UTF8_MODE = ("-X", "utf8")


class CadError(RuntimeError):
    def __init__(self, message, kind="canonical_invalid"):
        super().__init__(message)
        self.kind = kind


async def run_tool(argv, cwd, cancel, timeout=120):
    kwargs = (
        {"start_new_session": True}
        if os.name != "nt"
        else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    )
    p = await asyncio.create_subprocess_exec(
        *map(str, argv),
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs,
    )
    try:
        out, err = await cancellable(p.communicate(), cancel, timeout)
        if p.returncode:
            raise CadError(err.decode(errors="replace")[-12000:])
        return out.decode()
    finally:
        if p.returncode is None:
            if os.name == "nt":
                stop = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/PID",
                    str(p.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await stop.wait()
            else:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            await p.wait()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class PinnedRepository:
    root: Path
    commit: str
    hashes: dict

    @classmethod
    def pin(cls, checkout: Path, destination: Path, commit="HEAD"):
        checkout = Path(checkout).resolve()
        destination = Path(destination).resolve()
        revision = subprocess.run(
            ["git", "rev-parse", "--verify", str(commit) + "^{commit}"],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        manifest = destination / "pin.json"
        if destination.exists():
            data = json.loads(manifest.read_text())
            if data["commit"] != revision:
                raise CadError(
                    "Repository snapshot commit mismatch", "repository_changed"
                )
            result = cls(destination, revision, data["hashes"])
            result.verify()
            return result
        archive = subprocess.run(
            ["git", "archive", revision], cwd=checkout, check=True, capture_output=True
        ).stdout
        destination.mkdir(parents=True)
        hashes = {}
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                # Export only production authority/tools. No regression dimensions reach AI.
                name = member.name
                approved = name in (
                    "AI_BOOTSTRAP.md",
                    "AI_ENTRYPOINT.md",
                    "JOB_CARD.md",
                    "templates/CAD_OUTPUT_TEMPLATE.dxf",
                ) or name.startswith(("references/", "skills/lispcad/", "tools/"))
                forbidden = name.startswith(
                    ("skills/lispcad/versions/", "skills/lispcad/portable/")
                )
                if not approved or forbidden or member.isdir():
                    continue
                target = destination / name
                if not member.isfile() or not target.resolve().is_relative_to(
                    destination
                ):
                    raise CadError("Unsafe repository archive")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
                hashes[name] = digest(target)
        manifest.write_text(
            json.dumps({"commit": revision, "hashes": hashes}), encoding="utf-8"
        )
        result = cls(destination, revision, hashes)
        result.verify()
        return result

    def verify(self):
        for name, expected in self.hashes.items():
            path = self.root / name
            if not path.is_file() or path.is_symlink() or digest(path) != expected:
                raise CadError(
                    "Pinned repository file changed: " + name, "repository_changed"
                )
        if not self.contract:
            raise CadError("Current canonical contract missing")

    @property
    def router(self):
        return yaml.safe_load(self.read("skills/lispcad/router/ROUTER.yaml"))

    @property
    def contract(self):
        found = re.search(
            r"TrainAiCad-CANONICAL-V\d+\.\d+", self.read("AI_ENTRYPOINT.md")
        )
        return found.group(0) if found else None

    def read(self, name):
        if name not in self.hashes:
            raise CadError("Unapproved rule/tool path: " + str(name), "routing_gap")
        path = self.root / name
        if digest(path) != self.hashes[name]:
            raise CadError(
                "Pinned repository file changed: " + name, "repository_changed"
            )
        return path.read_text(encoding="utf-8")

    def bootstrap_text(self, source_mode):
        r = self.router
        paths = [
            "AI_BOOTSTRAP.md",
            *(["JOB_CARD.md"] if "JOB_CARD.md" in self.hashes else []),
            "AI_ENTRYPOINT.md",
            "skills/lispcad/router/FEATURE_CENSUS.md",
            "skills/lispcad/router/ROUTER.yaml",
            *r["default_load"],
        ]
        paths += [
            e["path"]
            for e in r.get("conditional_default_load", [])
            if e["path"] != "references/REFERENCE_CALIBRATION_AUDIT.md"
        ]
        for stage in ("L0_BOOTSTRAP", "L1_SOURCE_CENSUS"):
            paths += r["stage_routes"][stage]["load"]
        paths += r["source_routes"][source_mode]["load"]
        return self.text(paths)

    def text(self, paths):
        return "\n\n".join(
            "FILE " + p + "\n" + self.read(p) for p in dict.fromkeys(paths)
        )

    def stage_text(self, route, stage):
        return self.text(route["stage_plans"][stage]["rule_paths"])

    def contract_notes(self):
        from .contract import contract_notes
        return contract_notes(self.read("tools/DXF_INPUT_SCHEMA.md"))

    async def resolve(self, census, workspace, cancel):
        self.verify()
        workspace.mkdir(parents=True, exist_ok=True)
        source = workspace / "census.json"
        source.write_text(json.dumps(census), encoding="utf-8")
        return json.loads(
            await run_tool(
                [
                    sys.executable,
                    *UTF8_MODE,
                    self.root / "tools/resolve_rules.py",
                    source,
                    "--repo-root",
                    self.root,
                ],
                self.root,
                cancel,
            )
        )

    async def validate(self, job, workspace, cancel, *, timeout: float = 120):
        deadline = time.monotonic() + timeout
        self.verify()
        workspace.mkdir(parents=True, exist_ok=True)
        path = workspace / "validate.json"
        path.write_text(json.dumps(job), encoding="utf-8")
        code = """import json,sys
from canonical_contract import validate_canonical_job
from export_dxf import validate_job
from holistic_engineering_guard import canonical_job_anomalies, job_anomalies
j=json.load(open(sys.argv[1],encoding='utf-8'))
errors=[]
v={}
for name,check in [('canonical',validate_canonical_job),('export',validate_job),('geometry',canonical_job_anomalies),('holistic',job_anomalies)]:
    try:
        result=check(j)
        if name=='canonical': v=result
        if name in ('geometry','holistic') and result: errors.extend(result)
    except Exception as exc:
        errors.append(name+': '+str(exc))
if errors: raise ValueError(' | '.join(errors))
print(json.dumps(v))
"""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderError("timeout", "Host validation elapsed budget exhausted")
        result = json.loads(
            await run_tool(
                [sys.executable, *UTF8_MODE, "-c", code, path],
                self.root / "tools",
                cancel,
                timeout=remaining,
            )
        )
        # The checks above are the contract, not the exporter: layout gates such as "source views must be
        # separated by >=10 mm" only run inside export_job. Run the real exporter once on this job too, so the
        # model meets them in its own validate loop instead of after every code has been paid for.
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderError("timeout", "Host validation elapsed budget exhausted")
        trial = workspace / "trial-export"
        shutil.rmtree(trial, ignore_errors=True)
        trial.mkdir(parents=True)
        (trial / "canonical.json").write_text(json.dumps(job), encoding="utf-8")
        await run_tool(
            [sys.executable, *UTF8_MODE, self.root / "tools/export_canonical_dxf.py",
             trial / "canonical.json", trial / "output"],
            self.root,
            cancel,
            timeout=remaining,
        )
        return result

    async def export(self, job, workspace, cancel, individual=False):
        self.verify()
        workspace.mkdir(parents=True, exist_ok=True)
        path = workspace / "canonical.json"
        path.write_text(json.dumps(job), encoding="utf-8")
        output = workspace / "output"
        args = [
            sys.executable,
            *UTF8_MODE,
            self.root / "tools/export_canonical_dxf.py",
            path,
            output,
        ]
        if individual:
            args += ["--individual-dxf"]
        result = json.loads(await run_tool(args, self.root, cancel))
        files = {p.relative_to(output).as_posix(): p for p in output.rglob("*.dxf")}
        if not files:
            raise CadError("Canonical exporter emitted no files")
        return result, files
