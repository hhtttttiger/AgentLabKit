from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from alkit_db.base import EntityBase
from .errors import NotFoundError

T = TypeVar("T", bound=EntityBase)


async def list_entities(
    session: AsyncSession,
    model: type[T],
    *,
    page: int = 1,
    page_size: int = 20,
    filters: dict[str, Any] | None = None,
    order_by: str | None = None,
) -> tuple[list[T], int]:
    query = select(model)
    count_q = select(func.count()).select_from(model)

    if filters:
        for key, value in filters.items():
            if value is not None and hasattr(model, key):
                col = getattr(model, key)
                query = query.where(col == value)
                count_q = count_q.where(col == value)

    total = (await session.execute(count_q)).scalar() or 0

    if order_by and hasattr(model, order_by.lstrip("-")):
        col = getattr(model, order_by.lstrip("-"))
        query = query.order_by(col.desc() if order_by.startswith("-") else col)
    else:
        query = query.order_by(model.id.desc())

    items = (await session.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(items), total


async def get_entity(session: AsyncSession, model: type[T], id: int) -> T:
    obj = await session.get(model, id)
    if obj is None:
        raise NotFoundError(model.__name__, str(id))
    return obj


async def create_entity(session: AsyncSession, model: type[T], **kwargs: Any) -> T:
    obj = model(**kwargs)
    session.add(obj)
    await session.flush()
    return obj
