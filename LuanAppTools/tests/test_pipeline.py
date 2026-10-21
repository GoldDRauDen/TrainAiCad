"""Synthetic source/provider fixtures; actual pinned canonical validation/export/readback."""

import asyncio
import copy
from contextlib import asynccontextmanager
from pathlib import Path
import ezdxf
import fitz
import pytest
from LuanAppTools.ai.protocol import AIResult, ProviderError
from LuanAppTools.cad.pipeline import CadPipeline, RunControl, PipelineError, Paused
from LuanAppTools.cad.repository import PinnedRepository
from LuanAppTools.core.store import Store

ROOT = Path(__file__).resolve().parents[2]
CHECKS = [
    "source_completeness",
    "geometry",
    "dimensions",
    "topology",
    "manufacturing",
    "readability",
]


def synthetic_part(code="26-000001", review=False, hole=False):
    # Explicitly synthetic dimensions, adapted from repository V4.34 tests.
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    from export_dxf import CHECKS

    e = "E_" + code
    p = {
        "code": code,
        "material": "SS",
        "thickness_mm": 1.6,
        "status": "PASS",
        "checks": {k: "PASS" for k in CHECKS},
        "flags": [],
        "entities": [
            {
                "entity_id": e,
                "type": "LWPOLYLINE",
                "role": "outer",
                "closed": True,
                "vertices": [[0, 0, 0], [12, 0, 0], [12, 40, 0], [0, 40, 0]],
            }
        ],
        "source_groups": [
            {
                "group_id": "G",
                "family": "OUTER",
                "status": "PROVED",
                "source_quantity": 1,
                "members": [{"member_id": "M", "status": "PROVED"}],
            }
        ],
        "canonical_members": [
            {
                "canonical_member_id": "CM_" + code,
                "origin": "SOURCE",
                "source_member_id": "M",
                "group_id": "G",
                "status": "PROVED",
                "entity_ids": [e],
            }
        ],
    }
    if review:
        p.update(
            material="SUS304 HL",
            grain={"is_hl": True, "direction_xy": None, "evidence_ref": None},
            status="REVIEW",
            review_reason="HL_DIRECTION_UNPROVED",
            flags=["Synthetic source has no grain arrow"],
        )
    if hole:
        p["entities"].append(
            {
                "entity_id": e + "_H",
                "type": "CIRCLE",
                "role": "hole",
                "center": [6, 20],
                "radius": 2,
            }
        )
        p["source_groups"].append(
            {
                "group_id": "GH",
                "family": "HOLE",
                "status": "PROVED",
                "source_quantity": 1,
                "members": [{"member_id": "MH", "status": "PROVED"}],
            }
        )
        p["canonical_members"].append(
            {
                "canonical_member_id": "CMH_" + code,
                "origin": "SOURCE",
                "source_member_id": "MH",
                "group_id": "GH",
                "status": "PROVED",
                "entity_ids": [e + "_H"],
            }
        )
    return p


@asynccontextmanager
async def slot(model):
    yield


