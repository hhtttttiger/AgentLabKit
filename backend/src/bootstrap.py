"""Startup bootstrap — seed initial data.

Schema creation is handled by Alembic (`alembic upgrade head`).
This module only seeds default data (e.g. admin user).

Usage:
    python -m src.bootstrap
"""

from __future__ import annotations

import asyncio

from loguru import logger

from config import Settings
from alkit_db.engine import dispose_engine, init_engine

# Import all models so Base.metadata stays complete (needed by Alembic env.py)
from modules.auth.models import AuthUser  # noqa: F401
from modules.llm_catalog.models import (  # noqa: F401
    LlmConnectionProfile, LlmModel, LlmModelInstance,
    LlmFeature, LlmModelFeature, LlmModelBinding, LlmCatalogRevision,
)
from modules.agent.models import (  # noqa: F401
    AgentDefinition, AgentDefinitionVersion, AgentTool, AgentToolBinding,
    AgentSkill, AgentSkillBinding, AgentMcpServer, AgentMcpBinding,
    AgentKnowledgeBaseBinding, AgentCatalogRevision, AgentExecutionAudit,
)
from modules.knowledge_base.models import (  # noqa: F401
    KnowledgeBaseEntity, KnowledgeFolder, KnowledgeDocument,
    KnowledgeDocumentRecallStat, DocumentSegment, DocumentProcessingJob,
    DocumentIndex, SegmentEmbedding,
)
from modules.glossary.models import GlossaryCategory, GlossaryTerm, KnowledgeBaseGlossaryCategory  # noqa: F401
from modules.files.models import StoredFile  # noqa: F401
from modules.cost_analysis.models import CostBudget, CostAlert  # noqa: F401
from modules.observability.models import TraceRecordOrm, TraceSpanOrm  # noqa: F401
from modules.memory.models import MemoryRecordOrm, MemoryEmbeddingOrm  # noqa: F401
from modules.evaluation.models import (  # noqa: F401
    EvalDataset, EvalCase, EvalRunConfig, EvalRun, EvalRunResult,
)


async def bootstrap() -> None:
    """Seed initial data — assumes schema already exists (created by Alembic)."""
    settings = Settings()
    session_factory = init_engine(settings.database_url, echo=settings.debug)

    async with session_factory() as session:
        from modules.auth.service import seed_default_user
        await seed_default_user(session)

        from modules.llm_catalog.seed import seed_llm_catalog
        await seed_llm_catalog(session)

        from modules.agent.seed import seed_agent
        await seed_agent(session)

        from modules.agent.seed import seed_clock_agent
        await seed_clock_agent(session)

        from modules.agent.seed import seed_mcp_demo
        await seed_mcp_demo(session)

        from modules.agent.seed import seed_skill_demo
        await seed_skill_demo(session)

        await session.commit()

    logger.info("Bootstrap complete — seed data applied")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(bootstrap())
