"""Web 进程专用的模块装配工厂。

与 worker 共用的 infra / gateway / retrieval 在 ``runtime.bootstrap`` 中；
本模块只包含 web 进程独有的各业务模块初始化（cost / obs / eval / memory / agent_runtime）。
"""

from __future__ import annotations

from typing import Any


def build_cost_analysis_module(session_factory: Any) -> Any:
    """构造 Cost Analysis 模块。"""
    from cost_analysis import create_cost_analysis_module
    from cost_analysis.config import CostAnalysisSettings

    return create_cost_analysis_module(
        session_factory=session_factory,
        settings=CostAnalysisSettings(),
    )


def build_observability_module(session_factory: Any) -> Any:
    """构造 Observability 模块（trace 采集 + 持久化）。"""
    from observability import create_observability_module
    from observability.config import ObservabilitySettings

    return create_observability_module(
        session_factory=session_factory,
        settings=ObservabilitySettings(),
    )


def build_evaluation_module(gateway_service: Any | None) -> Any:
    """构造 Evaluation 模块。

    gateway_service 为 None 时 judge 回退为 None（评测功能降级但 API 仍可启动）。
    """
    from evaluation import create_evaluation_module
    from evaluation.config import EvaluationSettings
    from modules.evaluation.adapters import GatewayJudge

    eval_settings = EvaluationSettings()
    judge = (
        GatewayJudge(
            gateway_service=gateway_service,
            model=eval_settings.default_judge_model,
        )
        if gateway_service is not None
        else None
    )

    return create_evaluation_module(
        judge=judge,
        target_executor=None,  # per-run 动态解析
        settings=eval_settings,
    )


def build_memory_module(
    session_factory: Any,
    gateway_service: Any | None,
    retrieval_service: Any | None,
) -> Any:
    """构造 Long-Term Memory 模块。

    依赖 retrieval_service 提供 embedding_provider；retrieval 不可用时
    embedding 降级为 None（memory 仍可初始化但功能受限）。
    """
    from memory import create_memory_module
    from memory.config import MemorySettings

    embedding_prov = None
    if retrieval_service is not None:
        embedding_prov = retrieval_service.embedding_provider

    return create_memory_module(
        session_factory=session_factory,
        gateway_service=gateway_service,
        embedding_provider=embedding_prov,
        settings=MemorySettings(),
    )


def build_agent_runtime(
    *,
    gateway_service: Any,
    retrieval_service: Any | None = None,
    memory_module: Any | None = None,
    obs_module: Any,
    session_factory: Any,
) -> tuple[Any, Any]:
    """构造 Agent Runtime（definition-aware）。

    装配链路：
    1. ToolRegistry + BackendKnowledgeProvider（可选，依赖 retrieval）
    2. 注册内置工具（time_now / calculator）
    3. BackendAgentDefinitionLoader（ORM → agent 快照）
    4. Observability bridge（agent_runtime 事件 → TraceStore）
    5. create_agent_runtime 组装

    返回 ``(agent_runtime, agent_definition_loader)``。
    """
    from agent_runtime import create_agent_runtime
    from agent_runtime.config.agent import AgentSettings
    from agent_runtime.tools.registry import ToolRegistry
    from modules.agent.definition_loader import BackendAgentDefinitionLoader

    # Knowledge provider —— 可选。retrieval 未就绪/半安装时回退到
    # ToolRegistry 内置的 NullKnowledgeProvider（agent 可对话，知识库工具禁用）。
    registry_kwargs: dict[str, Any] = {}
    if retrieval_service is not None:
        try:
            from modules.knowledge_base.knowledge_provider import BackendKnowledgeProvider

            registry_kwargs["knowledge_provider"] = BackendKnowledgeProvider(retrieval_service)
        except Exception:
            from loguru import logger

            logger.exception("knowledge_provider init failed; agent KB tool disabled")

    tool_registry = ToolRegistry(**registry_kwargs)
    # knowledge_search 已在 ToolRegistry.__post_init__ 自动注册；这里补注册
    # agent_runtime 自带的 time_now / calculator 内置工具。
    from modules.agent.builtin_tools import register_builtin_tools

    register_builtin_tools(tool_registry)

    agent_definition_loader = BackendAgentDefinitionLoader(session_factory)

    # ── Observability bridge ──
    obs_settings = obs_module.settings

    def _obs_bridge_factory(trace_id: str, event_bus, agent_key: str | None = None):
        from observability.integrations.agent_runtime_listener import create_span_bridge

        return create_span_bridge(
            trace_store=obs_module.trace_store,
            trace_id=trace_id,
            agent_key=agent_key,
            event_bus=event_bus,
            max_spans=obs_settings.max_spans_per_trace,
            enabled=obs_settings.enabled,
        )

    agent_runtime = create_agent_runtime(
        settings=AgentSettings(enable_mcp=True),
        gateway=gateway_service,
        tool_registry=tool_registry,
        definition_loader=agent_definition_loader,
        memory_module=memory_module,
        observability_bridge_factory=_obs_bridge_factory,
    )

    return agent_runtime, agent_definition_loader
