"""Options router — 3 readonly option-list routes."""

from __future__ import annotations

from fastapi import APIRouter

from common.response import ok
from ..dependencies import OptionsServiceDep

router = APIRouter()


@router.get("/options/connection-profiles")
async def connection_profile_options(svc: OptionsServiceDep):
    return ok(await svc.connection_profile_options())


@router.get("/options/models")
async def model_options(svc: OptionsServiceDep):
    return ok(await svc.model_options())


@router.get("/options/features")
async def feature_options(svc: OptionsServiceDep):
    return ok(await svc.feature_options())
