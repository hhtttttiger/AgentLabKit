"""Semantic Runtime Events v2 — Run-Centric Execution Model.

统一语义事件基类和所有子事件类型。每个事件严格描述一个运行时事实，
Observability / Cost / Evaluation 只消费这些事件，不再重新解释。

事件分组：
- Run lifecycle: RunStarted, RunCompleted, RunFailed, RunCancelled
- Agent lifecycle: AgentStarted, AgentCompleted, AgentTurnStarted, AgentTurnCompleted
- LLM calls: LLMCallStarted, LLMCallCompleted, LLMCallFailed
- Tool calls: ToolCallStarted, ToolCallCompleted, ToolCallFailed
- Retrieval: RetrievalStarted, RetrievalCompleted, RetrievalFailed
- Guardrails: GuardrailEvaluated, GuardrailBlocked
- Multi-agent: HandoffStarted, HandoffCompleted, DelegationStarted, DelegationCompleted
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


# ── Enums ───────────────────────────────────────────────────────────


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpanKind(str, Enum):
    RUN = "RUN"
    AGENT = "AGENT"
    AGENT_TURN = "AGENT_TURN"
    LLM_CALL = "LLM_CALL"
    TOOL_CALL = "TOOL_CALL"
    RETRIEVAL = "RETRIEVAL"
    GUARDRAIL = "GUARDRAIL"
    HANDOFF = "HANDOFF"
    DELEGATION = "DELEGATION"
    WORKFLOW = "WORKFLOW"
    WORKFLOW_STEP = "WORKFLOW_STEP"
    CUSTOM = "CUSTOM"


# ── Base ────────────────────────────────────────────────────────────


@dataclass
class RuntimeEvent:
    """所有语义事件的基类。

    每个事件携带足够的上下文信息，使下游消费者（Trace、Cost、Eval）
    不需要再访问 Runtime 内部状态。
    """

    event_id: str = field(default_factory=lambda: uuid4().hex)
    run_id: str = ""
    trace_id: str = ""
    span_id: str | None = None
    parent_span_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


# ── Run lifecycle ───────────────────────────────────────────────────


@dataclass
class RunStarted(RuntimeEvent):
    """Agent run 开始。"""
    event_type: str = "run.started"
    agent_key: str = ""
    agent_version: str = ""
    input_text: str = ""
    session_id: str = ""
    # Authoritative execution owner, propagated from ExecutionContext.
    user_id: str | None = None


@dataclass
class RunCompleted(RuntimeEvent):
    """Agent run 正常完成。"""
    event_type: str = "run.completed"
    output_text: str = ""
    status: RunStatus = RunStatus.COMPLETED
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_duration_ms: int = 0


@dataclass
class RunFailed(RuntimeEvent):
    """Agent run 异常终止。"""
    event_type: str = "run.failed"
    error_code: str = ""
    error_message: str = ""


@dataclass
class RunCancelled(RuntimeEvent):
    """Agent run 被取消。"""
    event_type: str = "run.cancelled"
    reason: str = ""


# ── Agent lifecycle ─────────────────────────────────────────────────


@dataclass
class AgentStarted(RuntimeEvent):
    """Agent 开始处理。"""
    event_type: str = "agent.started"
    agent_key: str = ""
    agent_version: str = ""


@dataclass
class AgentCompleted(RuntimeEvent):
    """Agent 处理完成。"""
    event_type: str = "agent.completed"
    agent_key: str = ""


@dataclass
class AgentTurnStarted(RuntimeEvent):
    """Agent turn 开始（一次 assistant response cycle）。"""
    event_type: str = "agent.turn_started"
    turn_index: int = 0


@dataclass
class AgentTurnCompleted(RuntimeEvent):
    """Agent turn 完成。"""
    event_type: str = "agent.turn_completed"
    turn_index: int = 0
    output_text: str = ""


# ── LLM calls ───────────────────────────────────────────────────────


@dataclass
class LLMCallStarted(RuntimeEvent):
    """LLM 调用开始。"""
    event_type: str = "llm.call_started"
    model: str = ""
    provider: str = ""
    agent_key: str | None = None


@dataclass
class LLMCallCompleted(RuntimeEvent):
    """LLM 调用完成。携带完整的 usage 信息供 Cost 分析。"""
    event_type: str = "llm.call_completed"
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: int = 0
    finish_reason: str = ""
    # Cost projector needs these (5.1)
    agent_key: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class LLMCallFailed(RuntimeEvent):
    """LLM 调用失败。"""
    event_type: str = "llm.call_failed"
    model: str = ""
    provider: str = ""
    error_code: str = ""
    error_message: str = ""
    # Cost projector needs these (5.1)
    agent_key: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ── Tool calls ──────────────────────────────────────────────────────


@dataclass
class ToolCallStarted(RuntimeEvent):
    """Tool 调用开始。"""
    event_type: str = "tool.call_started"
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    source_type: str = ""  # "builtin", "mcp", "http_external", "delegate"
    source_ref: str = ""


@dataclass
class ToolCallCompleted(RuntimeEvent):
    """Tool 调用完成。"""
    event_type: str = "tool.call_completed"
    tool_name: str = ""
    result: str = ""
    duration_ms: int = 0
    is_error: bool = False


@dataclass
class ToolCallFailed(RuntimeEvent):
    """Tool 调用失败。"""
    event_type: str = "tool.call_failed"
    tool_name: str = ""
    error_code: str = ""
    error_message: str = ""


# ── Retrieval ───────────────────────────────────────────────────────


@dataclass
class RetrievalStarted(RuntimeEvent):
    """Retrieval 操作开始。"""
    event_type: str = "retrieval.started"
    query: str = ""
    source: str = ""


@dataclass
class RetrievalCompleted(RuntimeEvent):
    """Retrieval 操作完成。"""
    event_type: str = "retrieval.completed"
    result_count: int = 0
    duration_ms: int = 0


@dataclass
class RetrievalFailed(RuntimeEvent):
    """Retrieval 操作失败。"""
    event_type: str = "retrieval.failed"
    error_message: str = ""


# ── Guardrails ──────────────────────────────────────────────────────


@dataclass
class GuardrailEvaluated(RuntimeEvent):
    """Guardrail 评估完成（未阻断）。"""
    event_type: str = "guardrail.evaluated"
    guardrail_name: str = ""
    guardrail_type: str = ""  # "input", "output", "global"
    passed: bool = True
    reason: str = ""


@dataclass
class GuardrailBlocked(RuntimeEvent):
    """Guardrail 阻断了执行。"""
    event_type: str = "guardrail.blocked"
    guardrail_name: str = ""
    guardrail_type: str = ""
    action: str = ""  # "block", "handoff", "alert"
    reason: str = ""


# ── Multi-agent ─────────────────────────────────────────────────────


@dataclass
class HandoffStarted(RuntimeEvent):
    """Agent 间 handoff 开始。"""
    event_type: str = "handoff.started"
    source_agent: str = ""
    target_agent: str = ""
    reason: str = ""


@dataclass
class HandoffCompleted(RuntimeEvent):
    """Agent 间 handoff 完成。"""
    event_type: str = "handoff.completed"
    source_agent: str = ""
    target_agent: str = ""


@dataclass
class DelegationStarted(RuntimeEvent):
    """Sub-agent delegation 开始。"""
    event_type: str = "delegation.started"
    delegating_agent: str = ""
    target_agent: str = ""
    tool_name: str = ""


@dataclass
class DelegationCompleted(RuntimeEvent):
    """Sub-agent delegation 完成。"""
    event_type: str = "delegation.completed"
    delegating_agent: str = ""
    target_agent: str = ""
    output_text: str = ""


# ── Union type ──────────────────────────────────────────────────────

SemanticEvent = (
    RunStarted
    | RunCompleted
    | RunFailed
    | RunCancelled
    | AgentStarted
    | AgentCompleted
    | AgentTurnStarted
    | AgentTurnCompleted
    | LLMCallStarted
    | LLMCallCompleted
    | LLMCallFailed
    | ToolCallStarted
    | ToolCallCompleted
    | ToolCallFailed
    | RetrievalStarted
    | RetrievalCompleted
    | RetrievalFailed
    | GuardrailEvaluated
    | GuardrailBlocked
    | HandoffStarted
    | HandoffCompleted
    | DelegationStarted
    | DelegationCompleted
)


__all__ = [
    # Base
    "RuntimeEvent",
    # Enums
    "RunStatus",
    "SpanKind",
    # Run
    "RunStarted",
    "RunCompleted",
    "RunFailed",
    "RunCancelled",
    # Agent
    "AgentStarted",
    "AgentCompleted",
    "AgentTurnStarted",
    "AgentTurnCompleted",
    # LLM
    "LLMCallStarted",
    "LLMCallCompleted",
    "LLMCallFailed",
    # Tool
    "ToolCallStarted",
    "ToolCallCompleted",
    "ToolCallFailed",
    # Retrieval
    "RetrievalStarted",
    "RetrievalCompleted",
    "RetrievalFailed",
    # Guardrail
    "GuardrailEvaluated",
    "GuardrailBlocked",
    # Multi-agent
    "HandoffStarted",
    "HandoffCompleted",
    "DelegationStarted",
    "DelegationCompleted",
    # Union
    "SemanticEvent",
]
