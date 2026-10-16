"""Local subprocess/HTTP substitutes; these are NOT real account tests."""

import asyncio
import json
import os
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from LuanAppTools.ai.claude import ClaudeRunner
from LuanAppTools.ai.gateway import GatewayRunner
from LuanAppTools.ai.protocol import AIRequest, ProviderError


@pytest.fixture
def cli(tmp_path):
    p = tmp_path / "fixture.py"
    p.write_text("""import json, os, sys, time
if '--version' in sys.argv: print('2.1.300 (Claude Code)'); sys.exit()
if 'auth' in sys.argv: print(json.dumps({'loggedIn':True,'authMethod':'claude.ai'})); sys.exit()
payload=json.loads(sys.stdin.readline())
prompt=payload['message']['content'][0]['text']
open('pid','w').write(str(os.getpid()))
if prompt == 'hang': time.sleep(30)
if prompt == 'malformed': print('not json'); sys.exit()
print(json.dumps({'type':'system','subtype':'init','session_id':'s1','model':'wrong' if prompt=='mismatch' else 'claude-sonnet-5-5','effort':'high'}),flush=True)
print(json.dumps({'type':'assistant','message':{'id':'m1','model':'claude-sonnet-5-5','usage':{'input_tokens':10,'output_tokens':2}}}),flush=True)
print(json.dumps({'type':'result','subtype':'success','is_error':prompt=='rate','result':'rate_limit' if prompt=='rate' else '{"answer":42}', 'structured_output':{'answer':42},'session_id':'s1','usage':{'input_tokens':10,'output_tokens':5}}),flush=True)
""")
    return ClaudeRunner(command=(sys.executable, str(p)))


def request(prompt="ok", timeout=3):
    return AIRequest(model="sonnet-5.5", effort="high", prompt=prompt, timeout=timeout)


async def emit(event):
    pass


def test_cli_success_and_usage_highwater(cli, tmp_path):
    async def run():
        events = []

        async def collect(e):
            events.append(e)

        result = await cli.complete(
            request(), workspace=tmp_path, cancel=asyncio.Event(), emit=collect
        )
        assert result.data == {"answer": 42}
        assert result.usage == {"input_tokens": 10, "output_tokens": 5}
        assert result.actual_model == "claude-sonnet-5-5"
        assert (
            sum(
                e["metrics"].get("output_tokens", 0)
                for e in events
                if e["kind"] == "usage"
            )
            == 5
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    "prompt,kind",
    [
        ("mismatch", "model_mismatch"),
        ("rate", "rate_limit"),
        ("malformed", "malformed_output"),
        ("hang", "timeout"),
    ],
)
def test_cli_errors_even_exit_zero(cli, tmp_path, prompt, kind):
    async def run():
        with pytest.raises(ProviderError) as exc:
            await cli.complete(
                request(prompt, 0.2 if prompt == "hang" else 3),
                workspace=tmp_path,
                cancel=asyncio.Event(),
                emit=emit,
            )
        assert exc.value.kind == kind
        assert exc.value.outcome == ("rejected" if prompt == "rate" else "unknown")

    asyncio.run(run())


def test_cancel_terminates_provider_process(cli, tmp_path, monkeypatch):
    children = []
    original = asyncio.create_subprocess_exec
    async def launch(*argv, **kwargs):
        child = await original(*argv, **kwargs)
        if str(argv[0]).lower() != 'taskkill':
            children.append(child)
        return child
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', launch)
    async def run():
        cancel = asyncio.Event()
        task = asyncio.create_task(
            cli.complete(request("hang"), workspace=tmp_path, cancel=cancel, emit=emit)
        )
        for _ in range(100):
            if (tmp_path / "pid").exists():
                break
            await asyncio.sleep(0.01)
        pid = int((tmp_path / "pid").read_text())
        cancel.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert any(child.pid == pid and child.returncode is not None for child in children)

    asyncio.run(run())


