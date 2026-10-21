"""Official subscription CLI runner; Read only, isolated routing, no shell."""

from __future__ import annotations
import asyncio
import base64
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import uuid

from .protocol import (
    AIResult,
    ProviderError,
    cancellable,
    local_path,
    same_model,
    validate_schema,
)

_CLI_MODEL_IDS = {
    "haiku-5.5": "claude-haiku-5-5",
    "sonnet-5.5": "claude-sonnet-5-5",
    "opus-5.5": "claude-opus-5-5",
}


# --append-system-prompt-file first shipped in the CLI generation this runner is verified against.
SHARED_CONTEXT_MIN_VERSION = (2, 1, 301)


class ClaudeRunner:
    supports_shared_context = True

    def __init__(self, command=None):
        self.command = tuple(command or ("claude",))

    def environment(self):
        # Preserve the user's ordinary CLI OAuth profile; remove paid/provider routing.
        return {
            k: v
            for k, v in os.environ.items()
            if not (
                k.startswith(("ANTHROPIC_", "OPENAI_", "AWS_", "AZURE_", "GOOGLE_"))
                or k.startswith("CLAUDE_")
                or k == "CLAUDECODE"
            )
        }

    def executable(self):
        executable = shutil.which(self.command[0])
        if not executable:
            raise ProviderError(
                "unavailable",
                "Install the official Claude Code CLI and run claude auth login with your subscription.",
            )
        if os.name == "nt" and Path(executable).suffix.lower() in (".cmd", ".bat"):
            # Never invoke command shims through cmd.exe with prompt interpolation.
            script = (
                Path(executable).parent
                / "node_modules/@anthropic-ai/claude-code/cli.js"
            )
            node = shutil.which("node")
            if not node or not script.is_file():
                raise ProviderError(
                    "unavailable",
                    "Use the native Claude executable or the official Node CLI installation.",
                )
            return [node, str(script), *self.command[1:]]
        return [executable, *self.command[1:]]

    async def preflight(self):
        async def probe(args):
            p = await asyncio.create_subprocess_exec(
                *self.executable(),
                *args,
                env=self.environment(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                out, _ = await asyncio.wait_for(p.communicate(), 15)
            except BaseException:
                p.kill()
                await p.wait()
                raise
            return out.decode()

        version = await probe(["--version"])
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
        if not match or tuple(map(int, match.groups())) < (2, 1, 300):
            raise ProviderError(
                "unavailable",
                "Update Claude Code to 2.1.300 or later for the verified restricted launch contract.",
            )
        try:
            auth = json.loads(await probe(["auth", "status"]))
        except (ValueError, OSError) as exc:
            raise ProviderError(
                "auth_unavailable",
                "Unable to read Claude subscription auth status; run claude auth login.",
            ) from exc
        if not auth.get("loggedIn") or auth.get("authMethod") not in (
            "claude.ai",
            "oauth_token",
        ):
            raise ProviderError(
                "auth_unavailable",
                "Run claude auth login with a Claude subscription; API-key/provider auth is not used.",
            )
        return {"version": match.group(0), "auth_method": auth["authMethod"]}

    def login(self):
        """Open the official interactive Claude sign-in flow in its own console."""
        if os.name != "nt":
            raise ProviderError(
                "unavailable", "Interactive Claude sign-in is supported on Windows"
            )
        try:
            return subprocess.Popen(
                [*self.executable(), "auth", "login"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                close_fds=True,
                env=self.environment(),
            )
        except OSError as exc:
            raise ProviderError(
                "unavailable", "Could not open the official Claude sign-in window"
            ) from exc

    def argv(self, request, workspace, shared_file=False):
        return [
            *self.executable(),
            "--print",
            "--verbose",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--restricted",
            "--safe-mode",
            "--tools",
            ",".join(["Read", *(["Bash"] if request.agent_commands else [])]),
            "--allowedTools",
            ",".join(["Read", *[f"Bash({command}:*)" for command in request.agent_commands]]),
            "--permission-prompts",
            "none",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--model",
            _CLI_MODEL_IDS.get(request.model, request.model),
            "--effort",
            request.effort,
            "--json-schema",
            json.dumps(request.schema),
            *(["--append-system-prompt-file", str(local_path(request.shared_context_file, workspace))]
              if shared_file else []),
            *(["--resume" if request.resume_session else "--session-id", request.session_id]
              if request.session_id else ["--no-session-persistence"]),
        ]

    async def complete(self, request, *, workspace, cancel, emit):
        if cancel.is_set():
            raise asyncio.CancelledError()
        provider = await cancellable(self.preflight(), cancel, min(request.timeout, 30))
        workspace = Path(workspace).resolve()
        text, shared_file = request.prompt, False
        if request.shared_context_file is not None:
            shared_path = local_path(request.shared_context_file, workspace)
            if tuple(int(part) for part in provider["version"].split(".")) >= SHARED_CONTEXT_MIN_VERSION:
                shared_file = True
            else:  # older CLI: same rules, just back in the user message
                text = shared_path.read_text(encoding="utf-8") + "\n" + text
        content = [{"type": "text", "text": text}]
        for path in request.paths:
            content[0]["text"] += "\nApproved local source: " + str(
                local_path(path, workspace)
            )
        for path in request.images:
            p = local_path(path, workspace)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mimetypes.guess_type(p)[0] or "image/png",
                        "data": base64.b64encode(p.read_bytes()).decode(),
                    },
                }
            )
        payload = (
            json.dumps(
                {"type": "user", "message": {"role": "user", "content": content}}
            )
            + "\n"
        )
        kwargs = (
            {"start_new_session": True}
            if os.name != "nt"
            else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        )
        process = await asyncio.create_subprocess_exec(
            *self.argv(request, workspace, shared_file),
            cwd=workspace,
            env=self.environment(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024,
            **kwargs,
        )
        session = str(uuid.uuid4())
        actual = None
        effort = None
        usage = {}
        result = None
        reported_error = None

        async def consume():
            nonlocal session, actual, effort, result, reported_error
            process.stdin.write(payload.encode())
            await process.stdin.drain()
            process.stdin.close()

            # stderr is drained but never logged: CLI errors can contain profile details.
            async def drain():
                while await process.stderr.read(8192):
                    pass

            stderr = asyncio.create_task(drain())
            try:
                while line := await process.stdout.readline():
                    try:
                        event = json.loads(line)
                    except ValueError as exc:
                        raise ProviderError(
                            "malformed_output",
                            "Claude emitted malformed JSON",
                            accepted=True,
                        ) from exc
                    if not isinstance(event, dict):
                        raise ProviderError(
                            "malformed_output",
                            "Claude stream event must be an object",
                            accepted=True,
                        )
                    session = event.get("session_id", session)
                    # `message` is an object on assistant/user events but plain text on system events
                    # (e.g. permission_denied after a Read outside the workspace).
                    message = event.get("message")
                    model = event.get("model") or (message.get("model") if isinstance(message, dict) else None)
                    # Claude Code can emit synthetic bookkeeping messages that do
                    # not identify a model. Ignore that marker and keep reading;
                    # a concrete model still has to be reported before success.
                    if isinstance(model, str):
                        model = model.strip()
                        if model.lower() == "<synthetic>":
                            model = None
                    if model:
                        actual = model
                        if not same_model(request.model, model):
                            raise ProviderError(
                                "model_mismatch",
                                f"Claude reported model {model!r} for requested model {request.model!r}",
                                accepted=True,
                                outcome=(
                                    "completed_invalid"
                                    if event.get("type") == "result"
                                    else "unknown"
                                ),
                            )
                    reported_effort = event.get("effort")
                    if reported_effort:
                        effort = reported_effort
                        if effort != request.effort:
                            raise ProviderError(
                                "effort_mismatch",
                                "Claude substituted effort",
                                accepted=True,
                                outcome=(
                                    "completed_invalid"
                                    if event.get("type") == "result"
                                    else "unknown"
                                ),
                            )
                    if (
                        event.get("is_error")
                        or event.get("type") == "error"
                        or event.get("error")
                    ):
                        if event.get("type") != "result":
                            reported_error = event.get("error") or event.get("type")
                            continue
                        body = json.dumps(
                            {"event": event, "reported_error": reported_error}
                        ).lower()
                        if any(
                            x in body
                            for x in ("model_not_found", "model not found", "selected model")
                        ):
                            kind = "model_unavailable"
                        elif "input_schema" in body and "api error: 400" in body:
                            kind = "invalid_schema"
                        elif any(
                            x in body for x in ("rate_limit", "rate limit", "usage limit")
                        ):
                            kind = "rate_limit"
                        elif any(
                            x in body for x in ("not logged", "authentication", "auth_error")
                        ):
                            kind = "auth_unavailable"
                        else:
                            kind = "provider_error"
                        rejected = kind in (
                            "rate_limit",
                            "auth_unavailable",
                            "model_unavailable",
                            "invalid_schema",
                        )
                        if kind == "model_unavailable":
                            message = (
                                f"Claude Code cannot use model {request.model!r}; "
                                "choose an available model."
                            )
                        elif kind == "auth_unavailable":
                            message = "Claude request failed; inspect official CLI account status."
                        elif kind == "invalid_schema":
                            message = "Claude rejected the app output schema"
                        else:
                            message = f"Claude {kind}"
                        detail = event.get("result")
                        if isinstance(detail, str) and detail.startswith("API Error: "):
                            message += ": " + detail.splitlines()[0][:300]
                        raise ProviderError(
                            kind,
                            message,
                            accepted=not rejected,
                            outcome=(
                                "rejected"
                                if rejected
                                else (
                                    "completed_invalid"
                                    if event.get("type") == "result"
                                    else "unknown"
                                )
                            ),
                        )
                    metrics = (
                        event.get("usage") if event.get("type") == "result" else None
                    )
                    # Only final cumulative request usage is billed; assistant fragments overlap.
                    if isinstance(metrics, dict):
                        delta = {}
                        for key in (
                            "input_tokens",
                            "output_tokens",
                            "cache_read_input_tokens",
                            "cache_creation_input_tokens",
                        ):
                            if type(metrics.get(key)) is int and metrics[key] >= 0:
                                delta[key] = max(0, metrics[key] - usage.get(key, 0))
                                usage[key] = max(metrics[key], usage.get(key, 0))
                        await emit(
                            {
                                "kind": "usage",
                                "session_id": session,
                                "event_key": f"{session}:final:"
                                + json.dumps(usage, sort_keys=True),
                                "metrics": dict(usage),
                                # CLI result usage belongs to this invocation, even
                                # when --resume keeps the conversation/session ID.
                                "cumulative": not bool(request.session_id),
                            }
                        )
                    await emit(
                        {
                            "kind": "provider_activity",
                            "session_id": session,
                            "type": event.get("type"),
                            "model": actual,
                            "effort": effort,
                        }
                    )
                    if event.get("type") == "result":
                        result = event
                await process.wait()
                await stderr
            finally:
                stderr.cancel()
                await asyncio.gather(stderr, return_exceptions=True)
            if process.returncode or not result:
                raise ProviderError(
                    "provider_error",
                    "Claude ended without a valid result",
                    accepted=True,
                )
            try:
                data = result.get("structured_output")
                if data is None:
                    data = json.loads(result.get("result", ""))
                if not isinstance(data, dict):
                    raise ValueError()
            except ValueError as exc:
                raise ProviderError(
                    "malformed_output",
                    "Claude response is not a JSON object",
                    accepted=True,
                    outcome="completed_invalid",
                ) from exc
            # Job conversations validate in the host loop, where a completed
            # malformed turn can be corrected without starting a new session.
            if not request.session_id:
                validate_schema(data, request.schema)
            elif session != request.session_id:
                raise ProviderError("session_mismatch", "Claude changed the job conversation", accepted=True, outcome="completed_invalid")
            if actual is None:
                raise ProviderError(
                    "model_unverified",
                    "Claude did not report the actual model",
                    accepted=True,
                    outcome="completed_invalid",
                )
            return AIResult(data, usage, session, actual, effort)

        identity = None
        try:
            identity = process_identity(process.pid, workspace)
            await emit({"kind": "provider_process_started", "process": identity})
            return await cancellable(consume(), cancel, request.timeout)
        finally:
            if process.returncode is None:
                if os.name == "nt":
                    killer = await asyncio.create_subprocess_exec(
                        "taskkill",
                        "/PID",
                        str(process.pid),
                        "/T",
                        "/F",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await killer.wait()
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                await process.wait()
            if identity is not None:
                await emit(
                    {
                        "kind": "provider_process_exited",
                        "process": identity,
                        "returncode": process.returncode,
                    }
                )


def _namespace_pid(proc_pid: int) -> int:
    status = (Path("/proc") / str(proc_pid) / "status").read_text()
    row = next(line for line in status.splitlines() if line.startswith("NSpid:"))
    return int(row.split()[-1])


def _inspect_process(pid: int):
    import psutil

    if os.name != "posix" or not Path("/proc/self/status").exists():
        return psutil.Process(pid)
    own = Path("/proc/self").resolve()
    if int(own.name) == os.getpid():
        return psutil.Process(pid)
    # A container may mount an ancestor's procfs. Inspect its visible PID, but
    # only signal the PID belonging to our own kernel PID namespace.
    namespace = os.readlink("/proc/self/ns/pid")
    for proc_pid in psutil.pids():
        try:
            if (
                os.readlink(f"/proc/{proc_pid}/ns/pid") == namespace
                and _namespace_pid(proc_pid) == pid
            ):
                return psutil.Process(proc_pid)
        except (OSError, ValueError, StopIteration):
            continue
    raise psutil.NoSuchProcess(pid)


def process_identity(pid: int, workspace: Path) -> dict:
    """OS creation time and command fingerprint distinguish PID reuse."""
    import hashlib

    process = _inspect_process(pid)
    return {
        "pid": pid,
        "inspection_pid": process.pid,
        "namespace": (
            os.readlink("/proc/self/ns/pid")
            if Path("/proc/self/ns/pid").exists()
            else None
        ),
        "created_at": process.create_time(),
        "executable": process.exe(),
        "cwd": process.cwd(),
        "workspace": str(Path(workspace).resolve()),
        "command_hash": hashlib.sha256(
            json.dumps(process.cmdline()).encode()
        ).hexdigest(),
        "token": uuid.uuid4().hex,
    }


async def stop_owned_process(identity: dict) -> bool:
    """Stop only an identity-verified tree. False means it had already exited.

    Creation time, executable, working directory, command hash and PID namespace
    must match. A reused PID or a changed namespace is a reconciliation blocker.
    """
    import psutil
    import time

    def stop():
        try:
            actual = process_identity(identity["pid"], Path(identity["workspace"]))
            keys = (
                "inspection_pid",
                "namespace",
                "created_at",
                "executable",
                "cwd",
                "command_hash",
            )
            if any(actual[key] != identity[key] for key in keys):
                raise ProviderError(
                    "reconciliation_required",
                    "Process identity changed; refusing to stop an unrelated process",
                )
            process = _inspect_process(identity["pid"])
            if process.create_time() != identity["created_at"]:
                raise ProviderError(
                    "reconciliation_required",
                    "Root PID was reused before tree inspection",
                )
            children = process.children(recursive=True)
            owned = [(child, child.create_time()) for child in reversed(children)] + [
                (process, process.create_time())
            ]
            # Enumerating a tree can take time. Recheck the complete root
            # fingerprint before signaling any descendant collected from it.
            actual = process_identity(identity["pid"], Path(identity["workspace"]))
            if any(actual[key] != identity[key] for key in keys):
                raise ProviderError(
                    "reconciliation_required",
                    "Root identity changed while inspecting its tree",
                )
            for child, created in owned:
                try:
                    if psutil.Process(child.pid).create_time() != created:
                        raise ProviderError(
                            "reconciliation_required", "Child identity changed"
                        )
                    if identity["namespace"] is None:
                        child.kill()  # psutil checks PID reuse on Windows.
                    else:
                        if (
                            os.readlink(f"/proc/{child.pid}/ns/pid")
                            != identity["namespace"]
                        ):
                            raise ProviderError(
                                "reconciliation_required",
                                "Child belongs to another PID namespace",
                            )
                        local_pid = _namespace_pid(child.pid)
                        if not hasattr(os, "pidfd_open") or not hasattr(
                            signal, "pidfd_send_signal"
                        ):
                            raise ProviderError(
                                "reconciliation_required",
                                "This Linux runtime cannot signal an identity-bound process handle",
                            )
                        descriptor = os.pidfd_open(local_pid)
                        try:
                            if psutil.Process(child.pid).create_time() != created:
                                raise ProviderError(
                                    "reconciliation_required",
                                    "Child identity changed before stop",
                                )
                            signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                        finally:
                            os.close(descriptor)
                except (psutil.NoSuchProcess, ProcessLookupError):
                    pass
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                alive = []
                for child, created in owned:
                    try:
                        if (
                            psutil.Process(child.pid).create_time() == created
                            and child.status() != psutil.STATUS_ZOMBIE
                        ):
                            alive.append(child)
                    except psutil.NoSuchProcess:
                        pass
                if not alive:
                    return True
                time.sleep(0.05)
            raise ProviderError(
                "reconciliation_required", "Owned process tree has not confirmed exit"
            )
        except psutil.NoSuchProcess:
            return False
        except (psutil.AccessDenied, PermissionError) as exc:
            raise ProviderError(
                "reconciliation_required",
                "Cannot verify/stop owned provider process; check account permissions",
            ) from exc

    return await asyncio.to_thread(stop)
