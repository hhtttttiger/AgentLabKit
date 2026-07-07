from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from llm_gateway import ProviderId, UsageInfo
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AgentAction(str, Enum):
    REPLY = "reply"
    HANDOFF = "handoff"          # Legacy alias — kept for backward compatibility
    HANDOFF_HUMAN = "handoff_human"   # Explicit human handoff (new)
    HANDOFF_AGENT = "handoff_agent"   # Agent-to-agent handoff (new)


class AgentMessage(BaseModel):
    role: AgentRole
    content: str
    name: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgeChunk(BaseModel):
    content: str
    title: str | None = None
    source: str | None = None
    score: float | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class HandoffTarget(BaseModel):
    """Structured handoff target — used by the orchestration layer."""

    target_type: Literal["human", "agent"] = "human"
    target_agent_key: str | None = None  # Required when target_type="agent"
    reason: str | None = None
    context_message: str | None = None   # Optional summary passed to the target agent


class HandoffDecision(BaseModel):
    should_handoff: bool = False
    reason: str | None = None            # Legacy flat reason string
    target: HandoffTarget | None = None  # Structured target (Phase 1+)


class ToolExecutionRecord(BaseModel):
    tool_name: str
    status: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_text: str | None = None
    structured_data: dict[str, Any] | None = None
    error_message: str | None = None
    display_name: str | None = None
    source_type: Literal["builtin", "http_external", "mcp", "delegate"] | None = None
    source_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    duration_ms: int | None = None


class AppliedSkillRecord(BaseModel):
    skill_key: str
    display_name: str
    order: int = 100
    config: dict[str, Any] = Field(default_factory=dict)


class AgentSessionState(BaseModel):
    session_id: str
    customer_id: str | None = None
    locale: str | None = None
    channel: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AgentErrorDetail(BaseModel):
    code: str
    message: str
    provider: str | None = None
    model: str | None = None


class AgentTurnRequest(BaseModel):
    session_id: str
    user_message: str
    history: list[AgentMessage] = Field(default_factory=list)
    user_id: str | None = None
    customer_id: str | None = None
    locale: str | None = None
    channel: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    knowledge_chunks: list[KnowledgeChunk] = Field(default_factory=list)
    knowledge_lookup_status: Literal["none", "hit", "miss"] = "none"
    model: str | None = None
    provider: ProviderId | None = None
    trace_id: str | None = None
    # Definition-aware fields (Section 7.2)
    agent_key: str | None = None
    agent_version: int | None = None
    agent_runtime_overrides: dict[str, str] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    reply_text: str
    should_handoff: bool = False
    handoff_reason: str | None = None
    # Orchestration fields (Phase 1) — optional, ignored by non-orchestrating runtimes
    handoff_target_type: Literal["human", "agent"] | None = None
    handoff_target_agent: str | None = None


class AgentTurnResult(BaseModel):
    session_id: str
    trace_id: str
    action: AgentAction
    reply_text: str
    handoff_reason: str | None = None
    tool_events: list[ToolExecutionRecord] = Field(default_factory=list)
    usage: UsageInfo | None = None
    raw_messages: list[AgentMessage] = Field(default_factory=list)
    agent_key: str | None = None
    agent_version: int | None = None
    applied_skills: list[AppliedSkillRecord] = Field(default_factory=list)
    error: AgentErrorDetail | None = None
    # Orchestration fields (Phase 1)
    responding_agent_key: str | None = None         # Actual agent that replied (may differ after handoff)
    orchestration_chain: list[str] | None = None    # e.g. ["triage", "refund-specialist"]
    handoff_target: HandoffTarget | None = None      # Structured handoff target


class AgentTurnStreamEvent(BaseModel):
    event_type: Literal[
        "turn_context",
        "reply_delta",
        "reply_completed",
        "handoff",
        "tool_call",
        "tool_result",
        "delegation_delta",
        "error",
    ]
    session_id: str
    trace_id: str
    delta: str | None = None
    reply_text: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    tool_event: ToolExecutionRecord | None = None
    handoff_reason: str | None = None
    usage: UsageInfo | None = None
    raw_messages: list[AgentMessage] = Field(default_factory=list)
    applied_skills: list[AppliedSkillRecord] = Field(default_factory=list)
    agent_key: str | None = None
    agent_version: int | None = None
    error: AgentErrorDetail | None = None
    # Orchestration fields (Phase 1)
    handoff_target: HandoffTarget | None = None
    # Orchestration fields (Phase 2) — streaming delegation
    delegation_agent_key: str | None = None
    """Populated for ``event_type="delegation_delta"`` — identifies the sub-agent
    whose streaming output is being forwarded."""
