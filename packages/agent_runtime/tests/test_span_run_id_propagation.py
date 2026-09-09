"""DF-02 regression: the Runtime's authoritative run_id reaches the root span.

Production traces are built by TraceBufferSpanProcessor from OTel spans; it
reads ``agentlabkit.run_id`` from the root span and never fabricates one.
Before this fix the runtime never attached the attribute, so every real run
produced an unpublishable trace (UUID("") validation) whose exception could
propagate through Span.end() into the runtime.  These tests drive the real
engine with a real OTel TracerProvider in both blocking and streaming modes
and assert the span identity matches the ExecutionContext identity.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider

from agent_runtime import AgentTurnRequest, ToolRegistry
from agent_runtime.config import AgentSettings
from agent_runtime.contracts.run import AgentRun, RunStatus
from agent_runtime.runtime import AgentRuntime
from llm_gateway import (
    ProviderId,
    TextGenerateResponse,
    TextStreamEvent,
    UsageInfo,
)


class _RecordingProcessor(SpanProcessor):
    def __init__(self) -> None:
        self.ended: list[ReadableSpan] = []

    def on_start(self, span, parent_context=None) -> None:  # noqa: ANN001
        return

    def on_end(self, span: ReadableSpan) -> None:
        self.ended.append(span)

    def shutdown(self) -> None:
        return

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True


class FakeGatewayService:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def generate_text(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _StreamingGateway:
    def __init__(self, responses: list[list[TextStreamEvent]]) -> None:
        self.responses = list(responses)

    async def generate_text_stream(self, request) -> AsyncIterator[TextStreamEvent]:
        for event in self.responses.pop(0):
            yield event


def _final(text: str) -> TextGenerateResponse:
    import json
    payload = json.dumps({"kind": "final", "reply_text": text, "should_handoff": False})
    return TextGenerateResponse(
        provider=ProviderId.OPENAI, model="test-model", text=payload,
        usage=UsageInfo(input_tokens=10, output_tokens=5),
    )


def _tool_call(name: str, arguments: dict) -> TextGenerateResponse:
    import json
    payload = json.dumps({"kind": "tool_call", "tool_name": name, "arguments": arguments})
    return TextGenerateResponse(
        provider=ProviderId.OPENAI, model="test-model", text=payload,
        usage=UsageInfo(input_tokens=10, output_tokens=5),
    )


def _stream_final(text: str) -> list[TextStreamEvent]:
    import json
    payload = json.dumps({"kind": "final", "reply_text": text, "should_handoff": False})
    return [TextStreamEvent(
        event_type="completed", provider=ProviderId.OPENAI, model="test-model",
        text=payload, usage=UsageInfo(input_tokens=1, output_tokens=1),
    )]


def _make_tracer_and_recorder():
    provider = TracerProvider()
    recorder = _RecordingProcessor()
    provider.add_span_processor(recorder)
    return provider.get_tracer("test"), recorder


def _root_span(recorder: _RecordingProcessor) -> ReadableSpan:
    roots = [s for s in recorder.ended if s.name == "agent.run"]
    assert roots, "the runtime must end an 'agent.run' root span"
    assert len(roots) == 1
    return roots[0]


@pytest.mark.asyncio
async def test_blocking_run_attaches_authoritative_run_id_to_root_span():
    tracer, recorder = _make_tracer_and_recorder()
    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=FakeGatewayService([_final("hello")]),
        tool_registry=ToolRegistry(),
        tracer=tracer,
    )

    agent_run: AgentRun = await runtime.run(AgentTurnRequest(
        user_message="hi", session_id="s1",
    ))
    assert agent_run.status == RunStatus.COMPLETED

    root = _root_span(recorder)
    attrs = dict(root.attributes or {})
    # The span carries the Runtime-owned identity — exactly, not a re-encoding.
    assert attrs.get("agentlabkit.run_id") == agent_run.run_id
    assert attrs.get("agentlabkit.trace.root") is True
    # The OTel trace id equals the Runtime-owned trace identity so the Run
    # projection (which carries the same id) links to this trace exactly.
    assert format(root.context.trace_id, "032x") == agent_run.trace_id


@pytest.mark.asyncio
async def test_streaming_run_attaches_authoritative_run_id_to_root_span():
    tracer, recorder = _make_tracer_and_recorder()
    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=_StreamingGateway([_stream_final("streamed")]),
        tool_registry=ToolRegistry(),
        tracer=tracer,
    )

    event_run_ids = set()
    async for event in runtime.stream(AgentTurnRequest(
        user_message="hi", session_id="s2",
    )):
        if getattr(event, "run_id", ""):
            event_run_ids.add(event.run_id)

    assert event_run_ids, "stream events must carry the context run_id"
    assert len(event_run_ids) == 1, "one run — one authoritative run_id"

    root = _root_span(recorder)
    attrs = dict(root.attributes or {})
    assert attrs.get("agentlabkit.run_id") == event_run_ids.pop()


@pytest.mark.asyncio
async def test_child_spans_share_the_root_trace_and_parent_to_it():
    """Streaming llm.generate / tool.* spans must land in the same trace, under the root."""
    import json

    from agent_runtime.tools.contracts import ToolExecutionContext, ToolResult
    from agent_runtime.tools.registry import ToolSpec

    class _EchoTool:
        async def execute(self, arguments, context: ToolExecutionContext):  # noqa: ANN001, ARG002
            return ToolResult(output="echo")

    def _stream_events(text: str) -> list[TextStreamEvent]:
        return [TextStreamEvent(
            event_type="completed", provider=ProviderId.OPENAI, model="test-model",
            text=text, usage=UsageInfo(input_tokens=1, output_tokens=1),
        )]

    tracer, recorder = _make_tracer_and_recorder()
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="echo_tool",
            description="echo",
            parameters_schema={"type": "object", "properties": {}},
        ),
        _EchoTool(),
    )

    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=_StreamingGateway([
            _stream_events(json.dumps({
                "kind": "tool_call", "tool_name": "echo_tool", "arguments": {},
            })),
            _stream_events(json.dumps({
                "kind": "final", "reply_text": "done after tool", "should_handoff": False,
            })),
        ]),
        tool_registry=registry,
        tracer=tracer,
    )

    async for _ in runtime.stream(AgentTurnRequest(
        user_message="use the tool", session_id="s3",
    )):
        pass

    root = _root_span(recorder)
    root_trace = root.context.trace_id
    root_span_id = root.context.span_id

    llm_spans = [s for s in recorder.ended if s.name == "llm.generate"]
    tool_spans = [s for s in recorder.ended if s.name.startswith("tool.")]
    assert llm_spans, "LLM spans must be recorded"
    assert tool_spans, "tool span must be recorded"

    for span in llm_spans + tool_spans:
        assert span.context.trace_id == root_trace, (
            f"{span.name} must share the root trace"
        )
        assert span.parent is not None and span.parent.span_id == root_span_id, (
            f"{span.name} must be parented to agent.run"
        )


@pytest.mark.asyncio
async def test_retrieval_span_lands_under_tool_span_with_execution_facts():
    """knowledge_search retrieval becomes an OTel span with bounded refs."""
    import json

    from agent_runtime.contracts.models import KnowledgeChunk
    from agent_runtime.events_v2 import RetrievalCompleted, RetrievalStarted
    from agent_runtime.tools.contracts import ToolExecutionContext, ToolResult
    from agent_runtime.tools.registry import ToolSpec

    class _KbProvider:
        async def search(self, query: str, top_k: int = 5):
            return [
                KnowledgeChunk(
                    title="Policy", content="Ships within 24h", source="kb://policy",
                    knowledge_base_id="355981249820491776", document_id="9007199254740993",
                    segment_id="9007199254740995", score=0.87,
                ),
            ]

    def _stream_events(text: str) -> list[TextStreamEvent]:
        return [TextStreamEvent(
            event_type="completed", provider=ProviderId.OPENAI, model="test-model",
            text=text, usage=UsageInfo(input_tokens=1, output_tokens=1),
        )]

    tracer, recorder = _make_tracer_and_recorder()
    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=_StreamingGateway([
            _stream_events(json.dumps({
                "kind": "tool_call", "tool_name": "knowledge_search",
                "arguments": {"query": "shipping policy"},
            })),
            _stream_events(json.dumps({"kind": "final", "reply_text": "ok", "should_handoff": False})),
        ]),
        tool_registry=ToolRegistry(knowledge_provider=_KbProvider()),
        tracer=tracer,
    )

    events: list = []
    runtime.subscribe(events.append)
    async for _ in runtime.stream(AgentTurnRequest(
        user_message="shipping?", session_id="s-rag",
    )):
        pass

    assert any(isinstance(e, RetrievalStarted) for e in events)
    assert any(isinstance(e, RetrievalCompleted) for e in events)

    root = _root_span(recorder)
    tool_spans = [s for s in recorder.ended if s.name.startswith("tool.")]
    retrieval_spans = [s for s in recorder.ended if s.name == "retrieval.search"]
    assert tool_spans, "knowledge_search tool span must be recorded"
    assert retrieval_spans, "retrieval span must be recorded"

    rspan = retrieval_spans[0]
    attrs = dict(rspan.attributes or {})
    assert attrs.get("agentlabkit.kind") == "retrieval"
    assert attrs.get("retrieval.query") == "shipping policy"
    assert attrs.get("retrieval.result_count") == 1
    # OTel attributes carry the refs as JSON; the span processor decodes them.
    results = json.loads(attrs.get("retrieval.results"))
    assert results and results[0]["knowledge_base_id"] == "355981249820491776"
    assert results[0]["score"] == 0.87
    # ToolCall → Retrieval hierarchy: retrieval parented to the tool span.
    assert rspan.parent is not None and rspan.parent.span_id == tool_spans[0].context.span_id
    # and the tool span shares the root trace.
    assert tool_spans[0].context.trace_id == root.context.trace_id

    # Semantic kinds are stamped on every span for the trace view.
    root_attrs = dict(root.attributes or {})
    assert root_attrs.get("agentlabkit.kind") == "agent"
    llm_attrs = dict([s for s in recorder.ended if s.name == "llm.generate"][0].attributes or {})
    assert llm_attrs.get("agentlabkit.kind") == "llm"
    tool_attrs = dict(tool_spans[0].attributes or {})
    assert tool_attrs.get("agentlabkit.kind") == "tool"
