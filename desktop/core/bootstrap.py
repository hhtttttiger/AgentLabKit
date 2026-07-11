"""桌面端组装层：根据配置创建 GatewayService。"""
from __future__ import annotations

from core.config import LLMConfig
from llm_gateway import Capability, ProviderId
from llm_gateway.bootstrap import create_gateway_service
from llm_gateway.config import GatewaySettings, ModelDefinition, ProviderConfig
from llm_gateway.core.service import GatewayService


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