@pytest.fixture
def setup(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    pdf = fitz.open()
    p = pdf.new_page(width=300, height=300)
    p.insert_text((20, 30), "SYNTHETIC TEST: 26-000001, 26-000002. Plate 12 x 40, t1.6")
    p.draw_rect(fitz.Rect(20, 50, 80, 250))
    pdf.save(source / "source.pdf")
    pdf.close()
    store = Store(tmp_path / "state.sqlite")
    job = store.register_job(source)
    repo = PinnedRepository.pin(ROOT, tmp_path / "engine")
    run = store.create_run(job["id"], "synthetic-source", repo.commit)
    lease = store.claim_run(run["id"], "test")
    control = RunControl(
        store, run["id"], lease, "synthetic-source", tmp_path / "work", slot=slot
    )
    return repo, source, control


class ScriptedRunner:
    def __init__(self, parts, *, reject=False, pause=None):
        self.parts = parts
        self.reject = reject
        self.pause = pause
        self.requests = []

    async def complete(self, request, *, workspace, cancel, emit):
        import json

        self.requests.append(request)
        context = json.loads(request.prompt.split("\nCONTEXT_JSON\n", 1)[1])
        stage = context["stage"]
        if stage == "intake":
            codes = list(self.parts)
            data = {
                "pages": [{"page_id": "source.pdf:p1", "disposition": "inspected"}],
                "views": [
                    {
                        "id": "v1",
                        "page_id": "source.pdf:p1",
                        "rect": [0, 0, 300, 300],
                        "codes": codes,
                    }
                ],
                "notes": [],
                "data_entities": [],
                "codes": [
                    {
                        "code": code,
                        "page_ids": ["source.pdf:p1"],
                        "view_ids": ["v1"],
                        "note_ids": [],
                        "data_ids": [],
                        "difficulty": "easy",
                        "difficulty_evidence": ["source.pdf:p1"],
                        "independent": False,
                        "census": {
                            "source_mode": "PDF_ONLY",
                            "part_mode": "FLAT_NO_BEND",
                            "reference_present": "NO",
                            "multi_code_or_assembly": "YES",
                            "features": {k: "NO" for k in context["feature_families"]},
                        },
                    }
                    for code in codes
                ],
            }
        elif stage == "solve":
            code = context["code"]["code"]
            data = {
                "part": copy.deepcopy(self.parts[code]),
                "evidence_refs": ["source.pdf:p1"],
            }
            if self.pause:
                self.pause.set()
        else:
            data = {
                "candidate_hash": context["candidate_hash"],
                "accepted": not self.reject,
                "issues": ["Source interpretation rejected"] if self.reject else [],
                "page_ids": ["source.pdf:p1"],
                "view_ids": ["v1"],
                "note_ids": [],
                "data_ids": [],
                "source_member_ids": [
                    m["member_id"]
                    for g in context["part"]["source_groups"]
                    for m in g["members"]
                ],
                "inventory_complete": True,
                "source_reprojection": {
                    "applicable": False,
                    "reason": "synthetic flat PDF only",
                },
                "engineering_challenge": "completed",
            }
        if request.session_id and stage == "intake":
            for code in data["codes"]:
                for key in ("difficulty", "difficulty_evidence", "independent"):
                    code.pop(key, None)
        return AIResult(data, {}, "fixture-session", request.model, request.effort)


def test_real_pipeline_mixed_status_and_saved_entity_ids(setup):
    repo, source, c = setup
    runner = ScriptedRunner(
        {
            "26-000001": synthetic_part(),
            "26-000002": synthetic_part("26-000002", review=True),
        }
    )
    result = asyncio.run(
        CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC", individual=True)
    )
    assert set(result.staged_files) == {
        "SYNTHETIC_ALL_REVIEW_ONLY.dxf",
        "parts_dxf/26-000001.dxf",
    }
    saved = ezdxf.readfile(result.staged_files["SYNTHETIC_ALL_REVIEW_ONLY.dxf"])
    ids = [
        str(t.value)
        for e in saved.modelspace()
        if e.dxf.layer == "0"
        for t in e.get_xdata("TRAINAICAD")
        if str(t.value).startswith("ENTITY_ID=")
    ]
    assert ids and any("E_26-000001" in s for s in ids)
    assert [p.status for p in result.parts] == ["PASS", "REVIEW"]
    assert c.store.attempts(c.run_id, "26-000001") == 1
    assert all(
        r.schema.get("type") == "object" and "anyOf" not in r.schema
        for r in runner.requests
    )
    intake_request = next(r for r in runner.requests if '"stage": "intake"' in r.prompt)
    census_schema = intake_request.schema['properties']['codes']['items']['properties']['census']
    assert 'source_mode' in census_schema['required']
    assert all(
        r.model == "sonnet-5.5" and r.effort == "high"
        for r in runner.requests
        if '"stage": "qa"' in r.prompt
    )


def test_missing_witness_cannot_be_promoted_by_model_pass(setup):
    repo, source, c = setup
    runner = ScriptedRunner({"26-000001": synthetic_part(hole=True)})
    with pytest.raises(PipelineError) as exc:
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert exc.value.kind == "no_valid_representation"
    assert c.store.attempts(c.run_id, "26-000001") == 2
    assert "WITNESS_REQUIRED_FEATURE_MISSING" in str(c.store.parts(c.run_id))
    assert not list((c.workspace / "aggregate").rglob("*.dxf"))


def test_qa_cannot_repair_or_get_a_third_attempt(setup):
    repo, source, c = setup
    runner = ScriptedRunner({"26-000001": synthetic_part()}, reject=True)
    with pytest.raises(PipelineError):
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert c.store.attempts(c.run_id, "26-000001") == 2
    c.cancel = asyncio.Event()
    with pytest.raises(PipelineError):
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert c.store.attempts(c.run_id, "26-000001") == 2


def test_pause_at_candidate_boundary_and_resume_same_attempt(setup):
    repo, source, c = setup
    runner = ScriptedRunner({"26-000001": synthetic_part()}, pause=c.pause)
    pipeline = CadPipeline(repo, runner)
    with pytest.raises(Paused):
        asyncio.run(pipeline.run(source, c, job_name="SYNTHETIC"))
    assert (
        c.store.get_run(c.run_id)["checkpoint"]["parts"]["26-000001"]["phase"]
        == "qa_ready"
    )
    c.pause.clear()
    runner.pause = None
    c.cancel = asyncio.Event()
    result = asyncio.run(pipeline.run(source, c, job_name="SYNTHETIC"))
    assert (
        result.parts[0].status == "PASS"
        and c.store.attempts(c.run_id, "26-000001") == 1
    )


def test_interrupted_accepted_request_requires_reconciliation(setup):
    repo, source, c = setup

    class Unknown(ScriptedRunner):
        async def complete(self, *args, **kwargs):
            raise ProviderError("connection_unknown", "unknown outcome", accepted=True)

    pipeline = CadPipeline(repo, Unknown({}))
    with pytest.raises(ProviderError):
        asyncio.run(pipeline.run(source, c, job_name="SYNTHETIC"))
    with pytest.raises(PipelineError) as exc:
        asyncio.run(pipeline.run(source, c, job_name="SYNTHETIC"))
    assert exc.value.kind == "reconciliation_required"


def test_source_snapshot_bytes_are_verified_before_ai(setup):
    repo, source, c = setup
    # Once intake uses a source, resume cannot silently use changed bytes.
    runner = ScriptedRunner({"26-000001": synthetic_part()}, pause=c.pause)
    with pytest.raises(Paused):
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    with fitz.open(source / "source.pdf") as doc:
        doc[0].insert_text((10, 280), "CHANGED")
        doc.save(source / "different.pdf")
    c.pause.clear()
    c.cancel = asyncio.Event()
    with pytest.raises(PipelineError) as exc:
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert exc.value.kind == "source_changed"


def test_completed_response_survives_host_crash_without_paid_replay(setup):
    repo, source, c = setup

    class CrashAfterResponse(ScriptedRunner):
        async def complete(self, request, **kw):
            result = await super().complete(request, **kw)
            if '"stage": "solve"' in request.prompt:
                c.pause.set()
            return result

    runner = CrashAfterResponse({"26-000001": synthetic_part()})
    with pytest.raises(Paused):
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    checkpoint = c.store.get_run(c.run_id)["checkpoint"]
    assert checkpoint["parts"]["26-000001"]["candidate"]["code"] == "26-000001"
    assert checkpoint.get("pending") is None


def test_qa_geometry_payload_is_rejected(setup):
    repo, source, c = setup

    class Repair(ScriptedRunner):
        async def complete(self, request, **kw):
            result = await super().complete(request, **kw)
            if '"stage": "qa"' in request.prompt:
                result.data["part"] = synthetic_part()
            return result

    with pytest.raises(PipelineError):
        asyncio.run(
            CadPipeline(repo, Repair({"26-000001": synthetic_part()})).run(
                source, c, job_name="SYNTHETIC"
            )
        )
    assert c.store.attempts(c.run_id, "26-000001") == 2


def test_unknown_solver_gateway_transition_uses_remaining_attempt(setup):
    from LuanAppTools.cad.pipeline import reconcile_request

    repo, source, c = setup

    class UnknownSolve(ScriptedRunner):
        async def complete(self, request, **kw):
            if '"stage": "solve"' in request.prompt:
                raise ProviderError("connection_unknown", "unknown", accepted=True)
            return await super().complete(request, **kw)

    runner = UnknownSolve({"26-000001": synthetic_part()})
    with pytest.raises(ProviderError):
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert c.store.attempts(c.run_id, "26-000001") == 1
    c.gateway_authorized = True
    c.gateway_model = "synthetic-free-model"
    c.gateway_effort = "high"
    c.cancel = asyncio.Event()
    reconcile_request(c, disposition="abandon_for_gateway")
    fallback = ScriptedRunner({"26-000001": synthetic_part()})
    result = asyncio.run(
        CadPipeline(repo, runner, gateway=fallback).run(source, c, job_name="SYNTHETIC")
    )
    assert result.parts[0].status == "PASS" and result.parts[0].attempts == 2


def test_response_buffer_recovered_after_validation_crash(setup, monkeypatch):
    repo, source, c = setup
    runner = ScriptedRunner({"26-000001": synthetic_part()})
    original = type(repo).validate

    async def crash(*args, **kw):
        raise RuntimeError("simulated host crash after provider response")

    monkeypatch.setattr(type(repo), "validate", crash)
    with pytest.raises(RuntimeError):
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert (
        c.store.get_run(c.run_id)["checkpoint"]["response"]["result"]["data"]["part"][
            "code"
        ]
        == "26-000001"
    )
    monkeypatch.setattr(type(repo), "validate", original)
    c.cancel = asyncio.Event()
    result = asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert result.parts[0].attempts == 1
    assert sum('"stage": "solve"' in r.prompt for r in runner.requests) == 1


@pytest.mark.parametrize("native", [False, True])
def test_repeated_tool_requests_stop_without_scaling_to_more_codes(setup, native):
    repo, source, c = setup

    class Loop(ScriptedRunner):
        calls = 0

        async def complete(self, request, **kw):
            if '"stage": "solve"' in request.prompt:
                self.calls += 1
                call = {"name": "calculate", "arguments": {"expression": "2+2"}}
                return AIResult(
                    {} if native else {"tool_requests": [call]},
                    {},
                    "loop",
                    request.model,
                    request.effort,
                    [{**call, "id": f"different-id-{self.calls}"}] if native else [],
                )
            return await super().complete(request, **kw)

    runner = Loop(
        {"26-000001": synthetic_part(), "26-000002": synthetic_part("26-000002")}
    )
    with pytest.raises(PipelineError) as exc:
        asyncio.run(CadPipeline(repo, runner).run(source, c, job_name="SYNTHETIC"))
    assert exc.value.kind == "no_progress"
    assert c.store.attempts(c.run_id, "26-000001") == 1
    assert c.store.attempts(c.run_id, "26-000002") == 0


def test_process_exit_ack_survives_cancel_and_revoked_lease(setup):
    _, _, control = setup
    control.cancel.set()
    control.store.set_run_status(control.run_id, "cancelled")
    asyncio.run(
        control.emit(
            {
                "kind": "provider_process_exited",
                "process": {"token": "owned"},
                "returncode": -9,
            }
        )
    )
    events = control.store.events_since(control.run_id)
    assert events[-1]["kind"] == "provider_process_exited"
    assert events[-1]["payload"]["process"]["token"] == "owned"


def test_real_source_snapshot_pipeline_and_publication(setup, tmp_path):
    from LuanAppTools.core.sources import discover_jobs, snapshot_job
    from LuanAppTools.core.publisher import Publisher

    repo, source, control = setup
    snapshot = snapshot_job(
        discover_jobs([source])[0], tmp_path / "snapshots", stable_seconds=0
    )
    job = control.store.register_job(source)
    run = control.store.create_run(
        job["id"], snapshot.source_hash, repo.commit, snapshot_dir=snapshot.directory
    )
    control.run_id = run["id"]
    control.source_hash = snapshot.source_hash
    control.lease = control.store.claim_run(control.run_id, "snapshot-integration")
    result = asyncio.run(
        CadPipeline(repo, ScriptedRunner({"26-000001": synthetic_part()})).run(
            snapshot.directory, control, job_name=job["name"]
        )
    )
    Publisher(control.store, tmp_path / "archive").publish(
        control.run_id, control.lease, control.source_hash, result.staged_files
    )
    assert control.store.get_run(control.run_id)["status"] == "completed"
    assert set(result.staged_files) == {"source_ALL.dxf"}
    saved = ezdxf.readfile(source / "source_ALL.dxf")
    assert not saved.audit().has_errors


def test_qa_configuration_cannot_downgrade_required_independent_model(setup):
    from LuanAppTools.core.settings import DEFAULT_MODELS

    repo, _, _ = setup
    models = {k: dict(v) for k, v in DEFAULT_MODELS.items()}
    models["qa"] = {"model": "haiku-5.5", "effort": "medium"}
    with pytest.raises(ValueError, match="Sonnet high"):
        CadPipeline(repo, ScriptedRunner({}), models=models)


@pytest.mark.parametrize("transport", ["cli_no_final", "gateway_503"])
def test_unknown_accepted_transport_outcome_blocks_solve_replay(
    setup, tmp_path, transport
):
    import json
    import sys
    import threading
    from dataclasses import replace
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from LuanAppTools.ai.claude import ClaudeRunner
    from LuanAppTools.ai.gateway import GatewayRunner

    repo, source, control = setup
    server = None
    if transport == "cli_no_final":
        script = tmp_path / "no_final.py"
        script.write_text("""import json,sys
if '--version' in sys.argv: print('2.1.300 (Claude Code)');sys.exit()
if 'auth' in sys.argv: print(json.dumps({'loggedIn':True,'authMethod':'claude.ai'}));sys.exit()
sys.stdin.readline()
print(json.dumps({'type':'system','subtype':'init','model':sys.argv[sys.argv.index('--model')+1]}),flush=True)
""")
        provider = ClaudeRunner(command=(sys.executable, str(script)))
    else:

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b'{"error":"upstream result lost"}')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        provider = GatewayRunner(f"http://127.0.0.1:{server.server_port}/v1")

    class BrokenSolve(ScriptedRunner):
        solve_calls = 0

        async def complete(self, request, **kw):
            if '"stage": "solve"' in request.prompt:
                self.solve_calls += 1
                return await provider.complete(
                    replace(request, gateway_authorized=True), **kw
                )
            return await super().complete(request, **kw)

    runner = BrokenSolve({"26-000001": synthetic_part()})
    pipeline = CadPipeline(repo, runner)
    try:
        with pytest.raises(ProviderError) as first:
            asyncio.run(pipeline.run(source, control, job_name="SYNTHETIC"))
        assert first.value.accepted is True
        assert (
            control.store.get_run(control.run_id)["checkpoint"]["pending"] is not None
        )
        with pytest.raises(PipelineError) as resumed:
            asyncio.run(pipeline.run(source, control, job_name="SYNTHETIC"))
        assert resumed.value.kind == "reconciliation_required"
        assert runner.solve_calls == 1
        assert control.store.attempts(control.run_id, "26-000001") == 1
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


