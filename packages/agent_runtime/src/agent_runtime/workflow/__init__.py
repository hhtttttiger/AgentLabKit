"""Workflow orchestration — deterministic multi-step execution engine.

Provides:
- ``WorkflowDef`` / ``StepDef`` — workflow and step definitions
- ``WorkflowEngine`` — deterministic step-by-step execution
- ``StepExecutor`` — dispatches steps to tool/agent/gate handlers
- ``WorkflowStateStore`` — checkpoint persistence for human gates
- ``WorkflowGenerator`` — LLM-based workflow generation (Phase 3)

Usage::

    from agent_runtime.workflow import (
        WorkflowDef,
        StepDef,
        InputRef,
        FailurePolicy,
        WorkflowEngine,
        StepExecutor,
        InMemoryWorkflowStateStore,
    )
"""

from .contracts import (
    FailurePolicy,
    InputRef,
    StepDef,
    StepResult,
    WorkflowDef,
    WorkflowRequest,
    WorkflowResult,
    WorkflowStreamEvent,
)
from .engine import WorkflowEngine
from .state_store import InMemoryWorkflowStateStore, WorkflowCheckpoint, WorkflowStateStore
from .step_executor import StepExecutor

__all__ = [
    # Contracts
    "FailurePolicy",
    "InputRef",
    "StepDef",
    "StepResult",
    "WorkflowDef",
    "WorkflowRequest",
    "WorkflowResult",
    "WorkflowStreamEvent",
    # Engine
    "WorkflowEngine",
    # Step executor
    "StepExecutor",
    # State store
    "InMemoryWorkflowStateStore",
    "WorkflowCheckpoint",
    "WorkflowStateStore",
]
