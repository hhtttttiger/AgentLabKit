"""AgentSkill definition CRUD + publish."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import AgentSkill


class SkillDefinitionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_skill_defs(self, *, page: int, page_size: int, published_only: bool = False):
        query = select(AgentSkill)
        count_q = select(func.count()).select_from(AgentSkill)
        if published_only:
            query = query.where(AgentSkill.is_published == True)
            count_q = count_q.where(AgentSkill.is_published == True)
        query = query.order_by(AgentSkill.id.desc())
        total = (await self._db.execute(count_q)).scalar() or 0
        items = (await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return [self._to_view(s) for s in items], total

    async def get_skill_def(self, skill_key: str) -> dict:
        return self._to_view(await self._get(skill_key))

    async def create_skill_def(self, **kwargs) -> dict:
        skill = AgentSkill(**kwargs)
        self._db.add(skill)
        await self._db.flush()
        await self._db.commit()
        return self._to_view(skill)

    async def update_skill_def(self, skill_key: str, **kwargs) -> dict:
        skill = await self._get(skill_key)
        for k, v in kwargs.items():
            setattr(skill, k, v)
        await self._db.commit()
        return self._to_view(skill)

    async def delete_skill_def(self, skill_key: str) -> None:
        skill = await self._get(skill_key)
        await self._db.delete(skill)
        await self._db.commit()

    async def publish_skill_def(self, skill_key: str) -> dict:
        skill = await self._get(skill_key)
        skill.is_published = True
        await self._db.commit()
        return self._to_view(skill)

    async def unpublish_skill_def(self, skill_key: str) -> dict:
        skill = await self._get(skill_key)
        skill.is_published = False
        await self._db.commit()
        return self._to_view(skill)

    async def _get(self, skill_key: str) -> AgentSkill:
        result = await self._db.execute(select(AgentSkill).where(AgentSkill.skill_key == skill_key))
        skill = result.scalar_one_or_none()
        if skill is None:
            raise NotFoundError("SkillDefinition", skill_key)
        return skill

    @staticmethod
    def _to_view(s: AgentSkill) -> dict:
        return {
            "id": s.id, "skillKey": s.skill_key, "displayName": s.display_name,
            "description": s.description, "content": s.content, "isPublished": s.is_published,
            "createdAtUtc": s.created_at_utc.isoformat() if s.created_at_utc else None,
        }
