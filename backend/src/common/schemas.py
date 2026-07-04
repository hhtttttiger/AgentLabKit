"""Shared Pydantic base models.

``CamelModel`` auto-serializes snake_case Python fields as camelCase in JSON,
keeping API contracts frontend-friendly without manual alias boilerplate.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    """Base model that serializes snake_case fields as camelCase."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Default to ``by_alias=True`` so JSON output uses camelCase."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)
