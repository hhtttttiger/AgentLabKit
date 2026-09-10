"""Blocking-mode executions must project the same ToolCall → Retrieval span
hierarchy as the streaming path.

``run_agent_loop`` (the run()/EvaluateDataset execution path) builds its
retrieval observer internally. The per-tool OTel scope opened through the
factory is an execution-time fact bridge only — identity still comes from
the Runtime. Projection parity matters: the Runtime's own span stack treats
the ToolCall span as the retrieval's parent, so a projection that parents
retrieval directly to the run root (or drops the ToolCall span) is not the
real parent chain.
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


class RecordingScope:
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        self.started: list[dict[str, Any]] = []
        self.succeeded: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.finished: list[bool] = []

    def start(self, *, query: str, source: str, knowledge_base_ids,
              top_k: int | None, search_mode: str | None) -> Any:
        self.started.append({"query": query, "source": source})
        return object()

    def succeed(self, span: Any, *, result_count: int, duration_ms: int, results) -> None:
        self.succeeded.append({"result_count": result_count, "results": list(results)})

    def fail(self, span: Any, error_message: str) -> None:
        self.failed.append({"error_message": error_message})

    def finish(self, *, is_error: bool) -> None:
        self.finished.append(is_error)


class RecordingScopeFactory:
    def __init__(self) -> None:
        self.scopes: list[RecordingScope] = []

    def open(self, tool_name: str) -> RecordingScope:
        scope = RecordingScope(tool_name)
        self.scopes.append(scope)
        return scope


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
async def test_loop_retrieval_execution_reaches_per_tool_scope():
    captured: dict[str, Any] = {}
    factory = RecordingScopeFactory()

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
        tool_span_scope_factory=factory,
    )

    assert captured["observed"] is True
    assert len(factory.scopes) == 1
    scope = factory.scopes[0]
    assert scope.tool_name == "search"
    assert len(scope.started) == 1
    assert scope.started[0]["query"] == "falcon"
    assert len(scope.succeeded) == 1
    refs = scope.succeeded[0]["results"]
    assert refs[0].content_preview == "Tuesday 03:00 UTC"
    assert scope.failed == []
    # The ToolCall span is closed exactly once on the success path.
    assert scope.finished == [False]
    assert result.final_directive is not None


@pytest.mark.asyncio
async def test_loop_tool_span_finishes_as_error_on_invocation_failure():
    factory = RecordingScopeFactory()

    async def tool_executor(tool_name, arguments, tool_call_id, observers=None):
        raise RuntimeError("tool exploded")

    with pytest.raises(RuntimeError, match="tool exploded"):
        await run_agent_loop(
            prompts=[],
            context=LoopContext(system_prompt="", messages=[], tools=[]),
            config=LoopConfig(tool_executor=tool_executor),
            llm=FakeLLM(),
            event_bus=None,
            tool_span_scope_factory=factory,
        )

    assert len(factory.scopes) == 1
    assert factory.scopes[0].finished == [True]


@pytest.mark.asyncio
async def test_loop_without_scope_factory_still_executes_retrieval():
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
        tool_span_scope_factory=None,
    )
    assert result.final_directive is not None
