from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from common.dependencies import DbSession
from .services.connection_profile_service import ConnectionProfileService
from .services.feature_service import FeatureService
from .services.model_binding_service import ModelBindingService
from .services.model_feature_service import ModelFeatureService
from .services.model_instance_service import ModelInstanceService
from .services.model_service import ModelService
from .services.options_service import OptionsService


# ── Factory functions ──────────────────────────────────────────

def get_connection_profile_service(db: DbSession) -> ConnectionProfileService:
    return ConnectionProfileService(db)


def get_model_service(db: DbSession) -> ModelService:
    return ModelService(db)


def get_model_instance_service(db: DbSession) -> ModelInstanceService:
    return ModelInstanceService(db)


def get_feature_service(db: DbSession) -> FeatureService:
    return FeatureService(db)


def get_model_binding_service(db: DbSession) -> ModelBindingService:
    return ModelBindingService(db)


def get_model_feature_service(db: DbSession) -> ModelFeatureService:
    return ModelFeatureService(db)


def get_options_service(db: DbSession) -> OptionsService:
    return OptionsService(db)


# ── Dep type aliases ───────────────────────────────────────────

ConnectionProfileServiceDep = Annotated[ConnectionProfileService, Depends(get_connection_profile_service)]
ModelServiceDep = Annotated[ModelService, Depends(get_model_service)]
ModelInstanceServiceDep = Annotated[ModelInstanceService, Depends(get_model_instance_service)]
FeatureServiceDep = Annotated[FeatureService, Depends(get_feature_service)]
ModelBindingServiceDep = Annotated[ModelBindingService, Depends(get_model_binding_service)]
ModelFeatureServiceDep = Annotated[ModelFeatureService, Depends(get_model_feature_service)]
OptionsServiceDep = Annotated[OptionsService, Depends(get_options_service)]
