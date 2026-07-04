"""Glossary module schemas — CamelModel for snake→camelCase conversion."""

from __future__ import annotations

from common.schemas import CamelModel


class CategoryView(CamelModel):
    id: str  # snowflake → always string
    name: str
    description: str | None = None
    created_at_utc: str
    updated_at_utc: str | None = None


class CategoryCreateRequest(CamelModel):
    name: str
    description: str | None = None


class CategoryUpdateRequest(CamelModel):
    name: str | None = None
    description: str | None = None


class TermView(CamelModel):
    id: str
    category_id: str
    term: str
    synonyms: list[str] = []
    created_at_utc: str
    updated_at_utc: str | None = None


class TermCreateRequest(CamelModel):
    category_id: int
    term: str
    synonyms: list[str] = []


class TermUpdateRequest(CamelModel):
    category_id: int | None = None
    term: str | None = None
    synonyms: list[str] | None = None


class KbGlossaryBindingView(CamelModel):
    knowledge_base_id: str
    category_ids: list[str]
    categories: list[CategoryView]
