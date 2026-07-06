"""Agent runtime engine — thin orchestration layer delegating to split modules.

This is the main public API of ``agent_runtime``.  The heavy lifting has been
extracted into dedicated modules:

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
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
import json
import logging
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

if TYPE_CHECKING:
    from ..workflow.contracts import WorkflowDef, WorkflowResult, WorkflowStreamEvent

from llm_gateway import GatewayModule, GatewayService, UsageInfo, load_gateway_module

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
from ..guardrails import (
    GuardsPipeline,
    GuardVerdict,
    GlobalGuardrailsRepository,
    GlobalGuardrailsSnapshot,
)
from ..guardrails.factory import build_guards_pipeline
from ..guardrails.global_guard import GlobalGuardrailService
from ..memory import (
    ContextManager,
    ContextWindow,
    ContextWindowConfig,
    GatewaySummarizer,
    InMemorySessionStore,
    SessionSnapshot,
    SessionStore,
    create_default_token_counter,
)
from ..mcp import McpClientManager
from ..orchestration import DelegateToAgentTool, HandoffManager
from ..prompts import build_system_prompt
from ..skills import SkillRegistry, SkillComposer
from ..skills.builtin import register_builtin_skills
from ..tools import ToolBinding, ToolRegistry
from ..tools.contracts import ToolResult
from ..tools.executor import ToolExecutor

from .cancel import CancelToken
from .llm_adapter import FinalDirective, LlmAdapter, ReplyTextStreamParser, ToolDirective, ToolSchema
from .loop import (
    LoopConfig,
    LoopContext,
    QueueMode,
    run_agent_loop,
    stream_agent_loop,
)
from .message_builder import MessageBuilder
from .session import SessionManager
from .tool_execution import ToolExecution
from .turn_guards import InputGuardResult, TurnGuards
from .turn_post import TurnOutput, TurnPostProcessor
from .turn_prep import PreparedTurn, TurnPrep

# ── Legacy voice imports (kept for backward compat during migration) ─────
from ..channels.voice import (
    VoiceGuardrailEvaluator,
    VoiceSegmentOutcome,
    split_flushable_voice_segments as _split_flushable_voice_segments,
    voice_tool_timeout_seconds as _voice_tool_timeout_seconds,
    voice_tool_fallback_output as _voice_tool_fallback_output,
    VOICE_SAFE_FALLBACK_TEXT as _VOICE_SAFE_FALLBACK_TEXT,
    VOICE_SUPPORTED_ACTIONS as _VOICE_SUPPORTED_ACTIONS,
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


# ── Factory helpers ───────────────────────────────────────────────────────


def _resolve_gateway_service(
    gateway: GatewayModule | GatewayService | None,
) -> GatewayService:
    if gateway is None:
        return load_gateway_module().service
    if isinstance(gateway, GatewayModule):
        return gateway.service
    return gateway


def _build_context_manager(
    settings: AgentSettings,
    gateway: GatewayService,
) -> ContextManager | None:
    if not settings.memory.enabled:
        return None
    summarizer = None
    if settings.memory.enable_summarization:
        summarizer = GatewaySummarizer(gateway, model=settings.memory.summarization_model)
    return ContextManager(
        config=ContextWindowConfig(
            max_total_tokens=settings.memory.max_total_tokens,
            reserve_for_response=settings.memory.reserve_for_response,
            reserve_for_system=settings.memory.reserve_for_system,
            summarize_threshold_ratio=settings.memory.summarize_threshold_ratio,
            min_recent_messages=settings.memory.min_recent_messages,
            enable_summarization=settings.memory.enable_summarization,
        ),
        token_counter=create_default_token_counter(settings.memory.tokenizer_model),
        summarizer=summarizer,
    )


def _build_session_store(settings: AgentSettings) -> SessionStore | None:
    if not settings.memory.enabled or not settings.memory.persist_sessions:
        return None
    return InMemorySessionStore()


def _build_guards_pipeline(settings: AgentSettings) -> GuardsPipeline | None:
    if not settings.guardrails.enabled:
        return None
    return build_guards_pipeline(settings.guardrails)


def _build_mcp_client_manager(settings: AgentSettings) -> McpClientManager | None:
    if not settings.enable_mcp:
        return None
    return McpClientManager(settings.mcp_servers)


# ── Runtime factory ───────────────────────────────────────────────────────


def create_agent_runtime(
    settings: AgentSettings | None = None,
    gateway: GatewayModule | GatewayService | None = None,
    tool_registry: ToolRegistry | None = None,
    definition_loader: AgentDefinitionLoader | None = None,
    context_manager: ContextManager | None = None,
    session_store: SessionStore | None = None,
    guards_pipeline: GuardsPipeline | None = None,
    skill_registry: SkillRegistry | None = None,
    mcp_client_manager: McpClientManager | None = None,
    handoff_manager: HandoffManager | None = None,
    global_guardrails_repository: GlobalGuardrailsRepository | None = None,
    observability_bridge_factory: Any | None = None,
    memory_module: Any | None = None,
) -> AgentRuntime:
    """Factory function — creates a fully wired :class:`AgentRuntime`."""
    resolved_settings = settings or AgentSettings()
    resolved_gateway = _resolve_gateway_service(gateway)
    resolved_registry = tool_registry or ToolRegistry()
    return AgentRuntime(
        settings=resolved_settings,
        gateway=resolved_gateway,
        tool_registry=resolved_registry,
        definition_loader=definition_loader,
        context_manager=context_manager or _build_context_manager(resolved_settings, resolved_gateway),
        session_store=session_store or _build_session_store(resolved_settings),
        guards_pipeline=guards_pipeline or _build_guards_pipeline(resolved_settings),
        skill_registry=skill_registry,
        mcp_client_manager=mcp_client_manager or _build_mcp_client_manager(resolved_settings),
        handoff_manager=handoff_manager,
        global_guardrails_repository=global_guardrails_repository,
        observability_bridge_factory=observability_bridge_factory,
        memory_module=memory_module,
    )


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
        gateway: GatewayService,
        tool_registry: ToolRegistry,
        definition_loader: AgentDefinitionLoader | None = None,
        context_manager: ContextManager | None = None,
        session_store: SessionStore | None = None,
        guards_pipeline: GuardsPipeline | None = None,
        skill_registry: SkillRegistry | None = None,
        mcp_client_manager=None,
        handoff_manager: HandoffManager | None = None,
        global_guardrails_repository: GlobalGuardrailsRepository | None = None,
        observability_bridge_factory: Any | None = None,
        memory_module: Any | None = None,
    ) -> None:
        self.settings = settings
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.definition_loader = definition_loader
        self.context_manager = context_manager
        self.session_store = session_store
        self.guards_pipeline = guards_pipeline
        self.global_guardrails_repository = global_guardrails_repository
        self._observability_bridge_factory = observability_bridge_factory
        self._memory_module = memory_module

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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Public API: run_turn / stream_turn
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def run_turn(
        self,
        request: AgentTurnRequest,
        *,
        cancel_token: CancelToken | None = None,
    ) -> AgentTurnResult:
        """Execute a single agent turn in blocking mode.

        Uses the self-built agent loop (no pydantic-ai). Delegates preparation,
        guards, and session management to the extracted helper modules.
        """
        # ── Observability bridge (optional) ─────────────────────────────
        _obs_bridge = None
        if self._observability_bridge_factory is not None:
            _obs_bridge = self._observability_bridge_factory(
                trace_id=getattr(request, "trace_id", None) or str(uuid4()),
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

        # ── Input Guards (delegates to TurnGuards) ──────────────────────
        guard_result = await self._turn_guards.run_input_guards(
            prepared.resolved_request, definition, applied_skills, mode="blocking",
        )
        if guard_result.blocked_result is not None:
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
            )
        except AgentError:
            if _obs_bridge:
                _obs_bridge.set_error("AgentError")
            raise
        except Exception as exc:
            if _obs_bridge:
                _obs_bridge.set_error(str(exc))
            raise AgentError(
                AgentErrorCode.RUNTIME_ERROR,
                str(exc),
                model=resolved_request.model,
                trace_id=resolved_request.trace_id,
            ) from exc
        finally:
            if _obs_bridge:
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

    async def stream_turn(
        self,
        request: AgentTurnRequest,
        *,
        cancel_token: CancelToken | None = None,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Execute a single agent turn in streaming mode.

        This method directly calls the gateway for streaming (no pydantic-ai).
        It delegates preparation, guards, and session management to the split modules.
        """
        await self._ensure_active_global_guardrails_snapshot_loaded()
        prepared = await self._turn_prep.prepare_turn(request)
        definition = prepared.definition
        effective_settings = prepared.effective_settings
        tool_bindings = prepared.tool_bindings
        auto_tool_names = prepared.auto_tool_names
        applied_skills = prepared.applied_skills

        # ── Input Guards (delegates to TurnGuards) ──────────────────────
        guard_result = await self._turn_guards.run_input_guards(
            prepared.resolved_request, definition, applied_skills, mode="streaming",
        )
        if guard_result.stream_blocked_event is not None:
            yield guard_result.stream_blocked_event
            return
        resolved_request = guard_result.resolved_request
        input_global_alert_match = guard_result.input_global_alert_match

        # ── Observability bridge (optional) ─────────────────────────────
        _obs_bridge = None
        if self._observability_bridge_factory is not None:
            _obs_bridge = self._observability_bridge_factory(
                trace_id=getattr(resolved_request, "trace_id", None) or str(uuid4()),
                agent_key=getattr(resolved_request, "agent_key", None),
                event_bus=self._event_bus,
            )
            await self._event_bus.emit(TurnStartEvent())

        async def _finalize_obs() -> None:
            if _obs_bridge is not None:
                await self._event_bus.emit(TurnEndEvent())
                try:
                    await _obs_bridge.finalize()
                except Exception:
                    logger.exception("observability.finalize_failed trace_id=%s", resolved_request.trace_id)

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

        _voice_buffer_mode = (
            resolved_request.channel == "voice"
            and definition is not None
            and definition.voice_guardrails is not None
        )
        voice_visible_reply_parts: list[str] = []
        voice_reply_modified = False
        voice_handoff_reason: str | None = None
        voice_handoff_outcome: VoiceSegmentOutcome | None = None
        pending_reply_deltas: list[str] = []
        for _ in range(_MAX_STREAM_TOOL_ROUNDS):
            accumulated = ""
            completed_text: str | None = None
            usage: UsageInfo | None = None
            voice_sentence_buffer = ""
            conversation = self._messages_to_conversation_tuple(stream_messages)
            if _obs_bridge:
                await self._event_bus.emit(MessageStartEvent(
                    message=AgentMessage(role=AgentRole.ASSISTANT, content=""),
                ))
            try:
                async for stream_delta in llm.generate_stream(
                    system_prompt=system_prompt,
                    conversation=conversation,
                    tools=tool_schemas,
                ):
                    if stream_delta.delta:
                        delta_text = stream_delta.delta
                        accumulated = stream_delta.full_text
                        if _voice_buffer_mode:
                            voice_sentence_buffer += delta_text
                            segments, voice_sentence_buffer = _split_flushable_voice_segments(voice_sentence_buffer)
                            for seg in segments:
                                if voice_handoff_reason is not None:
                                    continue
                                voice_outcome = await self._turn_guards.evaluate_voice_segment(
                                    request=resolved_request, definition=definition, segment=seg,
                                )
                                if voice_outcome is None:
                                    continue
                                voice_reply_modified = voice_reply_modified or voice_outcome.modified
                                if voice_outcome.action == "handoff":
                                    voice_handoff_reason = voice_outcome.handoff_reason
                                    voice_handoff_outcome = voice_outcome
                                    continue
                                if voice_outcome.visible_text:
                                    voice_visible_reply_parts.append(voice_outcome.visible_text)
                                    pending_reply_deltas.append(voice_outcome.visible_text)
                        else:
                            pending_reply_deltas.append(delta_text)
                    if stream_delta.is_done:
                        completed_text = stream_delta.full_text
                        usage = stream_delta.usage
                        if (
                            _voice_buffer_mode
                            and voice_handoff_reason is None
                            and voice_sentence_buffer.strip()
                        ):
                            segments, tail = _split_flushable_voice_segments(voice_sentence_buffer)
                            for seg in segments:
                                voice_outcome = await self._turn_guards.evaluate_voice_segment(
                                    request=resolved_request, definition=definition, segment=seg,
                                )
                                if voice_outcome is None:
                                    continue
                                voice_reply_modified = voice_reply_modified or voice_outcome.modified
                                if voice_outcome.action == "handoff":
                                    voice_handoff_reason = voice_outcome.handoff_reason
                                    voice_handoff_outcome = voice_outcome
                                    break
                                if voice_outcome.visible_text:
                                    voice_visible_reply_parts.append(voice_outcome.visible_text)
                                    pending_reply_deltas.append(voice_outcome.visible_text)
                            if voice_handoff_reason is None and tail.strip():
                                voice_outcome = await self._turn_guards.evaluate_voice_segment(
                                    request=resolved_request, definition=definition, segment=tail.strip(),
                                )
                                if voice_outcome is not None:
                                    voice_reply_modified = voice_reply_modified or voice_outcome.modified
                                    if voice_outcome.action == "handoff":
                                        voice_handoff_reason = voice_outcome.handoff_reason
                                        voice_handoff_outcome = voice_outcome
                                    elif voice_outcome.visible_text:
                                        voice_visible_reply_parts.append(voice_outcome.visible_text)
                                        pending_reply_deltas.append(voice_outcome.visible_text)
                            voice_sentence_buffer = ""
            except AgentError as exc:
                if _obs_bridge:
                    _obs_bridge.set_error(exc.message or "AgentError")
                await self._session_mgr.best_effort_save_on_error(
                    request=resolved_request, snapshot=restored_snapshot, settings=effective_settings,
                )
                raise
            except Exception as exc:
                from llm_gateway import GatewayError

                if _obs_bridge:
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
            if voice_handoff_reason is not None:
                # Check if voice guardrail targets an agent (not just human)
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
                                handoff_reason=voice_handoff_reason,
                                usage=total_usage,
                                raw_messages=sub_raw_messages,
                                handoff_target=sub_handoff_target or HandoffTarget(
                                    target_type="agent",
                                    target_agent_key=resolution.target_agent_key,
                                    reason=voice_handoff_reason,
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
                            await _finalize_obs()
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
                            handoff_reason=voice_handoff_reason,
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
                        await _finalize_obs()
                        yield handoff_event
                        return

                # Default: human handoff from voice guardrail
                handoff_event = AgentTurnStreamEvent(
                    event_type="handoff",
                    session_id=resolved_request.session_id,
                    trace_id=resolved_request.trace_id,
                    reply_text=effective_settings.default_handoff_message,
                    handoff_reason=voice_handoff_reason,
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
                        reason=voice_handoff_reason,
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
                await _finalize_obs()
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
                        await _finalize_obs()
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
                    await _finalize_obs()
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
            if _voice_buffer_mode and not handoff.should_handoff:
                if voice_reply_modified:
                    final_reply_text = "".join(voice_visible_reply_parts)
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
                        await _finalize_obs()
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
                and not _voice_buffer_mode
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
                    if _voice_buffer_mode else final_reply_text
                )
                handoff_raw_messages = (
                    [AgentMessage(role=AgentRole.ASSISTANT, content=effective_settings.default_handoff_message)]
                    if _voice_buffer_mode else raw_messages
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
                await _finalize_obs()
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

            await _finalize_obs()
            yield reply_event
            return

        if _obs_bridge:
            _obs_bridge.set_error("Streaming agent exceeded the maximum tool-call rounds.")
        await _finalize_obs()
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
        from ..workflow import WorkflowEngine, InMemoryWorkflowStateStore, StepExecutor
        from ..orchestration.sub_agent_executor import SubAgentExecutor

        # Resolve workflow definition
        if workflow is None:
            if request.agent_key and self.definition_loader:
                definition = await self.definition_loader.load(request.agent_key)
                if definition and definition.workflow:
                    workflow = definition.workflow
            if workflow is None:
                raise AgentError(
                    AgentErrorCode.INVALID_REQUEST,
                    "No workflow definition found for this request.",
                    trace_id=request.trace_id,
                )

        # Build workflow dependencies
        sub_agent_executor = SubAgentExecutor(
            runner=self,
            definition_loader=self.definition_loader,
        )
        step_executor = StepExecutor(
            tool_executor=ToolExecutor(),
            tool_registry=self.tool_registry.dynamic_registry,
            sub_agent_executor=sub_agent_executor,
        )
        state_store = InMemoryWorkflowStateStore()
        engine = WorkflowEngine(
            step_executor=step_executor,
            state_store=state_store,
            event_bus=self._event_bus,
        )

        # Build execution context
        from ..tools.contracts import ToolExecutionContext
        tool_context = ToolExecutionContext(
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            agent_key=request.agent_key,
            agent_version=request.agent_version,
            customer_id=request.customer_id,
            locale=request.locale,
            metadata=dict(request.metadata),
        )

        return await engine.run_workflow(
            workflow=workflow,
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
        from ..workflow import WorkflowEngine, InMemoryWorkflowStateStore, StepExecutor
        from ..orchestration.sub_agent_executor import SubAgentExecutor

        # Resolve workflow definition
        if workflow is None:
            if request.agent_key and self.definition_loader:
                definition = await self.definition_loader.load(request.agent_key)
                if definition and definition.workflow:
                    workflow = definition.workflow
            if workflow is None:
                raise AgentError(
                    AgentErrorCode.INVALID_REQUEST,
                    "No workflow definition found for this request.",
                    trace_id=request.trace_id,
                )

        # Build workflow dependencies
        sub_agent_executor = SubAgentExecutor(
            runner=self,
            definition_loader=self.definition_loader,
        )
        step_executor = StepExecutor(
            tool_executor=ToolExecutor(),
            tool_registry=self.tool_registry.dynamic_registry,
            sub_agent_executor=sub_agent_executor,
        )
        state_store = InMemoryWorkflowStateStore()
        engine = WorkflowEngine(
            step_executor=step_executor,
            state_store=state_store,
            event_bus=self._event_bus,
        )

        # Build execution context
        from ..tools.contracts import ToolExecutionContext
        tool_context = ToolExecutionContext(
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            agent_key=request.agent_key,
            agent_version=request.agent_version,
            customer_id=request.customer_id,
            locale=request.locale,
            metadata=dict(request.metadata),
        )

        async for event in engine.stream_workflow(
            workflow=workflow,
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
