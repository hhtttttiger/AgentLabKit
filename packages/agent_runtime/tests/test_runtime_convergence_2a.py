"""Phase 2A behavior matrix for Runtime convergence.

These tests deliberately exercise public Runtime boundaries with deterministic
gateway, guard, tool, sink, and event collectors.  Strict xfails document
known lifecycle defects that Phase 2B is expected to remove.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_runtime.config import AgentSettings
from agent_runtime.contracts.models import AgentAction, AgentTurnRequest, AgentTurnResult, HandoffTarget
from agent_runtime.contracts.run import AgentRun, RunStatus
from agent_runtime.events_v2 import RunCompleted, RunFailed, RunStarted, RunCancelled
from agent_runtime.guardrails import GuardsPipeline, GuardResult, GuardVerdict
from agent_runtime.orchestration import HandoffManager
from agent_runtime.runtime import AgentRuntime
from agent_runtime.runtime.cancel import CancelToken
from agent_runtime.tools import ToolRegistry
from agent_runtime.tools.contracts import ToolResult, ToolSpec
from agent_runtime.tools.contracts import ToolExecutionContext
from agent_runtime.workflow.contracts import FailurePolicy, StepDef, StepResult, WorkflowDef
from agent_runtime.workflow.engine import WorkflowEngine
from agent_runtime.workflow.state_store import InMemoryWorkflowStateStore
from llm_gateway import ProviderId, TextGenerateResponse, TextStreamEvent, UsageInfo


def _response(payload: dict, *, usage: UsageInfo | None = None) -> TextGenerateResponse:
    return TextGenerateResponse(
        provider=ProviderId.OPENAI,
        model="gpt-test",
        text=json.dumps(payload),
        usage=usage or UsageInfo(input_tokens=2, output_tokens=1, total_tokens=3),
    )


class FakeGateway:
    def __init__(self, responses, *, delay: float = 0.0):
        self.responses = list(responses)
        self.delay = delay
        self.calls = 0
        self.entered = asyncio.Event()

    async def generate_text(self, request):
        self.calls += 1
        self.entered.set()
        if self.delay:
            await asyncio.sleep(self.delay)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    async def generate_text_stream(self, request):
        self.calls += 1
        self.entered.set()
        if self.delay:
            await asyncio.sleep(self.delay)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        yield TextStreamEvent(
            event_type="completed",
            provider=ProviderId.OPENAI,
            model="gpt-test",
            text=response.text,
            usage=response.usage,
        )


def _runtime(gateway, *, guards=None, tools=None, sink=None):
    return AgentRuntime(
        settings=AgentSettings(),
        gateway=gateway,
        tool_registry=tools or ToolRegistry(),
        guards_pipeline=guards,
        completion_sink=sink,
    )


async def _events(runtime: AgentRuntime):
    collected = []
    original = runtime._event_bus.emit

    async def capture(event):
        collected.append(event)
        await original(event)

    runtime._event_bus.emit = capture
    return collected


class BlockingGuard:
    name = "phase2a_block"

    async def evaluate(self, context):
        return GuardResult(
            guard_name=self.name,
            verdict=GuardVerdict.BLOCK,
            reason="blocked by test",
        )


class RaisingTool:
    async def execute(self, arguments, context, on_update=None):
        raise RuntimeError("tool exploded")


@pytest.mark.asyncio
async def test_guardrail_early_complete_has_one_completed_terminal():
    runtime = _runtime(
        FakeGateway([]),
        guards=GuardsPipeline(input_guards=[BlockingGuard()], block_response="blocked"),
    )
    events = await _events(runtime)

    result = await runtime.run(AgentTurnRequest(user_message="secret", session_id="s1"))

    assert result.status is RunStatus.COMPLETED
    assert result.output_text == "blocked"
    assert len([event for event in events if isinstance(event, RunStarted)]) == 1
    assert len([event for event in events if isinstance(event, RunCompleted)]) == 1
    assert not [event for event in events if isinstance(event, RunFailed)]


@pytest.mark.asyncio
async def test_model_failure_is_one_failed_terminal_and_failed_run():
    from llm_gateway.errors import GatewayError, GatewayErrorCode

    runtime = _runtime(FakeGateway([GatewayError(GatewayErrorCode.PROVIDER_TIMEOUT, "timeout")]))
    events = await _events(runtime)

    result = await runtime.run(AgentTurnRequest(user_message="q", session_id="s1"))

    assert result.status is RunStatus.FAILED
    assert len([event for event in events if isinstance(event, RunStarted)]) == 1
    assert len([event for event in events if isinstance(event, RunFailed)]) == 1
    assert not [event for event in events if isinstance(event, RunCompleted)]


@pytest.mark.asyncio
async def test_tool_business_failure_is_handled_and_model_can_complete():
    registry = ToolRegistry()
    registry.dynamic_registry.register(
        ToolSpec(name="explode", description="explode", parameters_schema={"type": "object"}),
        RaisingTool(),
    )
    runtime = _runtime(
        FakeGateway([
            _response({"kind": "tool_call", "tool_name": "explode", "arguments": {}}),
            _response({"kind": "final", "reply_text": "recovered", "should_handoff": False}),
        ]),
        tools=registry,
    )

    result = await runtime.run(AgentTurnRequest(user_message="q", session_id="s1"))

    assert result.status is RunStatus.COMPLETED
    assert result.output_text == "recovered"
    assert result.tool_call_count == 1


@pytest.mark.asyncio
async def test_stream_max_tool_rounds_emits_one_failed_terminal_and_propagates():
    registry = ToolRegistry()
    registry.dynamic_registry.register(
        ToolSpec(name="loop", description="loop", parameters_schema={"type": "object"}),
        RaisingTool(),
    )
    response = _response({"kind": "tool_call", "tool_name": "loop", "arguments": {}})
    runtime = _runtime(FakeGateway([response] * 6), tools=registry)
    events = await _events(runtime)

    with pytest.raises(Exception, match="maximum tool-call rounds"):
        async for _ in runtime.stream(AgentTurnRequest(user_message="q", session_id="s1")):
            pass

    assert len([event for event in events if isinstance(event, RunStarted)]) == 1
    assert len([event for event in events if isinstance(event, RunFailed)]) == 1
    assert not [event for event in events if isinstance(event, RunCompleted)]


@pytest.mark.asyncio
async def test_completion_sink_failure_does_not_change_blocking_outcome(caplog):
    async def broken_sink(run: AgentRun):
        raise RuntimeError("projection unavailable")

    runtime = _runtime(
        FakeGateway([_response({"kind": "final", "reply_text": "ok", "should_handoff": False})]),
        sink=broken_sink,
    )

    result = await runtime.run(AgentTurnRequest(user_message="q", session_id="s1"))

    assert result.status is RunStatus.COMPLETED
    assert "completion_sink_failed" in caplog.text


@pytest.mark.asyncio
async def test_preparation_failure_is_recorded_as_started_failed_run_after_convergence():
    runtime = _runtime(FakeGateway([]))
    events = await _events(runtime)

    async def fail_preparation(request):
        raise RuntimeError("definition preparation failed")

    runtime._turn_prep.prepare_turn = fail_preparation

    result = await runtime.run(AgentTurnRequest(user_message="q", session_id="s1"))
    assert result.status is RunStatus.FAILED
    assert len([event for event in events if isinstance(event, RunStarted)]) == 1
    assert len([event for event in events if isinstance(event, RunFailed)]) == 1


@pytest.mark.asyncio
async def test_task_cancellation_raises_after_cancelled_terminal():
    gateway = FakeGateway([_response({"kind": "final", "reply_text": "ok", "should_handoff": False})], delay=1)
    runtime = _runtime(gateway)
    events = await _events(runtime)
    task = asyncio.create_task(runtime.run(AgentTurnRequest(user_message="q", session_id="s1")))
    await asyncio.wait_for(gateway.entered.wait(), timeout=1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert len([event for event in events if isinstance(event, RunCancelled)]) == 1


@pytest.mark.asyncio
async def test_token_cancellation_raises_after_cancelled_terminal():
    token = CancelToken()
    gateway = FakeGateway([_response({"kind": "final", "reply_text": "ok", "should_handoff": False})], delay=1)
    runtime = _runtime(gateway)
    events = await _events(runtime)
    task = asyncio.create_task(runtime.run(AgentTurnRequest(user_message="q", session_id="s1"), cancel_token=token))
    await asyncio.wait_for(gateway.entered.wait(), timeout=1)
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert len([event for event in events if isinstance(event, RunCancelled)]) == 1


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 2B finalizes stream aclose as cancelled before GeneratorExit")
async def test_stream_aclose_before_terminal_emits_cancelled_without_post_close_yield():
    runtime = _runtime(FakeGateway([_response({"kind": "final", "reply_text": "ok", "should_handoff": False})]))
    events = await _events(runtime)
    stream = runtime.stream(AgentTurnRequest(user_message="q", session_id="s1"))
    first = await stream.__anext__()
    assert first.event_type == "turn_context"
    await stream.aclose()

    assert len([event for event in events if isinstance(event, RunStarted)]) == 1
    assert len([event for event in events if isinstance(event, RunCancelled)]) == 1


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 2B removes concatenated child trace IDs and keeps child scope under the root")
async def test_agent_handoff_produces_one_root_terminal():
    class StubRunner:
        def __init__(self):
            self.requests = []

        async def run_turn(self, request):
            self.requests.append(request)
            return AgentTurnResult(
                session_id=request.session_id,
                trace_id=request.trace_id or "child-trace",
                action=AgentAction.HANDOFF_AGENT,
                reply_text="child reply",
                handoff_target=HandoffTarget(target_type="agent", target_agent_key="child"),
            )

    child_runner = StubRunner()
    runtime = _runtime(
        FakeGateway([_response({
            "kind": "final", "reply_text": "", "should_handoff": True,
            "handoff_target_type": "agent", "handoff_target_agent": "child",
            "handoff_reason": "specialist",
        })]),
    )
    runtime._handoff_manager = HandoffManager(child_runner)
    events = await _events(runtime)

    stream_events = [event async for event in runtime.stream(AgentTurnRequest(user_message="q", session_id="s1"))]

    assert any(event.event_type == "handoff" for event in stream_events)
    assert child_runner.requests[0].trace_id == stream_events[0].trace_id
    assert len([event for event in events if isinstance(event, RunStarted)]) == 1
    assert len([event for event in events if isinstance(event, RunCompleted)]) == 1


@pytest.mark.asyncio
async def test_workflow_stream_preserves_skip_failure_policy():
    step_executor = MagicMock()
    step_executor.execute_step = AsyncMock()
    step_executor.execute_step.side_effect = [
        StepResult(step_id="first", status="failed", error_message="tool failed"),
        StepResult(step_id="second", status="success", output={"ok": True}),
    ]
    engine = WorkflowEngine(step_executor, InMemoryWorkflowStateStore())
    workflow = WorkflowDef(
        workflow_id="wf-2a-skip",
        agent_key="agent",
        version=1,
        steps=(
            StepDef(
                step_id="first", step_type="tool", display_name="First",
                tool_name="first", failure_policy=FailurePolicy(on_failure="skip"),
            ),
            StepDef(step_id="second", step_type="tool", display_name="Second", tool_name="second"),
        ),
    )

    events = [event async for event in engine.stream_workflow(
        workflow, "input", ToolExecutionContext(session_id="s1", trace_id="t1"),
    )]

    assert [event.event_type for event in events][-1] == "workflow_completed"
    assert events[2].event_type == "step_skipped"
    assert events[2].step_result.status == "skipped"


@pytest.mark.asyncio
async def test_workflow_stream_waiting_human_persists_checkpoint_and_event():
    step_executor = MagicMock()
    step_executor.execute_step = AsyncMock(return_value=StepResult(
        step_id="confirm", status="waiting_human", output={"gate_prompt": "Confirm?"},
    ))
    state_store = InMemoryWorkflowStateStore()
    engine = WorkflowEngine(step_executor, state_store)
    workflow = WorkflowDef(
        workflow_id="wf-2a-human",
        agent_key="agent",
        version=1,
        steps=(StepDef(
            step_id="confirm", step_type="human_gate", display_name="Confirm",
            gate_prompt="Confirm?",
        ),),
    )

    events = [event async for event in engine.stream_workflow(
        workflow, "input", ToolExecutionContext(session_id="s1", trace_id="t1"),
    )]
    checkpoint = await state_store.load_checkpoint(workflow.workflow_id)

    assert events[-1].event_type == "step_waiting_human"
    assert checkpoint is not None
    assert checkpoint.current_step_index == 0
