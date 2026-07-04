"""AgentMcpServer CRUD."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import AgentMcpServer


class McpServerService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_mcp_servers(self, *, page: int, page_size: int):
        query = select(AgentMcpServer).order_by(AgentMcpServer.id.desc())
        total = (await self._db.execute(select(func.count()).select_from(AgentMcpServer))).scalar() or 0
        items = (await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return [self._to_view(s) for s in items], total

    async def get_mcp_server(self, name: str) -> dict:
        return self._to_view(await self._get(name))

    async def create_mcp_server(self, **kwargs) -> dict:
        server = AgentMcpServer(**kwargs)
        self._db.add(server)
        await self._db.flush()
        await self._db.commit()
        return self._to_view(server)

    async def update_mcp_server(self, name: str, **kwargs) -> dict:
        server = await self._get(name)
        for k, v in kwargs.items():
            setattr(server, k, v)
        await self._db.commit()
        return self._to_view(server)

    async def delete_mcp_server(self, name: str) -> None:
        server = await self._get(name)
        await self._db.delete(server)
        await self._db.commit()

    async def _get(self, name: str) -> AgentMcpServer:
        result = await self._db.execute(select(AgentMcpServer).where(AgentMcpServer.name == name))
        server = result.scalar_one_or_none()
        if server is None:
            raise NotFoundError("McpServer", name)
        return server

    @staticmethod
    def _to_view(c: AgentMcpServer) -> dict:
        return {
            "id": c.id, "name": c.name, "displayName": c.display_name,
            "transportType": c.transport_type, "url": c.url,
            "command": c.command, "argsJson": c.args_json,
            "headersJson": c.headers_json, "isEnabled": c.is_enabled,
            "createdAtUtc": c.created_at_utc.isoformat() if c.created_at_utc else None,
        }
