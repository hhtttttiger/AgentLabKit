"""Agent runtime engine — thin orchestration layer delegating to split modules.

This is the main public API of ``agent_runtime``.  The heavy lifting has been
extracted into dedicated modules:

- :mod:`factory` — runtime creation and dependency wiring
- :mod:`turn_prep` — definition resolution, settings overrides, skill composition
- :mod:`turn_guards` — input/output guardrails, global guardrails, voice evaluation
- :mod:`turn_post` — post-turn processing (handoff, output guards, result building)
- :mod:`session` — session snapshot load/save
- :mod:`message_builder` — message construction and normalization
- :mod:`tool_execution` — tool call dispatch and delegation
- :mod:`loop` — self-built agent loop with steering/follow-up queues
- :mod:`llm_adapter` — direct gateway calls without pydantic-ai
- :mod:`cancel` — cooperative cancellation tokens

The original 2600-line monolith has been decomposed into these focused modules
while preserving the same public API.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

if TYPE_CHECKING:
    from ..workflow.contracts import WorkflowDef, WorkflowResult, WorkflowStreamEvent

from llm_gateway import GatewayProtocol, UsageInfo

try:
    from opentelemetry.trace import Span, StatusCode, Tracer
except ModuleNotFoundError:  # pragma: no cover
    Span = None  # type: ignore[assignment,misc]
    StatusCode = None  # type: ignore[assignment,misc]
    Tracer = None  # type: ignore[assignment,misc]

from ..config import AgentSettings
from ..contracts.models import (
    AgentAction,
    AgentDecision,
    AgentMessage,
    AgentRole,
    AgentSessionState,
    AppliedSkillRecord,
    AgentTurnStreamEvent,
    AgentTurnRequest,
    AgentTurnResult,
    HandoffTarget,
    ToolExecutionRecord,
)
from ..contracts.run import AgentRun, ExecutionContext, RunError, RunStatus, RunTarget, RunUsage
from ..definition.loader import AgentDefinitionLoader
from ..definition.models import (
    AgentDefinitionSnapshot,
)
from ..errors import AgentError, AgentErrorCode
from ..event_bus import EventBus
from ..events import (
    AgentEvent,
    MessageEndEvent,
    MessageStartEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from ..events_v2 import (
    GuardrailBlocked,
    GuardrailEvaluated,
    RunCancelled,
    RunCompleted,
    RunFailed,
    RunStarted,
)
from ..guardrails import (
    GuardsPipeline,
    GuardVerdict,
    GlobalGuardrailsRepository,
    GlobalGuardrailsSnapshot,
)
from ..guardrails.global_guard import GlobalGuardrailService
from ..memory import (
    ContextManager,
    ContextWindow,
    SessionSnapshot,
    SessionStore,
)
from ..orchestration import DelegateToAgentTool, HandoffManager
from ..prompts import build_system_prompt
from ..skills import SkillRegistry, SkillComposer
from ..skills.builtin import register_builtin_skills
from ..tools import ToolBinding, ToolRegistry

from .cancel import CancelToken
from .llm_adapter import FinalDirective, LlmAdapter, ReplyTextStreamParser, ToolDirective, ToolSchema
from .loop import (
    LoopConfig,
    LoopContext,
    QueueMode,
    run_agent_loop,
    stream_agent_loop,
)
from .factory import create_agent_runtime as _create_agent_runtime_impl
from .message_builder import MessageBuilder
from .session import SessionManager
from .tool_execution import ToolExecution
from .turn_guards import InputGuardResult, TurnGuards
from .turn_post import TurnOutput, TurnPostProcessor
from .turn_prep import PreparedTurn, TurnPrep
from .voice_stream_handler import VoiceStreamHandler
from .workflow_runner import build_tool_context, build_workflow_engine, resolve_workflow

# ── Voice imports (for _post_process_turn) ──────────────────────────────
from ..channels.voice import (
    VoiceGuardrailEvaluator,
    VoiceSegmentOutcome,
)

_MAX_STREAM_TOOL_ROUNDS = 4
logger = logging.getLogger(__name__)


# ── Legacy helpers retained for backward compat ──────────────────────────


def _tool_binding_from_dict(d: dict) -> ToolBinding:
    """Construct a :class:`ToolBinding` from a raw override dict."""
    tool_name = d.get("tool_name", d.get("toolName"))
    if tool_name is None:
        raise KeyError("tool_name")
    mode = d.get("invocation_mode", d.get("invocationMode", "auto"))
    if mode not in ("auto", "manual_only", "disabled"):
        mode = "auto"
    return ToolBinding(
        tool_name=str(tool_name),
        display_name=d.get("display_name", d.get("displayName")),
        description=d.get("description"),
        invocation_mode=mode,  # type: ignore[arg-type]
        is_enabled=bool(d.get("is_enabled", d.get("isEnabled", True))),
        config=dict(d.get("config") or {}),
    )


# ── Legacy types kept for backward compat ────────────────────────────────


@dataclass(slots=True)
class AgentRunDeps:
    """Dependency object passed through the agent turn pipeline."""

    request: AgentTurnRequest
    session_state: AgentSessionState
    trace_id: str
    definition: AgentDefinitionSnapshot | None = None
    tool_events: list[ToolExecutionRecord] = field(default_factory=list)
    delegation_usage_list: list[UsageInfo] = field(default_factory=list)


# ── Runtime factory (delegated to factory.py) ────────────────────────────

#: Factory function — creates a fully wired :class:`AgentRuntime`.
#: Implementation lives in :mod:`factory.py`.
create_agent_runtime = _create_agent_runtime_impl


# ── OTel tracer span manager ───────────────────────────────────────────

_ROOT_ATTR = "agentlabkit.trace.root"


class _TracerSpanManager:
    """Manages an OTel root span for a single agent turn.

    Creates child spans for LLM calls and tool executions.  The root span
    carries ``agentlabkit.trace.root=True`` so the
    :class:`TraceBufferSpanProcessor` knows to flush the trace when it ends.
    """

    def __init__(self, tracer: Any, trace_id: str, agent_key: str | None = None) -> None:
        self._tracer = tracer
        self._trace_id = trace_id
        self._agent_key = agent_key
        self._root_span: Any = None
        self._error_message: str | None = None

    def start(self) -> None:
        self._root_span = self._tracer.start_span(
            "agent.run",
            attributes={
                _ROOT_ATTR: True,
                "agentlabkit.trace_id": self._trace_id,
                **({"agentlabkit.agent_key": self._agent_key} if self._agent_key else {}),
            },
        )

    def start_llm_span(self) -> Any:
        if self._root_span is None:
            return None
        return self._tracer.start_span("llm.generate")

    def start_tool_span(self, tool_name: str) -> Any:
        if self._root_span is None:
            return None
        return self._tracer.start_span(
            f"tool.{tool_name}",
            attributes={"tool.name": tool_name},
        )

    def set_error(self, message: str) -> None:
        self._error_message = message

    def end(self) -> None:
        if self._root_span is None:
            return
        if self._error_message:
            self._root_span.set_status(StatusCode.ERROR, self._error_message)
            self._root_span.set_attribute("agentlabkit.status", "error")
        self._root_span.end()
        self._root_span = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AgentRuntime — main public class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AgentRuntime:
    """Core agent runtime — orchestrates LLM calls, tools, guardrails, and memory.

    This class is the single entry-point for all agent operations.  Internally
    it delegates to focused helper modules (:class:`TurnPrep`, :class:`TurnGuards`,
    :class:`SessionManager`, etc.) rather than containing the logic itself.
    """

    def __init__(
        self,
        *,
        settings: AgentSettings,
        gateway: GatewayProtocol,
        tool_registry: ToolRegistry,
        definition_loader: AgentDefinitionLoader | None = None,
        context_manager: ContextManager | None = None,
        session_store: SessionStore | None = None,
        guards_pipeline: GuardsPipeline | None = None,
        skill_registry: SkillRegistry | None = None,
        mcp_client_manager=None,
        handoff_manager: HandoffManager | None = None,
        global_guardrails_repository: GlobalGuardrailsRepository | None = None,
        tracer: Tracer | None = None,
        observability_bridge_factory: Any | None = None,
        memory_module: Any | None = None,
        completion_sink: Callable[[AgentRun], Awaitable[None]] | None = None,
    ) -> None:
        self.settings = settings
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.definition_loader = definition_loader
        self.context_manager = context_manager
        self.session_store = session_store
        self.guards_pipeline = guards_pipeline
        self.global_guardrails_repository = global_guardrails_repository
        self._tracer = tracer
        self._observability_bridge_factory = observability_bridge_factory
        self._memory_module = memory_module
        # Framework-neutral hook: Runtime owns and creates the final snapshot;
        # an application projection may observe it without Runtime importing it.
        self._completion_sink = completion_sink

        # ── Global guardrails state ──────────────────────────────────────
        self.active_global_guardrails_snapshot: GlobalGuardrailsSnapshot | None = None
        self._active_global_guardrails_snapshot_loaded = False
        self._active_global_guardrails_snapshot_lock = asyncio.Lock()
        self._global_guardrail_service = GlobalGuardrailService(
            get_snapshot=lambda: self.active_global_guardrails_snapshot,
            get_block_text=self._global_block_text,
            get_handoff_message=lambda: self.settings.default_handoff_message,
        )

        # ── Voice guardrail evaluator ────────────────────────────────────
        self._voice_evaluator = VoiceGuardrailEvaluator()
        self._voice_evaluator.guards_pipeline = guards_pipeline
        self._voice_evaluator.build_output_guard_metadata = self._build_output_guard_metadata

        # ── Skills ───────────────────────────────────────────────────────
        self._skill_registry = skill_registry or register_builtin_skills(SkillRegistry())
        self._skill_composer = SkillComposer(self._skill_registry)

        # ── Orchestration ────────────────────────────────────────────────
        self._handoff_manager = handoff_manager

        # ── MCP ──────────────────────────────────────────────────────────
        self._mcp_manager = mcp_client_manager
        self._mcp_bridge = None
        if mcp_client_manager is not None:
            from ..mcp.adapter import McpToolAdapter
            from ..mcp.registry_bridge import McpRegistryBridge
            adapter = McpToolAdapter(mcp_client_manager)
            self._mcp_bridge = McpRegistryBridge(
                mcp_client_manager, adapter, self.tool_registry.dynamic_registry,
            )

        # ── Delegated helper modules ─────────────────────────────────────
        self._turn_prep = TurnPrep(
            settings=settings,
            tool_registry=tool_registry,
            definition_loader=definition_loader,
            skill_registry=self._skill_registry,
            mcp_manager=self._mcp_manager,
            mcp_bridge=self._mcp_bridge,
        )
        self._session_mgr = SessionManager(session_store)
        self._turn_guards = TurnGuards(
            guards_pipeline=guards_pipeline,
            global_guardrail_service=self._global_guardrail_service,
            voice_evaluator=self._voice_evaluator,
            settings=settings,
        )
        self._tool_exec = ToolExecution(tool_registry)

        # ── Event bus for lifecycle events ───────────────────────────────
        self._event_bus = EventBus()

    # ── Properties (backward compat) ─────────────────────────────────────

    @property
    def handoff_manager(self) -> HandoffManager | None:
        return self._handoff_manager

    # ── Global guardrails management ─────────────────────────────────────

    async def load_active_global_guardrails_snapshot(self) -> GlobalGuardrailsSnapshot | None:
        if self.global_guardrails_repository is None:
            self.active_global_guardrails_snapshot = None
            self._active_global_guardrails_snapshot_loaded = True
            return None
        self.active_global_guardrails_snapshot = (
            await self.global_guardrails_repository.get_active_snapshot()
        )
        self._active_global_guardrails_snapshot_loaded = True
        return self.active_global_guardrails_snapshot

    async def _ensure_active_global_guardrails_snapshot_loaded(self) -> GlobalGuardrailsSnapshot | None:
        if self._active_global_guardrails_snapshot_loaded:
            return self.active_global_guardrails_snapshot
        async with self._active_global_guardrails_snapshot_lock:
            if self._active_global_guardrails_snapshot_loaded:
                return self.active_global_guardrails_snapshot
            return await self.load_active_global_guardrails_snapshot()

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start MCP connections and sync tools into the registry."""
        await self._ensure_active_global_guardrails_snapshot_loaded()
        if self._mcp_manager is not None:
            await self._mcp_manager.start()
            if self._mcp_bridge is not None:
                await self._mcp_bridge.sync_all()

    async def stop(self) -> None:
        """Stop MCP connections."""
        if self._mcp_manager is not None:
            await self._mcp_manager.stop()

    # ── Observability ────────────────────────────────────────────────────

    def recent_voice_guardrail_samples(self, limit: int = 10) -> list[dict[str, object]]:
        return self._voice_evaluator.recent_samples(limit)

    def recent_global_guardrail_samples(self, limit: int = 10) -> list[dict[str, object]]:
        return self._global_guardrail_service.recent_samples(limit)

    def voice_guardrail_metrics(self) -> dict[str, int | float]:
        return self._voice_evaluator.metrics()

    # ── Event bus ────────────────────────────────────────────────────────

    def subscribe(self, listener) -> callable:
        """Subscribe to agent lifecycle events. Returns an unsubscribe callable."""
        return self._event_bus.subscribe(listener)

    async def _publish_completion(self, run: AgentRun) -> None:
        """Notify projection after Runtime has produced the authoritative snapshot.

        A projection/storage failure is deliberately not an execution failure:
        the terminal RuntimeEvent and returned AgentRun remain the truth.
        """
        if self._completion_sink is None:
            return
        try:
            await self._completion_sink(run)
        except Exception:
            logger.exception("run_projection.completion_sink_failed run_id=%s", run.run_id)

    @staticmethod
    def _stream_snapshot(
        context: ExecutionContext,
        request: AgentTurnRequest,
        terminal_event: AgentTurnStreamEvent | None,
        *,
        status: RunStatus = RunStatus.COMPLETED,
        error: Exception | None = None,
    ) -> AgentRun:
        run = AgentRun(
            run_id=context.run_id,
            trace_id=context.trace_id,
            input=request.user_message,
            session_id=context.session_id,
            target=context.target,
            started_at=context.started_at,
            metadata=dict(context.metadata),
        )
        if status is RunStatus.CANCELLED:
            run.mark_cancelled("stream_cancelled")
        elif status is RunStatus.FAILED:
            run.mark_failed(error_code="RUNTIME_ERROR", error_message=str(error or "stream failed"))
        else:
            output = ""
            usage = None
            if terminal_event is not None:
                output = terminal_event.reply_text or ""
                raw_usage = terminal_event.usage
                if raw_usage is not None:
                    usage = RunUsage(
                        input_tokens=getattr(raw_usage, "input_tokens", 0) or 0,
                        output_tokens=getattr(raw_usage, "output_tokens", 0) or 0,
                        total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
                        cache_write_tokens=getattr(raw_usage, "cache_write_tokens", 0) or 0,
                        cache_read_tokens=getattr(raw_usage, "cache_read_tokens", 0) or 0,
                        estimated_cost=float(getattr(raw_usage, "estimated_cost", 0) or 0),
                    )
            run.mark_completed(output=output, usage=usage)
            if terminal_event is not None:
                run.applied_skills = [skill.skill_key for skill in terminal_event.applied_skills]
                if terminal_event.event_type == "handoff":
                    run.action = "handoff_human"
                    if terminal_event.handoff_target is not None:
                        run.handoff_target_agent = terminal_event.handoff_target.target_agent_key
        return run

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Public API: run_turn / stream_turn
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def run_turn(
        self,
        request: AgentTurnRequest,
        *,
        cancel_token: CancelToken | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> AgentTurnResult:
        """Execute a single agent turn in blocking mode.

        Uses the self-built agent loop (no pydantic-ai). Delegates preparation,
        guards, and session management to the extracted helper modules.

        Args:
            request: The turn request.
            cancel_token: Optional cancellation token.
            execution_context: Optional execution context providing run_id/trace_id.
                When provided (e.g. from ``run()``), the loop uses these identities
                so that ``RuntimeEvent.run_id == AgentRun.run_id``. When omitted,
                ``run_turn`` creates its own identities (legacy path).
        """
        # ── Identity: use ExecutionContext if provided, else create ─────
        if execution_context is not None:
            _run_id = execution_context.run_id
            _trace_id = execution_context.trace_id
        else:
            _run_id = str(uuid4())
            _trace_id = getattr(request, "trace_id", None) or str(uuid4())
        _span_mgr: _TracerSpanManager | None = None
        _obs_bridge = None
        if self._tracer is not None:
            _span_mgr = _TracerSpanManager(
                self._tracer, _trace_id, getattr(request, "agent_key", None),
            )
            _span_mgr.start()
        elif self._observability_bridge_factory is not None:
            _obs_bridge = self._observability_bridge_factory(
                trace_id=_trace_id,
                agent_key=getattr(request, "agent_key", None),
                event_bus=self._event_bus,
            )

        await self._ensure_active_global_guardrails_snapshot_loaded()
        prepared = await self._turn_prep.prepare_turn(request)
        definition = prepared.definition
        effective_settings = prepared.effective_settings
        tool_bindings = prepared.tool_bindings
        auto_tool_names = prepared.auto_tool_names
        applied_skills = prepared.applied_skills

        # ── Emit RunStarted BEFORE guardrails (P0: run boundary) ────────
        _run_lifecycle_started = False
        if execution_context is not None:
            await self._event_bus.emit(RunStarted(
                run_id=_run_id,
                trace_id=_trace_id,
                agent_key=prepared.resolved_request.agent_key or "",
                agent_version=definition.version_number if definition else "",
                input_text=prepared.resolved_request.user_message,
                session_id=prepared.resolved_request.session_id,
                span_id=execution_context.root_span_id,
            ))
            _run_lifecycle_started = True

        # ── Input Guards (delegates to TurnGuards) ──────────────────────
        guard_result = await self._turn_guards.run_input_guards(
            prepared.resolved_request, definition, applied_skills, mode="blocking",
        )
        if guard_result.blocked_result is not None:
            # A guardrail block is a completed business outcome, not a
            # runtime failure. This early return owns the terminal boundary.
            if _run_lifecycle_started:
                guardrail_span_id = uuid4().hex[:16]
                await self._event_bus.emit(GuardrailEvaluated(
                    run_id=_run_id, trace_id=_trace_id, span_id=guardrail_span_id,
                    parent_span_id=execution_context.root_span_id,
                    guardrail_name="input_guard", guardrail_type="input", passed=False,
                ))
                await self._event_bus.emit(GuardrailBlocked(
                    run_id=_run_id, trace_id=_trace_id, span_id=guardrail_span_id,
                    parent_span_id=execution_context.root_span_id,
                    guardrail_name="input_guard", guardrail_type="input", action="block",
                ))
                await self._event_bus.emit(RunCompleted(
                    run_id=_run_id, trace_id=_trace_id,
                    span_id=execution_context.root_span_id,
                    output_text=guard_result.blocked_result.reply_text or "",
                    attributes={"outcome": "blocked", "blocked": True},
                ))
                execution_context.metadata["terminal_emitted"] = True
                if _span_mgr:
                    _span_mgr.end()
                elif _obs_bridge:
                    await _obs_bridge.finalize()
            return guard_result.blocked_result
        resolved_request = guard_result.resolved_request
        input_global_alert_match = guard_result.input_global_alert_match

        # ── Session management (delegates to SessionManager) ─────────────
        restored_snapshot = await self._session_mgr.load_session_snapshot(
            resolved_request, effective_settings,
        )
        resolved_request = self._session_mgr.restore_request_history(
            resolved_request, restored_snapshot,
        )
        resolved_request, _ = await self._prepare_request_context(
            resolved_request, effective_settings,
        )

        # ── Long-term memory injection (optional) ─────────────────────
        if self._memory_module is not None:
            try:
                user_id = resolved_request.user_id or ""
                if user_id:
                    memories = await self._memory_module.retriever.retrieve(
                        query=resolved_request.user_message,
                        user_id=user_id,
                    )
                    if memories:
                        enriched = self._memory_module.injector.inject(
                            memories, list(resolved_request.history),
                        )
                        resolved_request.history = enriched
            except Exception:
                logger.exception("memory.inject_failed")

        # ── Build LLM adapter & loop context ────────────────────────────
        llm = LlmAdapter(self.gateway, settings=effective_settings, request=resolved_request)
        tool_schemas = self._build_tool_schemas(auto_tool_names, tool_bindings, effective_settings)
        context = LoopContext(
            system_prompt=build_system_prompt(effective_settings, resolved_request),
            messages=list(resolved_request.history),
            tools=tool_schemas,
        )

        deps = AgentRunDeps(
            request=resolved_request,
            session_state=self._build_session_state(resolved_request),
            trace_id=resolved_request.trace_id,
            definition=definition,
        )
        config = LoopConfig(
            tool_executor=self._make_tool_executor(resolved_request, effective_settings, deps, prepared),
        )

        try:
            loop_result = await run_agent_loop(
                prompts=[AgentMessage(role=AgentRole.USER, content=resolved_request.user_message)],
                context=context,
                config=config,
                llm=llm,
                event_bus=self._event_bus,
                cancel=cancel_token,
                run_id=_run_id,
                trace_id=_trace_id,
                agent_key=resolved_request.agent_key or "",
                skip_run_lifecycle=_run_lifecycle_started,
                root_span_id=execution_context.root_span_id if execution_context else None,
            )
        except AgentError as exc:
            if _span_mgr:
                _span_mgr.set_error("AgentError")
            elif _obs_bridge:
                _obs_bridge.set_error("AgentError")
            if _run_lifecycle_started:
                await self._event_bus.emit(RunFailed(
                    run_id=_run_id, trace_id=_trace_id,
                    span_id=execution_context.root_span_id,
                    error_code="AGENT_ERROR", error_message=exc.message,
                ))
                execution_context.metadata["terminal_emitted"] = True
            raise
        except Exception as exc:
            if _span_mgr:
                _span_mgr.set_error(str(exc))
            elif _obs_bridge:
                _obs_bridge.set_error(str(exc))
            if _run_lifecycle_started:
                await self._event_bus.emit(RunFailed(
                    run_id=_run_id, trace_id=_trace_id,
                    span_id=execution_context.root_span_id,
                    error_code=type(exc).__name__, error_message=str(exc),
                ))
                execution_context.metadata["terminal_emitted"] = True
            raise AgentError(
                AgentErrorCode.RUNTIME_ERROR,
                str(exc),
                model=resolved_request.model,
                trace_id=resolved_request.trace_id,
            ) from exc
        finally:
            if _span_mgr:
                try:
                    _span_mgr.end()
                except Exception:
                    logger.exception("observability.span_end_failed")
            elif _obs_bridge:
                try:
                    await _obs_bridge.finalize()
                except Exception:
                    logger.exception("observability.finalize_failed")

        # ── Build decision from loop result ─────────────────────────────
        final = loop_result.final_directive
        decision = AgentDecision(
            reply_text=final.reply_text if final else "",
            should_handoff=final.should_handoff if final else False,
            handoff_reason=final.handoff_reason if final else None,
            handoff_target_type=final.handoff_target_type if final else None,
            handoff_target_agent=final.handoff_target_agent if final else None,
        )

        # ── Post-processing (delegates to extracted modules) ────────────
        output = await self._post_process_turn(
            decision=decision,
            deps=deps,
            raw_messages_input=loop_result.messages,
            loop_usage=loop_result.usage,
            resolved_request=resolved_request,
            definition=definition,
            effective_settings=effective_settings,
            restored_snapshot=restored_snapshot,
            applied_skills=applied_skills,
            input_global_alert_match=input_global_alert_match,
            original_request=request,
        )

        if isinstance(output, AgentTurnResult):
            return output  # agent-to-agent handoff short-circuit

        # ── Long-term memory extraction (optional) ────────────────────
        if self._memory_module is not None:
            try:
                user_id = resolved_request.user_id or ""
                if user_id and loop_result.messages:
                    await self._extract_memories(
                        user_id=user_id,
                        session_id=resolved_request.session_id,
                        messages=loop_result.messages,
                    )
            except Exception:
                logger.exception("memory.extract_failed")

        await self._session_mgr.save_session_snapshot(
            request=resolved_request,
            result=output.result,
            snapshot=output.session_snapshot_to_save,
            settings=effective_settings,
        )
        return output.result

    async def run(
        self,
        request: AgentTurnRequest,
        *,
        cancel_token: CancelToken | None = None,
    ) -> AgentRun:
        """Execute a single agent turn and return an AgentRun.

        This is the v2 API that returns a unified AgentRun object instead
        of a scattered AgentTurnResult. The underlying execution is identical
        to run_turn — this method wraps it and builds the AgentRun.

        Runtime is the sole creator of run_id and trace_id (via ExecutionContext).
        All downstream components receive identity from the context — they must
        never generate their own.

        Returns:
            An :class:`AgentRun` with status, usage, tool info, etc.
        """
        # ── Runtime creates identity (1.2) ────────────────────────────
        # Build RunTarget first so ExecutionContext carries it.
        _target = RunTarget(
            type="agent",
            agent_key=getattr(request, "agent_key", None),
            agent_version=str(getattr(request, "agent_version", "")) if getattr(request, "agent_version", None) else None,
        )
        ctx = ExecutionContext(
            session_id=request.session_id or "",
            agent_key=_target.agent_key,
            agent_version=_target.agent_version,
            target=_target,
        )

        run = AgentRun(
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            input=request.user_message,
            session_id=ctx.session_id,
            target=_target,
            started_at=ctx.started_at,
        )

        # ── run_turn emits RunStarted before guardrails ──
        # Terminal events (RunCompleted/RunFailed) are emitted HERE in run()
        # to guarantee exactly-once emission — the loop skips them when
        # skip_run_lifecycle=True.
        try:
            result = await self.run_turn(
                request,
                cancel_token=cancel_token,
                execution_context=ctx,
            )
        except asyncio.CancelledError as exc:
            # Cancellation is a first-class terminal state, never a failure.
            await self._event_bus.emit(RunCancelled(
                run_id=ctx.run_id,
                trace_id=ctx.trace_id,
                span_id=ctx.root_span_id,
                reason="run_cancelled",
            ))
            run.mark_cancelled("run_cancelled")
            await self._publish_completion(run)
            return run
        except Exception as exc:
            # Emit RunFailed (P0: terminal invariant — exactly one terminal)
            error_code = "AGENT_ERROR" if isinstance(exc, AgentError) else type(exc).__name__
            error_message = exc.message if isinstance(exc, AgentError) else str(exc)
            if not ctx.metadata.pop("terminal_emitted", False):
                await self._event_bus.emit(RunFailed(
                    run_id=ctx.run_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.root_span_id,
                    error_code=error_code,
                    error_message=error_message,
                ))
            run.status = RunStatus.FAILED
            run.error = RunError(
                code=error_code,
                message=error_message,
            )
            run.finished_at = datetime.now(timezone.utc)
            await self._publish_completion(run)
            return run

        # run_turn owns the terminal for an early guardrail completion;
        # normal turns are completed here after the result is produced.
        if not ctx.metadata.pop("terminal_emitted", False):
            await self._event_bus.emit(RunCompleted(
                run_id=ctx.run_id,
                trace_id=ctx.trace_id,
                span_id=ctx.root_span_id,
                output_text=result.reply_text or "",
            ))

        # Build RunUsage from the turn result
        usage = None
        if result.usage:
            usage = RunUsage(
                input_tokens=getattr(result.usage, "input_tokens", 0) or 0,
                output_tokens=getattr(result.usage, "output_tokens", 0) or 0,
                total_tokens=getattr(result.usage, "total_tokens", 0) or 0,
                cache_write_tokens=getattr(result.usage, "cache_write_tokens", 0) or 0,
                cache_read_tokens=getattr(result.usage, "cache_read_tokens", 0) or 0,
                estimated_cost=float(getattr(result.usage, "estimated_cost", 0) or 0),
                tool_call_count=len(result.tool_events),
            )

        # Identity comes from ExecutionContext — no post-hoc override needed.
        run.output = result.reply_text
        run.action = result.action.value if hasattr(result.action, "value") else str(result.action)
        run.handoff_target_agent = getattr(result.handoff_target, "target_agent_key", None)
        run.orchestration_chain = result.orchestration_chain or []
        run.tool_names = [te.tool_name for te in result.tool_events]
        run.tool_call_count = len(result.tool_events)
        run.applied_skills = [s.skill_key for s in result.applied_skills]

        if result.error:
            run.mark_failed(
                error_code=result.error.code,
                error_message=result.error.message,
                provider=result.error.provider,
                model=result.error.model,
            )
        else:
            run.mark_completed(output=result.reply_text, usage=usage)
        await self._publish_completion(run)

        return run

    async def stream(
        self,
        request: AgentTurnRequest,
        *,
        cancel_token: CancelToken | None = None,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Stream one real execution with Runtime-owned identity.

        This is the v2 streaming boundary.  ``stream_turn`` remains the lower
        level compatibility API; callers that need an execution boundary use
        this method so they never manufacture ``run_id``/``trace_id``.
        """
        target = RunTarget(
            type="agent", agent_key=request.agent_key,
            agent_version=str(request.agent_version) if request.agent_version else None,
        )
        context = ExecutionContext(
            session_id=request.session_id or "",
            agent_key=target.agent_key,
            agent_version=target.agent_version,
            target=target,
            metadata=dict(getattr(request, "metadata", {}) or {}),
        )
        request = request.model_copy(update={"trace_id": context.trace_id})
        terminal_event: AgentTurnStreamEvent | None = None
        try:
            async for event in self.stream_turn(
                request, cancel_token=cancel_token, execution_context=context,
            ):
                event.run_id = context.run_id
                # The context is authoritative even if request preparation cloned data.
                event.trace_id = context.trace_id
                if event.event_type in {"reply_completed", "handoff"}:
                    terminal_event = event
                yield event
        except asyncio.CancelledError:
            run = self._stream_snapshot(context, request, terminal_event, status=RunStatus.CANCELLED)
            await self._publish_completion(run)
            raise
        except Exception as exc:
            run = self._stream_snapshot(context, request, terminal_event, status=RunStatus.FAILED, error=exc)
            await self._publish_completion(run)
            raise
        else:
            run = self._stream_snapshot(context, request, terminal_event)
            await self._publish_completion(run)

    async def stream_turn(
        self,
        request: AgentTurnRequest,
        *,
        cancel_token: CancelToken | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Execute a single agent turn in streaming mode.

        This method directly calls the gateway for streaming (no pydantic-ai).
        It delegates preparation, guards, and session management to the split modules.

        Args:
            request: The turn request.
            cancel_token: Optional cancellation token.
            execution_context: Optional execution context. When provided, v2
                semantic events (RunStarted/RunCompleted/etc.) are emitted with
                the context's identity. When omitted, the streaming path creates
                its own trace_id but does not emit v2 run lifecycle events.
        """
        await self._ensure_active_global_guardrails_snapshot_loaded()
        prepared = await self._turn_prep.prepare_turn(request)
        definition = prepared.definition
        effective_settings = prepared.effective_settings
        tool_bindings = prepared.tool_bindings
        auto_tool_names = prepared.auto_tool_names
        applied_skills = prepared.applied_skills

        # ── Identity: use ExecutionContext if provided ──────────────────
        _run_id = execution_context.run_id if execution_context else ""
        _trace_id = (
            execution_context.trace_id
            if execution_context
            else getattr(prepared.resolved_request, "trace_id", None) or str(uuid4())
        )
        _run_started = False
        _terminal_emitted = False

        async def _emit_run_terminal(*, status: str = "completed", **kwargs) -> None:
            """Emit the terminal v2 event for the run (exactly once)."""
            nonlocal _terminal_emitted
            if _terminal_emitted or not _run_started:
                return
            _terminal_emitted = True
            if status == "completed":
                await self._event_bus.emit(RunCompleted(
                    run_id=_run_id, trace_id=_trace_id, **kwargs,
                ))
            elif status == "failed":
                await self._event_bus.emit(RunFailed(
                    run_id=_run_id, trace_id=_trace_id, **kwargs,
                ))
            elif status == "cancelled":
                await self._event_bus.emit(RunCancelled(
                    run_id=_run_id, trace_id=_trace_id, **kwargs,
                ))

        # Create observability before RunStarted so the root event is not lost.
        _span_mgr: _TracerSpanManager | None = None
        _obs_bridge = None
        if self._tracer is not None:
            _span_mgr = _TracerSpanManager(
                self._tracer, _trace_id, getattr(prepared.resolved_request, "agent_key", None),
            )
            _span_mgr.start()
        elif self._observability_bridge_factory is not None:
            _obs_bridge = self._observability_bridge_factory(
                trace_id=_trace_id,
                agent_key=getattr(prepared.resolved_request, "agent_key", None),
                event_bus=self._event_bus,
            )

        # ── Emit RunStarted BEFORE guardrails (P0: run boundary) ────────
        if execution_context:
            await self._event_bus.emit(RunStarted(
                run_id=_run_id,
                trace_id=_trace_id,
                agent_key=prepared.resolved_request.agent_key or "",
                agent_version=definition.version_number if definition else "",
                input_text=prepared.resolved_request.user_message,
                session_id=prepared.resolved_request.session_id,
                span_id=execution_context.root_span_id,
            ))
            _run_started = True

        async def _finalize_obs(*, terminal_status: str | None = None, **terminal_kwargs: Any) -> None:
            # The terminal event must precede the bridge flush so the projector
            # can close the root span and publish a complete TraceEnvelope.
            if terminal_status is not None:
                await _emit_run_terminal(status=terminal_status, **terminal_kwargs)
            if _span_mgr is not None:
                try:
                    _span_mgr.end()
                except Exception:
                    logger.exception("observability.span_end_failed trace_id=%s", _trace_id)
            elif _obs_bridge is not None:
                # TurnStartEvent is emitted only after input guards pass;
                # guardrail-only runs intentionally contain no fake Agent span.
                await self._event_bus.emit(TurnEndEvent())
                try:
                    await _obs_bridge.finalize()
                except Exception:
                    logger.exception("observability.finalize_failed trace_id=%s", _trace_id)

        # ── Input Guards (delegates to TurnGuards) ──────────────────────
        guard_result = await self._turn_guards.run_input_guards(
            prepared.resolved_request, definition, applied_skills, mode="streaming",
        )
        if guard_result.stream_blocked_event is not None:
            yield guard_result.stream_blocked_event
            guardrail_span_id = uuid4().hex[:16]
            await self._event_bus.emit(GuardrailEvaluated(
                run_id=_run_id, trace_id=_trace_id, span_id=guardrail_span_id,
                parent_span_id=execution_context.root_span_id if execution_context else None,
                guardrail_name="input_guard", guardrail_type="input", passed=False,
            ))
            await self._event_bus.emit(GuardrailBlocked(
                run_id=_run_id, trace_id=_trace_id, span_id=guardrail_span_id,
                parent_span_id=execution_context.root_span_id if execution_context else None,
                guardrail_name="input_guard", guardrail_type="input", action="block",
            ))
            await _finalize_obs(terminal_status="completed", output_text="")
            return
        resolved_request = guard_result.resolved_request
        input_global_alert_match = guard_result.input_global_alert_match
        if _obs_bridge is not None:
            await self._event_bus.emit(TurnStartEvent())

        # ── Session management (delegates to SessionManager) ─────────────
        restored_snapshot = await self._session_mgr.load_session_snapshot(
            resolved_request, effective_settings,
        )
        resolved_request = self._session_mgr.restore_request_history(
            resolved_request, restored_snapshot,
        )
        resolved_request, _ = await self._prepare_request_context(
            resolved_request, effective_settings,
        )
        deps = AgentRunDeps(
            request=resolved_request,
            session_state=self._build_session_state(resolved_request),
            trace_id=resolved_request.trace_id,
            definition=definition,
        )
        if resolved_request.agent_key:
            yield AgentTurnStreamEvent(
                event_type="turn_context",
                session_id=resolved_request.session_id,
                trace_id=resolved_request.trace_id,
                agent_key=resolved_request.agent_key,
                agent_version=definition.version_number if definition else resolved_request.agent_version,
                applied_skills=applied_skills,
            )

        # ── Long-term memory injection (optional) ─────────────────────
        if self._memory_module is not None:
            try:
                user_id = resolved_request.user_id or ""
                if user_id:
                    memories = await self._memory_module.retriever.retrieve(
                        query=resolved_request.user_message,
                        user_id=user_id,
                    )
                    if memories:
                        enriched = self._memory_module.injector.inject(
                            memories, list(resolved_request.history),
                        )
                        resolved_request.history = enriched
            except Exception:
                logger.exception("memory.inject_failed")

        # Build LLM adapter & context for streaming
        llm = LlmAdapter(self.gateway, settings=effective_settings, request=resolved_request)
        tool_schemas = self._build_tool_schemas(auto_tool_names, tool_bindings, effective_settings)
        system_prompt = build_system_prompt(effective_settings, resolved_request)
        stream_messages: list[AgentMessage] = list(resolved_request.history)
        turn_start_index = len(stream_messages)
        stream_messages.append(AgentMessage(role=AgentRole.USER, content=resolved_request.user_message))
        stream_usage = UsageInfo()

        voice_handler = VoiceStreamHandler(
            turn_guards=self._turn_guards,
            request=resolved_request,
            definition=definition,
        )
        pending_reply_deltas: list[str] = []
        try:
            for _ in range(_MAX_STREAM_TOOL_ROUNDS):
                accumulated = ""
                completed_text: str | None = None
                usage: UsageInfo | None = None
                conversation = self._messages_to_conversation_tuple(stream_messages)
                if _obs_bridge:
                    await self._event_bus.emit(MessageStartEvent(
                        message=AgentMessage(role=AgentRole.ASSISTANT, content=""),
                    ))
                _llm_span = _span_mgr.start_llm_span() if _span_mgr else None
                try:
                    async for stream_delta in llm.generate_stream(
                        system_prompt=system_prompt,
                        conversation=conversation,
                        tools=tool_schemas,
                    ):
                        if stream_delta.delta:
                            delta_text = stream_delta.delta
                            accumulated = stream_delta.full_text
                            pending_reply_deltas.extend(
                                await voice_handler.process_delta(delta_text),
                            )
                        if stream_delta.is_done:
                            completed_text = stream_delta.full_text
                            usage = stream_delta.usage
                            pending_reply_deltas.extend(await voice_handler.flush())
                except AgentError as exc:
                    if _span_mgr:
                        _span_mgr.set_error(exc.message or "AgentError")
                    elif _obs_bridge:
                        _obs_bridge.set_error(exc.message or "AgentError")
                    await self._session_mgr.best_effort_save_on_error(
                        request=resolved_request, snapshot=restored_snapshot, settings=effective_settings,
                    )
                    raise
                except Exception as exc:
                    from llm_gateway import GatewayError

                    if _span_mgr:
                        _span_mgr.set_error(str(exc))
                    elif _obs_bridge:
                        _obs_bridge.set_error(str(exc))
                    await self._session_mgr.best_effort_save_on_error(
                        request=resolved_request, snapshot=restored_snapshot, settings=effective_settings,
                    )
                    if isinstance(exc, GatewayError):
                        raise AgentError(
                            AgentErrorCode.GATEWAY_ERROR,
                            exc.message,
                            model=resolved_request.model,
                            trace_id=resolved_request.trace_id,
                        ) from exc
                    raise AgentError(
                        AgentErrorCode.RUNTIME_ERROR,
                        str(exc),
                        model=resolved_request.model,
                        trace_id=resolved_request.trace_id,
                    ) from exc

                directive_text = completed_text or accumulated or ""
                directive = llm.parse_response(directive_text)
                if _obs_bridge:
                    await self._event_bus.emit(MessageEndEvent(
                        message=AgentMessage(role=AgentRole.ASSISTANT, content=directive_text),
                        usage=usage,
                    ))
                if _llm_span is not None:
                    _llm_span.end()
                if isinstance(directive, ToolDirective):
                    self._ensure_tool_allowed(directive.tool_name, auto_tool_names)
                    started_tool_event = self._tool_exec.build_tool_started_event(
                        directive.tool_name, directive.arguments,
                    )
                    yield AgentTurnStreamEvent(
                        event_type="tool_call",
                        session_id=resolved_request.session_id,
                        trace_id=resolved_request.trace_id,
                        reply_text=directive.reply_text,
                        tool_name=directive.tool_name,
                        tool_arguments=dict(directive.arguments),
                        tool_event=started_tool_event,
                    )
                    if _obs_bridge:
                        await self._event_bus.emit(ToolExecutionStartEvent(
                            tool_name=directive.tool_name,
                            args=dict(directive.arguments),
                        ))
                    _tool_span = _span_mgr.start_tool_span(directive.tool_name) if _span_mgr else None
                    recorded_before = len(deps.tool_events)

                    # Streaming delegation
                    delegate_handler = self.tool_registry.dynamic_registry.get_handler(
                        directive.tool_name
                    )
                    if (
                        directive.tool_name == "delegate_to_agent"
                        and isinstance(delegate_handler, DelegateToAgentTool)
                    ):
                        tool_output = ""
                        async for delegation_event in self._tool_exec.execute_streaming_delegate_tool_call(
                            request=resolved_request,
                            settings=effective_settings,
                            deps=deps,
                            delegate_handler=delegate_handler,
                            arguments=dict(directive.arguments),
                            allowed_tool_names=auto_tool_names,
                            tool_bindings=tool_bindings,
                        ):
                            if delegation_event.event_type == "delegation_delta":
                                yield delegation_event
                            elif delegation_event.event_type == "reply_completed":
                                tool_output = delegation_event.reply_text or ""
                        stream_usage = self._merge_usage(stream_usage, usage)
                        stream_usage = self._drain_delegation_usage(stream_usage, deps)
                    else:
                        tool_output = await self._tool_exec.execute_tool_call(
                            request=resolved_request,
                            settings=effective_settings,
                            deps=deps,
                            tool_name=directive.tool_name,
                            arguments=dict(directive.arguments),
                            allowed_tool_names=auto_tool_names,
                            tool_bindings=tool_bindings,
                            guards_pipeline=self.guards_pipeline,
                        )
                        stream_usage = self._merge_usage(stream_usage, usage)
                        stream_usage = self._drain_delegation_usage(stream_usage, deps)

                    if _obs_bridge:
                        await self._event_bus.emit(ToolExecutionEndEvent(
                            tool_name=directive.tool_name,
                            result=tool_output[:200] if tool_output else "",
                            is_error=False,
                        ))
                    if _tool_span is not None:
                        _tool_span.end()

                    for tool_event in deps.tool_events[recorded_before:]:
                        yield AgentTurnStreamEvent(
                            event_type="tool_result",
                            session_id=resolved_request.session_id,
                            trace_id=resolved_request.trace_id,
                            tool_name=tool_event.tool_name,
                            tool_arguments=dict(tool_event.arguments),
                            tool_event=tool_event.model_copy(deep=True),
                        )

                    stream_messages.append(
                        AgentMessage(
                            role=AgentRole.ASSISTANT,
                            content=directive.reply_text or "",
                            name=directive.tool_name,
                        )
                    )
                    stream_messages.append(
                        AgentMessage(
                            role=AgentRole.TOOL,
                            content=tool_output,
                            name=directive.tool_name,
                        )
                    )
                    continue

                total_usage = self._merge_usage(stream_usage, usage)

                # Voice guardrail handoff takes precedence
                if voice_handler.should_handoff:
                    # Check if voice guardrail targets an agent (not just human)
                    if (
                        voice_handler.handoff_outcome is not None
                        and voice_handler.handoff_outcome.handoff_target_type == "agent"
                        and self._handoff_manager is not None
                    ):
                        voice_handoff_target = HandoffTarget(
                            target_type="agent",
                            reason=voice_handler.handoff_reason,
                        )
                        definition_handoff_policy = (
                            dict(definition.handoff_policy) if definition else None
                        )
                        resolution = await self._handoff_manager.resolve_handoff(
                            voice_handoff_target,
                            handoff_policy=definition_handoff_policy,
                        )
                        if resolution.action is AgentAction.HANDOFF_AGENT:
                            # Stream agent handoff from voice trigger
                            if self._handoff_manager.can_stream:
                                handoff_stream_usage = None
                                sub_reply_text = ""
                                sub_raw_messages: list = []
                                sub_handoff_target: HandoffTarget | None = None

                                async for sub_event in self._handoff_manager.stream_execute_agent_handoff(
                                    resolution,
                                    request=resolved_request,
                                    history=resolved_request.history,
                                ):
                                    if sub_event.event_type == "reply_delta" and sub_event.delta:
                                        yield AgentTurnStreamEvent(
                                            event_type="delegation_delta",
                                            session_id=resolved_request.session_id,
                                            trace_id=resolved_request.trace_id,
                                            delta=sub_event.delta,
                                            delegation_agent_key=resolution.target_agent_key,
                                        )
                                    elif sub_event.event_type == "reply_completed":
                                        sub_reply_text = sub_event.reply_text or ""
                                        handoff_stream_usage = self._merge_usage(
                                            handoff_stream_usage, sub_event.usage,
                                        )
                                        sub_raw_messages = list(sub_event.raw_messages or [])
                                        if sub_event.handoff_target:
                                            sub_handoff_target = sub_event.handoff_target
                                    elif sub_event.event_type == "handoff":
                                        handoff_stream_usage = self._merge_usage(
                                            handoff_stream_usage, sub_event.usage,
                                        )
                                        if sub_event.reply_text:
                                            sub_reply_text = sub_event.reply_text
                                        if sub_event.handoff_target:
                                            sub_handoff_target = sub_event.handoff_target

                                total_usage = self._merge_usage(total_usage, handoff_stream_usage)
                                handoff_event = AgentTurnStreamEvent(
                                    event_type="handoff",
                                    session_id=resolved_request.session_id,
                                    trace_id=resolved_request.trace_id,
                                    reply_text=sub_reply_text,
                                    handoff_reason=voice_handler.handoff_reason,
                                    usage=total_usage,
                                    raw_messages=sub_raw_messages,
                                    handoff_target=sub_handoff_target or HandoffTarget(
                                        target_type="agent",
                                        target_agent_key=resolution.target_agent_key,
                                        reason=voice_handler.handoff_reason,
                                    ),
                                    applied_skills=applied_skills,
                                    agent_key=resolved_request.agent_key,
                                    agent_version=definition.version_number if definition else None,
                                )
                                await self._session_mgr.save_session_snapshot(
                                    request=resolved_request,
                                    result=self._stream_event_to_result(
                                        request=resolved_request, definition=definition,
                                        event=handoff_event, action=AgentAction.HANDOFF_AGENT,
                                        handoff_target=handoff_event.handoff_target,
                                        responding_agent_key=resolution.target_agent_key,
                                    ),
                                    snapshot=restored_snapshot, settings=effective_settings,
                                )
                                await _finalize_obs(terminal_status="completed")
                                yield handoff_event
                                return

                            # Blocking agent handoff from voice
                            handoff_result = await self._handoff_manager.execute_agent_handoff(
                                resolution,
                                request=resolved_request,
                                history=resolved_request.history,
                            )
                            total_usage = self._merge_usage(total_usage, handoff_result.usage)
                            handoff_event = AgentTurnStreamEvent(
                                event_type="handoff",
                                session_id=resolved_request.session_id,
                                trace_id=resolved_request.trace_id,
                                reply_text=handoff_result.reply_text,
                                handoff_reason=voice_handler.handoff_reason,
                                usage=total_usage,
                                raw_messages=list(handoff_result.raw_messages),
                                handoff_target=handoff_result.handoff_target,
                                applied_skills=applied_skills,
                                agent_key=resolved_request.agent_key,
                                agent_version=definition.version_number if definition else None,
                            )
                            await self._session_mgr.save_session_snapshot(
                                request=resolved_request,
                                result=self._stream_event_to_result(
                                    request=resolved_request, definition=definition,
                                    event=handoff_event, action=AgentAction.HANDOFF_AGENT,
                                    handoff_target=handoff_result.handoff_target,
                                    responding_agent_key=handoff_result.responding_agent_key,
                                    orchestration_chain=handoff_result.orchestration_chain,
                                ),
                                snapshot=restored_snapshot, settings=effective_settings,
                            )
                            await _finalize_obs(terminal_status="completed")
                            yield handoff_event
                            return

                    # Default: human handoff from voice guardrail
                    handoff_event = AgentTurnStreamEvent(
                        event_type="handoff",
                        session_id=resolved_request.session_id,
                        trace_id=resolved_request.trace_id,
                        reply_text=effective_settings.default_handoff_message,
                        handoff_reason=voice_handler.handoff_reason,
                        usage=total_usage,
                        raw_messages=[
                            AgentMessage(
                                role=AgentRole.ASSISTANT,
                                content=effective_settings.default_handoff_message,
                            )
                        ],
                        applied_skills=applied_skills,
                        agent_key=resolved_request.agent_key,
                        agent_version=definition.version_number if definition else None,
                        handoff_target=HandoffTarget(
                            target_type="human",
                            reason=voice_handler.handoff_reason,
                        ),
                    )
                    await self._session_mgr.save_session_snapshot(
                        request=resolved_request,
                        result=self._stream_event_to_result(
                            request=resolved_request, definition=definition,
                            event=handoff_event, action=AgentAction.HANDOFF_HUMAN,
                            handoff_target=handoff_event.handoff_target,
                        ),
                        snapshot=restored_snapshot, settings=effective_settings,
                    )
                    await _finalize_obs(terminal_status="completed")
                    yield handoff_event
                    return

                # Model-driven agent handoff
                if (
                    directive.should_handoff
                    and directive.handoff_target_type == "agent"
                    and directive.handoff_target_agent
                    and self._handoff_manager is not None
                ):
                    handoff_target = HandoffTarget(
                        target_type="agent",
                        target_agent_key=directive.handoff_target_agent,
                        reason=directive.handoff_reason,
                    )
                    definition_handoff_policy = (
                        dict(definition.handoff_policy) if definition else None
                    )
                    resolution = await self._handoff_manager.resolve_handoff(
                        handoff_target,
                        handoff_policy=definition_handoff_policy,
                    )
                    if resolution.action is AgentAction.HANDOFF_AGENT:
                        # Emit any pending reply deltas from the parent agent
                        for delta in pending_reply_deltas:
                            yield AgentTurnStreamEvent(
                                event_type="reply_delta",
                                session_id=resolved_request.session_id,
                                trace_id=resolved_request.trace_id,
                                delta=delta,
                            )

                        # Prefer streaming handoff when available
                        if self._handoff_manager.can_stream:
                            handoff_stream_usage = None
                            sub_reply_text = ""
                            sub_raw_messages: list = []
                            sub_chain: list[str] = []
                            sub_agent_key: str | None = resolution.target_agent_key
                            sub_handoff_target: HandoffTarget | None = None

                            async for sub_event in self._handoff_manager.stream_execute_agent_handoff(
                                resolution,
                                request=resolved_request,
                                history=resolved_request.history,
                            ):
                                if sub_event.event_type == "reply_delta" and sub_event.delta:
                                    yield AgentTurnStreamEvent(
                                        event_type="delegation_delta",
                                        session_id=resolved_request.session_id,
                                        trace_id=resolved_request.trace_id,
                                        delta=sub_event.delta,
                                        delegation_agent_key=resolution.target_agent_key,
                                    )
                                elif sub_event.event_type == "reply_completed":
                                    sub_reply_text = sub_event.reply_text or ""
                                    handoff_stream_usage = self._merge_usage(
                                        handoff_stream_usage, sub_event.usage,
                                    )
                                    sub_raw_messages = list(sub_event.raw_messages or [])
                                    if sub_event.handoff_target:
                                        sub_handoff_target = sub_event.handoff_target
                                elif sub_event.event_type == "handoff":
                                    # Nested handoff from sub-agent
                                    handoff_stream_usage = self._merge_usage(
                                        handoff_stream_usage, sub_event.usage,
                                    )
                                    if sub_event.reply_text:
                                        sub_reply_text = sub_event.reply_text
                                    if sub_event.handoff_target:
                                        sub_handoff_target = sub_event.handoff_target

                            total_usage = self._merge_usage(
                                self._merge_usage(stream_usage, usage),
                                handoff_stream_usage,
                            )
                            handoff_event = AgentTurnStreamEvent(
                                event_type="handoff",
                                session_id=resolved_request.session_id,
                                trace_id=resolved_request.trace_id,
                                reply_text=sub_reply_text,
                                handoff_reason=resolution.reason or directive.handoff_reason,
                                usage=total_usage,
                                raw_messages=sub_raw_messages,
                                handoff_target=sub_handoff_target or HandoffTarget(
                                    target_type="agent",
                                    target_agent_key=resolution.target_agent_key,
                                    reason=resolution.reason,
                                ),
                                applied_skills=applied_skills,
                                agent_key=resolved_request.agent_key,
                                agent_version=definition.version_number if definition else None,
                            )
                            await self._session_mgr.save_session_snapshot(
                                request=resolved_request,
                                result=self._stream_event_to_result(
                                    request=resolved_request, definition=definition,
                                    event=handoff_event, action=AgentAction.HANDOFF_AGENT,
                                    handoff_target=handoff_event.handoff_target,
                                    responding_agent_key=sub_agent_key,
                                    orchestration_chain=sub_chain,
                                ),
                                snapshot=restored_snapshot, settings=effective_settings,
                            )
                            await _finalize_obs(terminal_status="completed")
                            yield handoff_event
                            return

                        # Blocking fallback (no stream_runner available)
                        handoff_result = await self._handoff_manager.execute_agent_handoff(
                            resolution,
                            request=resolved_request,
                            history=resolved_request.history,
                        )
                        total_usage = self._merge_usage(
                            self._merge_usage(stream_usage, usage),
                            handoff_result.usage,
                        )
                        handoff_event = AgentTurnStreamEvent(
                            event_type="handoff",
                            session_id=resolved_request.session_id,
                            trace_id=resolved_request.trace_id,
                            reply_text=handoff_result.reply_text,
                            handoff_reason=resolution.reason or directive.handoff_reason,
                            usage=total_usage,
                            raw_messages=list(handoff_result.raw_messages),
                            handoff_target=handoff_result.handoff_target,
                            applied_skills=applied_skills,
                            agent_key=resolved_request.agent_key,
                            agent_version=definition.version_number if definition else None,
                        )
                        await self._session_mgr.save_session_snapshot(
                            request=resolved_request,
                            result=self._stream_event_to_result(
                                request=resolved_request, definition=definition,
                                event=handoff_event, action=AgentAction.HANDOFF_AGENT,
                                handoff_target=handoff_result.handoff_target,
                                responding_agent_key=handoff_result.responding_agent_key,
                                orchestration_chain=handoff_result.orchestration_chain,
                            ),
                            snapshot=restored_snapshot, settings=effective_settings,
                        )
                        await _finalize_obs(terminal_status="completed")
                        yield handoff_event
                        return

                handoff = await self.tool_registry.apply_handoff_policy(
                    directive.handoff_reason if directive.should_handoff else None,
                    session_state=deps.session_state,
                    enabled=effective_settings.enable_handoff_policy,
                )
                stream_messages.append(AgentMessage(role=AgentRole.ASSISTANT, content=directive.reply_text))
                raw_messages = MessageBuilder.normalize_raw_messages(stream_messages[turn_start_index:])

                final_reply_text = (
                    effective_settings.default_handoff_message
                    if handoff.should_handoff
                    else directive.reply_text
                )
                suppress_reply_deltas = False
                if voice_handler.is_active and not handoff.should_handoff:
                    if voice_handler.was_modified:
                        final_reply_text = voice_handler.visible_reply
                        raw_messages = MessageBuilder.replace_terminal_assistant_message(
                            raw_messages, final_reply_text,
                        )
                elif self.guards_pipeline is not None:
                    output_result = await self.guards_pipeline.run_output_guards(
                        message=final_reply_text,
                        session_id=resolved_request.session_id,
                        trace_id=resolved_request.trace_id or "",
                        metadata=self._build_output_guard_metadata(
                            request=resolved_request, segment=final_reply_text,
                        ),
                    )
                    if output_result.final_verdict is GuardVerdict.BLOCK:
                        final_reply_text = self.guards_pipeline.block_response
                    elif output_result.modified_text is not None:
                        final_reply_text = output_result.modified_text

                output_global_match = None
                if not handoff.should_handoff:
                    output_global_match = await self._turn_guards.evaluate_global_guardrails(
                        request=resolved_request, stage="output", content=final_reply_text,
                    )
                    if output_global_match is not None:
                        self._global_guardrail_service.record_match(
                            request=resolved_request, match=output_global_match,
                        )
                        if output_global_match.rule.action == "block":
                            final_reply_text = self._global_block_text()
                            suppress_reply_deltas = True
                            raw_messages = [
                                AgentMessage(
                                    role=AgentRole.ASSISTANT,
                                    content=final_reply_text,
                                    metadata=self._build_global_guardrail_metadata(output_global_match),
                                )
                            ]
                        elif output_global_match.rule.action == "handoff":
                            handoff_event = self._global_guardrail_handoff_stream_event(
                                request=resolved_request, definition=definition,
                                match=output_global_match,
                                handoff_text=effective_settings.default_handoff_message,
                                usage=total_usage, applied_skills=applied_skills,
                            )
                            await self._session_mgr.save_session_snapshot(
                                request=resolved_request,
                                result=self._stream_event_to_result(
                                    request=resolved_request, definition=definition,
                                    event=handoff_event, action=AgentAction.HANDOFF_HUMAN,
                                    handoff_target=handoff_event.handoff_target,
                                ),
                                snapshot=restored_snapshot, settings=effective_settings,
                            )
                            await _finalize_obs(terminal_status="completed")
                            yield handoff_event
                            return
                        else:
                            raw_messages = MessageBuilder.annotate_terminal_assistant_message(
                                raw_messages, reply_text=final_reply_text,
                                metadata=self._build_global_guardrail_metadata(output_global_match),
                            )

                if input_global_alert_match is not None and output_global_match is None:
                    raw_messages = MessageBuilder.annotate_terminal_assistant_message(
                        raw_messages, reply_text=final_reply_text,
                        metadata=self._build_global_guardrail_metadata(input_global_alert_match),
                    )

                deltas_to_emit = [] if suppress_reply_deltas else list(pending_reply_deltas)
                if (
                    not handoff.should_handoff
                    and not suppress_reply_deltas
                    and final_reply_text
                    and not voice_handler.is_active
                    and "".join(deltas_to_emit) != final_reply_text
                ):
                    deltas_to_emit = [final_reply_text]
                elif (
                    not handoff.should_handoff
                    and not suppress_reply_deltas
                    and not deltas_to_emit
                    and final_reply_text
                ):
                    deltas_to_emit = [final_reply_text]

                if handoff.should_handoff:
                    if not suppress_reply_deltas:
                        for delta in pending_reply_deltas:
                            yield AgentTurnStreamEvent(
                                event_type="reply_delta",
                                session_id=resolved_request.session_id,
                                trace_id=resolved_request.trace_id,
                                delta=delta,
                            )
                    handoff_reply_text = (
                        effective_settings.default_handoff_message
                        if voice_handler.is_active else final_reply_text
                    )
                    handoff_raw_messages = (
                        [AgentMessage(role=AgentRole.ASSISTANT, content=effective_settings.default_handoff_message)]
                        if voice_handler.is_active else raw_messages
                    )
                    handoff_event = AgentTurnStreamEvent(
                        event_type="handoff",
                        session_id=resolved_request.session_id,
                        trace_id=resolved_request.trace_id,
                        reply_text=handoff_reply_text,
                        handoff_reason=handoff.reason,
                        usage=total_usage,
                        raw_messages=handoff_raw_messages,
                        applied_skills=applied_skills,
                        agent_key=resolved_request.agent_key,
                        agent_version=definition.version_number if definition else None,
                        handoff_target=HandoffTarget(
                            target_type="human",
                            reason=handoff.reason,
                        ),
                    )
                    await self._session_mgr.save_session_snapshot(
                        request=resolved_request,
                        result=self._stream_event_to_result(
                            request=resolved_request, definition=definition,
                            event=handoff_event, action=AgentAction.HANDOFF,
                            handoff_target=handoff_event.handoff_target,
                        ),
                        snapshot=restored_snapshot, settings=effective_settings,
                    )
                    await _finalize_obs(terminal_status="completed")
                    yield handoff_event
                    return
                for delta in deltas_to_emit:
                    yield AgentTurnStreamEvent(
                        event_type="reply_delta",
                        session_id=resolved_request.session_id,
                        trace_id=resolved_request.trace_id,
                        delta=delta,
                    )
                reply_event = AgentTurnStreamEvent(
                    event_type="reply_completed",
                    session_id=resolved_request.session_id,
                    trace_id=resolved_request.trace_id,
                    reply_text=final_reply_text,
                    usage=total_usage,
                    raw_messages=raw_messages,
                    applied_skills=applied_skills,
                    agent_key=resolved_request.agent_key,
                    agent_version=definition.version_number if definition else None,
                )
                await self._session_mgr.save_session_snapshot(
                    request=resolved_request,
                    result=self._stream_event_to_result(
                        request=resolved_request, definition=definition,
                        event=reply_event, action=AgentAction.REPLY,
                        handoff_target=reply_event.handoff_target,
                    ),
                    snapshot=restored_snapshot, settings=effective_settings,
                )

                # ── Long-term memory extraction (fire-and-forget) ──────────
                if self._memory_module is not None:
                    user_id = resolved_request.user_id or ""
                    if user_id and raw_messages:
                        print(f"[MEMORY] Scheduling extraction for user={user_id} msgs={len(raw_messages)}", flush=True)
                        asyncio.create_task(self._extract_memories(
                            user_id=user_id,
                            session_id=resolved_request.session_id,
                            messages=raw_messages,
                        ))

                await _finalize_obs(terminal_status="completed", output_text=final_reply_text)
                yield reply_event
                return

        except asyncio.CancelledError:
            await _finalize_obs(terminal_status="cancelled", reason="stream_cancelled")
            raise
        except Exception as _stream_exc:
            await _finalize_obs(terminal_status="failed", error_code="RUNTIME_ERROR", error_message=str(_stream_exc))
            raise
        else:
            if _span_mgr:
                _span_mgr.set_error("Streaming agent exceeded the maximum tool-call rounds.")
            elif _obs_bridge:
                _obs_bridge.set_error("Streaming agent exceeded the maximum tool-call rounds.")
            await _finalize_obs(
                terminal_status="failed",
                error_code="RUNTIME_ERROR",
                error_message="Streaming agent exceeded the maximum tool-call rounds.",
            )
            raise AgentError(
                AgentErrorCode.RUNTIME_ERROR,
                "Streaming agent exceeded the maximum tool-call rounds.",
                model=resolved_request.model,
                trace_id=resolved_request.trace_id,
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Workflow execution (parallel entry point to run_turn/stream_turn)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def run_workflow(
        self,
        request: AgentTurnRequest,
        *,
        workflow: WorkflowDef | None = None,
    ) -> WorkflowResult:
        """Execute a deterministic workflow.

        This is an independent entry point parallel to ``run_turn()``.
        When the agent definition has a bound workflow, this method is
        used instead of the Agent Loop.

        Args:
            request: The turn request (provides user_message, session, trace).
            workflow: Optional workflow definition. If None, loaded from
                the agent definition via ``request.agent_key``.

        Returns:
            A ``WorkflowResult`` with the execution outcome.
        """
        resolved_workflow = await resolve_workflow(
            request, self.definition_loader, workflow,
        )
        engine = build_workflow_engine(
            runner=self,
            definition_loader=self.definition_loader,
            event_bus=self._event_bus,
        )
        tool_context = build_tool_context(request)

        return await engine.run_workflow(
            workflow=resolved_workflow,
            user_input=request.user_message,
            context=tool_context,
        )

    async def stream_workflow(
        self,
        request: AgentTurnRequest,
        *,
        workflow: WorkflowDef | None = None,
    ) -> AsyncIterator[WorkflowStreamEvent]:
        """Execute a deterministic workflow in streaming mode.

        Yields ``WorkflowStreamEvent`` objects as steps complete.

        Args:
            request: The turn request.
            workflow: Optional workflow definition. If None, loaded from
                the agent definition.

        Yields:
            ``WorkflowStreamEvent`` objects for real-time UI updates.
        """
        resolved_workflow = await resolve_workflow(
            request, self.definition_loader, workflow,
        )
        engine = build_workflow_engine(
            runner=self,
            definition_loader=self.definition_loader,
            event_bus=self._event_bus,
        )
        tool_context = build_tool_context(request)

        async for event in engine.stream_workflow(
            workflow=resolved_workflow,
            user_input=request.user_message,
            context=tool_context,
        ):
            yield event

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Memory helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _extract_memories(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list,
    ) -> None:
        """从对话消息中提取长期记忆并持久化。"""
        try:
            print(f"[MEMORY] Extraction START user={user_id} msgs={len(messages)}", flush=True)
            logger.info("memory.extraction_started user_id=%s msg_count=%d", user_id, len(messages))
            from memory.contracts import MemoryRecord, MemoryType

            episodic = await self._memory_module.extractor.extract_episodic(messages)
            semantic = await self._memory_module.extractor.extract_semantic(messages)
            print(f"[MEMORY] Extracted episodic={len(episodic)} semantic={len(semantic)}", flush=True)
            logger.info("memory.extraction_results episodic=%d semantic=%d", len(episodic), len(semantic))
            new_memories: list[MemoryRecord] = []
            for text in episodic:
                new_memories.append(MemoryRecord(
                    user_id=user_id,
                    session_id=session_id,
                    memory_type=MemoryType.EPISODIC,
                    content=text,
                ))
            for text in semantic:
                new_memories.append(MemoryRecord(
                    user_id=user_id,
                    session_id=session_id,
                    memory_type=MemoryType.SEMANTIC,
                    content=text,
                ))
            if not new_memories:
                print(f"[MEMORY] No memories extracted", flush=True)
                logger.info("memory.extraction_skipped user_id=%s (no new memories)", user_id)
                return
            print(f"[MEMORY] Saving {len(new_memories)} memories...", flush=True)
            saved = await self._memory_module.store.save_batch(new_memories)
            print(f"[MEMORY] Saved {len(saved)} records", flush=True)
            logger.info("memory.extraction_saved user_id=%s count=%d", user_id, len(saved))
            # Generate embeddings (placeholder — may be no-op)
            embedding_prov = getattr(self._memory_module, 'embedding_provider', None)
            if embedding_prov is not None:
                for rec in saved:
                    try:
                        emb = await embedding_prov.aembed(rec.content)
                        if emb:
                            await self._memory_module.store.save_embedding(rec.id, emb)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[MEMORY] Extraction FAILED: {e}", flush=True)
            logger.exception("memory._extract_memories_failed")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Internal helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_tool_schemas(
        self,
        allowed_tool_names: frozenset[str] | None,
        tool_bindings: list[ToolBinding] | None,
        settings: AgentSettings,
    ) -> list[ToolSchema]:
        """Build tool schemas for the LLM prompt."""
        raw_defs = self.tool_registry.tool_definitions(
            settings,
            allowed_tool_names=allowed_tool_names,
            tool_bindings=tool_bindings,
        )
        schemas: list[ToolSchema] = []
        for raw in raw_defs:
            schemas.append(ToolSchema(
                name=raw.name,
                description=raw.description,
                parameters_json_schema=raw.parameters_json_schema,
                tags=raw.tags,
            ))
        return schemas

    @staticmethod
    def _build_conversation_history(request: AgentTurnRequest) -> list[AgentMessage]:
        """Build message history from request."""
        messages = list(request.history)
        # System prompt handled separately via LoopContext
        return messages

    @staticmethod
    def _build_session_state(request: AgentTurnRequest) -> AgentSessionState:
        return AgentSessionState(
            session_id=request.session_id,
            customer_id=request.customer_id,
            locale=request.locale,
            channel=request.channel,
            metadata=dict(request.metadata),
        )

    def _make_tool_executor(
        self,
        request: AgentTurnRequest,
        settings: AgentSettings,
        deps: AgentRunDeps,
        prepared: PreparedTurn,
    ):
        """Create a tool executor callable for the loop config."""
        async def executor(
            tool_name: str,
            arguments: dict[str, Any],
            tool_call_id: str,
        ) -> tuple[str, bool]:
            try:
                result = await self._tool_exec.execute_tool_call(
                    request=request,
                    settings=settings,
                    deps=deps,
                    tool_name=tool_name,
                    arguments=arguments,
                    allowed_tool_names=prepared.auto_tool_names,
                    tool_bindings=prepared.tool_bindings,
                    guards_pipeline=self.guards_pipeline,
                )
                return result, False
            except AgentError as exc:
                return exc.message, True
            except Exception as exc:
                return str(exc), True
        return executor

    @staticmethod
    def _build_tool_events_from_loop(loop_result, deps: AgentRunDeps) -> list[ToolExecutionRecord]:
        """Build tool execution records from loop result."""
        records = list(deps.tool_events)
        return records

    async def _prepare_request_context(
        self,
        request: AgentTurnRequest,
        settings: AgentSettings,
    ) -> tuple[AgentTurnRequest, ContextWindow | None]:
        if not settings.memory.enabled or self.context_manager is None:
            trimmed_history = SessionManager.trim_history(request.history, settings)
            return request.model_copy(update={"history": trimmed_history}), None

        system_prompt = build_system_prompt(settings, request)
        context_window = await self.context_manager.prepare_context(
            system_prompt=system_prompt,
            history=request.history,
            user_message=request.user_message,
        )
        return request.model_copy(update={"history": context_window.to_messages()}), context_window

    # ── Guardrail helpers (backward compat) ──────────────────────────────

    def _global_block_text(self) -> str:
        if self.guards_pipeline is not None:
            return self.guards_pipeline.block_response
        return self.settings.guardrails.block_response

    def _build_output_guard_metadata(
        self,
        *,
        request: AgentTurnRequest,
        segment: str,
    ) -> dict[str, str]:
        metadata = dict(request.metadata)
        metadata.setdefault("user_message", request.user_message)
        metadata["reply_segment"] = segment
        return metadata

    # ── Method proxies for backward compat with tests ────────────────────

    async def _execute_tool_call(self, **kwargs) -> str:
        """Backward compat proxy — delegates to ToolExecution."""
        return await self._tool_exec.execute_tool_call(
            guards_pipeline=self.guards_pipeline,
            **kwargs,
        )

    async def _execute_streaming_delegate_tool_call(self, **kwargs) -> AsyncIterator[AgentTurnStreamEvent]:
        """Backward compat proxy — delegates to ToolExecution."""
        async for event in self._tool_exec.execute_streaming_delegate_tool_call(
            guards_pipeline=self.guards_pipeline,
            **kwargs,
        ):
            yield event

    async def _post_process_turn(
        self,
        *,
        decision: AgentDecision,
        deps: AgentRunDeps,
        raw_messages_input: list,
        loop_usage: Any = None,
        resolved_request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        effective_settings: AgentSettings,
        restored_snapshot: SessionSnapshot | None,
        applied_skills: list[AppliedSkillRecord],
        input_global_alert_match: Any | None,
        original_request: AgentTurnRequest,
    ) -> TurnOutput | AgentTurnResult:
        """Post-process a completed LLM turn (voice guardrails, handoff, output guards)."""
        is_voice_guardrail_turn = (
            resolved_request.channel == "voice"
            and definition is not None
            and definition.voice_guardrails is not None
        )
        voice_reply_text = decision.reply_text
        voice_handoff_reason: str | None = None
        voice_handoff_outcome: VoiceSegmentOutcome | None = None

        if is_voice_guardrail_turn:
            voice_outcome = await self._turn_guards.evaluate_voice_segment(
                request=resolved_request, definition=definition, segment=decision.reply_text,
            )
            if voice_outcome is not None:
                if voice_outcome.action == "handoff":
                    voice_handoff_reason = voice_outcome.handoff_reason
                    voice_handoff_outcome = voice_outcome
                elif voice_outcome.action == "emit":
                    voice_reply_text = voice_outcome.visible_text
                else:
                    voice_reply_text = ""

        # Agent-to-agent handoff
        if (
            voice_handoff_reason is None
            and decision.should_handoff
            and decision.handoff_target_type == "agent"
            and decision.handoff_target_agent
            and self._handoff_manager is not None
        ):
            handoff_target = HandoffTarget(
                target_type="agent",
                target_agent_key=decision.handoff_target_agent,
                reason=decision.handoff_reason,
            )
            definition_handoff_policy = dict(definition.handoff_policy) if definition else None
            resolution = await self._handoff_manager.resolve_handoff(
                handoff_target, handoff_policy=definition_handoff_policy,
            )
            if resolution.action is AgentAction.HANDOFF_AGENT:
                handoff_result = await self._handoff_manager.execute_agent_handoff(
                    resolution, request=resolved_request, history=resolved_request.history,
                )
                await self._session_mgr.save_session_snapshot(
                    request=resolved_request, result=handoff_result,
                    snapshot=restored_snapshot, settings=effective_settings,
                )
                return handoff_result

        # Legacy human handoff
        handoff = await self.tool_registry.apply_handoff_policy(
            decision.handoff_reason if decision.should_handoff else None,
            session_state=deps.session_state,
            enabled=effective_settings.enable_handoff_policy,
        )
        action = AgentAction.HANDOFF if handoff.should_handoff else AgentAction.REPLY
        handoff_reason = handoff.reason if handoff.should_handoff else None
        reply_text = (
            voice_reply_text if is_voice_guardrail_turn else decision.reply_text
            if action is AgentAction.REPLY
            else effective_settings.default_handoff_message
        )

        # Output guards
        if self.guards_pipeline is not None and not is_voice_guardrail_turn:
            output_result = await self.guards_pipeline.run_output_guards(
                message=reply_text,
                session_id=resolved_request.session_id,
                trace_id=resolved_request.trace_id or "",
                metadata=dict(resolved_request.metadata),
            )
            if output_result.final_verdict is GuardVerdict.BLOCK:
                reply_text = self.guards_pipeline.block_response
            elif output_result.modified_text is not None:
                reply_text = output_result.modified_text

        raw_messages = MessageBuilder.normalize_raw_messages(raw_messages_input)
        handoff_target: HandoffTarget | None = None

        if is_voice_guardrail_turn:
            if voice_handoff_reason is not None:
                # Check if voice guardrail targets an agent
                if (
                    voice_handoff_outcome is not None
                    and voice_handoff_outcome.handoff_target_type == "agent"
                    and self._handoff_manager is not None
                ):
                    voice_handoff_target = HandoffTarget(
                        target_type="agent",
                        reason=voice_handoff_reason,
                    )
                    definition_handoff_policy = (
                        dict(definition.handoff_policy) if definition else None
                    )
                    resolution = await self._handoff_manager.resolve_handoff(
                        voice_handoff_target,
                        handoff_policy=definition_handoff_policy,
                    )
                    if resolution.action is AgentAction.HANDOFF_AGENT:
                        handoff_result = await self._handoff_manager.execute_agent_handoff(
                            resolution,
                            request=resolved_request,
                            history=resolved_request.history,
                        )
                        merged_usage = self._drain_delegation_usage(
                            self._merge_usage(merged_usage, handoff_result.usage), deps,
                        )
                        return handoff_result.model_copy(update={
                            "usage": merged_usage,
                        })

                # Default: human handoff
                action = AgentAction.HANDOFF_HUMAN
                reply_text = effective_settings.default_handoff_message
                handoff_reason = voice_handoff_reason
                handoff_target = HandoffTarget(target_type="human", reason=voice_handoff_reason)
                raw_messages = [AgentMessage(role=AgentRole.ASSISTANT, content=effective_settings.default_handoff_message)]
            elif action is AgentAction.REPLY and reply_text != decision.reply_text:
                raw_messages = MessageBuilder.replace_terminal_assistant_message(raw_messages, reply_text)
            elif action is AgentAction.REPLY:
                last_assistant = next(
                    (message for message in reversed(raw_messages) if message.role is AgentRole.ASSISTANT),
                    None,
                )
                if last_assistant is None or last_assistant.content != reply_text:
                    raw_messages = MessageBuilder.replace_terminal_assistant_message(raw_messages, reply_text)
            elif handoff.should_handoff:
                reply_text = effective_settings.default_handoff_message
                handoff_target = HandoffTarget(target_type="human", reason=handoff_reason)
                raw_messages = [AgentMessage(role=AgentRole.ASSISTANT, content=effective_settings.default_handoff_message)]

        # Global output guardrails
        output_global_match = None
        if action is AgentAction.REPLY:
            output_global_match = await self._turn_guards.evaluate_global_guardrails(
                request=resolved_request, stage="output", content=reply_text,
            )
            if output_global_match is not None:
                self._global_guardrail_service.record_match(request=resolved_request, match=output_global_match)
                if output_global_match.rule.action == "block":
                    reply_text = self._global_block_text()
                    raw_messages = [
                        AgentMessage(
                            role=AgentRole.ASSISTANT, content=reply_text,
                            metadata=self._build_global_guardrail_metadata(output_global_match),
                        )
                    ]
                elif output_global_match.rule.action == "handoff":
                    action = AgentAction.HANDOFF_HUMAN
                    handoff_reason = output_global_match.reason or f"global_guardrail:{output_global_match.rule.rule_key}"
                    reply_text = effective_settings.default_handoff_message
                    handoff_target = HandoffTarget(target_type="human", reason=handoff_reason)
                    raw_messages = [
                        AgentMessage(
                            role=AgentRole.ASSISTANT, content=reply_text,
                            metadata=self._build_global_guardrail_metadata(output_global_match),
                        )
                    ]
                else:
                    raw_messages = MessageBuilder.annotate_terminal_assistant_message(
                        raw_messages, reply_text=reply_text,
                        metadata=self._build_global_guardrail_metadata(output_global_match),
                    )

        if input_global_alert_match is not None and output_global_match is None:
            raw_messages = MessageBuilder.annotate_terminal_assistant_message(
                raw_messages, reply_text=reply_text,
                metadata=self._build_global_guardrail_metadata(input_global_alert_match),
            )

        # Merge usage: loop_usage + delegation usage
        merged_usage = loop_usage
        if not isinstance(merged_usage, UsageInfo) and merged_usage is not None:
            merged_usage = self._to_usage_info(merged_usage)
        merged_usage = self._drain_delegation_usage(merged_usage, deps)

        result_payload = AgentTurnResult(
            session_id=resolved_request.session_id,
            trace_id=deps.trace_id,
            action=action,
            reply_text=reply_text,
            handoff_reason=handoff_reason,
            tool_events=list(deps.tool_events),
            usage=merged_usage,
            raw_messages=raw_messages,
            agent_key=original_request.agent_key,
            agent_version=definition.version_number if definition else None,
            applied_skills=applied_skills,
            handoff_target=handoff_target,
        )
        return TurnOutput(
            result=result_payload,
            session_snapshot_to_save=restored_snapshot,
        )

    async def _evaluate_global_guardrails(
        self, *, request: AgentTurnRequest, stage: str, content: str
    ):
        """Backward compat proxy — delegates to TurnGuards."""
        return await self._turn_guards.evaluate_global_guardrails(
            request=request, stage=stage, content=content,
        )

    def _record_global_guardrail_match(self, *, request, match) -> None:
        """Backward compat proxy."""
        self._global_guardrail_service.record_match(request=request, match=match)

    async def _ensure_mcp_for_definition(self, definition: AgentDefinitionSnapshot | None) -> None:
        """Ensure MCP servers for definition bindings.

        Kept as instance method (not delegated) because test stubs use it directly.
        """
        if (
            definition is None
            or not definition.mcp_bindings
            or self._mcp_manager is None
            or self._mcp_bridge is None
        ):
            return

        from ..mcp.contracts import McpServerBinding, McpServerConfig

        configs: list[McpServerConfig] = []
        bindings: list[McpServerBinding] = []
        for snap in definition.mcp_bindings:
            if not snap.is_enabled:
                continue
            try:
                config = McpServerConfig.model_validate(snap.server_config_json)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "mcp_definition_config_invalid agent=%s server=%s error=%s",
                    definition.agent_key, snap.server_name, exc,
                )
                continue
            await self._mcp_manager.ensure_server(config)
            configs.append(config)
            bindings.append(
                McpServerBinding(
                    server_name=snap.server_name,
                    is_enabled=True,
                    tool_whitelist=list(snap.tool_whitelist) if snap.tool_whitelist is not None else None,
                )
            )
        if configs:
            await self._mcp_bridge.sync_all(configs=configs, bindings=bindings)

    # ── Static proxies (backward compat — delegates to TurnPrep) ─────────

    @staticmethod
    def _resolve_tool_bindings(
        definition: AgentDefinitionSnapshot | None,
    ) -> list[ToolBinding] | None:
        return TurnPrep._resolve_tool_bindings(definition)

    @staticmethod
    def _collect_applied_skills(
        definition: AgentDefinitionSnapshot | None,
    ) -> list[AppliedSkillRecord]:
        return TurnPrep._collect_applied_skills(definition)

    @staticmethod
    def _merge_usage(left: UsageInfo | None, right: UsageInfo | None) -> UsageInfo | None:
        if left is None:
            return right
        if right is None:
            return left
        return UsageInfo(
            input_tokens=(left.input_tokens or 0) + (right.input_tokens or 0),
            output_tokens=(left.output_tokens or 0) + (right.output_tokens or 0),
            total_tokens=(left.total_tokens or 0) + (right.total_tokens or 0),
            audio_duration_ms=(left.audio_duration_ms or 0) + (right.audio_duration_ms or 0),
        )

    @staticmethod
    def _drain_delegation_usage(base: UsageInfo | None, deps: AgentRunDeps) -> UsageInfo | None:
        """Merge all accumulated sub-agent delegation usage into *base*."""
        result = base
        for sub_usage in deps.delegation_usage_list:
            result = AgentRuntime._merge_usage(result, sub_usage)
        deps.delegation_usage_list.clear()
        return result

    @staticmethod
    def _messages_to_conversation_tuple(messages: list[AgentMessage]) -> list[tuple[str, str]]:
        """Convert AgentMessage list to (role, content) tuples for LlmAdapter."""
        result: list[tuple[str, str]] = []
        for msg in messages:
            role_name = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            prefix = role_name
            if msg.name:
                prefix = f"{role_name}[{msg.name}]"
            result.append((prefix, msg.content))
        return result

    @staticmethod
    def _ensure_tool_allowed(
        tool_name: str,
        allowed_tool_names: frozenset[str] | None,
    ) -> None:
        if allowed_tool_names is None or tool_name in allowed_tool_names:
            return
        raise AgentError(
            AgentErrorCode.INVALID_REQUEST,
            f"Tool '{tool_name}' is not enabled for this agent definition.",
        )

    def _stream_event_to_result(
        self,
        *,
        request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        event: AgentTurnStreamEvent,
        action: AgentAction,
        handoff_target: HandoffTarget | None = None,
        responding_agent_key: str | None = None,
        orchestration_chain: list[str] | None = None,
    ) -> AgentTurnResult:
        return AgentTurnResult(
            session_id=request.session_id,
            trace_id=request.trace_id,
            action=action,
            reply_text=event.reply_text or "",
            handoff_reason=event.handoff_reason,
            usage=event.usage,
            raw_messages=list(event.raw_messages),
            agent_key=event.agent_key or request.agent_key,
            agent_version=event.agent_version if event.agent_version is not None else (definition.version_number if definition else None),
            applied_skills=list(event.applied_skills),
            handoff_target=handoff_target or event.handoff_target,
            responding_agent_key=responding_agent_key,
            orchestration_chain=orchestration_chain,
        )

    def _build_global_guardrail_metadata(self, match: Any) -> dict[str, str]:
        return self._global_guardrail_service.build_metadata(match)

    @staticmethod
    def _to_usage_info(usage) -> UsageInfo:
        return UsageInfo(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
        )

    def _global_guardrail_handoff_stream_event(
        self,
        *,
        request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        match: Any,
        handoff_text: str,
        usage: UsageInfo | None = None,
        applied_skills: list[AppliedSkillRecord] | None = None,
    ) -> AgentTurnStreamEvent:
        return self._global_guardrail_service.handoff_stream_event(
            request=request, definition=definition, match=match,
            handoff_text=handoff_text, usage=usage, applied_skills=applied_skills,
        )

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=True)
        except TypeError:
            return str(value)
