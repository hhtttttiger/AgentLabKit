"""AgentTool definition CRUD."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import AgentTool


class ToolDefinitionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_tool_defs(self, *, page: int, page_size: int, source_type: str | None = None, status: str | None = None, search: str | None = None):
        query = select(AgentTool)
        count_q = select(func.count()).select_from(AgentTool)
        if source_type:
            source_db = "builtin" if source_type == "builtin" else "external"
            query = query.where(AgentTool.source == source_db)
            count_q = count_q.where(AgentTool.source == source_db)
        if status:
            query = query.where(AgentTool.status == status)
            count_q = count_q.where(AgentTool.status == status)
        if search:
            pattern = f"%{search}%"
            query = query.where(AgentTool.tool_name.ilike(pattern) | AgentTool.display_name.ilike(pattern) | AgentTool.description.ilike(pattern))
            count_q = count_q.where(AgentTool.tool_name.ilike(pattern) | AgentTool.display_name.ilike(pattern) | AgentTool.description.ilike(pattern))
        query = query.order_by(AgentTool.id.desc())
        total = (await self._db.execute(count_q)).scalar() or 0
        items = (await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return [self._to_view(t) for t in items], total

    async def get_tool_def(self, tool_name: str) -> dict:
        return self._to_view(await self._get(tool_name))

    async def create_tool_def(self, **kwargs) -> dict:
        tool = AgentTool(
            tool_name=kwargs["tool_name"],
            display_name=kwargs["display_name"],
            description=kwargs.get("description"),
            parameters_json=kwargs.get("parameters_json", {}),
            source="external",
            status="active",
            tags_json=kwargs.get("tags_json", []),
            endpoint_url=kwargs.get("endpoint_url"),
            http_method=kwargs.get("http_method", "POST"),
            credential_key=kwargs.get("credential_key"),
            timeout_seconds=kwargs.get("timeout_seconds", 30),
            max_retries=kwargs.get("max_retries", 0),
        )
        self._db.add(tool)
        await self._db.flush()
        await self._db.commit()
        return self._to_view(tool)

    async def update_tool_def(self, tool_name: str, **kwargs) -> dict:
        tool = await self._get(tool_name)
        field_map = {
            "display_name", "description", "parameters_json", "tags_json",
            "endpoint_url", "http_method", "credential_key",
            "timeout_seconds", "max_retries", "status",
        }
        for key, value in kwargs.items():
            if key in field_map and value is not None:
                setattr(tool, key, value)
        await self._db.commit()
        return self._to_view(tool)

    async def disable_tool_def(self, tool_name: str) -> dict:
        tool = await self._get(tool_name)
        tool.is_enabled = False
        tool.status = "disabled"
        await self._db.commit()
        return self._to_view(tool)

    async def sync_builtin_tools(self, specs: list[dict]) -> int:
        """Upsert built-in tool definitions from the runtime ToolRegistry.

        *specs* is a list of dicts with keys: ``name``, ``description``,
        ``parameters_schema``, ``label``.  Each is upserted into *agent_tools*
        with ``source='builtin'``.  Returns the number of tools synced.
        """
        if not specs:
            return 0

        rows = [
            {
                "tool_name": s["name"],
                "display_name": s.get("label") or s["name"],
                "description": s.get("description", ""),
                "parameters_json": s.get("parameters_schema", {}),
                "source": "builtin",
                "is_enabled": True,
                "status": "active",
                "tags_json": s.get("tags", []),
                "endpoint_url": None,
                "http_method": "POST",
                "credential_key": None,
                "timeout_seconds": 30,
                "max_retries": 0,
            }
            for s in specs
        ]

        stmt = pg_insert(AgentTool).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AgentTool.tool_name],
            set_={
                "display_name": stmt.excluded.display_name,
                "description": stmt.excluded.description,
                "parameters_json": stmt.excluded.parameters_json,
                "source": "builtin",
                "status": "active",
            },
        )
        await self._db.execute(stmt)
        await self._db.commit()
        return len(rows)

    async def _get(self, tool_name: str) -> AgentTool:
        result = await self._db.execute(select(AgentTool).where(AgentTool.tool_name == tool_name))
        tool = result.scalar_one_or_none()
        if tool is None:
            raise NotFoundError("ToolDefinition", tool_name)
        return tool

    @staticmethod
    def _to_view(t: AgentTool) -> dict:
        return {
            "id": str(t.id),
            "toolName": t.tool_name,
            "displayName": t.display_name,
            "description": t.description or "",
            "sourceType": "builtin" if t.source == "builtin" else "http_external",
            "status": t.status,
            "parametersSchema": t.parameters_json,
            "tags": t.tags_json,
            "endpointUrl": t.endpoint_url,
            "httpMethod": t.http_method,
            "credentialKey": t.credential_key,
            "timeoutSeconds": t.timeout_seconds,
            "maxRetries": t.max_retries,
            "createdAtUtc": t.created_at_utc.isoformat() if t.created_at_utc else "",
            "updatedAtUtc": t.updated_at_utc.isoformat() if t.updated_at_utc else None,
        }
