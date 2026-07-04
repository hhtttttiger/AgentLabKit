from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..mcp.contracts import McpServerConfig
from .guardrails import GuardrailsSettings
from .memory import MemorySettings


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_RUNTIME_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    agent_name: str = "customer_support_agent"
    default_model: str = "gpt-5.4-mini"
    default_system_prompt: str = (
        "You are a customer support agent. Be accurate, direct, and practical."
    )
    max_history_messages: int = 20
    max_output_tokens: int | None = 800
    temperature: float | None = 0.2
    enable_knowledge_tool: bool = True
    knowledge_top_k: int = 5
    enable_handoff_policy: bool = True
    default_handoff_message: str = (
        "I need to hand this conversation to a human agent."
    )
    model_retries: int = 1
    output_retries: int = 1
    memory: MemorySettings = Field(default_factory=MemorySettings)
    guardrails: GuardrailsSettings = Field(default_factory=GuardrailsSettings)
    prompt_sections: tuple[str, ...] = Field(
        default=(
            "role",
            "tooling",
            "handoff",
        )
    )

    # MCP integration (Phase 1)
    enable_mcp: bool = False
    """Master switch for MCP client.  False = zero overhead, no imports."""

    mcp_servers: list[McpServerConfig] = Field(default_factory=list)
    """Global MCP server configs shared by all agents in this runtime."""
