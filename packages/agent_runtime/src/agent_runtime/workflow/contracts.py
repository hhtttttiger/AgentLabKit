"""Workflow contracts — data types for deterministic workflow orchestration.

All types in this module are pure data (no logic, no external dependencies).
Import from anywhere in the workflow package without risk of cycles.

Design principles:
- Workflows are agent config items, tied to agent versions
- Steps reference tools/agents by name, resolved at execution time
- Data flows between steps via explicit input/output mapping
- Failure handling is configurable per-step (fail/retry/skip)
- Human gates pause execution and persist state for resume
- Condition steps enable branching without LLM intervention
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from llm_gateway import UsageInfo

from ..contracts.models import ToolExecutionRecord


# ---------------------------------------------------------------------------
# InputRef — where a step's input value comes from
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InputRef:
    """Reference to a step input's source.

    Three source types:
    - ``$user_input`` — the original user message
    - ``$steps.<step_id>.<output_key>`` — output from a previous step
    - ``$const:<value>`` — a literal constant value

    Examples::

        InputRef("$user_input")
        InputRef("$steps.lookup_order.order_id")
        InputRef("$const:default_value")
    """

    ref: str

    def resolve(self, context_vars: dict[str, Any]) -> Any:
        """Resolve this reference against the current context variables.

        Args:
            context_vars: Accumulated variables from previous steps.
                Keys use dotted notation: ``$user_input``, ``$steps.step_id.key``.

        Returns:
            The resolved value, or ``None`` if the reference cannot be resolved.
        """
        if self.ref == "$user_input":
            return context_vars.get("$user_input")

        if self.ref.startswith("$const:"):
            return self.ref[len("$const:"):]

        if self.ref.startswith("$steps."):
            # Walk the dotted path: $steps.step_id.output_key
            parts = self.ref.split(".")
            # parts[0] = "$steps", parts[1] = step_id, parts[2..] = output path
            if len(parts) < 3:
                return None
            step_id = parts[1]
            step_output = context_vars.get(f"$steps.{step_id}")
            if step_output is None:
                return None
            # Walk remaining path segments
            current: Any = step_output
            for part in parts[2:]:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
                if current is None:
                    return None
            return current

        # Fallback: treat as a direct key lookup
        return context_vars.get(self.ref)


# ---------------------------------------------------------------------------
# FailurePolicy — per-step failure handling
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FailurePolicy:
    """Configures how a step handles execution failures.

    - ``fail``: Abort the workflow immediately (default).
    - ``retry``: Retry up to ``max_retries`` times with ``retry_delay_seconds`` delay.
    - ``skip``: Silently skip the step, mark as skipped.
    """

    on_failure: Literal["fail", "retry", "skip"] = "fail"
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


# ---------------------------------------------------------------------------
# StepDef — definition of a single workflow step
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StepDef:
    """Definition of a single workflow step.

    A step has a type that determines its execution strategy:
    - ``tool``: Call a registered tool by name.
    - ``agent``: Delegate to a sub-agent via SubAgentExecutor.
    - ``human_gate``: Pause execution and wait for human input.
    - ``condition``: Evaluate an expression and branch to different steps.
    """

    step_id: str
    """Unique identifier within the workflow, e.g. ``"lookup_order"``."""

    step_type: Literal["tool", "agent", "human_gate", "condition"]
    """Determines which executor handles this step."""

    display_name: str
    """Human-readable name for UI display, e.g. ``"查询订单"``."""

    # --- tool type fields ---
    tool_name: str | None = None
    """Reference to a registered ``ToolSpec.name``. Required for ``step_type="tool"``."""

    tool_arguments: dict[str, InputRef] = field(default_factory=dict)
    """Tool argument mapping. Keys are parameter names, values are InputRef sources."""

    # --- agent type fields ---
    agent_key: str | None = None
    """Sub-agent identifier. Required for ``step_type="agent"``."""

    agent_task: str | None = None
    """Task description for the sub-agent. Supports ``{variable}`` interpolation."""

    # --- human_gate type fields ---
    gate_prompt: str | None = None
    """Message displayed to the user when pausing. Required for ``step_type="human_gate"``."""

    gate_options: tuple[str, ...] = ()
    """Optional predefined choices, e.g. ``("approve", "reject")``."""

    # --- condition type fields ---
    condition_expr: str | None = None
    """Expression to evaluate, e.g. ``"$steps.check.eligible == true"``.
    Supports comparisons against context variables."""

    condition_true_step: str | None = None
    """Step ID to jump to when condition is true. If None, continues to next step."""

    condition_false_step: str | None = None
    """Step ID to jump to when condition is false. If None, continues to next step."""

    # --- general fields ---
    input_mapping: dict[str, InputRef] = field(default_factory=dict)
    """General input mapping for the step. Keys are logical input names."""

    output_mapping: dict[str, str] = field(default_factory=dict)
    """Maps step output keys to context variable names.
    E.g. ``{"order_id": "order_id"}`` stores the step's ``order_id`` output
    as ``$steps.<step_id>.order_id`` in context."""

    failure_policy: FailurePolicy = field(default_factory=FailurePolicy)
    """How to handle step execution failures."""

    timeout_seconds: float = 60.0
    """Maximum wall-clock seconds for this step."""

    description: str = ""
    """Detailed description for the LLM (used during generation, not execution)."""


# ---------------------------------------------------------------------------
# WorkflowDef — top-level workflow definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkflowDef:
    """A deterministic workflow bound to an agent definition.

    The workflow is generated by ``WorkflowGenerator`` from user intent +
    agent capabilities, then persisted as part of the agent definition.
    Execution is fully deterministic — no LLM calls during execution (except
    for ``agent`` type steps which run their own Agent Loop).
    """

    workflow_id: str
    """Unique identifier (UUID)."""

    agent_key: str
    """The agent this workflow belongs to."""

    version: int
    """Follows the agent's version number."""

    steps: tuple[StepDef, ...]
    """Ordered list of steps. Execution follows index order unless a
    ``condition`` step redirects to a different step_id."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Generation metadata: user intent, generation model, timestamp, etc."""

    created_at: str = ""
    """ISO 8601 timestamp of workflow creation."""

    def get_step(self, step_id: str) -> StepDef | None:
        """Look up a step by its ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def step_index(self, step_id: str) -> int:
        """Return the index of a step by ID, or -1 if not found."""
        for i, step in enumerate(self.steps):
            if step.step_id == step_id:
                return i
        return -1


# ---------------------------------------------------------------------------
# StepResult — outcome of a single step execution
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class StepResult:
    """Outcome of executing a single workflow step."""

    step_id: str
    """The step that was executed."""

    status: Literal["success", "failed", "skipped", "waiting_human"] = "success"
    """Execution outcome."""

    output: dict[str, Any] = field(default_factory=dict)
    """Step output data, available for downstream steps via ``$steps.<step_id>.<key>``."""

    error_message: str | None = None
    """Error detail when ``status="failed"``."""

    tool_events: list[ToolExecutionRecord] = field(default_factory=list)
    """Tool execution records from this step."""

    duration_ms: int = 0
    """Wall-clock execution time in milliseconds."""

    retry_count: int = 0
    """Number of retries attempted."""


# ---------------------------------------------------------------------------
# WorkflowResult — outcome of the entire workflow
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WorkflowResult:
    """Outcome of executing an entire workflow."""

    workflow_id: str
    """The workflow that was executed."""

    status: Literal["completed", "failed", "waiting_human", "cancelled"] = "completed"
    """Final workflow status."""

    step_results: list[StepResult] = field(default_factory=list)
    """Results for each executed step, in execution order."""

    final_output: str = ""
    """Aggregated output text from the workflow."""

    total_usage: UsageInfo | None = None
    """Accumulated LLM token usage across all agent steps."""

    error_message: str | None = None
    """Error detail when ``status="failed"``."""

    waiting_step_id: str | None = None
    """When ``status="waiting_human"``, the step_id that is paused."""


# ---------------------------------------------------------------------------
# WorkflowStreamEvent — streaming events during workflow execution
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WorkflowStreamEvent:
    """A streaming event emitted during workflow execution."""

    event_type: Literal[
        "workflow_start",
        "step_start",
        "step_progress",
        "step_completed",
        "step_failed",
        "step_skipped",
        "step_waiting_human",
        "workflow_completed",
        "workflow_failed",
    ]
    """Event type discriminator."""

    workflow_id: str
    """The workflow being executed."""

    step_id: str | None = None
    """The step this event relates to (None for workflow-level events)."""

    step_result: StepResult | None = None
    """Populated for ``step_completed``, ``step_failed``, ``step_skipped``."""

    delta: str | None = None
    """Incremental text from agent steps (``step_progress``)."""

    workflow_result: WorkflowResult | None = None
    """Populated for ``workflow_completed``, ``workflow_failed``."""


# ---------------------------------------------------------------------------
# WorkflowRequest — request to execute a workflow
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WorkflowRequest:
    """Request to execute a workflow, parallel to AgentTurnRequest."""

    session_id: str
    user_message: str
    agent_key: str
    agent_version: int | None = None
    workflow: WorkflowDef | None = None
    """Direct workflow definition. If None, loaded from agent definition."""

    resume_checkpoint: str | None = None
    """Workflow ID to resume from a human_gate checkpoint."""

    human_response: str | None = None
    """Human's response to a human_gate prompt."""

    trace_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    customer_id: str | None = None
    locale: str | None = None
