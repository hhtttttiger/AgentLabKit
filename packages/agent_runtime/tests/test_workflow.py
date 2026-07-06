"""Unit tests for the workflow module.

Tests cover:
- InputRef resolution
- FailurePolicy defaults
- StepDef construction
- WorkflowDef navigation
- StepExecutor (tool/agent/condition/human_gate)
- WorkflowEngine execution
- Checkpoint/resume
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.workflow.contracts import (
    FailurePolicy,
    InputRef,
    StepDef,
    StepResult,
    WorkflowDef,
    WorkflowRequest,
    WorkflowResult,
    WorkflowStreamEvent,
)
from agent_runtime.workflow.state_store import InMemoryWorkflowStateStore, WorkflowCheckpoint
from agent_runtime.workflow.step_executor import StepExecutor
from agent_runtime.workflow.engine import WorkflowEngine


# ============================================================================
# InputRef tests
# ============================================================================


class TestInputRef:
    """Tests for InputRef resolution."""

    def test_resolve_user_input(self):
        ref = InputRef("$user_input")
        assert ref.resolve({"$user_input": "hello"}) == "hello"

    def test_resolve_user_input_missing(self):
        ref = InputRef("$user_input")
        assert ref.resolve({}) is None

    def test_resolve_const(self):
        ref = InputRef("$const:default_value")
        assert ref.resolve({}) == "default_value"

    def test_resolve_const_empty(self):
        ref = InputRef("$const:")
        assert ref.resolve({}) == ""

    def test_resolve_step_output(self):
        ref = InputRef("$steps.lookup.order_id")
        context = {"$steps.lookup": {"order_id": "12345", "status": "active"}}
        assert ref.resolve(context) == "12345"

    def test_resolve_step_output_nested(self):
        ref = InputRef("$steps.lookup.data.amount")
        context = {"$steps.lookup": {"data": {"amount": 100}}}
        assert ref.resolve(context) == 100

    def test_resolve_step_output_missing_step(self):
        ref = InputRef("$steps.missing.key")
        assert ref.resolve({}) is None

    def test_resolve_step_output_missing_key(self):
        ref = InputRef("$steps.lookup.nonexistent")
        context = {"$steps.lookup": {"order_id": "12345"}}
        assert ref.resolve(context) is None

    def test_resolve_fallback_direct_key(self):
        ref = InputRef("some_key")
        assert ref.resolve({"some_key": "value"}) == "value"

    def test_resolve_fallback_missing(self):
        ref = InputRef("missing_key")
        assert ref.resolve({}) is None


# ============================================================================
# FailurePolicy tests
# ============================================================================


class TestFailurePolicy:
    """Tests for FailurePolicy defaults."""

    def test_default_policy(self):
        policy = FailurePolicy()
        assert policy.on_failure == "fail"
        assert policy.max_retries == 3
        assert policy.retry_delay_seconds == 1.0

    def test_retry_policy(self):
        policy = FailurePolicy(on_failure="retry", max_retries=5, retry_delay_seconds=2.0)
        assert policy.on_failure == "retry"
        assert policy.max_retries == 5
        assert policy.retry_delay_seconds == 2.0

    def test_skip_policy(self):
        policy = FailurePolicy(on_failure="skip")
        assert policy.on_failure == "skip"


# ============================================================================
# StepDef tests
# ============================================================================


class TestStepDef:
    """Tests for StepDef construction."""

    def test_tool_step(self):
        step = StepDef(
            step_id="lookup",
            step_type="tool",
            display_name="查询订单",
            tool_name="order_lookup",
            tool_arguments={"order_id": InputRef("$user_input")},
        )
        assert step.step_id == "lookup"
        assert step.step_type == "tool"
        assert step.tool_name == "order_lookup"
        assert step.tool_arguments["order_id"].ref == "$user_input"

    def test_agent_step(self):
        step = StepDef(
            step_id="analyze",
            step_type="agent",
            display_name="分析数据",
            agent_key="data_analyst",
            agent_task="Analyze {topic}",
        )
        assert step.step_type == "agent"
        assert step.agent_key == "data_analyst"

    def test_human_gate_step(self):
        step = StepDef(
            step_id="confirm",
            step_type="human_gate",
            display_name="人工确认",
            gate_prompt="请确认是否执行退款",
            gate_options=("确认", "取消"),
        )
        assert step.step_type == "human_gate"
        assert step.gate_prompt == "请确认是否执行退款"
        assert "确认" in step.gate_options

    def test_condition_step(self):
        step = StepDef(
            step_id="check_amount",
            step_type="condition",
            display_name="检查金额",
            condition_expr="$steps.lookup.amount > 500",
            condition_true_step="manual_review",
            condition_false_step="auto_refund",
        )
        assert step.step_type == "condition"
        assert step.condition_expr == "$steps.lookup.amount > 500"


# ============================================================================
# WorkflowDef tests
# ============================================================================


class TestWorkflowDef:
    """Tests for WorkflowDef navigation."""

    def _make_workflow(self) -> WorkflowDef:
        return WorkflowDef(
            workflow_id="wf-001",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(step_id="step_1", step_type="tool", display_name="Step 1", tool_name="tool_a"),
                StepDef(step_id="step_2", step_type="tool", display_name="Step 2", tool_name="tool_b"),
                StepDef(step_id="step_3", step_type="agent", display_name="Step 3", agent_key="agent_x"),
            ),
        )

    def test_get_step(self):
        wf = self._make_workflow()
        step = wf.get_step("step_2")
        assert step is not None
        assert step.display_name == "Step 2"

    def test_get_step_missing(self):
        wf = self._make_workflow()
        assert wf.get_step("nonexistent") is None

    def test_step_index(self):
        wf = self._make_workflow()
        assert wf.step_index("step_1") == 0
        assert wf.step_index("step_2") == 1
        assert wf.step_index("step_3") == 2
        assert wf.step_index("nonexistent") == -1


# ============================================================================
# StepResult tests
# ============================================================================


class TestStepResult:
    """Tests for StepResult construction."""

    def test_success_result(self):
        result = StepResult(
            step_id="test",
            status="success",
            output={"key": "value"},
        )
        assert result.status == "success"
        assert result.output["key"] == "value"
        assert result.error_message is None

    def test_failed_result(self):
        result = StepResult(
            step_id="test",
            status="failed",
            error_message="Tool not found",
        )
        assert result.status == "failed"
        assert result.error_message == "Tool not found"

    def test_waiting_human_result(self):
        result = StepResult(
            step_id="confirm",
            status="waiting_human",
            output={"gate_prompt": "Please confirm"},
        )
        assert result.status == "waiting_human"


# ============================================================================
# WorkflowStateStore tests
# ============================================================================


class TestInMemoryWorkflowStateStore:
    """Tests for InMemoryWorkflowStateStore."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        store = InMemoryWorkflowStateStore()
        checkpoint = WorkflowCheckpoint(
            workflow_id="wf-001",
            step_results=[StepResult(step_id="s1", status="success")],
            context_vars={"$user_input": "test"},
            current_step_index=1,
        )
        await store.save_checkpoint(checkpoint)
        loaded = await store.load_checkpoint("wf-001")
        assert loaded is not None
        assert loaded.workflow_id == "wf-001"
        assert loaded.current_step_index == 1
        assert len(loaded.step_results) == 1

    @pytest.mark.asyncio
    async def test_load_missing(self):
        store = InMemoryWorkflowStateStore()
        loaded = await store.load_checkpoint("nonexistent")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_clear(self):
        store = InMemoryWorkflowStateStore()
        checkpoint = WorkflowCheckpoint(
            workflow_id="wf-001",
            step_results=[],
            context_vars={},
            current_step_index=0,
        )
        await store.save_checkpoint(checkpoint)
        await store.clear_checkpoint("wf-001")
        loaded = await store.load_checkpoint("wf-001")
        assert loaded is None


