"""BackendAgentDefinitionLoader — adapts backend ORM to agent_runtime snapshots.

The runtime ships its own ``SqlAlchemyAgentDefinitionLoader`` (in
``agent_runtime.definition.loader``), but that one targets the cross-language
(.NET-owned) PascalCase read model (``"Status"``, ``"PublishedVersionId"``,
``"SystemPromptTemplate"`` …). The backend's own tables in
:mod:`modules.agent.models` use a different snake_case schema, so we need this
adapter to bridge them into :class:`AgentDefinitionSnapshot`.

Implements the :class:`agent_runtime.definition.loader.AgentDefinitionLoader`
protocol — ``load`` + ``check_revision`` — so the runtime can resolve a
published agent definition by key/version.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_runtime.definition.cache import AgentDefinitionCache, InMemoryAgentDefinitionCache
from agent_runtime.definition.models import (
    AgentDefinitionSnapshot,
    KnowledgeBindingSnapshot,
    McpBindingSnapshot,
    SkillBindingSnapshot,
    SkillDefinitionSnapshot,
    ToolBindingSnapshot,
)

from .models import (
    AgentCatalogRevision,
    AgentDefinition,
    AgentDefinitionVersion,
    AgentKnowledgeBaseBinding,
    AgentMcpBinding,
    AgentMcpServer,
    AgentSkill,
    AgentSkillBinding,
    AgentToolBinding,
)

logger = logging.getLogger(__name__)


class BackendAgentDefinitionLoader:
    """Loads published agent definitions from the backend's own ORM tables.

    Drop-in for the runtime's loader protocol; constructed once in the app
    lifespan and shared across requests (with an in-memory snapshot cache).
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
                select(AgentCatalogRevision.revision)
                .order_by(AgentCatalogRevision.revision.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
        return row or 0

    async def _load_from_db(
        self,
        session: AsyncSession,
        agent_key: str,
        version: int | None,
    ) -> AgentDefinitionSnapshot | None:
        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
        )
        definition = result.scalar_one_or_none()
        if definition is None:
            return None
        if not definition.is_enabled:
            return None

        # version=None  →  resolve the currently published version number.
        target_version = version if version is not None else definition.published_version
        if target_version is None:
            return None

        ver_result = await session.execute(
            select(AgentDefinitionVersion).where(
                AgentDefinitionVersion.agent_id == definition.id,
                AgentDefinitionVersion.version_number == target_version,
            )
        )
        ver = ver_result.scalar_one_or_none()
        if ver is None:
            return None

        # The backend stores the editor's rich fields (locale, runtime knobs,
        # and the policy blobs) as a structured sub-document inside the
        # version's extra_json column. Read each known key out individually;
        # older/empty rows simply yield empty dicts / None.
        extra = ver.extra_json or {}
        runtime_options = dict(extra.get("runtime_options") or {})
        handoff_policy = dict(extra.get("handoff_policy") or {})
        response_policy = dict(extra.get("response_policy") or {})
        guardrails_policy = dict(extra.get("guardrails_policy") or {})
        default_locale = extra.get("default_locale")

        return AgentDefinitionSnapshot(
            agent_key=definition.agent_key,
            version_number=int(ver.version_number),
            display_name=definition.display_name,
            description=definition.description,
            status="published",
            system_prompt_template=ver.system_prompt or "",
            model_binding_key=ver.model_binding_key or "",
            tools=await self._load_tool_bindings(session, ver.id),
            knowledge_sources=(),
            knowledge_bindings=await self._load_knowledge_bindings(session, ver.id),
            default_locale=default_locale,
            runtime_options=runtime_options,
            handoff_policy=handoff_policy,
            response_policy=response_policy,
            guardrails_policy=guardrails_policy,
            checksum=ver.checksum or "",
            updated_at="",
            mcp_bindings=await self._load_mcp_bindings(session, ver.id),
            skill_bindings=await self._load_skill_bindings(session, ver.id),
        )

    async def _load_tool_bindings(
        self, session: AsyncSession, version_id: int
    ) -> tuple[ToolBindingSnapshot, ...]:
        result = await session.execute(
            select(AgentToolBinding).where(
                AgentToolBinding.agent_version_id == version_id,
                AgentToolBinding.is_enabled == True,  # noqa: E712
            )
        )
        return tuple(
            ToolBindingSnapshot(
                tool_name=binding.tool_name,
                invocation_mode=(binding.extra_json or {}).get("invocation_mode", "auto"),
                config=dict(binding.extra_json or {}),
            )
            for binding in result.scalars().all()
        )

    async def _load_mcp_bindings(
        self, session: AsyncSession, version_id: int
    ) -> tuple[McpBindingSnapshot, ...]:
        binding_result = await session.execute(
            select(AgentMcpBinding).where(
                AgentMcpBinding.agent_version_id == version_id,
                AgentMcpBinding.is_enabled == True,  # noqa: E712
            )
        )
        bindings = binding_result.scalars().all()
        if not bindings:
            return ()

        server_names = {b.server_name for b in bindings}
        server_result = await session.execute(
            select(AgentMcpServer).where(
                AgentMcpServer.name.in_(server_names),
                AgentMcpServer.is_enabled == True,  # noqa: E712
            )
        )
        servers_by_name: dict[str, AgentMcpServer] = {
            s.name: s for s in server_result.scalars().all()
        }

        snapshots: list[McpBindingSnapshot] = []
        for binding in bindings:
            server = servers_by_name.get(binding.server_name)
            if server is None:
                logger.warning(
                    "mcp_binding_refers_to_missing_server server=%s version_id=%s",
                    binding.server_name,
                    version_id,
                )
                continue

            server_config = {
                "name": server.name,
                "transport": server.transport_type,
                "command": server.command,
                "args": list(server.args_json) if server.args_json else [],
                "env": {},
                "url": server.url,
                "headers": dict(server.headers_json) if server.headers_json else {},
            }

            binding_extra = binding.extra_json or {}
            config_overrides = dict(binding_extra.get("config_overrides") or {})
            if config_overrides:
                server_config.update(config_overrides)

            tool_whitelist_raw = binding_extra.get("tool_whitelist")
            tool_whitelist: tuple[str, ...] | None = (
                tuple(tool_whitelist_raw)
                if isinstance(tool_whitelist_raw, list)
                else None
            )

            snapshots.append(
                McpBindingSnapshot(
                    server_name=binding.server_name,
                    is_enabled=binding.is_enabled,
                    tool_whitelist=tool_whitelist,
                    server_config_json=server_config,
                )
            )

        return tuple(snapshots)

    async def _load_knowledge_bindings(
        self, session: AsyncSession, version_id: int
    ) -> tuple[KnowledgeBindingSnapshot, ...]:
        result = await session.execute(
            select(AgentKnowledgeBaseBinding).where(
                AgentKnowledgeBaseBinding.agent_version_id == version_id,
                AgentKnowledgeBaseBinding.is_enabled == True,  # noqa: E712
            )
        )
        # knowledge_base_id is kept as str to match the runtime's snapshot
        # contract and the str-based retrieval chain (asearch/asearch_multi).
        return tuple(
            KnowledgeBindingSnapshot(
                knowledge_base_id=str(binding.knowledge_base_id),
                sort_order=0,
                config=dict(binding.extra_json or {}),
            )
            for binding in result.scalars().all()
        )

    async def _load_skill_bindings(
        self, session: AsyncSession, version_id: int
    ) -> tuple[SkillBindingSnapshot, ...]:
        """Load enabled skill bindings for a version, resolving skill definitions.

        Only bindings with ``is_enabled=True`` are returned. Bindings whose
        ``skill_key`` does not reference a published skill are silently skipped.
        The skill's ``content`` column is parsed as JSON to produce the
        ``SkillDefinitionSnapshot.spec`` dict (``version`` key is extracted).
        """
        import json as _json

        binding_result = await session.execute(
            select(AgentSkillBinding).where(
                AgentSkillBinding.agent_version_id == version_id,
                AgentSkillBinding.is_enabled == True,  # noqa: E712
            )
        )
        bindings = binding_result.scalars().all()
        if not bindings:
            return ()

        skill_keys = {b.skill_key for b in bindings}
        skill_result = await session.execute(
            select(AgentSkill).where(
                AgentSkill.skill_key.in_(skill_keys),
                AgentSkill.is_published == True,  # noqa: E712
            )
        )
        skills_by_key: dict[str, AgentSkill] = {
            s.skill_key: s for s in skill_result.scalars().all()
        }

        snapshots: list[SkillBindingSnapshot] = []
        for binding in bindings:
            skill = skills_by_key.get(binding.skill_key)
            if skill is None:
                logger.warning(
                    "skill_binding_skip version_id=%s skill=%s reason=definition_not_found_or_unpublished",
                    version_id,
                    binding.skill_key,
                )
                continue

            # Parse skill.content as JSON → spec dict; extract version.
            try:
                raw_spec = _json.loads(skill.content) if skill.content else {}
            except _json.JSONDecodeError:
                logger.warning(
                    "skill_content_invalid_json skill=%s — treating as empty spec",
                    binding.skill_key,
                )
                raw_spec = {}

            if not isinstance(raw_spec, dict):
                raw_spec = {}

            version = str(raw_spec.pop("version", "1.0.0"))

            definition = SkillDefinitionSnapshot(
                skill_key=skill.skill_key,
                display_name=skill.display_name,
                description=skill.description or "",
                version=version,
                spec=raw_spec,
            )

            binding_extra = binding.extra_json or {}
            binding_order = int(binding_extra.get("binding_order", 100))
            config = dict(binding_extra.get("config") or {})
            tool_overrides_raw = binding_extra.get("tool_overrides")

            snapshots.append(
                SkillBindingSnapshot(
                    skill_key=binding.skill_key,
                    is_enabled=binding.is_enabled,
                    binding_order=binding_order,
                    config=config,
                    tool_overrides_raw=tuple(tool_overrides_raw) if isinstance(tool_overrides_raw, list) else (),
                    definition=definition,
                )
            )

        return tuple(snapshots)
