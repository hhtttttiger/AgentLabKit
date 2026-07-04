"""AgentDefinition CRUD, version management, publish/disable, audits, bindings."""

from __future__ import annotations

from sqlalchemy import delete, insert, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import list_entities, create_entity
from common.errors import NotFoundError, BusinessError
from ..models import (
    AgentDefinition,
    AgentDefinitionVersion,
    AgentMcpBinding,
    AgentSkillBinding,
    AgentToolBinding,
    AgentKnowledgeBaseBinding,
    AgentExecutionAudit,
)
from ..schemas import VersionCreate


class AgentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Agent CRUD ──────────────────────────────────────────────────

    async def list_options(self) -> list[dict]:
        """下拉选项 — 仅返回 value/label。"""
        from sqlalchemy import select
        result = await self._db.execute(
            select(AgentDefinition.agent_key, AgentDefinition.display_name)
            .where(AgentDefinition.is_enabled == True)
            .order_by(AgentDefinition.agent_key)
        )
        return [{"value": r.agent_key, "label": r.display_name} for r in result.all()]

    async def list_agents(self, *, page: int, page_size: int, status: str | None = None):
        query = select(AgentDefinition)
        count_q = select(func.count()).select_from(AgentDefinition)
        if status == "draft":
            query = query.where(AgentDefinition.is_enabled == True, AgentDefinition.published_version == None)
            count_q = count_q.where(AgentDefinition.is_enabled == True, AgentDefinition.published_version == None)
        elif status == "published":
            query = query.where(AgentDefinition.is_enabled == True, AgentDefinition.published_version != None)
            count_q = count_q.where(AgentDefinition.is_enabled == True, AgentDefinition.published_version != None)
        elif status == "disabled":
            query = query.where(AgentDefinition.is_enabled == False)
            count_q = count_q.where(AgentDefinition.is_enabled == False)
        query = query.order_by(AgentDefinition.id.desc())
        total = (await self._db.execute(count_q)).scalar() or 0
        items = (await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return [self._to_agent_view(a) for a in items], total

    async def create_agent(self, **kwargs) -> dict:
        agent = await create_entity(self._db, AgentDefinition, **kwargs)
        await self._db.commit()
        return self._to_agent_view(agent)

    async def get_agent(self, agent_key: str) -> dict:
        return self._to_agent_view(await self._get_agent(agent_key))

    async def update_agent(self, agent_key: str, **kwargs) -> dict:
        agent = await self._get_agent(agent_key)
        row_version = kwargs.pop("row_version", None)
        if row_version is not None:
            stored_version = agent.updated_at_utc.timestamp() if agent.updated_at_utc else 0
            if abs(stored_version - row_version) > 1e-6:
                raise BusinessError("concurrency_conflict")
        for k, v in kwargs.items():
            setattr(agent, k, v)
        await self._db.commit()
        return self._to_agent_view(agent)

    async def delete_agent(self, agent_key: str) -> None:
        agent = await self._get_agent(agent_key)
        # Find all versions of this agent
        version_ids = (
            await self._db.execute(
                select(AgentDefinitionVersion.id).where(
                    AgentDefinitionVersion.agent_id == agent.id
                )
            )
        ).scalars().all()
        if version_ids:
            # Delete bindings for all versions
            for binding_model in (
                AgentToolBinding,
                AgentSkillBinding,
                AgentMcpBinding,
                AgentKnowledgeBaseBinding,
            ):
                await self._db.execute(
                    delete(binding_model).where(
                        binding_model.agent_version_id.in_(version_ids)
                    )
                )
            # Delete the versions themselves
            await self._db.execute(
                delete(AgentDefinitionVersion).where(
                    AgentDefinitionVersion.agent_id == agent.id
                )
            )
        # Delete audit records
        await self._db.execute(
            delete(AgentExecutionAudit).where(
                AgentExecutionAudit.agent_key == agent_key
            )
        )
        # Finally delete the agent
        await self._db.delete(agent)
        await self._db.commit()

    # ── Versions ────────────────────────────────────────────────────

    async def list_versions(self, agent_key: str, *, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        agent = await self._get_agent(agent_key)
        base = select(AgentDefinitionVersion).where(AgentDefinitionVersion.agent_id == agent.id)
        count_q = select(func.count()).select_from(AgentDefinitionVersion).where(AgentDefinitionVersion.agent_id == agent.id)
        total = (await self._db.execute(count_q)).scalar() or 0
        result = await self._db.execute(
            base.order_by(AgentDefinitionVersion.version_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [self._to_version_summary(v, agent.published_version) for v in result.scalars().all()], total

    async def create_version(self, agent_key: str, body: VersionCreate) -> dict:
        agent = await self._get_agent(agent_key)
        max_ver = await self._db.execute(
            select(func.max(AgentDefinitionVersion.version_number))
            .where(AgentDefinitionVersion.agent_id == agent.id)
        )
        next_ver = (max_ver.scalar() or 0) + 1
        version = await create_entity(
            self._db, AgentDefinitionVersion,
            agent_id=agent.id,
            version_number=next_ver,
            **self._version_columns(body),
            extra_json=self._pack_extra_json(body),
        )
        # create_entity flushes; version.id is now available for FK references
        await self._sync_tool_bindings(version.id, body.tool_bindings)
        await self._sync_kb_bindings(version.id, body.knowledge_base_bindings)
        await self._sync_mcp_bindings(version.id, body.mcp_bindings)
        await self._sync_skill_bindings(version.id, body.skill_bindings)

        await self._db.commit()
        return await self._load_version_detail(version, agent.published_version)

    async def get_version(self, agent_key: str, version_number: int) -> dict:
        agent = await self._get_agent(agent_key)
        version = await self._get_version(agent_key, version_number)
        return await self._load_version_detail(version, agent.published_version)

    async def update_version(self, agent_key: str, version_number: int, body: VersionCreate) -> dict:
        agent = await self._get_agent(agent_key)
        version = await self._get_version(agent_key, version_number)
        for column, value in self._version_columns(body).items():
            setattr(version, column, value)
        # Merge so future/unknown extra_json keys are preserved; the seven
        # editor-managed keys are overwritten from the incoming payload.
        version.extra_json = self._merge_extra_json(version.extra_json or {}, body)
        # Wipe old bindings and bulk-insert new ones in the same transaction
        await self._sync_tool_bindings(version.id, body.tool_bindings)
        await self._sync_kb_bindings(version.id, body.knowledge_base_bindings)
        await self._sync_mcp_bindings(version.id, body.mcp_bindings)
        await self._sync_skill_bindings(version.id, body.skill_bindings)
        await self._db.commit()
        # updated_at_utc is server-generated (onupdate); the async session can't
        # lazy-refresh it after UPDATE, so reload explicitly before reading it.
        await self._db.refresh(version)
        return await self._load_version_detail(version, agent.published_version)

    # ── Binding sync helpers (bulk delete + insert, no per-item loops) ─

    async def _sync_tool_bindings(self, version_id: int, items: list) -> None:
        await self._db.execute(
            delete(AgentToolBinding).where(AgentToolBinding.agent_version_id == version_id)
        )
        if items:
            await self._db.execute(
                insert(AgentToolBinding).values([
                    {
                        "agent_version_id": version_id,
                        "tool_name": item.tool_name,
                        "is_enabled": item.is_enabled,
                        "extra_json": {
                            "display_name": item.display_name,
                            "description": item.description,
                            "invocation_mode": item.invocation_mode,
                            "is_required": item.is_required,
                            "config": item.config,
                            "sort_order": item.sort_order,
                        },
                    }
                    for item in items
                ])
            )

    async def _sync_kb_bindings(self, version_id: int, items: list) -> None:
        await self._db.execute(
            delete(AgentKnowledgeBaseBinding).where(
                AgentKnowledgeBaseBinding.agent_version_id == version_id
            )
        )
        if items:
            await self._db.execute(
                insert(AgentKnowledgeBaseBinding).values([
                    {
                        "agent_version_id": version_id,
                        "knowledge_base_id": int(item.knowledge_base_id),
                        "is_enabled": item.is_enabled,
                        "extra_json": {
                            "sort_order": item.sort_order,
                            "config": item.config,
                        },
                    }
                    for item in items
                ])
            )

    async def _sync_mcp_bindings(self, version_id: int, items: list) -> None:
        await self._db.execute(
            delete(AgentMcpBinding).where(AgentMcpBinding.agent_version_id == version_id)
        )
        if items:
            await self._db.execute(
                insert(AgentMcpBinding).values([
                    {
                        "agent_version_id": version_id,
                        "server_name": item.server_name,
                        "is_enabled": item.is_enabled,
                        "extra_json": {
                            "tool_whitelist": item.tool_whitelist,
                            "config_overrides": item.config_overrides,
                        },
                    }
                    for item in items
                ])
            )

    async def _sync_skill_bindings(self, version_id: int, items: list) -> None:
        await self._db.execute(
            delete(AgentSkillBinding).where(AgentSkillBinding.agent_version_id == version_id)
        )
        if items:
            await self._db.execute(
                insert(AgentSkillBinding).values([
                    {
                        "agent_version_id": version_id,
                        "skill_key": item.skill_key,
                        "is_enabled": item.is_enabled,
                        "extra_json": {
                            "binding_order": item.binding_order,
                            "config": item.config,
                            "tool_overrides": item.tool_overrides,
                        },
                    }
                    for item in items
                ])
            )

    async def _load_version_detail(self, version, published_version) -> dict:
        """Load bindings from DB and assemble the full version detail view."""
        import asyncio
        tool_rows, kb_rows, mcp_rows, skill_rows = await asyncio.gather(
            self._fetch_bindings(AgentToolBinding, version.id),
            self._fetch_bindings(AgentKnowledgeBaseBinding, version.id),
            self._fetch_bindings(AgentMcpBinding, version.id),
            self._fetch_bindings(AgentSkillBinding, version.id),
        )
        return self._to_version_detail(
            version, published_version,
            tool_bindings=tool_rows,
            kb_bindings=kb_rows,
            mcp_bindings=mcp_rows,
            skill_bindings=skill_rows,
        )

    async def _fetch_bindings(self, model, version_id: int):
        result = await self._db.execute(
            select(model).where(model.agent_version_id == version_id)
        )
        return result.scalars().all()

    # ── Publish / Disable ───────────────────────────────────────────

    async def publish_agent(self, agent_key: str, version_number: int | None = None) -> dict:
        agent = await self._get_agent(agent_key)
        if version_number is not None:
            ver = await self._db.execute(
                select(AgentDefinitionVersion)
                .where(
                    AgentDefinitionVersion.agent_id == agent.id,
                    AgentDefinitionVersion.version_number == version_number,
                )
            )
            ver = ver.scalar_one_or_none()
            if ver is None:
                raise NotFoundError("AgentVersion", f"{agent_key}/v{version_number}")
        else:
            latest = await self._db.execute(
                select(AgentDefinitionVersion)
                .where(AgentDefinitionVersion.agent_id == agent.id)
                .order_by(AgentDefinitionVersion.version_number.desc()).limit(1)
            )
            ver = latest.scalar_one_or_none()
            if ver is None:
                raise BusinessError("No versions to publish")
        agent.published_version = ver.version_number
        await self._db.commit()
        # updated_at_utc is server-generated (onupdate); async session expires
        # instances after commit, so reload explicitly before reading it.
        await self._db.refresh(agent)
        return self._to_agent_view(agent)

    async def disable_agent(self, agent_key: str) -> dict:
        agent = await self._get_agent(agent_key)
        agent.is_enabled = False
        await self._db.commit()
        return self._to_agent_view(agent)

    # ── Audits ──────────────────────────────────────────────────────

    async def list_audits(self, agent_key: str, *, page: int, page_size: int):
        query = (
            select(AgentExecutionAudit)
            .where(AgentExecutionAudit.agent_key == agent_key)
            .order_by(AgentExecutionAudit.id.desc())
        )
        total = (await self._db.execute(
            select(func.count()).select_from(AgentExecutionAudit)
            .where(AgentExecutionAudit.agent_key == agent_key)
        )).scalar() or 0
        items = (await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return [self._to_audit_view(a) for a in items], total

    async def get_audit(self, agent_key: str, run_id: str) -> dict:
        result = await self._db.execute(
            select(AgentExecutionAudit).where(
                AgentExecutionAudit.agent_key == agent_key,
                AgentExecutionAudit.run_id == run_id,
            )
        )
        audit = result.scalar_one_or_none()
        if audit is None:
            raise NotFoundError("Audit", run_id)
        return self._to_audit_view(audit)

    # ── Tool Bindings (per version) ─────────────────────────────────

    async def list_tool_bindings(self, agent_key: str, version_number: int) -> list[dict]:
        version = await self._get_version(agent_key, version_number)
        result = await self._db.execute(
            select(AgentToolBinding).where(AgentToolBinding.agent_version_id == version.id)
        )
        return [self._to_tool_binding_view(b) for b in result.scalars().all()]

    async def create_tool_binding(self, agent_key: str, version_number: int, **kwargs) -> dict:
        version = await self._get_version(agent_key, version_number)
        binding = await create_entity(self._db, AgentToolBinding, agent_version_id=version.id, **kwargs)
        await self._db.commit()
        return self._to_tool_binding_view(binding)

    # ── KB Bindings (per version) ───────────────────────────────────

    async def list_kb_bindings(self, agent_key: str, version_number: int) -> list[dict]:
        version = await self._get_version(agent_key, version_number)
        result = await self._db.execute(
            select(AgentKnowledgeBaseBinding).where(AgentKnowledgeBaseBinding.agent_version_id == version.id)
        )
        return [
            {"id": b.id, "knowledgeBaseId": b.knowledge_base_id, "isEnabled": b.is_enabled}
            for b in result.scalars().all()
        ]

    async def create_kb_binding(self, agent_key: str, version_number: int, **kwargs) -> dict:
        version = await self._get_version(agent_key, version_number)
        binding = await create_entity(self._db, AgentKnowledgeBaseBinding, agent_version_id=version.id, **kwargs)
        await self._db.commit()
        return {"id": binding.id, "knowledgeBaseId": binding.knowledge_base_id, "isEnabled": binding.is_enabled}

    # ── Private helpers ─────────────────────────────────────────────

    async def _get_agent(self, agent_key: str) -> AgentDefinition:
        result = await self._db.execute(
            select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            raise NotFoundError("Agent", agent_key)
        return agent

    async def _get_version(self, agent_key: str, version_number: int) -> AgentDefinitionVersion:
        agent = await self._get_agent(agent_key)
        result = await self._db.execute(
            select(AgentDefinitionVersion).where(
                AgentDefinitionVersion.agent_id == agent.id,
                AgentDefinitionVersion.version_number == version_number,
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise NotFoundError("AgentVersion", f"{agent_key}/v{version_number}")
        return version

    # ── View mappers ────────────────────────────────────────────────

    @staticmethod
    def _to_agent_view(a: AgentDefinition) -> dict:
        if not a.is_enabled:
            status = "disabled"
        elif a.published_version is not None:
            status = "published"
        else:
            status = "draft"
        return {
            "id": a.id, "agentKey": a.agent_key, "displayName": a.display_name,
            "description": a.description, "icon": a.icon,
            "status": status,
            "tags": a.tags_json or [],
            "metadata": {},
            "isEnabled": a.is_enabled,
            "publishedVersionNumber": a.published_version,
            "rowVersion": a.updated_at_utc.timestamp() if a.updated_at_utc else 0,
            "createdAtUtc": a.created_at_utc.isoformat() if a.created_at_utc else None,
            "updatedAtUtc": a.updated_at_utc.isoformat() if a.updated_at_utc else None,
        }

    # Rich editor fields persisted as a structured sub-document inside the
    # version's extra_json column (no dedicated columns / migration).
    _EXTRA_KEYS = (
        "version_label",
        "change_summary",
        "default_locale",
        "runtime_options",
        "handoff_policy",
        "response_policy",
        "guardrails_policy",
    )

    @staticmethod
    def _version_status(v: AgentDefinitionVersion, published_version: int | None) -> str:
        if published_version is not None:
            if v.version_number == published_version:
                return "published"
            if v.version_number < published_version:
                return "archived"
        return "draft"

    @classmethod
    def _version_columns(cls, body: VersionCreate) -> dict:
        """Map the editor body onto the real AgentDefinitionVersion columns."""
        return {
            "system_prompt": body.system_prompt_template or None,
            "model_binding_key": body.model_key or None,
            "temperature": body.temperature,
            "max_tokens": body.max_tokens,
            "response_format": body.response_format,
        }

    @classmethod
    def _extra_payload(cls, body: VersionCreate) -> dict:
        return {
            "version_label": body.version_label,
            "change_summary": body.change_summary,
            "default_locale": body.default_locale,
            "runtime_options": dict(body.runtime_options or {}),
            "handoff_policy": dict(body.handoff_policy or {}),
            "response_policy": dict(body.response_policy or {}),
            "guardrails_policy": dict(body.guardrails_policy or {}),
        }

    @classmethod
    def _pack_extra_json(cls, body: VersionCreate) -> dict:
        return cls._extra_payload(body)

    @classmethod
    def _merge_extra_json(cls, existing: dict, body: VersionCreate) -> dict:
        merged = dict(existing or {})
        merged.update(cls._extra_payload(body))
        return merged

    @classmethod
    def _to_version_summary(cls, v: AgentDefinitionVersion, published_version: int | None = None) -> dict:
        extra = v.extra_json or {}
        return {
            "id": v.id, "agentId": v.agent_id, "versionNumber": v.version_number,
            "versionStatus": cls._version_status(v, published_version),
            "versionLabel": extra.get("version_label"),
            "changeSummary": extra.get("change_summary"),
            "modelKey": v.model_binding_key or "",
            "checksum": v.checksum,
            "rowVersion": v.updated_at_utc.timestamp() if v.updated_at_utc else 0,
            "publishedAtUtc": None,
            "createdAtUtc": v.created_at_utc.isoformat() if v.created_at_utc else None,
        }

    @classmethod
    def _to_version_detail(
        cls, v: AgentDefinitionVersion, published_version: int | None = None,
        tool_bindings: list | None = None,
        kb_bindings: list | None = None,
        mcp_bindings: list | None = None,
        skill_bindings: list | None = None,
    ) -> dict:
        extra = v.extra_json or {}
        detail = cls._to_version_summary(v, published_version)
        detail.update({
            "systemPromptTemplate": v.system_prompt or "",
            "defaultLocale": extra.get("default_locale"),
            "runtimeOptions": extra.get("runtime_options") or {},
            "handoffPolicy": extra.get("handoff_policy") or {},
            "responsePolicy": extra.get("response_policy") or {},
            "guardrailsPolicy": extra.get("guardrails_policy") or {},
            "temperature": v.temperature,
            "maxTokens": v.max_tokens,
            "responseFormat": v.response_format,
            "toolBindings": [cls._to_tool_binding_view(b) for b in (tool_bindings or [])],
            "knowledgeBaseBindings": [
                {
                    "id": str(b.id),
                    "knowledgeBaseId": str(b.knowledge_base_id),
                    "isEnabled": b.is_enabled,
                    "sortOrder": (b.extra_json or {}).get("sort_order", 0),
                    "config": (b.extra_json or {}).get("config", {}),
                }
                for b in (kb_bindings or [])
            ],
            "mcpBindings": [
                {
                    "id": str(b.id),
                    "serverName": b.server_name,
                    "isEnabled": b.is_enabled,
                    "toolWhitelist": (b.extra_json or {}).get("tool_whitelist"),
                    "configOverrides": (b.extra_json or {}).get("config_overrides", {}),
                }
                for b in (mcp_bindings or [])
            ],
            "skillBindings": [
                {
                    "id": str(b.id),
                    "skillKey": b.skill_key,
                    "isEnabled": b.is_enabled,
                    "displayName": None,
                    "sortOrder": (b.extra_json or {}).get("binding_order", 0),
                    "configOverrides": (b.extra_json or {}).get("config", {}),
                    "toolOverrides": (b.extra_json or {}).get("tool_overrides") or [],
                }
                for b in (skill_bindings or [])
            ],
        })
        return detail

    @staticmethod
    def _to_audit_view(a: AgentExecutionAudit) -> dict:
        return {
            "id": a.id, "agentKey": a.agent_key, "runId": a.run_id,
            "agentVersion": a.agent_version, "inputSummary": a.input_summary,
            "outputSummary": a.output_summary, "toolCallsJson": a.tool_calls_json,
            "status": a.status, "durationMs": a.duration_ms,
            "tokenUsageJson": a.token_usage_json, "errorMessage": a.error_message,
            "createdAtUtc": a.created_at_utc.isoformat() if a.created_at_utc else None,
        }

    @staticmethod
    def _to_tool_binding_view(b: AgentToolBinding) -> dict:
        extra = b.extra_json or {}
        return {
            "toolName": b.tool_name,
            "displayName": extra.get("display_name"),
            "description": extra.get("description"),
            "invocationMode": extra.get("invocation_mode", "auto"),
            "isRequired": extra.get("is_required", False),
            "config": extra.get("config", {}),
            "sortOrder": extra.get("sort_order", 0),
            "isEnabled": b.is_enabled,
        }
