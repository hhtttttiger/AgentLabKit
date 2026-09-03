from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from agent_runtime import AgentMessage, AgentRole, AgentTurnRequest, ToolRegistry
from agent_runtime.config import AgentSettings
from agent_runtime.contracts.models import KnowledgeChunk
from agent_runtime.contracts.run import ExecutionContext
from agent_runtime.events_v2 import RetrievalCompleted, RetrievalFailed, RetrievalStarted, ToolCallCompleted, ToolCallFailed, ToolCallStarted
from agent_runtime.runtime import AgentRuntime
from agent_runtime.tools.contracts import ToolResult, ToolSpec
from llm_gateway import ProviderId, TextStreamEvent, UsageInfo


class _StreamingGateway:
    def __init__(self, responses: list[list[TextStreamEvent]]) -> None:
        self.responses = list(responses)

    async def generate_text_stream(self, request) -> AsyncIterator[TextStreamEvent]:
        for event in self.responses.pop(0):
            yield event


class _SlowProvider:
    async def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        await asyncio.sleep(0.02)
        return [KnowledgeChunk(title="Policy", content="Ships tomorrow", source="kb://policy")]


class _FailingProvider:
    async def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        raise RuntimeError("provider unavailable")


class _BlockingProvider:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.block = asyncio.Event()

    async def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        self.entered.set()
        await self.block.wait()
        return []


class _RetryProvider:
    def __init__(self) -> None:
        self.attempts = 0

    async def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("transient provider error")
        return [KnowledgeChunk(title="Recovered", content="ok", source="kb://retry")]


class _RaisingTool:
    async def execute(self, arguments, context) -> ToolResult:
        raise RuntimeError("tool exploded")


class _PlainTool:
    async def execute(self, arguments, context) -> ToolResult:
        return ToolResult(output="plain result")


def _custom_spec(name: str) -> ToolSpec:
    return ToolSpec(name=name, description=name, parameters_schema={"type": "object", "properties": {}}, max_retries=0)


def _tool_call(name: str = "knowledge_search") -> list[TextStreamEvent]:
    args = '{"query":"policy"}' if name == "knowledge_search" else "{}"
    return [TextStreamEvent(event_type="completed", provider=ProviderId.OPENAI, model="test-model", text=f'{{"kind":"tool_call","tool_name":"{name}","arguments":{args}}}', usage=UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2))]


def _final() -> list[TextStreamEvent]:
    return [TextStreamEvent(event_type="completed", provider=ProviderId.OPENAI, model="test-model", text='{"kind":"final","reply_text":"done","should_handoff":false}', usage=UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2))]


def _request() -> AgentTurnRequest:
    return AgentTurnRequest(session_id="stream-observe", user_message="find policy", history=[AgentMessage(role=AgentRole.USER, content="hi")], trace_id="trace-stream-observe")


async def _run(runtime: AgentRuntime) -> list[object]:
    events: list[object] = []
    runtime.subscribe(events.append)
    async for _ in runtime.stream_turn(_request(), execution_context=ExecutionContext()):
        pass
    return events


@pytest.mark.asyncio
async def test_streaming_retrieval_is_nested_and_tool_duration_is_measured() -> None:
    runtime = AgentRuntime(settings=AgentSettings(), gateway=_StreamingGateway([_tool_call(), _final()]), tool_registry=ToolRegistry(knowledge_provider=_SlowProvider()))
    events = await _run(runtime)
    started = [e for e in events if isinstance(e, ToolCallStarted)]
    tool_done = [e for e in events if isinstance(e, ToolCallCompleted)]
    retrieval_started = [e for e in events if isinstance(e, RetrievalStarted)]
    retrieval_done = [e for e in events if isinstance(e, RetrievalCompleted)]
    assert len(started) == len(tool_done) == 1
    assert len(retrieval_started) == len(retrieval_done) == 1
    assert not [e for e in events if isinstance(e, RetrievalFailed)]
    assert retrieval_started[0].parent_span_id == started[0].span_id
    assert retrieval_done[0].span_id == retrieval_started[0].span_id
    assert tool_done[0].duration_ms >= 5
    types = [type(e) for e in events]
    assert types.index(ToolCallStarted) < types.index(RetrievalStarted) < types.index(RetrievalCompleted) < types.index(ToolCallCompleted)


