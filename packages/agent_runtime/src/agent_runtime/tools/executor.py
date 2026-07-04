"""Isolated, timeout-aware tool executor.

:class:`ToolExecutor` is the single execution gateway for all registered tools.
It provides:

* **Schema validation** — rejects bad LLM arguments before calling the handler
* **Timeout control** — ``asyncio.wait_for`` with per-spec deadline
* **Error isolation** — exceptions are caught and returned as ``ToolResult``
* **Retry logic** — exponential back-off, skipped for non-idempotent tools
* **Execution timing** — ``duration_ms`` always populated on the result
* **Streaming updates** — ``on_update`` callback for long-running tools
* **Sequential/parallel modes** — per-tool ``execution_mode`` override

Inspired by pi agent-core ``executeToolCalls()`` / ``executePreparedToolCall()``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import time
from typing import TYPE_CHECKING, Any, Callable

from .contracts import ToolExecutionContext, ToolExecutionMode, ToolHandler, ToolResult, ToolSpec
from .schema_validator import SchemaValidator

if TYPE_CHECKING:
    from .registry import DynamicToolRegistry

logger = logging.getLogger(__name__)

# Minimum back-off delay (seconds) between retry attempts.
_RETRY_BASE_DELAY = 0.1


@dataclass(frozen=True, slots=True)
class PreparedToolExecution:
    """Validated tool invocation ready to run."""

    spec: ToolSpec
    handler: ToolHandler


class ToolExecutor:
    """Isolated executor for tools registered in a :class:`DynamicToolRegistry`.

    The executor is **stateless** — one instance can safely be shared across
    requests and concurrent turns.

    Args:
        schema_validator: Optional custom validator; defaults to a new
            :class:`~agent_runtime.tools.schema_validator.SchemaValidator`.
    """

    def __init__(self, schema_validator: SchemaValidator | None = None) -> None:
        self._validator = schema_validator or SchemaValidator()

    # ------------------------------------------------------------------
    # Primary execution path
    # ------------------------------------------------------------------

    async def execute(
        self,
        registry: "DynamicToolRegistry",
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        *,
        on_update: Callable[[ToolResult], None] | None = None,
    ) -> ToolResult:
        """Execute a named tool with full isolation and policy enforcement.

        Args:
            registry: The registry that holds the tool's spec and handler.
            tool_name: Name of the tool to execute (must be registered).
            arguments: Raw argument dict from the LLM tool-call.
            context: Runtime context for audit / policy decisions.
            on_update: Optional callback for streaming partial results.

        Returns:
            Always a :class:`ToolResult` — never raises.
        """
        prepared = self.prepare_execution(registry, tool_name, arguments)
        if isinstance(prepared, ToolResult):
            return prepared

        # 2. Retry loop with timeout + error isolation
        max_attempts = 1 + max(0, prepared.spec.max_retries)
        last_result: ToolResult | None = None

        for attempt in range(max_attempts):
            if attempt > 0:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.debug("tool=%s retry=%d delay=%.2fs", tool_name, attempt, delay)
                await asyncio.sleep(delay)

            start_ns = time.perf_counter_ns()
            result = await self._attempt(
                tool_name=tool_name,
                handler=prepared.handler,
                arguments=arguments,
                context=context,
                timeout=prepared.spec.timeout_seconds,
                on_update=on_update,
            )
            result.duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

            last_result = result

            if result.status == "success":
                return result

            # Do not retry timeouts or non-idempotent failures
            if result.status == "timeout":
                return result
            if not prepared.spec.is_idempotent:
                return result

        # All attempts exhausted
        return last_result or ToolResult(
            output="",
            status="error",
            error_message=f"Tool '{tool_name}' failed after {max_attempts} attempt(s)",
        )

    def prepare_execution(
        self,
        registry: "DynamicToolRegistry",
        tool_name: str,
        arguments: dict[str, Any],
    ) -> PreparedToolExecution | ToolResult:
        """Resolve the handler and validate arguments without executing it."""
        spec = registry.get_spec(tool_name)
        if spec is None:
            return ToolResult(
                output="",
                status="error",
                error_message=f"Unknown tool: '{tool_name}'",
            )

        validation_error = self._validator.validate(spec.parameters_schema, arguments)
        if validation_error:
            logger.debug(
                "tool=%s schema_validation_failed reason=%r", tool_name, validation_error
            )
            return ToolResult(
                output="",
                status="error",
                error_message=f"Invalid arguments for tool '{tool_name}': {validation_error}",
            )

        handler = registry.get_handler(tool_name)
        if handler is None:
            return ToolResult(
                output="",
                status="error",
                error_message=f"No handler registered for tool: '{tool_name}'",
            )

        return PreparedToolExecution(spec=spec, handler=handler)

    # ------------------------------------------------------------------
    # Batch execution — sequential / parallel
    # ------------------------------------------------------------------

    async def execute_batch(
        self,
        calls: list[tuple[str, dict[str, Any]]],
        registry: "DynamicToolRegistry",
        context: ToolExecutionContext,
        *,
        default_mode: ToolExecutionMode = ToolExecutionMode.PARALLEL,
        on_update: Callable[[str, ToolResult], None] | None = None,
    ) -> list[ToolResult]:
        """Execute a batch of tool calls in sequential or parallel mode.

        Inspired by pi ``executeToolCalls()`` which checks
        ``config.toolExecution`` and per-tool ``executionMode`` overrides.

        Args:
            calls: List of ``(tool_name, arguments)`` pairs.
            registry: Tool registry for resolving handlers.
            context: Execution context.
            default_mode: Default execution mode when no per-tool override.
            on_update: Optional callback ``(tool_name, partial_result)`` for
                streaming updates.

        Returns:
            List of :class:`ToolResult` in the same order as *calls*.
        """
        if not calls:
            return []

        # Check if any tool requires sequential execution
        has_sequential = any(
            self._is_sequential(name, registry, default_mode) for name, _ in calls
        )

        if has_sequential or default_mode == ToolExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(calls, registry, context, on_update=on_update)
        return await self._execute_parallel(calls, registry, context, on_update=on_update)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _attempt(
        self,
        *,
        tool_name: str,
        handler: Any,  # noqa: ANN401
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        timeout: float,
        on_update: Callable[[ToolResult], None] | None = None,
    ) -> ToolResult:
        """Run one execution attempt, capturing timeout and generic errors."""
        try:
            # Try calling with on_update support
            try:
                result = await asyncio.wait_for(
                    handler.execute(arguments, context, on_update),
                    timeout=timeout,
                )
            except TypeError:
                # Handler doesn't accept on_update — call without it
                result = await asyncio.wait_for(
                    handler.execute(arguments, context),
                    timeout=timeout,
                )

            if not isinstance(result, ToolResult):
                # Defensive: wrap unexpected return types
                return ToolResult(output=str(result), status="success")
            return result
        except asyncio.TimeoutError:
            logger.warning("tool=%s timed_out after %.1fs", tool_name, timeout)
            return ToolResult(
                output="",
                status="timeout",
                error_message=f"Tool '{tool_name}' timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("tool=%s error=%r", tool_name, exc)
            return ToolResult(
                output="",
                status="error",
                error_message=str(exc),
            )

    async def _execute_sequential(
        self,
        calls: list[tuple[str, dict[str, Any]]],
        registry: "DynamicToolRegistry",
        context: ToolExecutionContext,
        *,
        on_update: Callable[[str, ToolResult], None] | None = None,
    ) -> list[ToolResult]:
        """Execute tool calls one by one."""
        results: list[ToolResult] = []
        for tool_name, arguments in calls:
            per_tool_update = None
            if on_update is not None:
                per_tool_update = lambda r, tn=tool_name: on_update(tn, r)
            result = await self.execute(registry, tool_name, arguments, context, on_update=per_tool_update)
            results.append(result)
        return results

    async def _execute_parallel(
        self,
        calls: list[tuple[str, dict[str, Any]]],
        registry: "DynamicToolRegistry",
        context: ToolExecutionContext,
        *,
        on_update: Callable[[str, ToolResult], None] | None = None,
    ) -> list[ToolResult]:
        """Execute tool calls concurrently."""
        async def _run_one(tool_name: str, arguments: dict[str, Any]) -> ToolResult:
            per_tool_update = None
            if on_update is not None:
                per_tool_update = lambda r, tn=tool_name: on_update(tn, r)
            return await self.execute(registry, tool_name, arguments, context, on_update=per_tool_update)

        tasks = [_run_one(name, args) for name, args in calls]
        return list(await asyncio.gather(*tasks))

    @staticmethod
    def _is_sequential(
        tool_name: str,
        registry: "DynamicToolRegistry",
        default_mode: ToolExecutionMode,
    ) -> bool:
        """Check if a specific tool requires sequential execution."""
        spec = registry.get_spec(tool_name)
        if spec is not None and spec.execution_mode == ToolExecutionMode.SEQUENTIAL:
            return True
        return default_mode == ToolExecutionMode.SEQUENTIAL