def test_completed_invalid_cli_solve_escalates_as_second_attempt(setup, tmp_path):
    import sys
    from LuanAppTools.ai.claude import ClaudeRunner

    repo, source, control = setup
    script = tmp_path / "invalid_final.py"
    script.write_text("""import json,sys
if '--version' in sys.argv: print('2.1.300 (Claude Code)');sys.exit()
if 'auth' in sys.argv: print(json.dumps({'loggedIn':True,'authMethod':'claude.ai'}));sys.exit()
sys.stdin.readline()
print(json.dumps({'type':'result','subtype':'success','is_error':False,'model':sys.argv[sys.argv.index('--model')+1],'structured_output':{'broken':True}}),flush=True)
""")
    provider = ClaudeRunner(command=(sys.executable, str(script)))

    class InvalidOnce(ScriptedRunner):
        solve_models = []

        async def complete(self, request, **kw):
            if '"stage": "solve"' in request.prompt:
                self.solve_models.append(request.model)
                if len(self.solve_models) == 1:
                    return await provider.complete(request, **kw)
            return await super().complete(request, **kw)

    runner = InvalidOnce({"26-000001": synthetic_part()})
    result = asyncio.run(
        CadPipeline(repo, runner).run(source, control, job_name="SYNTHETIC")
    )
    assert result.parts[0].status == "PASS"
    assert result.parts[0].attempts == 2
    assert runner.solve_models == ["haiku-5.5", "sonnet-5.5"]
    assert control.store.get_run(control.run_id)["checkpoint"]["pending"] is None


