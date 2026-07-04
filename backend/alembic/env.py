from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure src/ and the local packages are importable for both `pip install .`
# and direct `alembic` usage (no extra PYTHONPATH needed on the command line).
_HERE = Path(__file__).resolve().parent          # backend/alembic/
_BACKEND = _HERE.parent                            # backend/
_ROOT = _BACKEND.parent                            # project root
for _p in (
    _BACKEND / "src",
    _ROOT / "packages" / "db" / "src",
    _ROOT / "packages" / "llm_gateway" / "src",
    _ROOT / "packages" / "agent_runtime" / "src",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import Settings
from alkit_db import Base

# Import all ORM models so Alembic autogenerate can see every table.
from modules.auth.models import AuthUser  # noqa: F401
from modules.llm_catalog.models import (  # noqa: F401
    LlmCatalogRevision, LlmConnectionProfile, LlmFeature,
    LlmModel, LlmModelBinding, LlmModelFeature, LlmModelInstance,
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
from modules.chat.models import ChatSessionOrm, ChatMessageOrm  # noqa: F401
from modules.evaluation.models import (  # noqa: F401
    EvalDataset, EvalCase, EvalRunConfig, EvalRun, EvalRunResult,
)
# llm_gateway usage logs live on a separate DeclarativeBase (UsageBase),
# independent of alkit_db.Base — its metadata must be added to target_metadata too.
from llm_gateway.usage.orm_models import (  # noqa: F401
    ModelAttemptLogOrm, ModelRequestLogOrm, UsageBase,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# alkit_db.Base covers all EntityBase tables; UsageBase covers model_*_logs.
target_metadata = [Base.metadata, UsageBase.metadata]
settings = Settings()


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
