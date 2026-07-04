"""Agent definition loader — reads published definitions from shared database.

Follows the read-only consumption pattern established by llm_gateway's ModelCatalogRepository.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .cache import AgentDefinitionCache, InMemoryAgentDefinitionCache
from .models import (
    AgentDefinitionSnapshot,
    KnowledgeBindingSnapshot,
    McpBindingSnapshot,
    SkillBindingSnapshot,
    SkillDefinitionSnapshot,
    ToolBindingSnapshot,
)

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ORM models (read-only projections of .NET tables)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class _Base(DeclarativeBase):
    pass


class AgentDefinitionOrm(_Base):
    __tablename__ = "agent_definitions"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    agent_key: Mapped[str] = mapped_column("AgentKey", String(128), unique=True)
    display_name: Mapped[str] = mapped_column("DisplayName", String(256))
    description: Mapped[str | None] = mapped_column("Description", String(1024))
    status: Mapped[str] = mapped_column("Status", String(32))
    published_version_id: Mapped[int | None] = mapped_column("PublishedVersionId")
    owner_team: Mapped[str | None] = mapped_column("OwnerTeam", String(128))
    tags_json: Mapped[list] = mapped_column("TagsJson", JSONB)
    metadata_json: Mapped[dict] = mapped_column("MetadataJson", JSONB)


class AgentDefinitionVersionOrm(_Base):
    __tablename__ = "agent_definition_versions"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    agent_definition_id: Mapped[int] = mapped_column(
        "AgentDefinitionId", ForeignKey("agent_definitions.Id")
    )
    version_number: Mapped[int] = mapped_column("VersionNumber", Integer)
    version_status: Mapped[str] = mapped_column("VersionStatus", String(32))
    version_label: Mapped[str | None] = mapped_column("VersionLabel", String(64))
    change_summary: Mapped[str | None] = mapped_column("ChangeSummary", String(512))
    system_prompt_template: Mapped[str] = mapped_column("SystemPromptTemplate", Text)
    default_locale: Mapped[str | None] = mapped_column("DefaultLocale", String(16))
    model_binding_key: Mapped[str] = mapped_column("model_binding_key", String(128))
    runtime_options_json: Mapped[dict] = mapped_column("RuntimeOptionsJson", JSONB)
    handoff_policy_json: Mapped[dict] = mapped_column("HandoffPolicyJson", JSONB)
    response_policy_json: Mapped[dict] = mapped_column("ResponsePolicyJson", JSONB)
    guardrails_policy_json: Mapped[dict] = mapped_column("GuardrailsPolicyJson", JSONB)
    checksum: Mapped[str] = mapped_column("Checksum", String(128))
    published_at_utc: Mapped[str | None] = mapped_column("PublishedAtUtc")


class AgentToolBindingOrm(_Base):
    __tablename__ = "agent_tool_bindings"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    agent_definition_version_id: Mapped[int] = mapped_column(
        "AgentDefinitionVersionId",
        ForeignKey("agent_definition_versions.Id"),
    )
    tool_name: Mapped[str] = mapped_column("ToolName", String(128))
    display_name: Mapped[str | None] = mapped_column("DisplayName", String(256))
    description: Mapped[str | None] = mapped_column("Description", String(512))
    invocation_mode: Mapped[str] = mapped_column("InvocationMode", String(32))
    is_required: Mapped[bool] = mapped_column("IsRequired", Boolean)
    config_json: Mapped[dict] = mapped_column("ConfigJson", JSONB)
    sort_order: Mapped[int] = mapped_column("SortOrder", Integer)
    is_enabled: Mapped[bool] = mapped_column("IsEnabled", Boolean)


class AgentKnowledgeBaseBindingOrm(_Base):
    __tablename__ = "agent_knowledge_base_bindings"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    agent_definition_version_id: Mapped[int] = mapped_column(
        "AgentDefinitionVersionId",
        ForeignKey("agent_definition_versions.Id"),
    )
    knowledge_base_id: Mapped[int] = mapped_column("KnowledgeBaseId", BigInteger)
    sort_order: Mapped[int] = mapped_column("SortOrder", Integer)
    is_enabled: Mapped[bool] = mapped_column("IsEnabled", Boolean)
    config_json: Mapped[dict] = mapped_column("ConfigJson", JSONB)


class AgentCatalogRevisionOrm(_Base):
    __tablename__ = "agent_catalog_revisions"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    revision_number: Mapped[int] = mapped_column("RevisionNumber", BigInteger, unique=True)


class AgentMcpServerConfigOrm(_Base):
    """Read-only projection of ``agent_mcp_server_configs`` (owned by .NET)."""

    __tablename__ = "agent_mcp_server_configs"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column("Name", String(128), unique=True)
    transport: Mapped[str] = mapped_column("Transport", String(32))
    config_json: Mapped[dict] = mapped_column("ConfigJson", JSONB)
    is_active: Mapped[bool] = mapped_column("IsActive", Boolean)


class AgentMcpBindingOrm(_Base):
    """Read-only projection of ``agent_mcp_bindings`` (owned by .NET)."""

    __tablename__ = "agent_mcp_bindings"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    agent_definition_version_id: Mapped[int] = mapped_column(
        "AgentDefinitionVersionId",
        ForeignKey("agent_definition_versions.Id"),
    )
    server_name: Mapped[str] = mapped_column("ServerName", String(128))
    is_enabled: Mapped[bool] = mapped_column("IsEnabled", Boolean)
    tool_whitelist: Mapped[list | None] = mapped_column("ToolWhitelistJson", JSONB, nullable=True)
    config_overrides: Mapped[dict] = mapped_column("ConfigOverridesJson", JSONB)


class AgentSkillDefinitionOrm(_Base):
    """Read-only projection of ``agent_skill_definitions`` (owned by .NET)."""

    __tablename__ = "agent_skill_definitions"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    skill_key: Mapped[str] = mapped_column("SkillKey", String(128), unique=True)
    display_name: Mapped[str] = mapped_column("DisplayName", String(256))
    description: Mapped[str] = mapped_column("Description", String(1024))
    version: Mapped[str] = mapped_column("Version", String(32))
    spec_json: Mapped[dict[str, Any]] = mapped_column("SpecJson", JSONB)
    is_published: Mapped[bool] = mapped_column("IsPublished", Boolean)


class AgentSkillBindingOrm(_Base):
    """Read-only projection of ``agent_skill_bindings`` (owned by .NET)."""

    __tablename__ = "agent_skill_bindings"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    agent_definition_version_id: Mapped[int] = mapped_column(
        "AgentDefinitionVersionId",
        ForeignKey("agent_definition_versions.Id"),
    )
    skill_key: Mapped[str] = mapped_column("SkillKey", String(128))
    is_enabled: Mapped[bool] = mapped_column("IsEnabled", Boolean)
    binding_order: Mapped[int] = mapped_column("BindingOrder", Integer)
    config_json: Mapped[dict] = mapped_column("ConfigJson", JSONB)
    tool_overrides_json: Mapped[list | None] = mapped_column("ToolOverridesJson", JSONB, nullable=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Loader protocol + implementation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AgentDefinitionLoader(Protocol):
    """Protocol for loading agent definitions."""

    async def load(
        self, agent_key: str, version: int | None = None
    ) -> AgentDefinitionSnapshot | None:
        """Load a published definition. version=None → current published."""
        ...

    async def check_revision(self) -> int:
        """Get current agent catalog revision for cache invalidation."""
        ...


class SqlAlchemyAgentDefinitionLoader:
    """Loads agent definitions from the shared PostgreSQL database.

    Follows the same async session pattern as llm_gateway's SqlAlchemyModelCatalogRepository.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: AgentDefinitionCache | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._cache = cache or InMemoryAgentDefinitionCache()

    async def load(
        self, agent_key: str, version: int | None = None
    ) -> AgentDefinitionSnapshot | None:
        # Check cache first
        cached = await self._cache.get(agent_key, version)
        if cached is not None:
            return cached

        async with self._session_factory() as session:
            snapshot = await self._load_from_db(session, agent_key, version)

        if snapshot is not None:
            await self._cache.put(snapshot)

        return snapshot

    async def check_revision(self) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentCatalogRevisionOrm.revision_number)
                .order_by(AgentCatalogRevisionOrm.revision_number.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return row or 0

    async def refresh_if_stale(self) -> bool:
        """Check revision and invalidate cache if stale. Returns True if refreshed."""
        current_revision = await self.check_revision()
        cached_revision = await self._cache.get_revision()

        if current_revision > cached_revision:
            await self._cache.invalidate()
            await self._cache.set_revision(current_revision)
            logger.info(
                "Agent definition cache refreshed: revision %d → %d",
                cached_revision,
                current_revision,
            )
            return True
        return False

    async def _load_from_db(
        self,
        session: AsyncSession,
        agent_key: str,
        version: int | None,
    ) -> AgentDefinitionSnapshot | None:
        # Load definition
        result = await session.execute(
            select(AgentDefinitionOrm).where(AgentDefinitionOrm.agent_key == agent_key)
        )
        definition = result.scalar_one_or_none()
        if definition is None:
            return None
        if definition.status == "disabled":
            return None

        # Resolve version
        if version is not None:
            ver_result = await session.execute(
                select(AgentDefinitionVersionOrm).where(
                    AgentDefinitionVersionOrm.agent_definition_id == definition.id,
                    AgentDefinitionVersionOrm.version_number == version,
                    AgentDefinitionVersionOrm.version_status == "published",
                )
            )
        elif definition.published_version_id:
            ver_result = await session.execute(
                select(AgentDefinitionVersionOrm).where(
                    AgentDefinitionVersionOrm.id == definition.published_version_id,
                )
            )
        else:
            return None

        ver = ver_result.scalar_one_or_none()
        if ver is None:
            return None

        # Load tool bindings
        tools_result = await session.execute(
            select(AgentToolBindingOrm)
            .where(
                AgentToolBindingOrm.agent_definition_version_id == ver.id,
                AgentToolBindingOrm.is_enabled == True,  # noqa: E712
            )
            .order_by(AgentToolBindingOrm.sort_order)
        )
        tool_rows = tools_result.scalars().all()

        tools = tuple(
            ToolBindingSnapshot(
                tool_name=t.tool_name,
                description=t.description,
                invocation_mode=t.invocation_mode,
                is_required=t.is_required,
                config=dict(t.config_json or {}),
            )
            for t in tool_rows
        )

        return AgentDefinitionSnapshot(
            agent_key=definition.agent_key,
            version_number=ver.version_number,
            display_name=definition.display_name,
            description=definition.description,
            status=definition.status,
            default_locale=ver.default_locale,
            system_prompt_template=ver.system_prompt_template,
            model_binding_key=ver.model_binding_key,
            tools=tools,
            knowledge_sources=(),
            knowledge_bindings=await self._load_knowledge_bindings(session, ver.id),
            runtime_options=dict(ver.runtime_options_json or {}),
            handoff_policy=dict(ver.handoff_policy_json or {}),
            response_policy=dict(ver.response_policy_json or {}),
            guardrails_policy=dict(ver.guardrails_policy_json or {}),
            checksum=ver.checksum or "",
            updated_at=str(ver.published_at_utc or ""),
            mcp_bindings=await self._load_mcp_bindings(session, ver.id),
            skill_bindings=await self._load_skill_bindings(session, ver.id),
        )

    async def _load_knowledge_bindings(
        self,
        session: AsyncSession,
        version_id: int,
    ) -> tuple[KnowledgeBindingSnapshot, ...]:
        result = await session.execute(
            select(AgentKnowledgeBaseBindingOrm)
            .where(
                AgentKnowledgeBaseBindingOrm.agent_definition_version_id == version_id,
                AgentKnowledgeBaseBindingOrm.is_enabled == True,  # noqa: E712
            )
            .order_by(
                AgentKnowledgeBaseBindingOrm.sort_order,
                AgentKnowledgeBaseBindingOrm.knowledge_base_id,
            )
        )
        rows = result.scalars().all()
        return tuple(
            KnowledgeBindingSnapshot(
                knowledge_base_id=str(row.knowledge_base_id),
                sort_order=row.sort_order,
                config=dict(row.config_json or {}),
                config_version=1,
            )
            for row in rows
        )

    async def _load_mcp_bindings(
        self,
        session: AsyncSession,
        version_id: int,
    ) -> tuple[McpBindingSnapshot, ...]:
        """Load MCP bindings for a version, resolving server configs inline.

        Rows in ``agent_mcp_bindings`` reference ``agent_mcp_server_configs``
        by ``server_name``.  Both tables are read-only from the Python side.
        Inactive server configs and disabled bindings are silently skipped so
        the caller always receives a ready-to-use tuple.
        """
        binding_result = await session.execute(
            select(AgentMcpBindingOrm).where(
                AgentMcpBindingOrm.agent_definition_version_id == version_id,
                AgentMcpBindingOrm.is_enabled == True,  # noqa: E712
            )
        )
        binding_rows = binding_result.scalars().all()
        if not binding_rows:
            return ()

        # Batch-load referenced server configs by name
        server_names = {b.server_name for b in binding_rows}
        config_result = await session.execute(
            select(AgentMcpServerConfigOrm).where(
                AgentMcpServerConfigOrm.name.in_(server_names),
                AgentMcpServerConfigOrm.is_active == True,  # noqa: E712
            )
        )
        configs_by_name: dict[str, dict[str, Any]] = {
            row.name: dict(row.config_json or {})
            for row in config_result.scalars().all()
        }

        snapshots: list[McpBindingSnapshot] = []
        for b in binding_rows:
            base_config = configs_by_name.get(b.server_name)
            if base_config is None:
                logger.warning(
                    "mcp_binding_skip version_id=%s server=%s reason=config_not_found_or_inactive",
                    version_id,
                    b.server_name,
                )
                continue

            # Merge config_overrides on top of base config (shallow merge)
            overrides = dict(b.config_overrides or {})
            resolved_config = {**base_config, **overrides, "name": b.server_name}

            raw_whitelist: list[str] | None = b.tool_whitelist
            tool_whitelist: tuple[str, ...] | None = (
                tuple(raw_whitelist) if raw_whitelist is not None else None
            )

            snapshots.append(
                McpBindingSnapshot(
                    server_name=b.server_name,
                    is_enabled=b.is_enabled,
                    tool_whitelist=tool_whitelist,
                    server_config_json=resolved_config,
                )
            )

        return tuple(snapshots)

    async def _load_skill_bindings(
        self,
        session: AsyncSession,
        version_id: int,
    ) -> tuple[SkillBindingSnapshot, ...]:
        """Load enabled skill bindings for a version, ordered by binding_order.

        Only bindings where ``IsEnabled=True`` are returned. Rows whose
        ``skill_key`` does not reference a published skill definition are
        silently skipped so a missing or unpublished skill never hard-errors
        a running agent.
        """
        result = await session.execute(
            select(AgentSkillBindingOrm)
            .where(
                AgentSkillBindingOrm.agent_definition_version_id == version_id,
                AgentSkillBindingOrm.is_enabled == True,  # noqa: E712
            )
            .order_by(AgentSkillBindingOrm.binding_order)
        )
        rows = result.scalars().all()
        if not rows:
            return ()

        skill_keys = {row.skill_key for row in rows}
        definition_result = await session.execute(
            select(AgentSkillDefinitionOrm).where(
                AgentSkillDefinitionOrm.skill_key.in_(skill_keys),
                AgentSkillDefinitionOrm.is_published == True,  # noqa: E712
            )
        )
        definitions_by_key = {
            row.skill_key: SkillDefinitionSnapshot(
                skill_key=row.skill_key,
                display_name=row.display_name,
                description=row.description,
                version=row.version,
                spec=dict(row.spec_json or {}),
            )
            for row in definition_result.scalars().all()
        }

        snapshots: list[SkillBindingSnapshot] = []
        for row in rows:
            definition = definitions_by_key.get(row.skill_key)
            if definition is None:
                logger.warning(
                    "skill_binding_skip version_id=%s skill=%s reason=definition_not_found_or_unpublished",
                    version_id,
                    row.skill_key,
                )
                continue
            raw_overrides: list[dict[str, Any]] | None = row.tool_overrides_json
            snapshots.append(
                SkillBindingSnapshot(
                    skill_key=row.skill_key,
                    is_enabled=row.is_enabled,
                    binding_order=row.binding_order,
                    config=dict(row.config_json or {}),
                    tool_overrides_raw=tuple(raw_overrides) if raw_overrides else (),
                    definition=definition,
                )
            )
        return tuple(snapshots)



class StaticAgentDefinitionLoader:
    """In-memory loader for testing. Preloaded with static definitions."""

    def __init__(self, definitions: dict[str, AgentDefinitionSnapshot] | None = None) -> None:
        self._definitions = dict(definitions or {})
        self._revision = 1

    async def load(
        self, agent_key: str, version: int | None = None
    ) -> AgentDefinitionSnapshot | None:
        snapshot = self._definitions.get(agent_key)
        if snapshot is None:
            return None
        if version is not None and snapshot.version_number != version:
            return None
        return snapshot

    async def check_revision(self) -> int:
        return self._revision

    def register(self, snapshot: AgentDefinitionSnapshot) -> None:
        self._definitions[snapshot.agent_key] = snapshot
