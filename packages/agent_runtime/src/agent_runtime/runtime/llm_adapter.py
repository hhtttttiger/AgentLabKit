"""LLM adapter — direct gateway calls without pydantic-ai.

Extracts and refactors the LLM interaction logic from ``gateway_model.py``
so the agent loop can call the gateway directly. This module has **zero**
dependency on ``pydantic-ai``.

Responsibilities:
- Build prompts from conversation history + tool schemas
- Parse gateway JSON responses into typed directives (tool-call or final)
- Stream response deltas with incremental reply-text extraction
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from llm_gateway import GatewayError, GatewayService, TextGenerateRequest, TextStreamEvent, UsageInfo

from ..config import AgentSettings
from ..contracts.models import AgentDecision, AgentTurnRequest
from ..errors import AgentError, AgentErrorCode


# ── Response types ───────────────────────────────────────────────────────────


@dataclass
class ToolDirective:
    """The LLM wants to call a tool."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reply_text: str | None = None


@dataclass
class FinalDirective:
    """The LLM produced a final answer."""

    reply_text: str
    should_handoff: bool = False
    handoff_reason: str | None = None
    handoff_target_type: Literal["human", "agent"] | None = None
    handoff_target_agent: str | None = None


Directive = ToolDirective | FinalDirective


# ── Stream delta ─────────────────────────────────────────────────────────────


@dataclass
class StreamDelta:
    """Incremental output from a streaming LLM call."""

    delta: str = ""
    """Incremental text since last delta."""

    full_text: str = ""
    """Accumulated full text so far."""

    is_done: bool = False
    """True when the stream has completed."""

    usage: UsageInfo | None = None
    """Usage info, available when ``is_done`` is True."""


# ── Tool schema for prompt rendering ─────────────────────────────────────────


@dataclass
class ToolSchema:
    """Minimal tool description for prompt rendering."""

    name: str
    description: str
    parameters_json_schema: dict[str, Any]
    tags: list[str] = field(default_factory=list)


# ── LlmAdapter ──────────────────────────────────────────────────────────────


