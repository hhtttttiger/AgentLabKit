"""Dependencies for the model-usage module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from alkit_db.engine import get_session_factory

from .service import ModelUsageService


def get_model_usage_service() -> ModelUsageService:
    return ModelUsageService(get_session_factory())


ModelUsageServiceDep = Annotated[ModelUsageService, Depends(get_model_usage_service)]
