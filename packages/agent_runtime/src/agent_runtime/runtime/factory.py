"""Runtime factory — wiring helpers for :class:`AgentRuntime`.

Extracted from ``engine.py`` to keep the engine focused on turn orchestration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from llm_gateway import GatewayModule, GatewayProtocol, load_gateway_module

from ..config import AgentSettings
from ..guardrails import GuardsPipeline
from ..guardrails.factory import build_guards_pipeline
from ..memory import (
    ContextManager,
    ContextWindowConfig,
    GatewaySummarizer,
    InMemorySessionStore,
    SessionStore,
    create_default_token_counter,
)
from ..mcp import McpClientManager
from ..tools import ToolRegistry

if TYPE_CHECKING:
    from ..definition.loader import AgentDefinitionLoader
    from ..guardrails import GlobalGuardrailsRepository
    from ..orchestration import HandoffManager
    from ..skills import SkillRegistry
    from .engine import AgentRuntime

logger = logging.getLogger(__name__)


def resolve_gateway_service(
    gateway: GatewayModule | GatewayProtocol | None,
) -> GatewayProtocol:
    """Resolve a gateway reference to a :class:`GatewayProtocol` implementation."""
    if gateway is None:
        return load_gateway_module().service
    if isinstance(gateway, GatewayModule):
        return gateway.service
    return gateway


def build_context_manager(
    settings: AgentSettings,
    gateway: GatewayProtocol,
) -> ContextManager | None:
    """Build a :class:`ContextManager` from application settings."""
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


def build_session_store(settings: AgentSettings) -> SessionStore | None:
    """Build a :class:`SessionStore` from application settings."""
    if not settings.memory.enabled or not settings.memory.persist_sessions:
        return None
    return InMemorySessionStore()


def build_guards_pipeline_from_settings(settings: AgentSettings) -> GuardsPipeline | None:
    """Build a :class:`GuardsPipeline` from application settings."""
    if not settings.guardrails.enabled:
        return None
    return build_guards_pipeline(settings.guardrails)


def build_mcp_client_manager(settings: AgentSettings) -> McpClientManager | None:
    """Build an :class:`McpClientManager` from application settings."""
    if not settings.enable_mcp:
        return None
    return McpClientManager(settings.mcp_servers)


def create_agent_runtime(
    settings: AgentSettings | None = None,
    gateway: GatewayModule | GatewayProtocol | None = None,
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
    # Avoid circular import: AgentRuntime is defined in engine.py
    from .engine import AgentRuntime

    resolved_settings = settings or AgentSettings()
    resolved_gateway = resolve_gateway_service(gateway)
    resolved_registry = tool_registry or ToolRegistry()
    return AgentRuntime(
        settings=resolved_settings,
        gateway=resolved_gateway,
        tool_registry=resolved_registry,
        definition_loader=definition_loader,
        context_manager=context_manager or build_context_manager(resolved_settings, resolved_gateway),
        session_store=session_store or build_session_store(resolved_settings),
        guards_pipeline=guards_pipeline or build_guards_pipeline_from_settings(resolved_settings),
        skill_registry=skill_registry,
        mcp_client_manager=mcp_client_manager or build_mcp_client_manager(resolved_settings),
        handoff_manager=handoff_manager,
        global_guardrails_repository=global_guardrails_repository,
        observability_bridge_factory=observability_bridge_factory,
        memory_module=memory_module,
    )