class LlmAdapter:
    """Direct interface to ``llm_gateway`` without pydantic-ai middleware.

    This replaces the ``GatewayBackedModel`` + ``FunctionModel`` approach
    with straightforward ``gateway.generate_text()`` /
    ``gateway.generate_text_stream()`` calls.
    """

    def __init__(
        self,
        service: GatewayService,
        *,
        settings: AgentSettings,
        request: AgentTurnRequest,
    ) -> None:
        self._service = service
        self._settings = settings
        self._request = request

    # ── Blocking call ─────────────────────────────────────────────────────

    async def generate(
        self,
        system_prompt: str,
        conversation: Sequence[tuple[str, str]],
        tools: Sequence[ToolSchema],
    ) -> tuple[Directive, UsageInfo | None]:
        """Blocking LLM call → parsed directive.

        Returns:
            ``(directive, usage)`` — ``usage`` may be ``None`` on error.
        """
        prompt = self.build_prompt(system_prompt, conversation, tools)
        request = TextGenerateRequest(
            model=self._request.model,
            provider=self._request.provider,
            prompt=prompt,
            trace_id=self._request.trace_id,
            metadata=self._request.metadata,
            temperature=self._settings.temperature,
            max_output_tokens=self._settings.max_output_tokens,
            structured=True,
        )
        try:
            response = await self._service.generate_text(request)
        except GatewayError as exc:
            raise AgentError(
                AgentErrorCode.GATEWAY_ERROR,
                exc.message,
                model=self._request.model,
                trace_id=self._request.trace_id,
            ) from exc

        if response.error is not None:
            raise AgentError(
                AgentErrorCode.GATEWAY_ERROR,
                response.error.message,
                model=self._request.model,
                trace_id=self._request.trace_id,
            )

        usage = _extract_usage(response.usage)
        directive = self.parse_response(response.text)
        return directive, usage

    # ── Streaming call ────────────────────────────────────────────────────

    async def generate_stream(
        self,
        system_prompt: str,
        conversation: Sequence[tuple[str, str]],
        tools: Sequence[ToolSchema],
    ) -> AsyncIterator[StreamDelta]:
        """Streaming LLM call yielding incremental deltas.

        The final delta has ``is_done=True`` with the complete response text
        and usage info.
        """
        prompt = self.build_prompt(system_prompt, conversation, tools)
        request = TextGenerateRequest(
            model=self._request.model,
            provider=self._request.provider,
            prompt=prompt,
            trace_id=self._request.trace_id,
            metadata=self._request.metadata,
            temperature=self._settings.temperature,
            max_output_tokens=self._settings.max_output_tokens,
            structured=True,
        )
        parser = ReplyTextStreamParser()
        try:
            async for event in self._service.generate_text_stream(request):
                if event.event_type == "delta":
                    delta_text = parser.consume(event.delta or "")
                    yield StreamDelta(
                        delta=delta_text,
                        full_text=parser.full_text,
                    )
                elif event.event_type == "completed":
                    completed_text = event.text or parser.full_text
                    final_delta = parser.finalize(completed_text)
                    usage = _extract_usage(event.usage)
                    yield StreamDelta(
                        delta=final_delta,
                        full_text=completed_text,
                        is_done=True,
                        usage=usage,
                    )
                    # IMPORTANT: do NOT return here.  Async generators must
                    # be drained to completion — an early return triggers
                    # aclose() → GeneratorExit which skips the upstream
                    # generator's post-yield cleanup.  Let the underlying
                    # stream exhaust naturally so all finalisers run.
        except GatewayError as exc:
            raise AgentError(
                AgentErrorCode.GATEWAY_ERROR,
                exc.message,
                model=self._request.model,
                trace_id=self._request.trace_id,
            ) from exc
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError(
                AgentErrorCode.RUNTIME_ERROR,
                str(exc),
                model=self._request.model,
                trace_id=self._request.trace_id,
            ) from exc

    # ── Prompt construction ───────────────────────────────────────────────

    def build_prompt(
        self,
        system_prompt: str,
        conversation: Sequence[tuple[str, str]],
        tools: Sequence[ToolSchema],
    ) -> str:
        """Build the full prompt text sent to the gateway."""
        tool_block = self._render_tools(tools)
        conversation_block = self._render_conversation(conversation)
        output_schema = {
            "kind": "final",
            "reply_text": "string",
            "should_handoff": False,
            "handoff_reason": None,
            "handoff_target_type": "human|agent (optional, default human)",
            "handoff_target_agent": "agent_key (required if handoff_target_type=agent, else null)",
        }
        tool_schema = {
            "kind": "tool_call",
            "tool_name": "tool_name",
            "arguments": {},
            "reply_text": "brief caller-facing feedback; do not include the final answer",
        }
        sections = [
            "Return a single JSON object and nothing else.",
            f"Final response shape: {json.dumps(output_schema, ensure_ascii=True)}",
            f"Tool call shape: {json.dumps(tool_schema, ensure_ascii=True)}",
            "When returning a tool call, include reply_text with brief caller-facing feedback that can be spoken immediately while the tool runs.",
            "Choose a tool call only when it materially improves accuracy.",
            "For weather or forecast requests in any language, call weather_query when available. "
            "Extract the city from the user text; map common Chinese city names to English city arguments, "
            "for example 广州 or 廣州 -> Guangzhou, 深圳 -> Shenzhen, 上海 -> Shanghai, 北京 -> Beijing, 香港 -> Hong Kong.",
            f"Instructions:\n{system_prompt}",
            f"Available tools:\n{tool_block}",
            f"Conversation:\n{conversation_block}",
        ]
        return "\n\n".join(sections)

    # ── Response parsing ──────────────────────────────────────────────────

    def parse_response(self, text: str) -> Directive:
        """Parse a raw gateway response into a typed directive."""
        normalized = text.strip()
        if normalized.startswith("```"):
            normalized = _strip_fences(normalized)
        decoder = json.JSONDecoder()
        try:
            payload, _ = decoder.raw_decode(normalized)
        except json.JSONDecodeError:
            return FinalDirective(reply_text=normalized)

        if payload.get("kind") == "tool_call":
            return ToolDirective(
                tool_name=payload.get("tool_name", ""),
                arguments=payload.get("arguments", {}),
                reply_text=payload.get("reply_text"),
            )
        if payload.get("kind") == "final":
            return FinalDirective(
                reply_text=payload.get("reply_text", ""),
                should_handoff=payload.get("should_handoff", False),
                handoff_reason=payload.get("handoff_reason"),
                handoff_target_type=payload.get("handoff_target_type"),
                handoff_target_agent=payload.get("handoff_target_agent"),
            )
        if "tool_name" in payload:
            return ToolDirective(
                tool_name=payload["tool_name"],
                arguments=payload.get("arguments", {}),
                reply_text=payload.get("reply_text"),
            )
        if "reply_text" in payload:
            return FinalDirective(
                reply_text=payload["reply_text"],
                should_handoff=payload.get("should_handoff", False),
                handoff_reason=payload.get("handoff_reason"),
            )
        raise AgentError(
            AgentErrorCode.INVALID_MODEL_RESPONSE,
            "Gateway model response did not match the expected JSON schema.",
            model=self._request.model,
            trace_id=self._request.trace_id,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _render_tools(tools: Sequence[ToolSchema]) -> str:
        if not tools:
            return "No function tools are available."
        return "\n".join(
            json.dumps(
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_json_schema,
                },
                ensure_ascii=True,
            )
            for t in tools
        )

    @staticmethod
    def _render_conversation(conversation: Sequence[tuple[str, str]]) -> str:
        return "\n".join(f"{role}: {content}" for role, content in conversation)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _extract_usage(raw: Any) -> UsageInfo | None:
    if raw is None:
        return None
    return UsageInfo(
        input_tokens=raw.input_tokens or 0,
        output_tokens=raw.output_tokens or 0,
        total_tokens=(raw.input_tokens or 0) + (raw.output_tokens or 0),
    )


