"""Blocking-mode executions must project the same bounded retrieval spans as
the streaming path.

``run_agent_loop`` (the run()/EvaluateDataset execution path) builds its
retrieval observer internally; without a span sink the projected trace
legitimately contains no retrieval evidence. The sink is an execution-time
fact bridge only — identity still comes from the Runtime.
"""

from __future__ import annotations

from typing import Any

import pytest

from agent_runtime.contracts.models import KnowledgeChunk
from agent_runtime.runtime.llm_adapter import FinalDirective, ToolDirective
from agent_runtime.runtime.loop import (
    LoopConfig,
    LoopContext,
    run_agent_loop,
)
from agent_runtime.tools.contracts import ToolExecutionObservers, ToolResult


class RecordingSink:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.succeeded: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []

    def start(self, *, query: str, source: str, knowledge_base_ids,
              top_k: int | None, search_mode: str | None) -> Any:
        self.started.append({"query": query, "source": source})
        return object()

    def succeed(self, span: Any, *, result_count: int, duration_ms: int, results) -> None:
        self.succeeded.append({"result_count": result_count, "results": list(results)})

    def fail(self, span: Any, error_message: str) -> None:
        self.failed.append({"error_message": error_message})


class FakeLLM:
    """First call returns a tool directive, then a final reply."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, *, system_prompt, conversation, tools, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return ToolDirective(tool_name="search", arguments={"query": "falcon"}), None
        return FinalDirective(reply_text="done"), None


def _chunk(preview: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        knowledge_base_id="kb-1",
        document_id="doc-1",
        segment_id="seg-1",
        score=0.9,
        title="falcon",
        source="falcon.md",
        content=preview,
    )


@pytest.mark.asyncio
async def test_loop_retrieval_execution_reaches_span_sink():
    captured: dict[str, Any] = {}
    sink = RecordingSink()

    async def tool_executor(tool_name, arguments, tool_call_id, observers=None):
        if isinstance(observers, ToolExecutionObservers) and observers.retrieval is not None:
            async with observers.retrieval.observe(
                query="falcon", source="kb", knowledge_base_ids=("kb-1",),
            ) as observation:
                observation.set_results([_chunk("Tuesday 03:00 UTC")])
        captured["observed"] = observers is not None
        return ToolResult(output="Tuesday 03:00 UTC")

    result = await run_agent_loop(
        prompts=[],
        context=LoopContext(system_prompt="", messages=[], tools=[]),
        config=LoopConfig(tool_executor=tool_executor),
        llm=FakeLLM(),
        event_bus=None,
        retrieval_span_sink=sink,
    )

    assert captured["observed"] is True
    assert len(sink.started) == 1
    assert sink.started[0]["query"] == "falcon"
    assert len(sink.succeeded) == 1
    refs = sink.succeeded[0]["results"]
    assert refs[0].content_preview == "Tuesday 03:00 UTC"
    assert sink.failed == []
    assert result.final_directive is not None


@pytest.mark.asyncio
async def test_loop_without_sink_still_executes_retrieval():
    async def tool_executor(tool_name, arguments, tool_call_id, observers=None):
        if isinstance(observers, ToolExecutionObservers) and observers.retrieval is not None:
            async with observers.retrieval.observe(query="q", source="kb"):
                pass
        return ToolResult(output="ok")

    result = await run_agent_loop(
        prompts=[],
        context=LoopContext(system_prompt="", messages=[], tools=[]),
        config=LoopConfig(tool_executor=tool_executor),
        llm=FakeLLM(),
        event_bus=None,
        retrieval_span_sink=None,
    )
    assert result.final_directive is not None
