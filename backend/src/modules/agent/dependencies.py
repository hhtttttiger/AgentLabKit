"""FastAPI dependency injection for the agent module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from common.dependencies import DbSession
from .services.agent_service import AgentService
from .services.tool_service import ToolDefinitionService
from .services.skill_service import SkillDefinitionService
from .services.mcp_service import McpServerService


def get_agent_service(db: DbSession) -> AgentService:
    return AgentService(db)


def get_tool_service(db: DbSession) -> ToolDefinitionService:
    return ToolDefinitionService(db)


def get_skill_service(db: DbSession) -> SkillDefinitionService:
    return SkillDefinitionService(db)


def get_mcp_service(db: DbSession) -> McpServerService:
    return McpServerService(db)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
ToolServiceDep = Annotated[ToolDefinitionService, Depends(get_tool_service)]
SkillServiceDep = Annotated[SkillDefinitionService, Depends(get_skill_service)]
McpServiceDep = Annotated[McpServerService, Depends(get_mcp_service)]
