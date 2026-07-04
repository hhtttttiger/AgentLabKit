"""GuardsPipeline — sequential orchestrator for input / output / tool guards."""

from __future__ import annotations

import dataclasses
from collections.abc import Awaitable, Callable

from .contracts import (
    Guard,
    GuardAuditCallback,
    GuardContext,
    GuardPipelineResult,
    GuardResult,
    GuardVerdict,
)

SafeReplyGenerator = Callable[[GuardContext, GuardResult], str | Awaitable[str]]


class GuardsPipeline:
    """Run guards sequentially per phase.

    * **BLOCK** → stop immediately, return blocked result.
    * **MODIFY** → apply text rewrite, pass modified text to next guard.
    * **PASS** → continue.
    """

    def __init__(
        self,
        *,
        input_guards: list[Guard] | None = None,
        output_guards: list[Guard] | None = None,
        tool_guards: list[Guard] | None = None,
        block_response: str = "I'm unable to process this request.",
        audit_callback: GuardAuditCallback | None = None,
        safe_reply_generator: SafeReplyGenerator | None = None,
    ) -> None:
        self.input_guards: list[Guard] = list(input_guards or [])
        self.output_guards: list[Guard] = list(output_guards or [])
        self.tool_guards: list[Guard] = list(tool_guards or [])
        self.block_response = block_response
        self._audit = audit_callback
        self.safe_reply_generator = safe_reply_generator

    # ── public API ─────────────────────────────────────────

    async def run_input_guards(
        self,
        *,
        message: str,
        session_id: str = "",
        trace_id: str = "",
        metadata: dict[str, str] | None = None,
    ) -> GuardPipelineResult:
        ctx = GuardContext(
            phase="input",
            message=message,
            session_id=session_id,
            trace_id=trace_id,
            metadata=dict(metadata or {}),
        )
        return await self._run_guards(self.input_guards, ctx)

    async def run_output_guards(
        self,
        *,
        message: str,
        session_id: str = "",
        trace_id: str = "",
        metadata: dict[str, str] | None = None,
    ) -> GuardPipelineResult:
        ctx = GuardContext(
            phase="output",
            message=message,
            session_id=session_id,
            trace_id=trace_id,
            metadata=dict(metadata or {}),
        )
        return await self._run_guards(self.output_guards, ctx)

    async def run_tool_guards(
        self,
        *,
        tool_name: str,
        tool_arguments: dict,
        session_id: str = "",
        trace_id: str = "",
        metadata: dict[str, str] | None = None,
    ) -> GuardPipelineResult:
        """Validate tool arguments before execution.

        No ``message`` parameter — tool guards operate on ``tool_arguments``,
        not on a text payload.
        """
        ctx = GuardContext(
            phase="tool",
            session_id=session_id,
            trace_id=trace_id,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            metadata=dict(metadata or {}),
        )
        return await self._run_guards(self.tool_guards, ctx)

    # ── internal ───────────────────────────────────────────

    async def _run_guards(
        self,
        guards: list[Guard],
        ctx: GuardContext,
    ) -> GuardPipelineResult:
        results: list[GuardResult] = []
        current_text = ctx.message

        for guard in guards:
            eval_ctx = dataclasses.replace(ctx, message=current_text)
            result = await guard.evaluate(eval_ctx)
            results.append(result)

            if self._audit:
                await self._audit.on_guard_result(ctx.phase, result, eval_ctx)

            if result.verdict is GuardVerdict.BLOCK:
                return GuardPipelineResult(
                    final_verdict=GuardVerdict.BLOCK,
                    results=results,
                    blocked_by=result.guard_name,
                    block_reason=result.reason,
                )

            if result.verdict is GuardVerdict.MODIFY and result.modified_text is not None:
                current_text = result.modified_text

        # Determine final verdict: MODIFY if any guard modified, else PASS
        any_modified = any(r.verdict is GuardVerdict.MODIFY for r in results)
        return GuardPipelineResult(
            final_verdict=GuardVerdict.MODIFY if any_modified else GuardVerdict.PASS,
            results=results,
            modified_text=current_text if any_modified else None,
        )
