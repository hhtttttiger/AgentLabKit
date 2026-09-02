from dataclasses import dataclass, field
from typing import Any, Mapping

@dataclass(frozen=True)
class ExecuteAgentCommand:
    agent_key: str
    input: str
    session_id: str | None = None
    user_id: str | None = None
    history: tuple[Any, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecuteAgentResult:
    run: Any

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
