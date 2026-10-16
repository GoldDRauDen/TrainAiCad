"""Explicitly authorized OpenAI-compatible endpoint adapter. No automatic fallback."""

import base64
import json
import mimetypes
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import uuid
import httpx
from .protocol import (
    AIRequest,
    AIResult,
    ProviderError,
    cancellable,
    local_path,
    same_model,
    validate_schema,
)

CapabilityState = Literal["verified", "failed", "unverified"]


@dataclass(frozen=True)
class GatewayCapabilityReport:
    endpoint: str
    requested_model: str
    requested_effort: str
    checked_at: float
    structured_response: CapabilityState = "unverified"
    vision: CapabilityState = "unverified"
    tool_protocol: CapabilityState = "unverified"
    actual_model: str | None = None
    actual_effort: str | None = None
    error_kind: str | None = None

    @property
    def ready(self) -> bool:
        return all(
            s == "verified"
            for s in (self.structured_response, self.vision, self.tool_protocol)
        )


class GatewayRunner:
    def __init__(
        self,
        endpoint="http://localhost:20128/v1",
        *,
        headers=None,
        send_effort=True,
    ):
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Gateway requires a credential-free HTTP endpoint")
        self.endpoint = endpoint.rstrip("/")
        self.headers = dict(headers or {})
        self.send_effort = bool(send_effort)

    def _error_detail(self, response):
        """Return a short upstream message without echoing configured secrets."""
        try:
            body = response.json()
        except ValueError:
            return ""
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            message = error.get("message")
        elif isinstance(error, str):
            message = error
        else:
            message = body.get("message") if isinstance(body, dict) else None
        if not isinstance(message, str):
            return ""
        message = " ".join(message.split())
        for value in self.headers.values():
            if isinstance(value, str) and value:
                message = message.replace(value, "[redacted]")
                if value.lower().startswith("bearer "):
                    token = value[7:].strip()
                    if token:
                        message = message.replace(token, "[redacted]")
        return message[:400]

    def _body(self, request, workspace):
        if not request.gateway_authorized:
            raise ProviderError(
                "authorization_required",
                "Explicit run authorization is required for this AI endpoint",
            )
        content = [{"type": "text", "text": request.prompt}]
        for path in request.paths:
            p = local_path(path, workspace)
            content.append(
                {"type": "text", "text": p.name + "\n" + p.read_text(encoding="utf-8")}
            )
        for path in request.images:
            p = local_path(path, workspace)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f'data:{mimetypes.guess_type(p)[0] or "image/png"};base64,'
                        + base64.b64encode(p.read_bytes()).decode()
                    },
                }
            )
        body = {
            "model": request.model,
            "messages": [{"role": "user", "content": content}],
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "cad_response", "schema": request.schema},
            },
        }
        if request.history:
            from dataclasses import replace
            messages = []
            for turn in request.history:
                prior = replace(request, prompt=turn["prompt"], images=tuple(Path(p) for p in turn["images"]),
                                paths=(), history=())
                messages.extend(self._body(prior, workspace)["messages"])
                messages.append({"role": "assistant", "content": json.dumps(turn["answer"], ensure_ascii=False, separators=(",", ":"))})
            body["messages"] = messages + body["messages"]
        if self.send_effort:
            body["reasoning_effort"] = request.effort
        if request.tools:
            body["tools"] = [{"type": "function", "function": t} for t in request.tools]

        return body

    async def complete(self, request, *, workspace, cancel, emit):
        body = self._body(request, workspace)
        return await cancellable(
            self._perform(request, body, emit), cancel, request.timeout
        )

    async def _perform(self, request, body, emit):
        try:
            async with httpx.AsyncClient(
                timeout=request.timeout, follow_redirects=False, trust_env=False
            ) as client:
                response = await client.post(
                    self.endpoint + "/chat/completions",
                    json=body,
                    headers=self.headers,
                )
        except httpx.ConnectError as exc:
            raise ProviderError(
                "connection_refused",
                "Cannot connect to the configured AI endpoint",
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                "connection_unknown",
                "Gateway request outcome unknown; reconcile before replay",
                accepted=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError("rate_limit", "AI provider rate or usage limit")
        if response.status_code == 401:
            raise ProviderError(
                "auth_unavailable", "Check the API key or authentication header"
            )
        if response.status_code == 403:
            detail = self._error_detail(response)
            raise ProviderError(
                "access_denied",
                "The provider denied access to this model or account"
                + (f": {detail}" if detail else ""),
            )
        if response.status_code != 200:
            raise ProviderError(
                "provider_error",
                f"AI endpoint HTTP {response.status_code}",
                accepted=True,
            )
        completed = False
        try:
            obj = response.json()
            if not isinstance(obj, dict) or obj.get("error"):
                raise ValueError()
            message = obj["choices"][0]["message"]
            if not isinstance(message, dict):
                raise ValueError()
            completed = True
            model = obj.get("model")
            if not isinstance(model, str) or not model:
                raise ProviderError(
                    "model_unverified",
                    "Gateway did not report its actual model",
                    accepted=True,
                    outcome="completed_invalid",
                )
            if not same_model(request.model, model):
                raise ProviderError(
                    "model_mismatch",
                    "Gateway substituted a different model",
                    accepted=True,
                    outcome="completed_invalid",
                )
            calls = [
                {
                    "id": t["id"],
                    "name": t["function"]["name"],
                    "arguments": json.loads(t["function"]["arguments"]),
                }
                for t in message.get("tool_calls", [])
            ]
            if any(
                not isinstance(t["arguments"], dict)
                or not isinstance(t["id"], str)
                or not isinstance(t["name"], str)
                for t in calls
            ):
                raise ValueError()
            data = json.loads(message.get("content") or "{}")
            if not isinstance(data, dict):
                raise ValueError()
            usage = {
                dest: obj["usage"][src]
                for src, dest in [
                    ("prompt_tokens", "input_tokens"),
                    ("completion_tokens", "output_tokens"),
                ]
                if type(obj.get("usage", {}).get(src)) is int and obj["usage"][src] >= 0
            }
        except (KeyError, IndexError, AttributeError, ValueError, TypeError) as exc:
            raise ProviderError(
                "malformed_output",
                "Malformed AI endpoint response",
                accepted=True,
                outcome="completed_invalid" if completed else "unknown",
            ) from exc
        if not calls and not request.session_id:
            validate_schema(data, request.schema)
        effort = obj.get("reasoning_effort")
        if effort and effort != request.effort:
            raise ProviderError(
                "effort_mismatch",
                "Gateway substituted effort",
                accepted=True,
                outcome="completed_invalid",
            )
        session = obj.get("id") or str(uuid.uuid4())
        if usage:
            await emit(
                {
                    "kind": "usage",
                    "session_id": session,
                    "event_key": session,
                    "metrics": usage,
                    "cumulative": False,
                }
            )
        return AIResult(data, usage, session, model, obj.get("reasoning_effort"), calls)

    async def test_connection(self, model: str, *, timeout: float = 25) -> dict:
        """Make one small, non-streaming request to verify URL, auth and model."""
        if not isinstance(model, str) or not model.strip() or len(model) > 200:
            raise ProviderError("model_unavailable", "Enter a model name first")
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=False, trust_env=False
            ) as client:
                response = await client.post(
                    self.endpoint + "/chat/completions",
                    headers=self.headers,
                    json={
                        "model": model.strip(),
                        "messages": [
                            {"role": "user", "content": "Reply with only OK."}
                        ],
                        "max_completion_tokens": 8,
                        "stream": False,
                    },
                )
        except httpx.ConnectError as exc:
            raise ProviderError(
                "connection_refused", "Cannot connect to the configured AI endpoint"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "timeout", "AI connection check timed out", accepted=True
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                "connection_unknown", "AI endpoint request failed", accepted=True
            ) from exc
        if response.status_code == 401:
            raise ProviderError(
                "auth_unavailable", "Authentication failed; check the API key or auth header"
            )
        if response.status_code == 403:
            detail = self._error_detail(response)
            raise ProviderError(
                "access_denied",
                "The provider denied access to this model or account"
                + (f": {detail}" if detail else ""),
            )
        if response.status_code == 404:
            detail = self._error_detail(response)
            raise ProviderError(
                "model_unavailable",
                "Endpoint or model was not found; check the base URL and model ID"
                + (f": {detail}" if detail else ""),
            )
        if response.status_code == 429:
            raise ProviderError("rate_limit", "Provider rate or usage limit reached")
        if response.status_code != 200:
            raise ProviderError(
                "provider_error", f"AI endpoint returned HTTP {response.status_code}"
            )
        try:
            result = response.json()
            text = result["choices"][0]["message"].get("content")
            actual_model = result.get("model")
            if not isinstance(text, str) or not text.strip():
                raise ValueError()
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "malformed_output", "AI endpoint returned an unsupported response"
            ) from exc
        return {"model": actual_model if isinstance(actual_model, str) else model}

    async def probe(
        self,
        *,
        model: str,
        effort: str,
        workspace: Path,
        cancel,
        emit,
        authorized: bool = False,
        timeout: float = 30,
    ) -> GatewayCapabilityReport:
        """Opt-in network probe using only host-generated, harmless evidence.

        Four HTTP requests share one elapsed budget. A report is specific to this
        endpoint/model at checked_at; configuration flags never count as evidence.
        Cancellation propagates. Failure leaves later capabilities unverified.
        """
        if not authorized:
            raise ProviderError(
                "authorization_required",
                "Explicit authorization is required for 9Router probe",
            )
        from dataclasses import replace
        import fitz

        report = GatewayCapabilityReport(self.endpoint, model, effort, time.time())
        deadline = time.monotonic() + timeout
        workspace = Path(workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        workspace = workspace.resolve(strict=True)
        probe_image = None
        current = "structured_response"

        def schema(key):
            return {
                "type": "object",
                "properties": {key: {"type": "string"}},
                "required": [key],
                "additionalProperties": False,
            }

        async def exchange(
            prompt,
            output_schema,
            *,
            images=(),
            tools=(),
            messages=None,
            tool_choice=None,
        ):
            nonlocal report
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError(
                    "timeout", "Gateway probe elapsed budget exhausted", accepted=True
                )
            request = AIRequest(
                model,
                effort,
                prompt,
                images=images,
                schema=output_schema,
                tools=tools,
                timeout=remaining,
                gateway_authorized=True,
            )
            body = self._body(request, workspace)
            if messages is not None:
                body["messages"] = messages
            if tool_choice is not None:
                body["tool_choice"] = tool_choice
            result = await cancellable(
                self._perform(request, body, emit), cancel, remaining
            )
            report = replace(
                report,
                actual_model=result.actual_model,
                actual_effort=result.actual_effort,
            )
            return result, body

        try:
            nonce = secrets.token_hex(16)
            result, _ = await exchange(
                "Return a JSON object with nonce exactly: " + nonce, schema("nonce")
            )
            if result.tool_calls or result.data != {"nonce": nonce}:
                raise ProviderError(
                    "capability_mismatch",
                    "Structured nonce evidence did not match",
                    accepted=True,
                )
            report = replace(report, structured_response="verified")

            current = "vision"
            code = secrets.token_hex(3).upper()
            workspace = Path(workspace).resolve(strict=True)
            probe_image = workspace / ("gateway-probe-" + uuid.uuid4().hex + ".png")
            with fitz.open() as document:
                page = document.new_page(width=360, height=100)
                page.insert_text((30, 65), code, fontsize=42, fontname="cour")
                page.get_pixmap().save(probe_image)
            result, _ = await exchange(
                "Read the six characters in the supplied image. Return only JSON with key code.",
                schema("code"),
                images=(probe_image,),
            )
            if result.tool_calls or result.data != {"code": code}:
                raise ProviderError(
                    "capability_mismatch",
                    "Image-only evidence did not match",
                    accepted=True,
                )
            report = replace(report, vision="verified")

            current = "tool_protocol"
            name = "read_probe_nonce"
            tool = {
                "name": name,
                "description": "Read a harmless host-generated nonce.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
            result, body = await exchange(
                "Call read_probe_nonce once with empty arguments. Then return its nonce as JSON.",
                schema("nonce"),
                tools=(tool,),
                tool_choice={"type": "function", "function": {"name": name}},
            )
            if len(result.tool_calls) != 1:
                raise ProviderError(
                    "capability_mismatch",
                    "Missing single native tool call",
                    accepted=True,
                )
            call = result.tool_calls[0]
            if call["name"] != name or call["arguments"] != {} or not call["id"]:
                raise ProviderError(
                    "capability_mismatch", "Unexpected native tool call", accepted=True
                )
            tool_nonce = secrets.token_hex(24)
            messages = [
                *body["messages"],
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {"name": name, "arguments": "{}"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps({"nonce": tool_nonce}),
                },
            ]
            result, _ = await exchange(
                "",
                schema("nonce"),
                tools=(tool,),
                messages=messages,
                tool_choice="none",
            )
            if result.tool_calls or result.data != {"nonce": tool_nonce}:
                raise ProviderError(
                    "capability_mismatch",
                    "Native tool-result nonce did not match",
                    accepted=True,
                )
            return replace(report, tool_protocol="verified")
        except ProviderError as exc:
            return replace(report, **{current: "failed"}, error_kind=exc.kind)
        finally:
            if probe_image is not None:
                probe_image.unlink(missing_ok=True)
