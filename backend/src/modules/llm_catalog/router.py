"""llm_catalog composite router — aggregates all sub-routers.

This keeps the ``main.py`` import unchanged:
    from modules.llm_catalog.router import router as llm_catalog_router
"""

from __future__ import annotations

from fastapi import APIRouter

from .routers.connection_profiles_router import router as cp_router
from .routers.features_router import router as features_router
from .routers.model_bindings_router import router as bindings_router
from .routers.model_features_router import router as model_features_router
from .routers.model_instances_router import router as instances_router
from .routers.models_router import router as models_router
from .routers.options_router import router as options_router

router = APIRouter()
router.include_router(cp_router)
router.include_router(models_router)
router.include_router(instances_router)
router.include_router(features_router)
router.include_router(bindings_router)
router.include_router(model_features_router)
router.include_router(options_router)
