"""桌面端组装层：根据配置创建 GatewayService / AgentModule。"""
from __future__ import annotations

from core.config import LLMConfig
from llm_gateway import Capability, ProviderId
from llm_gateway.bootstrap import create_gateway_service
from llm_gateway.config import GatewaySettings, ModelDefinition, ProviderConfig
from llm_gateway.core.service import GatewayService

from agent_runtime import AgentModule, AgentSettings, ToolRegistry, create_agent_module


def create_gateway(llm_config: LLMConfig) -> GatewayService:
    """根据配置创建 GatewayService。"""
    provider_id = (
        ProviderId.OPENAI if llm_config.provider == "openai"
        else ProviderId.ANTHROPIC
    )

    config = ProviderConfig(
        api_key=llm_config.api_key or "not-set",
        base_url=llm_config.base_url or None,
    )

    model_def = ModelDefinition(
        model_key=llm_config.model,
        provider=provider_id,
        provider_model_name=llm_config.model,
        capabilities={Capability.TEXT},
    )

    if llm_config.provider == "openai":
        settings = GatewaySettings(
            openai=config,
            catalog={"enable_static_fallback": True},
            models=[model_def],
        )
    else:
        settings = GatewaySettings(
            anthropic=config,
            catalog={"enable_static_fallback": True},
            models=[model_def],
        )

    return create_gateway_service(settings)


def create_agent(
    llm_config: LLMConfig,
    tool_registry: ToolRegistry | None = None,
    system_prompt: str | None = None,
) -> AgentModule:
    """根据配置创建 AgentModule（含 Gateway + AgentRuntime + Tools）。"""
    gateway = create_gateway(llm_config)

    settings = AgentSettings(
        default_model=llm_config.model,
        default_system_prompt=system_prompt or _DEFAULT_SYSTEM_PROMPT,
    )

    return create_agent_module(
        settings=settings,
        gateway=gateway,
        tool_registry=tool_registry,
    )


_DEFAULT_SYSTEM_PROMPT = """你是 AgentLabKit 桌面助手。你可以：
- 与用户对话，回答问题
- 使用工具读取文件、搜索内容、操作剪贴板、截屏
- 帮助用户完成日常工作

请用简洁、友好的语气回复。中文优先。"""