@pytest.mark.asyncio
async def test_streaming_retrieval_failure_and_retry_have_one_terminal_per_attempt() -> None:
    runtime = AgentRuntime(settings=AgentSettings(), gateway=_StreamingGateway([_tool_call(), _final()]), tool_registry=ToolRegistry(knowledge_provider=_FailingProvider()))
    events = await _run(runtime)
    rs = [e for e in events if isinstance(e, RetrievalStarted)]
    rf = [e for e in events if isinstance(e, RetrievalFailed)]
    assert len(rs) == len(rf) == 2  # KnowledgeSearchTool retries once.
    assert not [e for e in events if isinstance(e, RetrievalCompleted)]
    assert {e.span_id for e in rs} == {e.span_id for e in rf}
    assert len([e for e in events if isinstance(e, ToolCallCompleted)]) == 1

    provider = _RetryProvider()
    runtime = AgentRuntime(settings=AgentSettings(), gateway=_StreamingGateway([_tool_call(), _final()]), tool_registry=ToolRegistry(knowledge_provider=provider))
    events = await _run(runtime)
    rs = [e for e in events if isinstance(e, RetrievalStarted)]
    rf = [e for e in events if isinstance(e, RetrievalFailed)]
    rc = [e for e in events if isinstance(e, RetrievalCompleted)]
    tool = next(e for e in events if isinstance(e, ToolCallStarted))
    assert provider.attempts == 2 and len(rs) == 2 and len(rf) == len(rc) == 1
    assert rf[0].span_id != rc[0].span_id
    assert all(e.parent_span_id == tool.span_id for e in rs + rf + rc)


@pytest.mark.asyncio
async def test_streaming_cancellation_closes_retrieval_and_tool_spans() -> None:
    provider = _BlockingProvider()
    runtime = AgentRuntime(settings=AgentSettings(), gateway=_StreamingGateway([_tool_call()]), tool_registry=ToolRegistry(knowledge_provider=provider))
    events: list[object] = []
    runtime.subscribe(events.append)
    stream = runtime.stream_turn(_request(), execution_context=ExecutionContext())
    await stream.__anext__()
    pending = asyncio.create_task(stream.__anext__())
    await provider.entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    rs = [e for e in events if isinstance(e, RetrievalStarted)]
    rf = [e for e in events if isinstance(e, RetrievalFailed)]
    assert len(rs) == len(rf) == 1
    assert not [e for e in events if isinstance(e, RetrievalCompleted)]
    await stream.aclose()


@pytest.mark.asyncio
async def test_streaming_exceptional_tool_call_has_failed_terminal() -> None:
    registry = ToolRegistry()
    registry.dynamic_registry.register(_custom_spec("explode"), _RaisingTool())
    runtime = AgentRuntime(settings=AgentSettings(), gateway=_StreamingGateway([_tool_call("explode")]), tool_registry=registry)
    # Exercise the boundary where execute_tool_call itself raises, rather than
    # a normal ToolResult(status="error") returned by ToolExecutor.
    runtime._tool_exec.execute_tool_call = AsyncMock(side_effect=RuntimeError("tool exploded"))
    events: list[object] = []
    runtime.subscribe(events.append)
    with pytest.raises(Exception, match="tool exploded"):
        async for _ in runtime.stream_turn(_request(), execution_context=ExecutionContext()):
            pass
    assert len([e for e in events if isinstance(e, ToolCallStarted)]) == 1
    assert len([e for e in events if isinstance(e, ToolCallFailed)]) == 1
    assert not [e for e in events if isinstance(e, ToolCallCompleted)]


@pytest.mark.asyncio
async def test_ordinary_streaming_tool_emits_no_retrieval_events() -> None:
    registry = ToolRegistry()
    registry.dynamic_registry.register(_custom_spec("plain"), _PlainTool())
    runtime = AgentRuntime(settings=AgentSettings(), gateway=_StreamingGateway([_tool_call("plain"), _final()]), tool_registry=registry)
    events = await _run(runtime)
    assert len([e for e in events if isinstance(e, ToolCallStarted)]) == 1
    assert len([e for e in events if isinstance(e, ToolCallCompleted)]) == 1
    assert not [e for e in events if isinstance(e, (RetrievalStarted, RetrievalCompleted, RetrievalFailed))]