def interaction_checkpoint(control, remaining):
    state = {
        "phase": "solving",
        "attempt": 1,
        "remaining_seconds": remaining,
        "issues": [],
    }
    checkpoint = {
        "version": 1,
        "source_hash": control.source_hash,
        "repo_commit": control.store.get_run(control.run_id)["repo_commit"],
        "parts": {"26-000001": state},
        "pending": None,
    }
    control.workspace.mkdir(parents=True, exist_ok=True)
    control.store.begin_attempt(control.run_id, "26-000001", checkpoint=checkpoint)
    return checkpoint, state


@pytest.mark.parametrize("tool", ["validate", "crop"])
@pytest.mark.parametrize("cancel_operation", [False, True])
def test_host_operation_is_stopped_before_completion_at_attempt_deadline(
    setup, tmp_path, monkeypatch, tool, cancel_operation
):
    from LuanAppTools.ai.tools import HostTools
    from LuanAppTools.cad.evidence import prepare_evidence

    repo, source, control = setup
    evidence = prepare_evidence(source, control.workspace)
    checkpoint, state = interaction_checkpoint(
        control, 2 if cancel_operation else 0.5
    )
    children = []
    completed = tmp_path / "validation-completed"
    original = asyncio.create_subprocess_exec

    async def launch(*argv, **kw):
        tracked = "-c" in argv or "--crop" in argv
        if "--crop" in argv:
            argv = (argv[0], "-c", "import time,runpy,sys;time.sleep(5);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')", *argv[1:])
        elif tracked:
            argv = (
                *argv[:2],
                "import time;time.sleep(5);" + argv[2] + "\nopen(" + repr(str(completed)) + ',"w").write("completed")',
                *argv[3:],
            )
        child = await original(*argv, **kw)
        if tracked:
            children.append(child)
            if cancel_operation:
                asyncio.get_running_loop().call_soon(control.cancel.set)
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    call = {
        "name": tool,
        "arguments": (
            {"part": synthetic_part()}
            if tool == "validate"
            else {"page_id": "source.pdf:p1", "rect": [0, 0, 200, 200]}
        ),
    }

    class ToolRunner:
        async def complete(self, request, **kw):
            return AIResult(
                {"tool_requests": [call]},
                {},
                "tool-fixture",
                request.model,
                request.effort,
            )

    tools = HostTools(repo, evidence, [], "SYNTHETIC", control.cancel)
    with pytest.raises(
        asyncio.CancelledError if cancel_operation else PipelineError
    ) as exc:
        asyncio.run(
            CadPipeline(repo, ToolRunner())._interact(
                "solve",
                {"code": {"code": "26-000001"}},
                (),
                "",
                tools,
                control,
                checkpoint,
                state,
                {"model": "sonnet-5.5", "effort": "high"},
            )
        )
    if not cancel_operation:
        assert exc.value.kind == "attempt_timeout"
    assert children, "Rendering/validation must have an interruptible process boundary"
    assert all(
        child.returncode is not None for child in children
    )
    assert (
        not completed.exists()
    ), "Pinned validation must be interrupted, not allowed to finish before timeout reporting"
    assert not list((control.workspace / "pages").glob("crop-*.png"))