def test_primary_environment_and_safe_flags(cli, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.invalid")
    assert "ANTHROPIC_API_KEY" not in cli.environment()
    assert "ANTHROPIC_BASE_URL" not in cli.environment()
    argv = cli.argv(request(), tmp_path)
    assert "--bare" not in argv
    for flag in ("--restricted", "--safe-mode", "--strict-mcp-config"):
        assert flag in argv
    assert argv[argv.index("--tools") + 1] == "Read"


def test_gateway_real_http_conversion_and_manual_authorization(tmp_path):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            data = json.dumps(
                {
                    "id": "gateway1",
                    "model": "sonnet-5.5",
                    "choices": [
                        {
                            "message": {
                                "content": '{"answer":42}',
                                "tool_calls": [
                                    {
                                        "id": "t1",
                                        "function": {
                                            "name": "calculate",
                                            "arguments": '{"expression":"2+2"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3},
                }
            ).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def run():
        runner = GatewayRunner(f"http://127.0.0.1:{server.server_port}/v1")
        with pytest.raises(ProviderError, match="authorization"):
            await runner.complete(
                request(), workspace=tmp_path, cancel=asyncio.Event(), emit=emit
            )
        image = tmp_path / "page.png"
        image.write_bytes(b"fixture-image")
        req = AIRequest(
            model="sonnet-5.5",
            effort="high",
            prompt="inspect",
            images=(image,),
            gateway_authorized=True,
        )
        result = await runner.complete(
            req, workspace=tmp_path, cancel=asyncio.Event(), emit=emit
        )
        assert result.tool_calls[0]["name"] == "calculate"
        assert result.usage["input_tokens"] == 7
        assert received[0]["messages"][0]["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )

    try:
        asyncio.run(run())
    finally:
        server.shutdown()
        server.server_close()


def test_schema_invalid_output_is_rejected(cli, tmp_path):
    req = AIRequest(
        model="sonnet-5.5",
        effort="high",
        prompt="ok",
        schema={"type": "object", "required": ["missing"]},
    )
    with pytest.raises(ProviderError) as exc:
        asyncio.run(
            cli.complete(req, workspace=tmp_path, cancel=asyncio.Event(), emit=emit)
        )
    assert exc.value.kind == "malformed_output"
    assert exc.value.outcome == "completed_invalid"
    assert exc.value.accepted is True


def test_primary_removes_oauth_override_and_config_injection(cli, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "secret")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/unapproved/profile")
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in cli.environment()
    assert "CLAUDE_CONFIG_DIR" not in cli.environment()


def test_process_identity_events_precede_submission_and_ack_exit(cli, tmp_path):
    async def run():
        events = []

        async def collect(event):
            if event["kind"] == "provider_process_started":
                assert not (
                    tmp_path / "pid"
                ).exists(), "Identity must be persisted before stdin submission"
                assert (
                    event["process"]["created_at"] > 0
                    and event["process"]["command_hash"]
                )
            events.append(event)

        await cli.complete(
            request(), workspace=tmp_path, cancel=asyncio.Event(), emit=collect
        )
        assert events[0]["kind"] == "provider_process_started"
        assert events[-1]["kind"] == "provider_process_exited"
        assert events[0]["process"]["token"] == events[-1]["process"]["token"]

    asyncio.run(run())


def test_restart_stop_rejects_wrong_process_identity(tmp_path):
    from LuanAppTools.ai.claude import process_identity, stop_owned_process

    identity = process_identity(os.getpid(), tmp_path)
    identity["created_at"] -= 100
    with pytest.raises(ProviderError) as exc:
        asyncio.run(stop_owned_process(identity))
    assert exc.value.kind == "reconciliation_required"


def test_restart_stop_verifies_and_terminates_owned_process(tmp_path):
    from LuanAppTools.ai.claude import process_identity, stop_owned_process

    async def run():
        child = await asyncio.create_subprocess_exec(
            sys.executable, "-c", "import time;time.sleep(30)", cwd=tmp_path
        )
        try:
            identity = process_identity(child.pid, tmp_path)
            assert await stop_owned_process(identity) is True
            await asyncio.wait_for(child.wait(), 2)
            assert await stop_owned_process(identity) is False
        finally:
            if child.returncode is None:
                child.kill()
                await child.wait()

    asyncio.run(run())


@pytest.mark.parametrize(
    "failure", [None, "vision", "structured", "tools", "model", "malformed"]
)
def test_gateway_capability_probe_requires_evidence_and_tool_roundtrip(
    tmp_path, monkeypatch, failure
):
    """Actual HTTP substitute verifies wire behavior, not a real model's vision."""
    import LuanAppTools.ai.gateway as gateway

    monkeypatch.setattr(
        gateway.secrets,
        "token_hex",
        lambda size: "C0FFEE" if size == 3 else "host-secret-" + str(size),
    )
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(body)
            messages = body["messages"]
            content = messages[0]["content"]
            image = next((c for c in content if c["type"] == "image_url"), None)
            calls = None
            if messages[-1]["role"] == "tool":
                value = json.loads(messages[-1]["content"])["nonce"]
                answer = {"nonce": "wrong" if failure == "tools" else value}
            elif body.get("tools"):
                name = body["tools"][0]["function"]["name"]
                calls = [
                    {
                        "id": "probe-call",
                        "type": "function",
                        "function": {"name": name, "arguments": "{}"},
                    }
                ]
                answer = {}
            elif image:
                assert "C0FFEE" not in json.dumps(
                    [c for c in content if c["type"] == "text"]
                )
                assert base64.b64decode(
                    image["image_url"]["url"].split(",", 1)[1]
                ).startswith(b"\x89PNG")
                answer = {"code": "wrong" if failure == "vision" else "C0FFEE"}
            else:
                answer = {"nonce": "host-secret-16"}
                if failure == "structured":
                    answer = {"unexpected": True}
            message = {"content": json.dumps(answer)}
            if calls:
                message["tool_calls"] = calls
            response = {
                "id": "probe-" + str(len(received)),
                "model": "wrong" if failure == "model" else body["model"],
                "choices": [{"message": message}],
            }
            data = json.dumps([] if failure == "malformed" else response).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    import base64

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def run():
        runner = GatewayRunner(f"http://127.0.0.1:{server.server_port}/v1")
        with pytest.raises(ProviderError) as exc:
            await runner.probe(
                model="sonnet-5.5",
                effort="high",
                workspace=tmp_path / "fresh-probes",
                cancel=asyncio.Event(),
                emit=emit,
            )
        assert exc.value.kind == "authorization_required"
        assert not received
        report = await runner.probe(
            model="sonnet-5.5",
            effort="high",
            workspace=tmp_path / "fresh-probes",
            cancel=asyncio.Event(),
            emit=emit,
            authorized=True,
            timeout=5,
        )
        assert report.ready is (failure is None)
        assert report.requested_model == "sonnet-5.5"
        if failure is None:
            assert (
                report.structured_response
                == report.vision
                == report.tool_protocol
                == "verified"
            )
            assert report.actual_model == "sonnet-5.5"
            assert len(received) == 4
            assert received[-1]["messages"][-2]["tool_calls"][0]["id"] == "probe-call"
            assert received[-1]["messages"][-1]["tool_call_id"] == "probe-call"
        else:
            assert "failed" in (
                report.structured_response,
                report.vision,
                report.tool_protocol,
            )
            assert report.error_kind

    try:
        asyncio.run(run())
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_precancelled_probe_sends_nothing(tmp_path):
    cancel = asyncio.Event()
    cancel.set()
    runner = GatewayRunner("http://127.0.0.1:1/v1")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runner.probe(
                model="sonnet-5.5",
                effort="high",
                workspace=tmp_path / "fresh-probes",
                cancel=cancel,
                emit=emit,
                authorized=True,
            )
        )
