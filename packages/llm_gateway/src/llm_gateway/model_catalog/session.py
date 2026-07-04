from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_catalog_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
    )


def create_catalog_session_factory(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(create_catalog_engine(database_url), expire_on_commit=False)
