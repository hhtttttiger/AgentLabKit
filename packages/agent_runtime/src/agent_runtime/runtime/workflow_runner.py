"""Workflow runner — shared setup logic for workflow execution.

Extracts the duplicated dependency-building code from
:meth:`AgentRuntime.run_workflow` and :meth:`AgentRuntime.stream_workflow`
so both methods share a single construction path.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..contracts.models import AgentTurnRequest
from ..definition.loader import AgentDefinitionLoader
from ..errors import AgentError, AgentErrorCode
from ..event_bus import EventBus
from ..tools.contracts import ToolExecutionContext
from ..tools.executor import ToolExecutor

if TYPE_CHECKING:
    from ..workflow.contracts import WorkflowDef
    from ..workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)


async def resolve_workflow(
    request: AgentTurnRequest,
    definition_loader: AgentDefinitionLoader | None,
    workflow: WorkflowDef | None,
) -> WorkflowDef:
    """Resolve a workflow definition from the request or explicit parameter.

    If *workflow* is ``None``, attempts to load it from the agent definition
    referenced by ``request.agent_key``.
    """
    if workflow is not None:
        return workflow

    if request.agent_key and definition_loader:
        definition = await definition_loader.load(request.agent_key)
        if definition and definition.workflow:
            return definition.workflow

    raise AgentError(
        AgentErrorCode.INVALID_REQUEST,
        "No workflow definition found for this request.",
        trace_id=request.trace_id,
    )


def build_workflow_engine(
    *,
    runner: Any,
    definition_loader: AgentDefinitionLoader | None,
    event_bus: EventBus,
) -> WorkflowEngine:
    """Build a fully-wired :class:`WorkflowEngine`.

    Constructs the ``SubAgentExecutor``, ``StepExecutor``, and state store
    needed by the workflow engine.
    """
    from ..orchestration.sub_agent_executor import SubAgentExecutor
    from ..workflow import InMemoryWorkflowStateStore, StepExecutor, WorkflowEngine

    sub_agent_executor = SubAgentExecutor(
        runner=runner,
        definition_loader=definition_loader,
    )
    step_executor = StepExecutor(
        tool_executor=ToolExecutor(),
        tool_registry=runner.tool_registry.dynamic_registry,
        sub_agent_executor=sub_agent_executor,
    )
    state_store = InMemoryWorkflowStateStore()
    return WorkflowEngine(
        step_executor=step_executor,
        state_store=state_store,
        event_bus=event_bus,
    )


def build_tool_context(request: AgentTurnRequest) -> ToolExecutionContext:
    """Build a :class:`ToolExecutionContext` from a turn request."""
    return ToolExecutionContext(
        session_id=request.session_id,
        trace_id=request.trace_id or "",
        agent_key=request.agent_key,
        agent_version=request.agent_version,
        customer_id=request.customer_id,
        locale=request.locale,
        metadata=dict(request.metadata),
    )
