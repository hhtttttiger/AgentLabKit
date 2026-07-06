"""WorkflowEngine — deterministic workflow execution engine.

Drives a workflow step-by-step according to its definition. Supports:
- Sequential execution of tool/agent/human_gate/condition steps
- Input reference resolution between steps
- Failure policies (fail/retry/skip)
- Condition-based branching
- Human gate pause/resume with checkpoint persistence
- Streaming events via EventBus

The engine does NOT make LLM decisions during execution — all branching
is determined by condition steps evaluating against context variables.
Only ``agent`` type steps invoke the LLM (via SubAgentExecutor's Agent Loop).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from llm_gateway import UsageInfo

from ..contracts.models import ToolExecutionRecord
from ..event_bus import EventBus
from ..tools.contracts import ToolExecutionContext
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
from .state_store import WorkflowCheckpoint, WorkflowStateStore
from .step_executor import StepExecutor

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Deterministic workflow execution engine.

    Executes a ``WorkflowDef`` step-by-step, resolving input references
    between steps and handling failures according to each step's
    ``FailurePolicy``.

    Args:
        step_executor: Dispatches step execution to tool/agent/gate handlers.
        state_store: Persists checkpoints for human_gate pause/resume.
        event_bus: Optional event bus for lifecycle event emission.
    """

    def __init__(
        self,
        step_executor: StepExecutor,
        state_store: WorkflowStateStore,
        event_bus: EventBus | None = None,
    ) -> None:
        self._step_executor = step_executor
        self._state_store = state_store
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Public API — run workflow
    # ------------------------------------------------------------------

    async def run_workflow(
        self,
        workflow: WorkflowDef,
        user_input: str,
        context: ToolExecutionContext,
    ) -> WorkflowResult:
        """Execute a workflow to completion or pause.

        Args:
            workflow: The workflow definition to execute.
            user_input: The original user message.
            context: Runtime context (session, trace, agent info).

        Returns:
            A ``WorkflowResult`` with status ``completed``, ``failed``,
            or ``waiting_human``.
        """
        context_vars: dict[str, Any] = {"$user_input": user_input}
        step_results: list[StepResult] = []
        total_usage = UsageInfo(input=0, output=0, cache_read=0, cache_write=0, total_tokens=0)

        self._emit_event(WorkflowStreamEvent(
            event_type="workflow_start",
            workflow_id=workflow.workflow_id,
        ))

        step_index = 0
        while step_index < len(workflow.steps):
            step = workflow.steps[step_index]

            # Resolve input references
            resolved_input = self._resolve_input(step, context_vars)

            # Emit step start
            self._emit_event(WorkflowStreamEvent(
                event_type="step_start",
                workflow_id=workflow.workflow_id,
                step_id=step.step_id,
            ))

            # Execute with retry policy
            step_result = await self._execute_with_policy(
                step, resolved_input, context,
            )

            step_results.append(step_result)

            # Handle result
            if step_result.status == "waiting_human":
                # Save checkpoint and return
                await self._state_store.save_checkpoint(WorkflowCheckpoint(
                    workflow_id=workflow.workflow_id,
                    step_results=step_results,
                    context_vars=context_vars,
                    current_step_index=step_index,
                ))
                self._emit_event(WorkflowStreamEvent(
                    event_type="step_waiting_human",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    step_result=step_result,
                ))
                return WorkflowResult(
                    workflow_id=workflow.workflow_id,
                    status="waiting_human",
                    step_results=step_results,
                    waiting_step_id=step.step_id,
                    total_usage=total_usage,
                )

            if step_result.status == "failed":
                self._emit_event(WorkflowStreamEvent(
                    event_type="step_failed",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    step_result=step_result,
                ))
                return WorkflowResult(
                    workflow_id=workflow.workflow_id,
                    status="failed",
                    step_results=step_results,
                    error_message=step_result.error_message,
                    total_usage=total_usage,
                )

            if step_result.status == "skipped":
                self._emit_event(WorkflowStreamEvent(
                    event_type="step_skipped",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    step_result=step_result,
                ))
            else:
                self._emit_event(WorkflowStreamEvent(
                    event_type="step_completed",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    step_result=step_result,
                ))

            # Store step output in context
            self._store_output(step, step_result, context_vars)

            # Determine next step
            step_index = self._resolve_next_step(step, step_result, workflow, step_index)

        # Workflow completed
        final_output = self._build_final_output(step_results)

        # Clear checkpoint if it exists
        await self._state_store.clear_checkpoint(workflow.workflow_id)

        result = WorkflowResult(
            workflow_id=workflow.workflow_id,
            status="completed",
            step_results=step_results,
            final_output=final_output,
            total_usage=total_usage,
        )

        self._emit_event(WorkflowStreamEvent(
            event_type="workflow_completed",
            workflow_id=workflow.workflow_id,
            workflow_result=result,
        ))

        return result

    # ------------------------------------------------------------------
    # Public API — stream workflow
    # ------------------------------------------------------------------

    async def stream_workflow(
        self,
        workflow: WorkflowDef,
        user_input: str,
        context: ToolExecutionContext,
    ) -> AsyncIterator[WorkflowStreamEvent]:
        """Execute a workflow, yielding events as steps complete.

        Same as ``run_workflow`` but yields ``WorkflowStreamEvent`` objects
        in real-time for streaming UI updates.
        """
        context_vars: dict[str, Any] = {"$user_input": user_input}
        step_results: list[StepResult] = []
        total_usage = UsageInfo(input=0, output=0, cache_read=0, cache_write=0, total_tokens=0)

        yield WorkflowStreamEvent(
            event_type="workflow_start",
            workflow_id=workflow.workflow_id,
        )

        step_index = 0
        while step_index < len(workflow.steps):
            step = workflow.steps[step_index]
            resolved_input = self._resolve_input(step, context_vars)

            yield WorkflowStreamEvent(
                event_type="step_start",
                workflow_id=workflow.workflow_id,
                step_id=step.step_id,
            )

            step_result = await self._execute_with_policy(
                step, resolved_input, context,
            )

            step_results.append(step_result)

            if step_result.status == "waiting_human":
                await self._state_store.save_checkpoint(WorkflowCheckpoint(
                    workflow_id=workflow.workflow_id,
                    step_results=step_results,
                    context_vars=context_vars,
                    current_step_index=step_index,
                ))
                yield WorkflowStreamEvent(
                    event_type="step_waiting_human",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    step_result=step_result,
                )
                return

            if step_result.status == "failed":
                yield WorkflowStreamEvent(
                    event_type="step_failed",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    step_result=step_result,
                )
                yield WorkflowStreamEvent(
                    event_type="workflow_failed",
                    workflow_id=workflow.workflow_id,
                    workflow_result=WorkflowResult(
                        workflow_id=workflow.workflow_id,
                        status="failed",
                        step_results=step_results,
                        error_message=step_result.error_message,
                        total_usage=total_usage,
                    ),
                )
                return

            event_type = "step_skipped" if step_result.status == "skipped" else "step_completed"
            yield WorkflowStreamEvent(
                event_type=event_type,
                workflow_id=workflow.workflow_id,
                step_id=step.step_id,
                step_result=step_result,
            )

            self._store_output(step, step_result, context_vars)
            step_index = self._resolve_next_step(step, step_result, workflow, step_index)

        final_output = self._build_final_output(step_results)
        await self._state_store.clear_checkpoint(workflow.workflow_id)

        result = WorkflowResult(
            workflow_id=workflow.workflow_id,
            status="completed",
            step_results=step_results,
            final_output=final_output,
            total_usage=total_usage,
        )

        yield WorkflowStreamEvent(
            event_type="workflow_completed",
            workflow_id=workflow.workflow_id,
            workflow_result=result,
        )

    # ------------------------------------------------------------------
    # Public API — resume workflow
    # ------------------------------------------------------------------

    async def resume_workflow(
        self,
        workflow: WorkflowDef,
        human_response: str,
        context: ToolExecutionContext,
    ) -> WorkflowResult:
        """Resume a paused workflow after human input.

        Args:
            workflow: The workflow definition (must match the paused workflow).
            human_response: The human's response to the gate prompt.
            context: Runtime context.

        Returns:
            Updated ``WorkflowResult``.

        Raises:
            ValueError: If no checkpoint exists for this workflow.
        """
        checkpoint = await self._state_store.load_checkpoint(workflow.workflow_id)
        if checkpoint is None:
            raise ValueError(
                f"No checkpoint found for workflow {workflow.workflow_id}"
            )

        # Restore state
        context_vars = checkpoint.context_vars
        step_results = list(checkpoint.step_results)
        step_index = checkpoint.current_step_index

        # Mark the human_gate step as completed with the response
        if step_results and step_results[-1].status == "waiting_human":
            step_results[-1].status = "success"
            step_results[-1].output["human_response"] = human_response

        # Store human response in context
        waiting_step = workflow.steps[step_index]
        context_vars[f"$steps.{waiting_step.step_id}"] = {
            **(context_vars.get(f"$steps.{waiting_step.step_id}") or {}),
            "human_response": human_response,
        }

        # Clear checkpoint
        await self._state_store.clear_checkpoint(workflow.workflow_id)

        # Continue execution from the next step
        step_index += 1
        total_usage = UsageInfo(input=0, output=0, cache_read=0, cache_write=0, total_tokens=0)

        while step_index < len(workflow.steps):
            step = workflow.steps[step_index]
            resolved_input = self._resolve_input(step, context_vars)

            step_result = await self._execute_with_policy(
                step, resolved_input, context,
            )

            step_results.append(step_result)

            if step_result.status == "waiting_human":
                await self._state_store.save_checkpoint(WorkflowCheckpoint(
                    workflow_id=workflow.workflow_id,
                    step_results=step_results,
                    context_vars=context_vars,
                    current_step_index=step_index,
                ))
                return WorkflowResult(
                    workflow_id=workflow.workflow_id,
                    status="waiting_human",
                    step_results=step_results,
                    waiting_step_id=step.step_id,
                    total_usage=total_usage,
                )

            if step_result.status == "failed":
                return WorkflowResult(
                    workflow_id=workflow.workflow_id,
                    status="failed",
                    step_results=step_results,
                    error_message=step_result.error_message,
                    total_usage=total_usage,
                )

            self._store_output(step, step_result, context_vars)
            step_index = self._resolve_next_step(step, step_result, workflow, step_index)

        final_output = self._build_final_output(step_results)
        return WorkflowResult(
            workflow_id=workflow.workflow_id,
            status="completed",
            step_results=step_results,
            final_output=final_output,
            total_usage=total_usage,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_input(
        self,
        step: StepDef,
        context_vars: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve all input references for a step.

        Returns a dict with resolved values from input_mapping and
        tool_arguments.
        """
        resolved: dict[str, Any] = {}

        # Resolve general input_mapping
        for key, input_ref in step.input_mapping.items():
            value = input_ref.resolve(context_vars)
            if value is not None:
                resolved[key] = value

        # Resolve tool_arguments
        for param_name, input_ref in step.tool_arguments.items():
            value = input_ref.resolve(context_vars)
            if value is not None:
                resolved[param_name] = value

        # Always include $user_input
        resolved["$user_input"] = context_vars.get("$user_input", "")

        return resolved

    def _store_output(
        self,
        step: StepDef,
        result: StepResult,
        context_vars: dict[str, Any],
    ) -> None:
        """Store step output in context variables for downstream steps."""
        step_key = f"$steps.{step.step_id}"

        # Apply output_mapping if defined
        if step.output_mapping:
            mapped_output: dict[str, Any] = {}
            for output_key, context_key in step.output_mapping.items():
                if output_key in result.output:
                    mapped_output[context_key] = result.output[output_key]
            context_vars[step_key] = mapped_output
        else:
            # Store full output
            context_vars[step_key] = result.output

    def _resolve_next_step(
        self,
        current_step: StepDef,
        result: StepResult,
        workflow: WorkflowDef,
        current_index: int,
    ) -> int:
        """Determine the index of the next step to execute.

        For condition steps, follows the branch target.
        For all other steps, advances to the next sequential step.
        """
        if current_step.step_type == "condition" and result.status == "success":
            next_step_id = result.output.get("next_step_id")
            if next_step_id:
                target_index = workflow.step_index(next_step_id)
                if target_index >= 0:
                    return target_index
                logger.warning(
                    "workflow_engine condition targets unknown step_id=%s, continuing sequentially",
                    next_step_id,
                )

        return current_index + 1

    async def _execute_with_policy(
        self,
        step: StepDef,
        resolved_input: dict[str, Any],
        context: ToolExecutionContext,
    ) -> StepResult:
        """Execute a step with retry policy enforcement."""
        policy = step.failure_policy
        max_attempts = 1 + (policy.max_retries if policy.on_failure == "retry" else 0)

        last_result: StepResult | None = None
        for attempt in range(max_attempts):
            result = await self._step_executor.execute_step(
                step, resolved_input, context,
            )

            if result.status != "failed":
                result.retry_count = attempt
                return result

            last_result = result

            if attempt < max_attempts - 1:
                logger.info(
                    "workflow_engine retrying step_id=%s attempt=%d/%d",
                    step.step_id,
                    attempt + 1,
                    max_attempts,
                )
                await asyncio.sleep(policy.retry_delay_seconds)

        # All attempts failed
        if last_result is not None:
            last_result.retry_count = max_attempts - 1

            # Check if we should skip
            if policy.on_failure == "skip":
                return StepResult(
                    step_id=step.step_id,
                    status="skipped",
                    error_message=last_result.error_message,
                    retry_count=last_result.retry_count,
                )

        return last_result or StepResult(
            step_id=step.step_id,
            status="failed",
            error_message="Execution failed with no result",
        )

    def _build_final_output(self, step_results: list[StepResult]) -> str:
        """Build aggregated output text from all step results."""
        outputs: list[str] = []
        for result in step_results:
            if result.status == "success":
                reply = result.output.get("reply_text") or result.output.get("result")
                if reply:
                    outputs.append(str(reply))
        return "\n\n".join(outputs) if outputs else ""

    def _emit_event(self, event: WorkflowStreamEvent) -> None:
        """Emit an event to the event bus if available."""
        if self._event_bus:
            try:
                self._event_bus.emit("workflow_event", event)
            except Exception:
                logger.debug("workflow_engine event emission failed", exc_info=True)
