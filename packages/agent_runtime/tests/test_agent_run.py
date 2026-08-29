"""AgentRun 核心测试 — Phase 2。

覆盖：构造、状态转换、属性计算、RunTarget、RunUsage、RunError、ExecutionContext。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent_runtime.contracts.run import (
    AgentRun,
    ExecutionContext,
    RunStatus,
    RunTarget,
    RunUsage,
    RunError,
)


# ── RunStatus ───────────────────────────────────────────────────────


class TestRunStatus:
    def test_values(self) -> None:
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.CANCELLED.value == "cancelled"

    def test_from_string(self) -> None:
        assert RunStatus("running") == RunStatus.RUNNING


# ── RunTarget ───────────────────────────────────────────────────────


class TestRunTarget:
    def test_default_agent_type(self) -> None:
        t = RunTarget()
        assert t.type == "agent"
        assert t.agent_key is None

    def test_workflow_target(self) -> None:
        t = RunTarget(
            type="workflow",
            workflow_id="wf-1",
            workflow_version="v2",
        )
        assert t.type == "workflow"
        assert t.workflow_id == "wf-1"

    def test_agent_target(self) -> None:
        t = RunTarget(
            type="agent",
            agent_key="customer-service",
            agent_version="3",
        )
        assert t.agent_key == "customer-service"


# ── RunUsage ────────────────────────────────────────────────────────


class TestRunUsage:
    def test_defaults(self) -> None:
        u = RunUsage()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.estimated_cost == 0.0

    def test_construction(self) -> None:
        u = RunUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            estimated_cost=0.005,
            llm_call_count=2,
            tool_call_count=3,
        )
        assert u.total_tokens == 150
        assert u.llm_call_count == 2


# ── RunError ────────────────────────────────────────────────────────


class TestRunError:
    def test_construction(self) -> None:
        e = RunError(
            code="GATEWAY_ERROR",
            message="timeout",
            provider="openai",
            model="gpt-4o",
        )
        assert e.code == "GATEWAY_ERROR"
        assert e.provider == "openai"


# ── ExecutionContext ────────────────────────────────────────────────


class TestExecutionContext:
    def test_auto_generates_identity(self) -> None:
        ctx = ExecutionContext()
        assert ctx.run_id  # auto-generated
        assert ctx.trace_id  # auto-generated
        assert ctx.run_id != ctx.trace_id  # independent

    def test_unique_per_instance(self) -> None:
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        assert ctx1.run_id != ctx2.run_id
        assert ctx1.trace_id != ctx2.trace_id

    def test_explicit_values(self) -> None:
        ctx = ExecutionContext(
            run_id="run-1",
            trace_id="trace-1",
            session_id="s1",
            agent_key="my-agent",
        )
        assert ctx.run_id == "run-1"
        assert ctx.trace_id == "trace-1"
        assert ctx.agent_key == "my-agent"


# ── AgentRun ────────────────────────────────────────────────────────


class TestAgentRun:
    def test_default_construction(self) -> None:
        """AgentRun 不再自动生成 run_id — Runtime 是唯一创建者。"""
        run = AgentRun()
        assert run.run_id == ""  # must be set by Runtime
        assert run.status == RunStatus.RUNNING
        assert run.is_terminal is False

    def test_run_id_from_context(self) -> None:
        """AgentRun 使用 ExecutionContext 提供的 identity。"""
        ctx = ExecutionContext()
        run = AgentRun(run_id=ctx.run_id, trace_id=ctx.trace_id)
        assert run.run_id == ctx.run_id
        assert run.trace_id == ctx.trace_id

    def test_identity_invariant(self) -> None:
        """同一批次的 AgentRun 和 events 共享 identity。"""
        ctx = ExecutionContext()
        run = AgentRun(run_id=ctx.run_id, trace_id=ctx.trace_id)
        # 模拟 RuntimeEvent 也使用同一个 ctx
        assert run.run_id == ctx.run_id
        assert run.trace_id == ctx.trace_id

    def test_agent_key_from_target(self) -> None:
        """agent_key 唯一来源是 target 字段（1.4 去重）。"""
        run = AgentRun(
            target=RunTarget(agent_key="customer-service", agent_version="v3"),
        )
        assert run.agent_key == "customer-service"
        assert run.agent_version == "v3"

    def test_mark_completed(self) -> None:
        run = AgentRun(run_id="r1")
        usage = RunUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        run.mark_completed(output="done", usage=usage)

        assert run.status == RunStatus.COMPLETED
        assert run.output == "done"
        assert run.output_text == "done"  # backward compat
        assert run.usage is usage
        assert run.finished_at is not None
        assert run.is_terminal is True

    def test_mark_failed(self) -> None:
        run = AgentRun(run_id="r1")
        run.mark_failed(
            error_code="RUNTIME_ERROR",
            error_message="something broke",
            provider="openai",
        )

        assert run.status == RunStatus.FAILED
        assert run.error is not None
        assert run.error.code == "RUNTIME_ERROR"
        assert run.error.provider == "openai"
        assert run.finished_at is not None
        assert run.is_terminal is True

    def test_mark_cancelled(self) -> None:
        run = AgentRun(run_id="r1")
        run.mark_cancelled(reason="user abort")

        assert run.status == RunStatus.CANCELLED
        assert run.metadata["cancel_reason"] == "user abort"
        assert run.is_terminal is True

    def test_duration_ms_when_completed(self) -> None:
        run = AgentRun(run_id="r1")
        run.started_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        run.mark_completed(output="ok")
        run.finished_at = datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc)

        assert run.duration_ms == 1000

    def test_duration_ms_when_running(self) -> None:
        run = AgentRun(run_id="r1")
        assert run.duration_ms is None

    def test_total_tokens_with_usage(self) -> None:
        run = AgentRun(run_id="r1")
        run.usage = RunUsage(input_tokens=100, output_tokens=50)
        assert run.total_tokens == 150

    def test_total_tokens_with_total_set(self) -> None:
        run = AgentRun(run_id="r1")
        run.usage = RunUsage(input_tokens=100, output_tokens=50, total_tokens=200)
        assert run.total_tokens == 200  # prefers total_tokens

    def test_total_tokens_without_usage(self) -> None:
        run = AgentRun(run_id="r1")
        assert run.total_tokens == 0

    def test_estimated_cost_with_usage(self) -> None:
        run = AgentRun(run_id="r1")
        run.usage = RunUsage(estimated_cost=0.013)
        assert run.estimated_cost == 0.013

    def test_estimated_cost_without_usage(self) -> None:
        run = AgentRun(run_id="r1")
        assert run.estimated_cost == 0.0

    def test_input_output_any_type(self) -> None:
        """input/output 支持任意类型（1.5 类型升级）。"""
        run = AgentRun(
            run_id="r1",
            input={"order_id": "123", "items": ["a", "b"]},
            output={"status": "refunded", "amount": 42.0},
        )
        assert run.input["order_id"] == "123"
        assert run.output["status"] == "refunded"
        # backward compat properties
        assert "123" in run.input_text
        assert "refunded" in run.output_text

    def test_full_lifecycle(self) -> None:
        """完整生命周期：创建 → 设置元数据 → 执行 → 完成。"""
        ctx = ExecutionContext(
            agent_key="customer-service",
            agent_version="v3",
        )
        run = AgentRun(
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            input="退款订单123",
            session_id="s1",
            target=RunTarget(
                type="agent",
                agent_key="customer-service",
                agent_version="v3",
            ),
        )
        run.tool_names = ["get_order", "verify_identity", "refund"]
        run.tool_call_count = 3
        run.applied_skills = ["customer_support"]

        usage = RunUsage(
            input_tokens=500,
            output_tokens=200,
            total_tokens=700,
            estimated_cost=0.013,
            llm_call_count=4,
            tool_call_count=3,
        )
        run.mark_completed(output="退款已提交", usage=usage)

        assert run.status == RunStatus.COMPLETED
        assert run.output == "退款已提交"
        assert run.output_text == "退款已提交"
        assert run.tool_call_count == 3
        assert run.estimated_cost == 0.013
        assert run.duration_ms is not None
        assert run.is_terminal is True
        # identity 来自 context
        assert run.run_id == ctx.run_id
        assert run.trace_id == ctx.trace_id
        # agent_key 来自 target
        assert run.agent_key == "customer-service"
        assert run.agent_version == "v3"

    def test_handoff_fields(self) -> None:
        run = AgentRun(
            run_id="r1",
            action="handoff_agent",
            handoff_target_agent="refund-agent",
            orchestration_chain=["triage", "refund-agent"],
        )
        assert run.action == "handoff_agent"
        assert run.handoff_target_agent == "refund-agent"
        assert len(run.orchestration_chain) == 2
