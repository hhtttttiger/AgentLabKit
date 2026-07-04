from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from alkit_db.engine import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
