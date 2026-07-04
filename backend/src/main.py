from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.errors import register_error_handlers
from common.auth import configure_auth, require_auth
from common.json_response import SnowflakeJSONResponse
from common.response import ok
from config import Settings
from alkit_db.engine import get_session_factory
from alkit_infra.queue import RedisStreamsQueue, QueueSettings
from runtime.bootstrap import (
    build_gateway_service,
    build_retrieval_service,
    cleanup_infrastructure,
    init_infrastructure,
)
from runtime.web_modules import (
    build_agent_runtime,
    build_cost_analysis_module,
    build_evaluation_module,
    build_memory_module,
    build_observability_module,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ── 基础设施（DB 引擎 + Redis，与 worker 同源）──
        init_infrastructure(settings)
        configure_auth(settings)
        app.state.settings = settings

        # ── Gateway（LLM 调用入口，与 worker 同源）──
        gateway = None
        if settings.gateway_catalog_database_url:
            gateway = build_gateway_service(settings)
            app.state.gateway_service = gateway
            app.state.catalog_service = gateway.catalog_service

        sf = get_session_factory()

        # ── 核心模块（始终初始化，不依赖 gateway）──
        app.state.cost_analysis_module = build_cost_analysis_module(sf)

        obs_module = build_observability_module(sf)
        app.state.observability_module = obs_module

        app.state.evaluation_module = build_evaluation_module(gateway)

        # ── Retrieval → Memory（链式依赖）──
        retrieval = None
        if settings.retrieval_enabled and gateway is not None:
            retrieval = build_retrieval_service(settings, gateway)
            app.state.retrieval_service = retrieval

        app.state.memory_module = build_memory_module(sf, gateway, retrieval)

        # ── 文档队列（web 只 enqueue，消费在 worker 进程）──
        if settings.redis_enabled and retrieval is not None:
            app.state.doc_queue = RedisStreamsQueue(settings=QueueSettings())

        # ── Agent Runtime（definition-aware）──
        if gateway is not None:
            agent_rt, agent_loader = build_agent_runtime(
                gateway_service=gateway,
                retrieval_service=retrieval,
                memory_module=app.state.memory_module,
                obs_module=obs_module,
                session_factory=sf,
            )
            app.state.agent_definition_loader = agent_loader
            app.state.agent_runtime = agent_rt

        yield

        # ── 清理 ──
        doc_queue = getattr(app.state, "doc_queue", None)
        if doc_queue is not None:
            await doc_queue.close()
        await cleanup_infrastructure()

    app = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        lifespan=lifespan,
        default_response_class=SnowflakeJSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # CORS spec: cannot be True when origins="*"
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    _register_routers(app)

    @app.get("/health")
    async def health():
        return ok({"status": "healthy"})

    return app


def _register_routers(app: FastAPI) -> None:
    from modules.auth.router import router as auth_router
    from modules.llm_catalog.router import router as llm_catalog_router
    from modules.agent.router import router as agents_router
    from modules.agent.tools_router import router as agent_tools_router
    from modules.agent.skills_router import router as agent_skills_router
    from modules.agent.mcp_router import router as agent_mcp_router
    from modules.knowledge_base.router import router as knowledge_base_router
    from modules.chat.router import router as chat_router
    from modules.ai_invoke.router import router as ai_invoke_router
    from modules.files.router import router as files_router
    from modules.glossary.router import router as glossary_router

    _auth = [Depends(require_auth)]

    # Auth router is intentionally unauthenticated (login endpoint).
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

    app.include_router(llm_catalog_router, prefix="/api/llm-catalog", tags=["llm-catalog"], dependencies=_auth)
    app.include_router(agents_router, prefix="/api/agents", tags=["agents"], dependencies=_auth)
    app.include_router(agent_tools_router, prefix="/api/agent-tools", tags=["agent-tools"], dependencies=_auth)
    app.include_router(agent_skills_router, prefix="/api/agent-skills", tags=["agent-skills"], dependencies=_auth)
    app.include_router(agent_mcp_router, prefix="/api/agent-mcp", tags=["agent-mcp"], dependencies=_auth)
    app.include_router(knowledge_base_router, prefix="/api/knowledge-bases", tags=["knowledge-bases"], dependencies=_auth)
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"], dependencies=_auth)
    app.include_router(ai_invoke_router, prefix="/api/ai/invoke", tags=["ai-invoke"], dependencies=_auth)
    app.include_router(files_router, prefix="/api/files", tags=["files"], dependencies=_auth)
    app.include_router(glossary_router, prefix="/api/glossary", tags=["glossary"], dependencies=_auth)

    from modules.cost_analysis.router import router as cost_analysis_router
    app.include_router(cost_analysis_router, prefix="/api/cost", tags=["cost-analysis"], dependencies=_auth)

    from modules.observability.router import router as observability_router
    app.include_router(observability_router, prefix="/api/traces", tags=["observability"], dependencies=_auth)

    from modules.memory.router import router as memory_router
    app.include_router(memory_router, prefix="/api/memories", tags=["memory"], dependencies=_auth)

    from modules.evaluation.router import router as evaluation_router
    app.include_router(evaluation_router, prefix="/api/eval", tags=["evaluation"], dependencies=_auth)

    from modules.model_usage.router import router as model_usage_router
    app.include_router(model_usage_router, prefix="/api/model-usage", tags=["model-usage"], dependencies=_auth)
