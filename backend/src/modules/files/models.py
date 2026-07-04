from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from alkit_db.base import EntityBase


class StoredFile(EntityBase):
    __tablename__ = "stored_files"
    file_name: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_path: Mapped[str] = mapped_column(String(1024))
    storage_type: Mapped[str] = mapped_column(String(32), default="local")
