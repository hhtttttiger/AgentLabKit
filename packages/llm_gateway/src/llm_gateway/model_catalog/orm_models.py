"""ORM models for the LLM model catalog.

Shared models are imported from alkit_db.llm_catalog. This module provides
backward-compatible aliases with the Orm suffix used throughout the gateway.
"""
from __future__ import annotations

from alkit_db.llm_catalog import (
    LlmCatalogRevision as LlmCatalogRevisionOrm,
    LlmConnectionProfile as LlmConnectionProfileOrm,
    LlmFeature as LlmFeatureDefinitionOrm,
    LlmModel as LlmModelOrm,
    LlmModelBinding as LlmModelBindingOrm,
    LlmModelFeature as LlmModelFeatureOrm,
    LlmModelInstance as LlmModelInstanceOrm,
)

__all__ = [
    "LlmCatalogRevisionOrm",
    "LlmConnectionProfileOrm",
    "LlmFeatureDefinitionOrm",
    "LlmModelBindingOrm",
    "LlmModelFeatureOrm",
    "LlmModelOrm",
    "LlmModelInstanceOrm",
]