def _strip_fences(text: str) -> str:
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text


class ReplyTextStreamParser:
    """Incremental parser that extracts ``reply_text`` from a streaming JSON response.

    Migrated from ``gateway_model.py::ReplyTextStreamParser`` — unchanged logic,
    just moved to the new module.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._emitted = ""

    def consume(self, delta: str) -> str:
        if not delta:
            return ""
        self._buffer += delta
        return self._extract_new_delta()

    def finalize(self, text: str) -> str:
        self._buffer = text
        return self._extract_new_delta()

    @property
    def full_text(self) -> str:
        return self._buffer

    def _extract_new_delta(self) -> str:
        current = self._extract_reply_text_prefix(self._buffer)
        if not current.startswith(self._emitted):
            return ""
        delta = current[len(self._emitted) :]
        self._emitted = current
        return delta

    def _extract_reply_text_prefix(self, text: str) -> str:
        kind = self._extract_kind(text)
        if kind not in {None, "final"}:
            return ""
        key_index = text.find('"reply_text"')
        if key_index < 0:
            return ""
        colon_index = text.find(":", key_index)
        if colon_index < 0:
            return ""
        quote_index = text.find('"', colon_index + 1)
        if quote_index < 0:
            return ""

        chars: list[str] = []
        index = quote_index + 1
        escaped = False
        while index < len(text):
            char = text[index]
            if escaped:
                if char == "u":
                    if index + 4 >= len(text):
                        break
                    hex_value = text[index + 1 : index + 5]
                    if any(part not in "0123456789abcdefABCDEF" for part in hex_value):
                        break
                    chars.append(chr(int(hex_value, 16)))
                    index += 4
                else:
                    chars.append(self._decode_escape(char))
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                break
            else:
                chars.append(char)
            index += 1
        return "".join(chars)

    @staticmethod
    def _extract_kind(text: str) -> str | None:
        key_index = text.find('"kind"')
        if key_index < 0:
            return None
        colon_index = text.find(":", key_index)
        if colon_index < 0:
            return None
        quote_index = text.find('"', colon_index + 1)
        if quote_index < 0:
            return None
        end_quote_index = text.find('"', quote_index + 1)
        if end_quote_index < 0:
            return None
        return text[quote_index + 1 : end_quote_index]

    @staticmethod
    def _decode_escape(char: str) -> str:
        mapping = {
            '"': '"',
            "\\": "\\",
            "/": "/",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
        }
        return mapping.get(char, char)


__all__ = [
    "Directive",
    "FinalDirective",
    "LlmAdapter",
    "ReplyTextStreamParser",
    "StreamDelta",
    "ToolDirective",
    "ToolSchema",
]
