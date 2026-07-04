"""Unit tests for the agent-turn SSE mapping + stream driver.

Pure/fake tests — no DB, no real LLM. Covers:
- ``map_stream_event``: every runtime event type → frontend camelCase dict,
  with runId/sessionId/traceId injected and the two renamed types.
- ``run_agent_turn_stream``: happy-path event sequence + terminal ``[DONE]``,
  the error path (runtime raises ``AgentError`` → ``error`` event), and that
  one audit row is persisted in each case.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import pytest

from agent_runtime import AgentTurnStreamEvent, ToolExecutionRecord
from agent_runtime.errors import AgentError, AgentErrorCode
from llm_gateway.models import UsageInfo

from modules.ai_invoke.agent_turn import map_stream_event, run_agent_turn_stream

RUN_ID = "run-xyz"
AGENT_KEY = "default"
AGENT_VERSION = 1


# ── map_stream_event ────────────────────────────────────────────────────────


def _map(event: AgentTurnStreamEvent) -> dict[str, Any]:
    return map_stream_event(
        event, run_id=RUN_ID, agent_key=AGENT_KEY, agent_version=AGENT_VERSION
    )


def test_turn_context_maps_to_context_with_applied_skills():
    event = AgentTurnStreamEvent(
        event_type="turn_context",
        session_id="s1",
        trace_id="t1",
        applied_skills=[],
    )
    payload = _map(event)
    assert payload["type"] == "context"
    assert payload["runId"] == RUN_ID
    assert payload["sessionId"] == "s1"
    assert payload["traceId"] == "t1"
    assert payload["agentKey"] == AGENT_KEY
    assert payload["agentVersion"] == AGENT_VERSION
    assert payload["appliedSkills"] == []


def test_reply_delta_carries_delta():
    payload = _map(AgentTurnStreamEvent(event_type="reply_delta", session_id="s", trace_id="t", delta="Hello"))
    assert payload["type"] == "reply_delta"
    assert payload["delta"] == "Hello"


def test_reply_completed_maps_to_completed_with_usage():
    payload = _map(
        AgentTurnStreamEvent(
            event_type="reply_completed",
            session_id="s",
            trace_id="t",
            reply_text="Hi there",
            usage=UsageInfo(input_tokens=5, output_tokens=7, total_tokens=12),
        )
    )
    assert payload["type"] == "completed"
    assert payload["replyText"] == "Hi there"
    assert payload["status"] == "succeeded"
    assert payload["usage"] == {"inputTokens": 5, "outputTokens": 7, "totalTokens": 12, "audioDurationMs": None}


def test_tool_call_and_tool_result_map_tool_event_camel_case():
    record = ToolExecutionRecord(
        tool_name="knowledge_search",
        status="succeeded",
        arguments={"query": "shipping"},
        output_text="Orders ship in 24h",
        display_name="Knowledge Search",
        source_type="builtin",
        duration_ms=42,
        tags=["kb"],
    )
    call = _map(
        AgentTurnStreamEvent(
            event_type="tool_call", session_id="s", trace_id="t",
            tool_name="knowledge_search", tool_arguments={"query": "shipping"}, tool_event=record,
        )
    )
    assert call["type"] == "tool_call"
    assert call["toolName"] == "knowledge_search"
    assert call["toolArguments"] == {"query": "shipping"}
    te = call["toolEvent"]
    assert te["toolName"] == "knowledge_search"
    assert te["outputText"] == "Orders ship in 24h"
    assert te["displayName"] == "Knowledge Search"
    assert te["sourceType"] == "builtin"
    assert te["durationMs"] == 42
    assert te["tags"] == ["kb"]

    result = _map(
        AgentTurnStreamEvent(event_type="tool_result", session_id="s", trace_id="t", tool_event=record)
    )
    assert result["type"] == "tool_result"
    assert result["toolEvent"]["status"] == "succeeded"


def test_handoff_maps_with_reason():
    payload = _map(
        AgentTurnStreamEvent(
            event_type="handoff", session_id="s", trace_id="t",
            reply_text="escalating", handoff_reason="needs human",
        )
    )
    assert payload["type"] == "handoff"
    assert payload["handoffReason"] == "needs human"
    assert payload["status"] == "succeeded"


def test_delegation_delta_maps():
    payload = _map(
        AgentTurnStreamEvent(
            event_type="delegation_delta", session_id="s", trace_id="t",
            delta="partial", delegation_agent_key="refund-specialist",
        )
    )
    assert payload["type"] == "delegation_delta"
    assert payload["delta"] == "partial"
    assert payload["delegationAgentKey"] == "refund-specialist"


# ── run_agent_turn_stream ───────────────────────────────────────────────────


class _FakeAuditSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeAuditSession":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.session = _FakeAuditSession()

    def __call__(self) -> _FakeAuditSession:
        return self.session


def _parse_sse_lines(lines: list[str]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for line in lines:
        data = line[len("data: "):].strip() if line.startswith("data: ") else None
        if data is None or data == "[DONE]":
            continue
        payloads.append(json.loads(data))
    return payloads


class _FakeRuntime:
    """Yields a scripted list of events from ``stream_turn``."""

    def __init__(self, events: list[AgentTurnStreamEvent]) -> None:
        self._events = events

    async def stream_turn(self, request: Any) -> AsyncIterator[AgentTurnStreamEvent]:
        for event in self._events:
            yield event


class _FakeRuntimeRaises:
    """Yields one event, then raises ``AgentError`` on the next pull."""

    def __init__(self, events: list[AgentTurnStreamEvent], error: AgentError) -> None:
        self._events = events
        self._error = error

    async def stream_turn(self, request: Any) -> AsyncIterator[AgentTurnStreamEvent]:
        for event in self._events:
            yield event
        raise self._error


@pytest.mark.asyncio
async def test_stream_happy_path_emits_context_deltas_completed_then_done():
    runtime = _FakeRuntime(
        [
            AgentTurnStreamEvent(event_type="turn_context", session_id="s", trace_id="t", applied_skills=[]),
            AgentTurnStreamEvent(event_type="reply_delta", session_id="s", trace_id="t", delta="Hello "),
            AgentTurnStreamEvent(event_type="reply_delta", session_id="s", trace_id="t", delta="world"),
            AgentTurnStreamEvent(
                event_type="reply_completed", session_id="s", trace_id="t",
                reply_text="Hello world",
                usage=UsageInfo(input_tokens=1, output_tokens=2, total_tokens=3),
            ),
        ]
    )
    sf = _FakeSessionFactory()

    lines = [
        line
        async for line in run_agent_turn_stream(
            runtime, agent_key=AGENT_KEY, agent_version=AGENT_VERSION,
            message="hi", session_id="s", history=[], session_factory=sf,
        )
    ]

    payloads = _parse_sse_lines(lines)
    assert [p["type"] for p in payloads] == ["context", "reply_delta", "reply_delta", "completed"]
    assert lines[-1] == "data: [DONE]\n\n"
    # every payload carries the run id
    assert all(p["runId"] for p in payloads)

    # audit written once, success, with aggregated reply text
    assert len(sf.session.added) == 1
    audit = sf.session.added[0]
    assert audit.status == "success"
    assert audit.output_summary == "Hello world"
    assert audit.agent_version == AGENT_VERSION
    assert sf.session.committed is True


@pytest.mark.asyncio
async def test_stream_error_path_emits_error_event_and_failed_audit():
    error = AgentError(AgentErrorCode.GATEWAY_ERROR, "upstream blew up")
    runtime = _FakeRuntimeRaises(
        [AgentTurnStreamEvent(event_type="turn_context", session_id="s", trace_id="t", applied_skills=[])],
        error,
    )
    sf = _FakeSessionFactory()

    lines = [
        line
        async for line in run_agent_turn_stream(
            runtime, agent_key=AGENT_KEY, agent_version=AGENT_VERSION,
            message="hi", session_id="s", history=[], session_factory=sf,
        )
    ]

    payloads = _parse_sse_lines(lines)
    assert [p["type"] for p in payloads] == ["context", "error"]
    err = payloads[-1]
    assert err["errorCode"] == "gateway_error"
    assert err["errorMessage"] == "upstream blew up"
    assert err["status"] == "failed"
    assert lines[-1] == "data: [DONE]\n\n"

    audit = sf.session.added[0]
    assert audit.status == "error"
    assert audit.error_message == "upstream blew up"
