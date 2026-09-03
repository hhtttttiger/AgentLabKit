"""Backend composition adapters for the framework-neutral EvaluateDataset use case."""
from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

from sqlalchemy import func, select

from application import EvaluationConfiguration
from evaluation.contracts import EvalCase, EvalRunConfig
from evaluation.contracts_v2 import DatasetExample, EvaluationResult
from modules.evaluation.models import EvalCase as EvalCaseModel, EvalRun, EvalRunConfig as EvalRunConfigModel, EvalRunResult


class BackendEvaluationConfigurationReader:
    def __init__(self, session_factory: Any) -> None:
        self._factory = session_factory

    async def get_configuration(self, config_id: str) -> EvaluationConfiguration:
        async with self._factory() as session:
            row = await session.get(EvalRunConfigModel, int(config_id))
            if row is None:
                raise LookupError(f"evaluation config {config_id} not found")
            return EvaluationConfiguration(
                config_id=str(row.id), dataset_id=str(row.dataset_id),
                target_type=row.target_type, target_key=row.target_key,
                metric_configs=tuple(row.metric_configs_json or []),
                judge_model_key=row.judge_model_key or "",
            )


class BackendEvaluationDatasetReader:
    def __init__(self, session_factory: Any) -> None:
        self._factory = session_factory

    async def get_examples(self, dataset_id: str) -> list[DatasetExample]:
        async with self._factory() as session:
            result = await session.execute(
                select(EvalCaseModel)
                .where(EvalCaseModel.dataset_id == int(dataset_id))
                .order_by(EvalCaseModel.case_index)
            )
            return [DatasetExample(
                example_id=str(row.id), dataset_id=str(row.dataset_id),
                input_text=row.input_text, expected_output=row.expected_output,
                context=list(row.context_json or []), tags=list(row.tags_json or []),
                metadata=dict(row.metadata_json or {}),
            ) for row in result.scalars().all()]


class BackendEvaluationRunStore:
    """Persists the v2 lifecycle into the existing evaluation tables."""
    def __init__(self, session_factory: Any, *, existing_run_id: int) -> None:
        self._factory = session_factory
        self._existing_run_id = existing_run_id

    async def start(self, *, dataset_id: str, agent_key: str, total_examples: int,
                   config_id: str | None = None) -> EvalRun:
        async with self._factory() as session:
            run = await session.get(EvalRun, self._existing_run_id)
            if run is None:
                raise LookupError(f"evaluation run {self._existing_run_id} not found")
            run.status = "running"
            run.started_at_utc = func.now()
            await session.commit()
            return run

    async def record_result(self, evaluation_run: EvalRun, result: EvaluationResult) -> None:
        async with self._factory() as session:
            session.add(EvalRunResult(
                run_id=self._existing_run_id,
                case_id=int(result.example_id),
                actual_output=str(result.details.get("actual_output", "")),
                metric_results_json=result.details.get("metric_results", []),
                overall_score=result.score or 0.0,
                error_message=result.message,
                duration_ms=result.duration_ms,
            ))
            await session.commit()

    async def complete(self, evaluation_run: EvalRun) -> EvalRun:
        async with self._factory() as session:
            run = await session.get(EvalRun, self._existing_run_id)
            run.status = "completed"
            run.completed_at_utc = func.now()
            await session.commit()
            return run

    async def fail(self, evaluation_run: EvalRun, error: Exception) -> EvalRun:
        async with self._factory() as session:
            run = await session.get(EvalRun, self._existing_run_id)
            if run is not None:
                run.status = "failed"
                run.completed_at_utc = func.now()
                run.summary_json = {"error": str(error)}
                await session.commit()
            return run


class BackendEvaluationEvaluator:
    """Adapter from the existing domain runner to the v2 Evaluator protocol."""
    name = "backend.evaluation.runner"

    def __init__(self, runner: Any, configuration: EvaluationConfiguration) -> None:
        self._runner = runner
        self._configuration = configuration

    async def evaluate(self, context: Any) -> EvaluationResult:
        started = time.monotonic()
        example = context.example
        actual = str(getattr(context.run, "output", "") or "")
        case = EvalCase(
            id=int(example.example_id), dataset_id=int(example.dataset_id),
            input_text=example.input_text, expected_output=example.expected_output,
            context=list(example.context), tags=list(example.tags),
            metadata={str(k): str(v) for k, v in example.metadata.items()},
        )
        config = EvalRunConfig(
            id=int(self._configuration.config_id), dataset_id=int(self._configuration.dataset_id),
            target_type=self._configuration.target_type, target_key=self._configuration.target_key,
            metric_configs=[dict(m) for m in self._configuration.metric_configs],
            judge_model_key=self._configuration.judge_model_key,
        )
        # The runner owns metric/judge semantics; this adapter only supplies the
        # already-produced Runtime output and translates the result contract.
        legacy = await self._runner._run_with_legacy(case, actual, config, started)
        metrics = [{
            "metric_name": metric.metric_name, "score": metric.score,
            "reasoning": metric.reasoning, "passed": metric.passed,
        } for metric in legacy.metric_results]
        return EvaluationResult(
            evaluator_name=self.name, example_id=example.example_id,
            run_id=getattr(context.run, "run_id", None), passed=legacy.overall_score >= 0.5,
            score=legacy.overall_score, message=legacy.error_message,
            duration_ms=legacy.duration_ms,
            details={"actual_output": actual, "metric_results": metrics},
        )


def build_evaluate_dataset(*, session_factory: Any, eval_module: Any,
                           agent_runtime: Any, existing_run_id: int):
    from application import EvaluateDataset
    from application_adapters.agent_runtime import AgentRuntimeExecutor, BackendAgentReader

    # The runtime definition loader is the canonical agent reader.
    loader = getattr(agent_runtime, "definition_loader", None)
    if loader is None:
        raise RuntimeError("AgentRuntime definition loader is unavailable")
    config_reader = BackendEvaluationConfigurationReader(session_factory)
    # The configuration is loaded by the use case; evaluator needs the same
    # snapshot, so it is supplied by the background entrypoint below.
    return config_reader, loader