# ============================================================================
# StepExecutor tests
# ============================================================================


class TestStepExecutor:
    """Tests for StepExecutor."""

    def _make_executor(self):
        tool_executor = MagicMock()
        tool_executor.execute = AsyncMock()
        tool_registry = MagicMock()
        sub_agent_executor = MagicMock()
        sub_agent_executor.run_sub_turn = AsyncMock()
        return StepExecutor(
            tool_executor=tool_executor,
            tool_registry=tool_registry,
            sub_agent_executor=sub_agent_executor,
        )

    @pytest.mark.asyncio
    async def test_tool_step_success(self):
        from agent_runtime.tools.contracts import ToolResult

        executor = self._make_executor()
        executor._tool_executor.execute.return_value = ToolResult(
            output="order found",
            structured_data={"order_id": "12345"},
            status="success",
        )

        step = StepDef(
            step_id="lookup",
            step_type="tool",
            display_name="查询",
            tool_name="order_lookup",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(step, {"$user_input": "12345"}, context)
        assert result.status == "success"
        assert result.output["order_id"] == "12345"

    @pytest.mark.asyncio
    async def test_tool_step_missing_name(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="bad_tool",
            step_type="tool",
            display_name="Bad Tool",
            # No tool_name
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(step, {}, context)
        assert result.status == "failed"
        assert "missing tool_name" in result.error_message

    @pytest.mark.asyncio
    async def test_agent_step_success(self):
        from agent_runtime.orchestration.contracts import DelegationResult
        from agent_runtime.contracts.models import AgentAction

        executor = self._make_executor()
        executor._sub_agent_executor.run_sub_turn.return_value = DelegationResult(
            agent_key="analyst",
            reply_text="Analysis complete",
            action=AgentAction.REPLY,
        )

        step = StepDef(
            step_id="analyze",
            step_type="agent",
            display_name="分析",
            agent_key="analyst",
            agent_task="Analyze the data",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(step, {"$user_input": "data"}, context)
        assert result.status == "success"
        assert result.output["reply_text"] == "Analysis complete"

    @pytest.mark.asyncio
    async def test_agent_step_missing_key(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="bad_agent",
            step_type="agent",
            display_name="Bad Agent",
            # No agent_key
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(step, {}, context)
        assert result.status == "failed"
        assert "missing agent_key" in result.error_message

    @pytest.mark.asyncio
    async def test_human_gate(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="confirm",
            step_type="human_gate",
            display_name="确认",
            gate_prompt="请确认退款",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(step, {}, context)
        assert result.status == "waiting_human"
        assert result.output["gate_prompt"] == "请确认退款"

    @pytest.mark.asyncio
    async def test_condition_true(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="check",
            step_type="condition",
            display_name="检查金额",
            condition_expr="$steps.lookup.amount > 500",
            condition_true_step="manual_review",
            condition_false_step="auto_refund",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(
            step,
            {"$steps.lookup": {"amount": 1000}},
            context,
        )
        assert result.status == "success"
        assert result.output["condition_result"] is True
        assert result.output["next_step_id"] == "manual_review"

    @pytest.mark.asyncio
    async def test_condition_false(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="check",
            step_type="condition",
            display_name="检查金额",
            condition_expr="$steps.lookup.amount > 500",
            condition_true_step="manual_review",
            condition_false_step="auto_refund",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(
            step,
            {"$steps.lookup": {"amount": 100}},
            context,
        )
        assert result.status == "success"
        assert result.output["condition_result"] is False
        assert result.output["next_step_id"] == "auto_refund"

    @pytest.mark.asyncio
    async def test_condition_equals(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="check",
            step_type="condition",
            display_name="检查状态",
            condition_expr="$steps.lookup.status == active",
            condition_true_step="proceed",
            condition_false_step="stop",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(
            step,
            {"$steps.lookup": {"status": "active"}},
            context,
        )
        assert result.output["condition_result"] is True

    @pytest.mark.asyncio
    async def test_unknown_step_type(self):
        executor = self._make_executor()
        step = StepDef(
            step_id="bad",
            step_type="unknown_type",  # type: ignore[arg-type]
            display_name="Bad",
        )
        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await executor.execute_step(step, {}, context)
        assert result.status == "failed"
        assert "Unknown step type" in result.error_message


# ============================================================================
# WorkflowEngine tests
# ============================================================================


class TestWorkflowEngine:
    """Tests for WorkflowEngine."""

    def _make_engine(self):
        step_executor = MagicMock()
        step_executor.execute_step = AsyncMock()
        state_store = InMemoryWorkflowStateStore()
        engine = WorkflowEngine(
            step_executor=step_executor,
            state_store=state_store,
        )
        return engine, step_executor

    @pytest.mark.asyncio
    async def test_simple_workflow(self):
        engine, step_executor = self._make_engine()

        # Mock step executor to return success
        step_executor.execute_step.return_value = StepResult(
            step_id="step_1",
            status="success",
            output={"result": "done"},
        )

        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="step_1",
                    step_type="tool",
                    display_name="Step 1",
                    tool_name="test_tool",
                ),
            ),
        )

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await engine.run_workflow(workflow, "test input", context)
        assert result.status == "completed"
        assert len(result.step_results) == 1
        assert result.step_results[0].status == "success"

    @pytest.mark.asyncio
    async def test_workflow_failure(self):
        engine, step_executor = self._make_engine()

        step_executor.execute_step.return_value = StepResult(
            step_id="step_1",
            status="failed",
            error_message="Tool error",
        )

        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="step_1",
                    step_type="tool",
                    display_name="Step 1",
                    tool_name="test_tool",
                    failure_policy=FailurePolicy(on_failure="fail"),
                ),
            ),
        )

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await engine.run_workflow(workflow, "test input", context)
        assert result.status == "failed"
        assert result.error_message == "Tool error"

    @pytest.mark.asyncio
    async def test_workflow_skip_on_failure(self):
        engine, step_executor = self._make_engine()

        step_executor.execute_step.return_value = StepResult(
            step_id="step_1",
            status="failed",
            error_message="Tool error",
        )

        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="step_1",
                    step_type="tool",
                    display_name="Step 1",
                    tool_name="test_tool",
                    failure_policy=FailurePolicy(on_failure="skip"),
                ),
                StepDef(
                    step_id="step_2",
                    step_type="tool",
                    display_name="Step 2",
                    tool_name="test_tool_2",
                ),
            ),
        )

        # First call fails, second succeeds
        step_executor.execute_step.side_effect = [
            StepResult(step_id="step_1", status="failed", error_message="error"),
            StepResult(step_id="step_2", status="success", output={"result": "ok"}),
        ]

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await engine.run_workflow(workflow, "test input", context)
        assert result.status == "completed"
        assert result.step_results[0].status == "skipped"
        assert result.step_results[1].status == "success"

    @pytest.mark.asyncio
    async def test_workflow_human_gate(self):
        engine, step_executor = self._make_engine()

        step_executor.execute_step.return_value = StepResult(
            step_id="confirm",
            status="waiting_human",
            output={"gate_prompt": "Confirm?"},
        )

        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="confirm",
                    step_type="human_gate",
                    display_name="确认",
                    gate_prompt="Confirm?",
                ),
            ),
        )

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await engine.run_workflow(workflow, "test input", context)
        assert result.status == "waiting_human"
        assert result.waiting_step_id == "confirm"

    @pytest.mark.asyncio
    async def test_workflow_resume(self):
        engine, step_executor = self._make_engine()

        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="confirm",
                    step_type="human_gate",
                    display_name="确认",
                    gate_prompt="Confirm?",
                ),
                StepDef(
                    step_id="execute",
                    step_type="tool",
                    display_name="Execute",
                    tool_name="do_something",
                ),
            ),
        )

        # Save a checkpoint
        await engine._state_store.save_checkpoint(WorkflowCheckpoint(
            workflow_id="wf-001",
            step_results=[StepResult(step_id="confirm", status="waiting_human")],
            context_vars={"$user_input": "test"},
            current_step_index=0,
        ))

        # Mock the second step
        step_executor.execute_step.return_value = StepResult(
            step_id="execute",
            status="success",
            output={"result": "done"},
        )

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await engine.resume_workflow(workflow, "confirmed", context)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_workflow_condition_branching(self):
        engine, step_executor = self._make_engine()

        def side_effect(step, resolved_input, context):
            if step.step_type == "condition":
                return StepResult(
                    step_id=step.step_id,
                    status="success",
                    output={"condition_result": True, "next_step_id": "branch_a"},
                )
            return StepResult(
                step_id=step.step_id,
                status="success",
                output={"result": "ok"},
            )

        step_executor.execute_step.side_effect = side_effect

        # Workflow: condition → branch_a (true) / branch_b (false)
        # After condition jumps to branch_a, execution continues sequentially
        # to branch_b (the next step after branch_a in the list).
        # To demonstrate true branching, put branch_b BEFORE branch_a.
        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="check",
                    step_type="condition",
                    display_name="Check",
                    condition_expr="$user_input == yes",
                    condition_true_step="branch_a",
                    condition_false_step="branch_b",
                ),
                StepDef(
                    step_id="branch_b",
                    step_type="tool",
                    display_name="Branch B",
                    tool_name="tool_b",
                ),
                StepDef(
                    step_id="branch_a",
                    step_type="tool",
                    display_name="Branch A",
                    tool_name="tool_a",
                ),
            ),
        )

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        result = await engine.run_workflow(workflow, "yes", context)
        assert result.status == "completed"
        # Condition jumps to branch_a (index 2), skipping branch_b (index 1)
        assert len(result.step_results) == 2
        assert result.step_results[0].step_id == "check"
        assert result.step_results[1].step_id == "branch_a"

    @pytest.mark.asyncio
    async def test_stream_workflow(self):
        engine, step_executor = self._make_engine()

        step_executor.execute_step.return_value = StepResult(
            step_id="step_1",
            status="success",
            output={"result": "done"},
        )

        workflow = WorkflowDef(
            workflow_id="wf-001",
            agent_key="test",
            version=1,
            steps=(
                StepDef(
                    step_id="step_1",
                    step_type="tool",
                    display_name="Step 1",
                    tool_name="test_tool",
                ),
            ),
        )

        from agent_runtime.tools.contracts import ToolExecutionContext
        context = ToolExecutionContext(session_id="s1", trace_id="t1")

        events = []
        async for event in engine.stream_workflow(workflow, "test input", context):
            events.append(event)

        assert len(events) >= 3  # workflow_start, step_start, step_completed, workflow_completed
        assert events[0].event_type == "workflow_start"
        assert events[-1].event_type == "workflow_completed"
