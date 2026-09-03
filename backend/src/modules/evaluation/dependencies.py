"""评估框架依赖注入。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from common.dependencies import DbSession
from application import CaptureRunAsDatasetExample, CompareEvaluationRuns
from evaluation import EvaluationModule
from .services.dataset_service import DatasetService
from .services.run_service import RunService


def get_eval_module(request: Request) -> EvaluationModule:
    mod: EvaluationModule | None = getattr(request.app.state, "evaluation_module", None)
    if mod is None:
        raise RuntimeError("EvaluationModule not initialized — check lifespan wiring")
    return mod


def get_dataset_service(db: DbSession) -> DatasetService:
    return DatasetService(db)


def get_run_service(db: DbSession) -> RunService:
    return RunService(db)


EvalModuleDep = Annotated[EvaluationModule, Depends(get_eval_module)]
DatasetServiceDep = Annotated[DatasetService, Depends(get_dataset_service)]
RunServiceDep = Annotated[RunService, Depends(get_run_service)]


def get_capture_run_as_dataset_example(request: Request) -> CaptureRunAsDatasetExample:
    use_case = getattr(request.app.state, "capture_run_as_dataset_example", None)
    if use_case is None:
        raise RuntimeError("CaptureRunAsDatasetExample not initialized — check lifespan wiring")
    return use_case


def get_compare_evaluation_runs(request: Request) -> CompareEvaluationRuns:
    use_case = getattr(request.app.state, "compare_evaluation_runs", None)
    if use_case is None:
        raise RuntimeError("CompareEvaluationRuns not initialized — check lifespan wiring")
    return use_case


CaptureRunAsDatasetExampleDep = Annotated[
    CaptureRunAsDatasetExample, Depends(get_capture_run_as_dataset_example)
]
CompareEvaluationRunsDep = Annotated[
    CompareEvaluationRuns, Depends(get_compare_evaluation_runs)
]
