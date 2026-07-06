"""Step executor — dispatches workflow steps to appropriate executors.

Handles four step types:
- ``tool``: Calls a registered tool via ToolExecutor
- ``agent``: Delegates to a sub-agent via SubAgentExecutor
- ``human_gate``: Returns a waiting result (actual pause/resume handled by engine)
- ``condition``: Evaluates an expression and determines next step

The executor is stateless — all per-step state lives in StepResult.
"""

from __future__ import annotations

import logging
import operator
import re
import time
from typing import Any

from ..contracts.models import AgentTurnRequest, ToolExecutionRecord
from ..orchestration.contracts import SubAgentContext
from ..orchestration.sub_agent_executor import SubAgentExecutor
from ..tools.contracts import ToolExecutionContext, ToolResult
from ..tools.executor import ToolExecutor
from ..tools.registry import DynamicToolRegistry
from .contracts import InputRef, StepDef, StepResult

logger = logging.getLogger(__name__)

# Regex to parse condition expressions like "$steps.check.eligible == true"
_CONDITION_PATTERN = re.compile(
    r"^\s*(\$steps\.[\w.]+|\$user_input)\s*(==|!=|>|<|>=|<=)\s*(.+?)\s*$"
)


class StepExecutor:
    """Dispatches workflow step execution to the appropriate handler.

    Stateless — one instance can be shared across concurrent workflow runs.

    Args:
        tool_executor: Executor for tool-type steps.
        tool_registry: Registry to look up tool specs and handlers.
        sub_agent_executor: Executor for agent-type steps.
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        tool_registry: DynamicToolRegistry,
        sub_agent_executor: SubAgentExecutor,
    ) -> None:
        self._tool_executor = tool_executor
        self._tool_registry = tool_registry
        self._sub_agent_executor = sub_agent_executor

    async def execute_step(
        self,
        step: StepDef,
        resolved_input: dict[str, Any],
        context: ToolExecutionContext,
    ) -> StepResult:
        """Execute a single workflow step.

        Args:
            step: The step definition to execute.
            resolved_input: Pre-resolved input values from InputRef resolution.
            context: Runtime context (session, trace, agent info).

        Returns:
            A StepResult with the execution outcome.
        """
        start_time = time.monotonic()

        try:
            if step.step_type == "tool":
                result = await self._execute_tool(step, resolved_input, context)
            elif step.step_type == "agent":
                result = await self._execute_agent(step, resolved_input, context)
            elif step.step_type == "human_gate":
                result = self._prepare_human_gate(step, resolved_input)
            elif step.step_type == "condition":
                result = self._evaluate_condition(step, resolved_input)
            else:
                result = StepResult(
                    step_id=step.step_id,
                    status="failed",
                    error_message=f"Unknown step type: {step.step_type}",
                )
        except Exception as exc:
            logger.error(
                "step_executor unexpected error step_id=%s error=%s",
                step.step_id,
                exc,
                exc_info=True,
            )
            result = StepResult(
                step_id=step.step_id,
                status="failed",
                error_message=f"Unexpected error: {exc}",
            )

        result.duration_ms = int((time.monotonic() - start_time) * 1000)
        return result

    # ------------------------------------------------------------------
    # Tool step
    # ------------------------------------------------------------------

    async def _execute_tool(
        self,
        step: StepDef,
        resolved_input: dict[str, Any],
        context: ToolExecutionContext,
    ) -> StepResult:
        """Execute a tool-type step."""
        if not step.tool_name:
            return StepResult(
                step_id=step.step_id,
                status="failed",
                error_message="Tool step missing tool_name",
            )

        # Build tool arguments from resolved input
        tool_args: dict[str, Any] = {}
        for param_name, input_ref in step.tool_arguments.items():
            value = input_ref.resolve(resolved_input)
            if value is not None:
                tool_args[param_name] = value

        # Also merge general input_mapping
        for key, value in resolved_input.items():
            if key.startswith("$"):
                continue
            if key not in tool_args:
                tool_args[key] = value

        logger.info(
            "step_executor executing tool step_id=%s tool=%s",
            step.step_id,
            step.tool_name,
        )

        tool_result: ToolResult = await self._tool_executor.execute(
            registry=self._tool_registry,
            tool_name=step.tool_name,
            arguments=tool_args,
            context=context,
        )

        # Build output
        output: dict[str, Any] = {}
        if tool_result.structured_data:
            output.update(tool_result.structured_data)
        output["result"] = tool_result.output

        # Build tool event record
        tool_event = ToolExecutionRecord(
            tool_name=step.tool_name,
            status=tool_result.status,
            arguments=tool_args,
            output_text=tool_result.output,
            structured_data=tool_result.structured_data,
            error_message=tool_result.error_message,
            duration_ms=tool_result.duration_ms,
        )

        if tool_result.status == "error":
            return StepResult(
                step_id=step.step_id,
                status="failed",
                output=output,
                error_message=tool_result.error_message,
                tool_events=[tool_event],
            )

        return StepResult(
            step_id=step.step_id,
            status="success",
            output=output,
            tool_events=[tool_event],
        )

    # ------------------------------------------------------------------
    # Agent step
    # ------------------------------------------------------------------

    async def _execute_agent(
        self,
        step: StepDef,
        resolved_input: dict[str, Any],
        context: ToolExecutionContext,
    ) -> StepResult:
        """Execute an agent-type step via SubAgentExecutor."""
        if not step.agent_key:
            return StepResult(
                step_id=step.step_id,
                status="failed",
                error_message="Agent step missing agent_key",
            )

        # Build the task message with variable interpolation
        task_message = step.agent_task or ""
        for key, value in resolved_input.items():
            placeholder = "{" + key + "}"
            if placeholder in task_message:
                task_message = task_message.replace(placeholder, str(value))

        # If no template placeholders were used, append the user input
        if "{" not in task_message and "$user_input" in resolved_input:
            task_message = f"{task_message}\n\n{resolved_input['$user_input']}"

        logger.info(
            "step_executor executing agent step_id=%s agent_key=%s",
            step.step_id,
            step.agent_key,
        )

        parent_context = SubAgentContext(
            parent_agent_key=context.agent_key or "workflow",
            parent_session_id=context.session_id,
            parent_trace_id=context.trace_id or "",
            depth=0,
            summary=task_message,
        )

        delegation_result = await self._sub_agent_executor.run_sub_turn(
            agent_key=step.agent_key,
            user_message=task_message,
            parent_context=parent_context,
        )

        output: dict[str, Any] = {
            "reply_text": delegation_result.reply_text,
            "action": delegation_result.action.value if delegation_result.action else "reply",
        }

        tool_events = list(delegation_result.tool_events) if delegation_result.tool_events else []

        if delegation_result.error_message:
            return StepResult(
                step_id=step.step_id,
                status="failed",
                output=output,
                error_message=delegation_result.error_message,
                tool_events=tool_events,
            )

        return StepResult(
            step_id=step.step_id,
            status="success",
            output=output,
            tool_events=tool_events,
        )

    # ------------------------------------------------------------------
    # Human gate step
    # ------------------------------------------------------------------

    def _prepare_human_gate(
        self,
        step: StepDef,
        resolved_input: dict[str, Any],
    ) -> StepResult:
        """Prepare a human gate step — returns waiting_human status.

        The actual pause/resume is handled by the WorkflowEngine.
        """
        logger.info(
            "step_executor human gate step_id=%s prompt=%s",
            step.step_id,
            step.gate_prompt,
        )

        return StepResult(
            step_id=step.step_id,
            status="waiting_human",
            output={
                "gate_prompt": step.gate_prompt or "",
                "gate_options": list(step.gate_options),
            },
        )

    # ------------------------------------------------------------------
    # Condition step
    # ------------------------------------------------------------------

    def _evaluate_condition(
        self,
        step: StepDef,
        resolved_input: dict[str, Any],
    ) -> StepResult:
        """Evaluate a condition expression and determine the next step.

        Supports expressions like:
        - ``$steps.check.eligible == true``
        - ``$steps.check.amount > 500``
        - ``$user_input == "cancel"``

        Returns a StepResult with ``output["next_step_id"]`` set to the
        appropriate branch target.
        """
        if not step.condition_expr:
            return StepResult(
                step_id=step.step_id,
                status="failed",
                error_message="Condition step missing condition_expr",
            )

        match = _CONDITION_PATTERN.match(step.condition_expr)
        if not match:
            return StepResult(
                step_id=step.step_id,
                status="failed",
                error_message=f"Invalid condition expression: {step.condition_expr}",
            )

        ref_str, op_str, expected_str = match.groups()

        # Resolve the left-hand side
        ref = InputRef(ref_str)
        actual_value = ref.resolve(resolved_input)

        # Parse the expected value
        expected_value = self._parse_value(expected_str)

        # Evaluate the comparison
        ops = {
            "==": operator.eq,
            "!=": operator.ne,
            ">": operator.gt,
            "<": operator.lt,
            ">=": operator.ge,
            "<=": operator.le,
        }

        op_func = ops.get(op_str)
        if op_func is None:
            return StepResult(
                step_id=step.step_id,
                status="failed",
                error_message=f"Unknown operator: {op_str}",
            )

        try:
            condition_result = op_func(actual_value, expected_value)
        except TypeError:
            # Incompatible types for comparison
            condition_result = False

        # Determine next step
        if condition_result:
            next_step_id = step.condition_true_step
        else:
            next_step_id = step.condition_false_step

        logger.info(
            "step_executor condition step_id=%s expr=%s result=%s next=%s",
            step.step_id,
            step.condition_expr,
            condition_result,
            next_step_id,
        )

        return StepResult(
            step_id=step.step_id,
            status="success",
            output={
                "condition_result": condition_result,
                "next_step_id": next_step_id,
            },
        )

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        """Parse a condition's expected value from string representation."""
        stripped = value_str.strip()

        # Boolean
        if stripped.lower() == "true":
            return True
        if stripped.lower() == "false":
            return False

        # None/null
        if stripped.lower() in ("none", "null"):
            return None

        # Quoted string
        if (stripped.startswith('"') and stripped.endswith('"')) or \
           (stripped.startswith("'") and stripped.endswith("'")):
            return stripped[1:-1]

        # Number
        try:
            if "." in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            pass

        # Fallback: treat as string
        return stripped