def test_abrupt_worker_death_does_not_renew_active_interaction_deadline(
    setup, tmp_path, monkeypatch
):
    import json
    import subprocess
    import sys
    import time

    repo, _, control = setup
    checkpoint, _ = interaction_checkpoint(control, 5)
    config = {
        "db": str(control.store.db_path),
        "run_id": control.run_id,
        "lease": control.lease,
        "source_hash": control.source_hash,
        "workspace": str(control.workspace),
    }
    script = r"""import asyncio,json,os,sys
from pathlib import Path
from LuanAppTools.ai.protocol import AIResult
from LuanAppTools.cad.pipeline import CadPipeline,RunControl
from LuanAppTools.core.store import Store
config=json.loads(sys.argv[1])
class CrashStore(Store):
    def save_checkpoint(self,run_id,checkpoint):
        super().save_checkpoint(run_id,checkpoint)
        if checkpoint.get('response') and checkpoint.get('pending') is None:
            os._exit(91)  # Actual abrupt death: no Python finally/atexit.
class Runner:
    async def complete(self,request,**kw):
        return AIResult({'tool_requests':[{'name':'calculate','arguments':{'expression':'2+2'}}]}, {},'crash-fixture',request.model,request.effort)
store=CrashStore(Path(config.pop('db')))
config['workspace']=Path(config['workspace'])
control=RunControl(store=store,**config)
cp=store.get_run(control.run_id)['checkpoint']
asyncio.run(CadPipeline(None,Runner())._interact('solve',{'code':{'code':'26-000001'}},(),'',None,control,cp,cp['parts']['26-000001'],{'model':'sonnet-5.5','effort':'high'}))
"""
    child = subprocess.run(
        [sys.executable, "-c", script, json.dumps(config)],
        cwd=ROOT,
        timeout=10,
        capture_output=True,
    )
    assert child.returncode == 91, child.stderr.decode()
    checkpoint = control.store.get_run(control.run_id)["checkpoint"]
    assert checkpoint["pending"] is None and checkpoint["response"]
    state = checkpoint["parts"]["26-000001"]
    assert state["deadline"] is not None
    # Advance the parent wall clock beyond the real persisted deadline after
    # an actual os._exit crash. Do not race Windows startup against 150 ms.
    expired_at = state["deadline"] + 1
    monkeypatch.setattr("LuanAppTools.cad.pipeline.time.time", lambda: expired_at)

    class NeverWork:
        provider_calls = 0
        tool_calls = 0

        async def complete(self, request, **kw):
            self.provider_calls += 1
            return AIResult(
                {"part": {}, "evidence_refs": []},
                {},
                "should-not-run",
                request.model,
                request.effort,
            )

        async def execute(self, call, **kw):
            self.tool_calls += 1
            return {"value": 4}, None

    never = NeverWork()
    with pytest.raises(PipelineError) as exc:
        asyncio.run(
            CadPipeline(repo, never)._interact(
                "solve",
                {"code": {"code": "26-000001"}},
                (),
                "",
                never,
                control,
                checkpoint,
                state,
                {"model": "sonnet-5.5", "effort": "high"},
            )
        )
    assert exc.value.kind == "attempt_timeout"
    assert never.provider_calls == never.tool_calls == 0
    assert control.store.attempts(control.run_id, "26-000001") == 1


