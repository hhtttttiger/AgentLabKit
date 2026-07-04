"""FastAPI dependencies for glossary module."""

from __future__ import annotations

from common.dependencies import DbSession


def get_glossary_service(db: DbSession):
    from .services.glossary_service import GlossaryService
    return GlossaryService(db)
