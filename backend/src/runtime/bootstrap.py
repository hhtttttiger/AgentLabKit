"""共享内核：web 进程与 worker 进程共同依赖的基础设施装配工厂。

把原本内联在 ``main.py`` lifespan 里的 gateway / retrieval 构造逻辑抽成
可复用函数，web 和 worker 各自调用同一份装配代码。
"""

from __future__ import annotations

from llm_gateway.bootstrap import create_gateway_service
from llm_gateway.config import (
    GatewaySettings,
    InstanceEncryptionSettings,
    ModelCatalogSettings,
)

from config import Settings


# ── 基础设施（DB 引擎 + Redis）──────────────────────────────────────────


def init_infrastructure(settings: Settings, **redis_kwargs: object) -> None:
    """初始化数据库引擎和 Redis 连接池。

    web 与 worker 进程共用，避免各自内联 init_engine / init_redis。
    ``**redis_kwargs`` 透传给 :func:`alkit_infra.redis.client.init_redis`。
    """
    from alkit_db.engine import init_engine
    from alkit_infra.redis.client import init_redis

    init_engine(settings.database_url, echo=settings.debug)
    if settings.redis_enabled:
        init_redis(settings.redis_url, **redis_kwargs)


async def cleanup_infrastructure() -> None:
    """释放数据库引擎和 Redis 连接池。

    安全幂等 —— 未初始化时调用也不会抛异常。
    """
    from alkit_infra.redis.client import close_redis
    from alkit_db.engine import dispose_engine

    await close_redis()
    await dispose_engine()


# ── Gateway / Retrieval（web 与 worker 共用）────────────────────────────


def build_gateway_service(settings: Settings):
    """构造 LLM gateway 服务（provider registry + 模型目录 + usage 记录）。

    抽自 ``main.py`` lifespan。gateway 是纯对象，不依赖 FastAPI，
    web 与 worker 均可独立构造。
    """
    gateway_settings = GatewaySettings(
        catalog=ModelCatalogSettings(
            database_url=settings.gateway_catalog_database_url,
            cache_backend="memory",
            enable_static_fallback=True,
        ),
        instance_encryption=InstanceEncryptionSettings(
            encryption_key=settings.gateway_catalog_encrypt_key or None,
        ),
    )
    return create_gateway_service(gateway_settings)


def build_retrieval_service(settings: Settings, gateway_service):
    """构造知识检索服务（embedding provider + pgvector 存储 + 检索编排）。

    抽自 ``main.py`` lifespan。复用主库 ``session_factory``（retrieval 与业务
    表共用同一 Postgres + pgvector）。调用方负责先开启 retrieval（``settings.
    retrieval_enabled``）并已 ``init_engine``。

    返回 ``KnowledgeRetrievalService``。
    """
    # 惰性导入：未启用 retrieval 时不应触发加载。
    from alkit_db.engine import get_session_factory
    from modules.knowledge_base.providers.gateway_embedding import GatewayEmbeddingProvider
    from modules.knowledge_base.retrieval_service import KnowledgeRetrievalService
    from modules.knowledge_base.stores.pgvector_store import PgVectorStore

    session_factory = get_session_factory()

    embedding_provider = GatewayEmbeddingProvider(
        gateway=gateway_service,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    vector_store = PgVectorStore(
        session_factory=session_factory,
        dimensions=settings.embedding_dimensions,
    )
    return KnowledgeRetrievalService(
        session_factory=session_factory,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
