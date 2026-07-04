from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .snowflake import next_id as _next_snowflake_id


class Base(DeclarativeBase):
    metadata = MetaData()


class EntityBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=_next_snowflake_id)
    created_at_utc: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at_utc: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
