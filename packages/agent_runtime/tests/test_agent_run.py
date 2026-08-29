"""AgentRun 核心测试 — Phase 2。

覆盖：构造、状态转换、属性计算、RunTarget、RunUsage、RunError。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent_runtime.contracts.run import (
    AgentRun,
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


# ── AgentRun ────────────────────────────────────────────────────────


class TestAgentRun:
    def test_default_construction(self) -> None:
        run = AgentRun()
        assert run.run_id  # auto-generated
        assert run.status == RunStatus.RUNNING
        assert run.is_terminal is False

    def test_run_id_unique(self) -> None:
        r1 = AgentRun()
        r2 = AgentRun()
        assert r1.run_id != r2.run_id

    def test_mark_completed(self) -> None:
        run = AgentRun()
        usage = RunUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        run.mark_completed(output_text="done", usage=usage)

        assert run.status == RunStatus.COMPLETED
        assert run.output_text == "done"
        assert run.usage is usage
        assert run.finished_at is not None
        assert run.is_terminal is True

    def test_mark_failed(self) -> None:
        run = AgentRun()
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
        run = AgentRun()
        run.mark_cancelled(reason="user abort")

        assert run.status == RunStatus.CANCELLED
        assert run.metadata["cancel_reason"] == "user abort"
        assert run.is_terminal is True

    def test_duration_ms_when_completed(self) -> None:
        run = AgentRun()
        run.started_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        run.mark_completed(output_text="ok")
        run.finished_at = datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc)

        assert run.duration_ms == 1000

    def test_duration_ms_when_running(self) -> None:
        run = AgentRun()
        assert run.duration_ms is None

    def test_total_tokens_with_usage(self) -> None:
        run = AgentRun()
        run.usage = RunUsage(input_tokens=100, output_tokens=50)
        assert run.total_tokens == 150

    def test_total_tokens_with_total_set(self) -> None:
        run = AgentRun()
        run.usage = RunUsage(input_tokens=100, output_tokens=50, total_tokens=200)
        assert run.total_tokens == 200  # prefers total_tokens

    def test_total_tokens_without_usage(self) -> None:
        run = AgentRun()
        assert run.total_tokens == 0

    def test_estimated_cost_with_usage(self) -> None:
        run = AgentRun()
        run.usage = RunUsage(estimated_cost=0.013)
        assert run.estimated_cost == 0.013

    def test_estimated_cost_without_usage(self) -> None:
        run = AgentRun()
        assert run.estimated_cost == 0.0

    def test_full_lifecycle(self) -> None:
        """完整生命周期：创建 → 设置元数据 → 执行 → 完成。"""
        run = AgentRun(
            input_text="退款订单123",
            session_id="s1",
            agent_key="customer-service",
            agent_version="v3",
            target=RunTarget(type="agent", agent_key="customer-service"),
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
        run.mark_completed(output_text="退款已提交", usage=usage)

        assert run.status == RunStatus.COMPLETED
        assert run.output_text == "退款已提交"
        assert run.tool_call_count == 3
        assert run.estimated_cost == 0.013
        assert run.duration_ms is not None
        assert run.is_terminal is True

    def test_handoff_fields(self) -> None:
        run = AgentRun(
            action="handoff_agent",
            handoff_target_agent="refund-agent",
            orchestration_chain=["triage", "refund-agent"],
        )
        assert run.action == "handoff_agent"
        assert run.handoff_target_agent == "refund-agent"
        assert len(run.orchestration_chain) == 2
