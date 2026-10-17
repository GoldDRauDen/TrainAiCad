"""Provider-neutral, bounded requests. Host tools never execute arbitrary commands."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Literal, Protocol

Emit = Callable[[dict], Awaitable[None]]


@dataclass(frozen=True)
class AIRequest:
    model: str
    effort: str
    prompt: str
    images: tuple[Path, ...] = ()
    paths: tuple[Path, ...] = ()
    schema: dict = field(default_factory=lambda: {"type": "object"})
    timeout: float = 1200
    gateway_authorized: bool = False
    tools: tuple[dict, ...] = ()
    # A job owns one conversation. Only successful, durable turns enter history.
    session_id: str | None = None
    resume_session: bool = False
    history: tuple[dict, ...] = ()
    # Rules shared by every code, kept out of the user message so fresh sessions can reuse the
    # provider's cache. Must live inside the run workspace.
    shared_context_file: Path | None = None


@dataclass
class AIResult:
    data: dict
    usage: dict
    session_id: str
    actual_model: str | None
    actual_effort: str | None
    tool_calls: list[dict] = field(default_factory=list)


ProviderOutcome = Literal["rejected", "unknown", "completed_invalid"]


class ProviderError(RuntimeError):
    def __init__(
        self,
        kind: str,
        message: str,
        *,
        accepted: bool = False,
        outcome: ProviderOutcome | None = None,
    ):
        super().__init__(message)
        self.kind, self.accepted = kind, accepted
        self.outcome = outcome or ("unknown" if accepted else "rejected")
        if self.outcome not in ("rejected", "unknown", "completed_invalid"):
            raise ValueError("Invalid provider outcome classification")


class Runner(Protocol):
    async def complete(
        self, request: AIRequest, *, workspace: Path, cancel: asyncio.Event, emit: Emit
    ) -> AIResult: ...


def same_model(requested, actual):
    def normalize(value):
        return value.lower().removeprefix("claude-").replace(".", "-").replace("_", "-")

    wanted, reported = normalize(requested), normalize(actual)
    # Providers often expand a stable alias (for example sonnet-5.5) to a
    # dated model ID. Accept that canonical suffix while still rejecting a
    # different family or version.
    return reported == wanted or reported.startswith(wanted + "-")


def local_path(path: Path, workspace: Path) -> Path:
    target = Path(path).resolve(strict=True)
    if not target.is_relative_to(workspace.resolve()):
        raise ValueError("Provider input must be inside the isolated run workspace")
    return target


async def cancellable(awaitable, cancel, timeout):
    operation = asyncio.ensure_future(awaitable)
    stop = asyncio.create_task(cancel.wait())
    try:
        done, _ = await asyncio.wait(
            (operation, stop), timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )
        if stop in done:
            await stop
            raise asyncio.CancelledError()
        if operation not in done:
            raise ProviderError(
                "timeout", "Provider elapsed budget exhausted", accepted=True
            )
        return await operation
    finally:
        for task in (operation, stop):
            if not task.done():
                task.cancel()
        await asyncio.gather(operation, stop, return_exceptions=True)


def validate_schema(data, schema):
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    try:
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(data))
    except SchemaError as exc:
        raise ValueError("Invalid host output schema") from exc
    if errors:
        raise ProviderError(
            "malformed_output",
            "Provider output does not satisfy requested schema",
            accepted=True,
            outcome="completed_invalid",
        )
