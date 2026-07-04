"""Orchestration package — multi-agent coordination for agent_runtime.

Public API
----------

**Contracts / protocols**

- :class:`SubTurnRunner` — Protocol implemented by ``AgentRuntime``
- :class:`SubStreamRunner` — Optional streaming variant of ``SubTurnRunner``
- :class:`SubAgentContext` — context propagated from parent to sub-agent
- :class:`DelegationResult` — result of a sub-agent turn
- :class:`HandoffRouteTarget` — resolved handoff destination (from router)
- :class:`HandoffResolution` — fully resolved handoff decision
- :class:`AgentHandoffContext` — context bundle sent to target agent
- :data:`MAX_ORCHESTRATION_DEPTH` — default depth cap (3)

**Router**

- :class:`AgentRouter` — keyword/regex route matching from handoff_policy_json

**Context passing**

- :class:`ContextPasser` — Protocol for context preparation strategies
- :class:`DirectContextPasser` — passes recent N messages verbatim
- :class:`SummarizingContextPasser` — LLM-compressed conversation summary

**Handoff**

- :class:`HandoffManager` — resolves and executes agent-to-agent handoffs

**Delegation**

- :class:`SubAgentExecutor` — runs sub-agent turns with depth/cycle guards
- :class:`DelegateToAgentTool` — built-in ToolHandler for delegation
"""

from .contracts import (
    AgentHandoffContext,
    DelegationResult,
    HandoffResolution,
    HandoffRouteTarget,
    MAX_ORCHESTRATION_DEPTH,
    SubAgentContext,
    SubStreamRunner,
    SubTurnRunner,
)
from .context_passing import (
    ContextPasser,
    DirectContextPasser,
    SummarizingContextPasser,
)
from .delegate_tool import DelegateToAgentTool
from .handoff_manager import HandoffManager
from .router import AgentRouter
from .sub_agent_executor import SubAgentExecutor

__all__ = [
    # Contracts
    "AgentHandoffContext",
    "DelegationResult",
    "HandoffResolution",
    "HandoffRouteTarget",
    "MAX_ORCHESTRATION_DEPTH",
    "SubAgentContext",
    "SubStreamRunner",
    "SubTurnRunner",
    # Router
    "AgentRouter",
    # Context passing
    "ContextPasser",
    "DirectContextPasser",
    "SummarizingContextPasser",
    # Handoff
    "HandoffManager",
    # Delegation
    "SubAgentExecutor",
    "DelegateToAgentTool",
]
