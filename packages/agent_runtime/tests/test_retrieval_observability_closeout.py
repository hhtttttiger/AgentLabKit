from __future__ import annotations

import pytest

from agent_runtime.contracts.models import KnowledgeChunk
from agent_runtime.events_v2 import RetrievalCompleted, RetrievalStarted
from agent_runtime.runtime.loop import LoopConfig, _SpanContext, _execute_tool
from agent_runtime.runtime.retrieval_observer import RuntimeRetrievalObserver
from agent_runtime.tools.contracts import ToolResult


@pytest.mark.asyncio
async def test_missing_executor_returns_canonical_tool_result() -> None:
    result = await _execute_tool(
        tool_name="knowledge_search",
        arguments={},
        tool_call_id="call-1",
        config=LoopConfig(),
        emit=lambda _: None,
    )
    assert isinstance(result, ToolResult)
    assert result.status == "error"
    assert result.error_message == "Tool 'knowledge_search' has no executor configured."


@pytest.mark.asyncio
async def test_legacy_executor_is_adapted_once() -> None:
    calls = 0

    async def legacy(name, arguments, call_id):
        nonlocal calls
        calls += 1
        return "legacy output", True

    result = await _execute_tool(
        tool_name="legacy_tool",
        arguments={},
        tool_call_id="call-1",
        config=LoopConfig(tool_executor=legacy),
        emit=lambda _: None,
    )
    assert result == ToolResult(output="legacy output", status="success")
    assert calls == 1


@pytest.mark.asyncio
async def test_internal_type_error_is_not_retried() -> None:
    calls = 0

    async def executor(name, arguments, call_id, observers):
        nonlocal calls
        calls += 1
        raise TypeError("internal tool bug")

    with pytest.raises(TypeError, match="internal tool bug"):
        await _execute_tool(
            tool_name="side_effect_tool",
            arguments={},
            tool_call_id="call-1",
            config=LoopConfig(tool_executor=executor),
            emit=lambda _: None,
        )
    assert calls == 1


@pytest.mark.asyncio
async def test_retrieval_provenance_is_bounded_but_count_is_full() -> None:
    events = []

    async def emit(event):
        events.append(event)

    span_context = _SpanContext()
    span_context.push("tool-span")
    observer = RuntimeRetrievalObserver(emit, span_context)
    chunks = [
        KnowledgeChunk(
            content="x" * 1000,
            score=0.0 if index == 0 else None,
            knowledge_base_id="kb",
            document_id=None,
            segment_id=None,
            title=f"title-{index}",
            source="source",
        )
        for index in range(15)
    ]

    async with observer.observe(
        query="query", source="knowledge", knowledge_base_ids=("kb",), top_k=15,
    ) as observation:
        observation.set_results(chunks)

    started = next(event for event in events if isinstance(event, RetrievalStarted))
    completed = next(event for event in events if isinstance(event, RetrievalCompleted))
    assert started.parent_span_id == "tool-span"
    assert completed.span_id == started.span_id
    assert completed.result_count == 15
    assert len(completed.results) == 10
    assert completed.results[0].score == 0.0
    assert completed.results[0].document_id is None
    assert len(completed.results[0].content_preview) == 400
