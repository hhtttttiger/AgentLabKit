from __future__ import annotations

from dataclasses import dataclass, field

from llm_gateway import GatewayModule, GatewayService

from .config import AgentSettings
from .definition.loader import AgentDefinitionLoader
from .memory import ContextManager, SessionStore
from .mcp import McpClientManager
from .orchestration import HandoffManager
from .runtime import AgentRuntime, create_agent_runtime
from .skills import SkillRegistry
from .tools import ToolRegistry
from .tools.catalog_syncer import ToolCatalogSyncer


@dataclass(slots=True)
class AgentModule:
    settings: AgentSettings
    runtime: AgentRuntime
    gateway: GatewayService
    tool_registry: ToolRegistry
    definition_loader: AgentDefinitionLoader | None = None
    context_manager: ContextManager | None = None
    session_store: SessionStore | None = None
    handoff_manager: HandoffManager | None = None
    catalog_syncer: ToolCatalogSyncer | None = None
    """Optional syncer; populated when the service has DB access configured."""


def create_agent_module(
    settings: AgentSettings | None = None,
    gateway: GatewayModule | GatewayService | None = None,
    tool_registry: ToolRegistry | None = None,
    definition_loader: AgentDefinitionLoader | None = None,
    context_manager: ContextManager | None = None,
    session_store: SessionStore | None = None,
    skill_registry: SkillRegistry | None = None,
    mcp_client_manager: McpClientManager | None = None,
    handoff_manager: HandoffManager | None = None,
    catalog_syncer: ToolCatalogSyncer | None = None,
) -> AgentModule:
    resolved_settings = settings or AgentSettings()
    resolved_tool_registry = tool_registry or ToolRegistry()
    runtime = create_agent_runtime(
        settings=resolved_settings,
        gateway=gateway,
        tool_registry=resolved_tool_registry,
        definition_loader=definition_loader,
        context_manager=context_manager,
        session_store=session_store,
        skill_registry=skill_registry,
        mcp_client_manager=mcp_client_manager,
        handoff_manager=handoff_manager,
    )
    return AgentModule(
        settings=resolved_settings,
        runtime=runtime,
        gateway=runtime.gateway,
        tool_registry=resolved_tool_registry,
        definition_loader=definition_loader,
        context_manager=runtime.context_manager,
        session_store=runtime.session_store,
        handoff_manager=handoff_manager,
        catalog_syncer=catalog_syncer,
    )


def load_agent_module() -> AgentModule:
    return create_agent_module()
