"""AgentRun — 统一执行结果模型。

AgentRun 是 Execution Model v2 的核心对象，代表一次完整的 Agent 执行。
所有执行路径（normal agent、workflow、handoff、delegation）最终都应该
形成一个 AgentRun。

Run != Trace。Run 是业务执行边界，Trace 是观测投影。
通过 trace_id 关联，而不是内嵌 Span。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunTarget:
    """描述 Run 的执行目标。

    不绑定某一种 Agent 实现。Agent、Workflow、Sub Agent、Evaluation Target
    都可以形成 Run。
    """

    type: str = "agent"  # "agent", "workflow", "eval_target"

    agent_key: str | None = None
    agent_version: str | None = None

    workflow_id: str | None = None
    workflow_version: str | None = None


@dataclass
class RunUsage:
    """Run 级别的 token 和成本汇总。"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    estimated_cost: float = 0.0
    llm_call_count: int = 0
    tool_call_count: int = 0


@dataclass
class RunError:
    """Run 级别的错误信息。"""

    code: str = ""
    message: str = ""
    provider: str | None = None
    model: str | None = None


@dataclass
class ExecutionContext:
    """执行上下文 — 在执行边界创建，贯穿整条执行链路。

    Runtime 是 run_id / trace_id 的唯一创建者。
    所有下层组件（Agent Loop、LLM、Tool、Guardrail、Handoff）
    只能传递已有 identity，禁止重新生成。

    ``root_span_id`` 是 Run 级 span 的 id，由 loop 用于构建 span 层级。
    ``target`` 描述执行目标（agent/workflow/eval_target）。
    ``started_at`` 记录执行开始的真实时间（UTC）。
    ``metadata`` 携带附加执行上下文（如 replay_of_run_id）。
    """

    run_id: str = field(default_factory=lambda: uuid4().hex)
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    session_id: str = ""
    agent_key: str | None = None
    agent_version: str | None = None
    root_span_id: str = field(default_factory=lambda: uuid4().hex[:16])
    target: RunTarget = field(default_factory=RunTarget)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRun:
    """一次 Agent 执行的完整结果。

    核心原则：
    - Run 是业务执行边界
    - Run 通过 trace_id 关联 Trace，不内嵌 Span
    - Run 携带足够的元数据供 Cost/Eval/Replay 消费
    - run_id / trace_id 由 Runtime 通过 ExecutionContext 注入
    - agent_key / agent_version 唯一来源是 target 字段
    """

    run_id: str = ""
    trace_id: str | None = None

    input: Any = ""
    output: Any | None = None

    status: RunStatus = RunStatus.RUNNING

    target: RunTarget = field(default_factory=RunTarget)

    usage: RunUsage | None = None

    error: RunError | None = None

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    session_id: str = ""

    # Orchestration
    action: str = "reply"  # "reply", "handoff_human", "handoff_agent"
    handoff_target_agent: str | None = None
    orchestration_chain: list[str] = field(default_factory=list)

    # Tool execution records
    tool_names: list[str] = field(default_factory=list)
    tool_call_count: int = 0

    # Skills
    applied_skills: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Backward-compat properties ────────────────────────────────────

    @property
    def input_text(self) -> str:
        """Backward compat — returns str(input)."""
        return str(self.input) if self.input is not None else ""

    @input_text.setter
    def input_text(self, value: str) -> None:
        self.input = value

    @property
    def output_text(self) -> str:
        """Backward compat — returns str(output)."""
        return str(self.output) if self.output is not None else ""

    @output_text.setter
    def output_text(self, value: str) -> None:
        self.output = value

    @property
    def agent_key(self) -> str | None:
        """唯一来源：target.agent_key。"""
        return self.target.agent_key

    @property
    def agent_version(self) -> str | None:
        """唯一来源：target.agent_version。"""
        return self.target.agent_version

    # ── Lifecycle methods ─────────────────────────────────────────────

    def mark_completed(
        self,
        *,
        output: Any = None,
        usage: RunUsage | None = None,
    ) -> None:
        """标记 Run 为完成状态。"""
        self.status = RunStatus.COMPLETED
        if output is not None:
            self.output = output
        self.usage = usage
        self.finished_at = datetime.now(timezone.utc)

    def mark_failed(
        self,
        *,
        error_code: str = "",
        error_message: str = "",
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """标记 Run 为失败状态。"""
        self.status = RunStatus.FAILED
        self.error = RunError(
            code=error_code,
            message=error_message,
            provider=provider,
            model=model,
        )
        self.finished_at = datetime.now(timezone.utc)

    def mark_cancelled(self, reason: str = "") -> None:
        """标记 Run 为取消状态。"""
        self.status = RunStatus.CANCELLED
        self.metadata["cancel_reason"] = reason
        self.finished_at = datetime.now(timezone.utc)

    @property
    def duration_ms(self) -> int | None:
        """执行耗时（毫秒）。未完成返回 None。"""
        if self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return int(delta.total_seconds() * 1000)

    @property
    def is_terminal(self) -> bool:
        """是否已结束（completed/failed/cancelled）。"""
        return self.status in (
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        )

    @property
    def total_tokens(self) -> int:
        """总 token 数。"""
        if self.usage is None:
            return 0
        return self.usage.total_tokens or (self.usage.input_tokens + self.usage.output_tokens)

    @property
    def estimated_cost(self) -> float:
        """预估成本。"""
        if self.usage is None:
            return 0.0
        return self.usage.estimated_cost


__all__ = [
    "AgentRun",
    "ExecutionContext",
    "RunStatus",
    "RunTarget",
    "RunUsage",
    "RunError",
]