@pytest.mark.parametrize("boundary_stage", ["solve", "qa"])
def test_direct_candidate_validation_uses_remaining_attempt_budget(
    setup, tmp_path, monkeypatch, boundary_stage
):
    repo, source, control = setup
    target = {"next": False}
    children = []
    completed = tmp_path / "direct-validation-completed"
    original = asyncio.create_subprocess_exec

    async def launch(*argv, **kw):
        # The code argument follows "-c"; interpreter flags such as "-X utf8" may precede it.
        code_at = argv.index("-c") + 1 if "-c" in argv else None
        tracked = (
            target["next"] and code_at is not None and "validate_canonical_job" in argv[code_at]
        )
        if tracked:
            target["next"] = False
            argv = (
                *argv[:code_at],
                "import time;time.sleep(5);" + argv[code_at] + "\nopen(" + repr(str(completed)) + ',"w").write("completed")',
                *argv[code_at + 1:],
            )
        child = await original(*argv, **kw)
        if tracked:
            children.append(child)
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)

    class BudgetAtBoundary(CadPipeline):
        async def _interact(
            self,
            stage,
            context,
            images,
            rules,
            tools,
            control,
            checkpoint,
            state,
            model,
        ):
            response = await super()._interact(
                stage, context, images, rules, tools, control, checkpoint, state, model
            )
            if stage == boundary_stage:
                state["remaining_seconds"] = 0.5
                control.save(checkpoint)
                target["next"] = True
            return response

    runner = ScriptedRunner({"26-000001": synthetic_part()})
    with pytest.raises(PipelineError) as exc:
        asyncio.run(
            BudgetAtBoundary(repo, runner).run(source, control, job_name="SYNTHETIC")
        )
    assert exc.value.kind == "no_valid_representation"
    assert children and all(
        child.returncode is not None for child in children
    )
    assert not completed.exists()
    assert control.store.attempts(control.run_id, "26-000001") == 2
    assert not list((control.workspace / "aggregate").rglob("*.dxf"))
