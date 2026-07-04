"""评估框架 API Router — 数据集、配置、运行。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query, Request

from common.response import ok, paged
from .dependencies import DatasetServiceDep, RunServiceDep, EvalModuleDep
from .schemas import (
    DatasetCreateRequest,
    CaseCreateRequest,
    RunConfigCreateRequest,
)

router = APIRouter()


# ── 数据集 CRUD ────────────────────────────────────────────────────────


@router.get("/datasets")
async def list_datasets(svc: DatasetServiceDep, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100)):
    items, total = await svc.list_datasets(page=page, page_size=pageSize)
    return ok(paged(items, total, page, pageSize))


@router.post("/datasets")
async def create_dataset(body: DatasetCreateRequest, svc: DatasetServiceDep):
    return ok(await svc.create_dataset(name=body.name, description=body.description, tags_json=body.tags))


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: int, svc: DatasetServiceDep):
    await svc.delete_dataset(dataset_id)
    return ok(None)


# ── 测试用例 ───────────────────────────────────────────────────────────


@router.get("/datasets/{dataset_id}/cases")
async def list_cases(dataset_id: int, svc: DatasetServiceDep):
    return ok(await svc.list_cases(dataset_id))


@router.post("/datasets/{dataset_id}/cases")
async def create_cases(dataset_id: int, body: list[CaseCreateRequest], svc: DatasetServiceDep):
    return ok(await svc.create_cases(dataset_id, [c.model_dump() for c in body]))


@router.delete("/datasets/{dataset_id}/cases/{case_id}")
async def delete_case(dataset_id: int, case_id: int, svc: DatasetServiceDep):
    await svc.delete_case(dataset_id, case_id)
    return ok(None)


# ── 运行配置 ───────────────────────────────────────────────────────────


@router.get("/run-configs")
async def list_run_configs(svc: RunServiceDep):
    return ok(await svc.list_run_configs())


@router.post("/run-configs")
async def create_run_config(body: RunConfigCreateRequest, svc: RunServiceDep):
    return ok(await svc.create_run_config(
        name=body.name, dataset_id=body.dataset_id,
        target_type=body.target_type, target_key=body.target_key,
        metric_configs_json=body.metric_configs,
        judge_model_binding_key=body.judge_model_binding_key,
    ))


# ── 运行 ──────────────────────────────────────────────────────────────


@router.post("/run-configs/{config_id}/run")
async def trigger_run(
    config_id: int,
    svc: RunServiceDep,
    eval_mod: EvalModuleDep,
    background_tasks: BackgroundTasks,
    request: Request,
):
    run = await svc.trigger_run_and_execute(
        config_id=config_id,
        eval_mod=eval_mod,
        background_tasks=background_tasks,
        request_app_state=request.app.state,
    )
    return ok(run)


@router.get("/runs")
async def list_runs(svc: RunServiceDep, limit: int = Query(20, ge=1, le=100)):
    return ok(await svc.list_runs(limit=limit))


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: int, svc: RunServiceDep):
    return ok(await svc.get_run_detail(run_id))
