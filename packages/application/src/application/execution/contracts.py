from dataclasses import dataclass, field
from typing import Any, Mapping

from agent_runtime import AgentMessage, AgentTurnStreamEvent
from agent_runtime.contracts.run import AgentRun, RunTarget

@dataclass(frozen=True)
class ExecuteAgentCommand:
    agent_key: str
    input: str
    session_id: str | None = None
    user_id: str | None = None
    history: tuple[AgentMessage, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecuteAgentResult:
    run: AgentRun

@dataclass(frozen=True)
class ExecuteAgentUpdate:
    """Framework-neutral streaming update; HTTP framing is an adapter concern."""
    event: AgentTurnStreamEvent
    run_id: str
    trace_id: str
    target: RunTarget

@dataclass(frozen=True)
class ReplayRunCommand:
    source_run_id: str
    target: Any | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class ReplayRunResult:
    source_run_id: str
    new_run_id: str
    run: Any
