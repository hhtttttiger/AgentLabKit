from __future__ import annotations

from typing import Any

from evaluation.contracts_v2 import EvaluationContext, EvaluationResult

from ..ports.agents import AgentDefinitionReader
from ..ports.datasets import DatasetReader
from ..ports.evaluation import EvaluationRunStore, EvaluationRunner, TraceReader
from ..ports.execution import RunExecutor
from .contracts import EvaluateDatasetCommand, EvaluateDatasetResult

class EvaluateDataset:
    """Coordinate dataset examples, real executions, traces, and evaluators.

    A failed verdict is recorded as a result. It is not an orchestration error;
    only infrastructure/lifecycle failures are delegated to the run store.
    """
    def __init__(
        self,
        datasets: DatasetReader,
        agents: AgentDefinitionReader,
        executor: RunExecutor,
        evaluator: EvaluationRunner,
        runs: EvaluationRunStore,
        traces: TraceReader | None = None,
    ) -> None:
        self._datasets = datasets
        self._agents = agents
        self._executor = executor
        self._evaluator = evaluator
        self._runs = runs
        self._traces = traces

    async def execute(self, command: EvaluateDatasetCommand) -> EvaluateDatasetResult:
        examples = await self._datasets.get_examples(command.dataset_id)
        evaluation_run = await self._runs.start(
            dataset_id=command.dataset_id,
            agent_key=command.agent_key,
            total_examples=len(examples),
        )
        try:
            target = await self._agents.resolve(command.agent_key)
            for example in examples:
                run: Any = None
                spans: list[Any] = []
                try:
                    run = await self._executor.execute(
                        input=example.input_text,
                        target=target,
                        metadata=dict(command.metadata),
                    )
                    trace_id = getattr(run, "trace_id", None)
                    if self._traces is not None and trace_id:
                        spans = (await self._traces.get_spans(trace_id)) or []
                    result = await self._evaluator.evaluate(
                        EvaluationContext(
                            example=example,
                            run=run,
                            spans=spans,
                            extra={"trace_unavailable": not bool(spans)},
                        )
                    )
                    # Evaluators must not accidentally break Dataset identity.
                    if not getattr(result, "example_id", None):
                        from dataclasses import replace
                        result = replace(result, example_id=example.example_id)
                except Exception as exc:
                    # Keep the EvaluationRun alive: this case has an execution
                    # or evaluator error, not necessarily a run-level failure.
                    result = EvaluationResult(
                        evaluator_name="application",
                        example_id=example.example_id,
                        run_id=getattr(run, "run_id", None),
                        message=str(exc),
                    )
                record = getattr(self._runs, "record_result", None)
                if record is not None:
                    await record(evaluation_run, result)
            completed = await self._runs.complete(evaluation_run)
            return EvaluateDatasetResult(evaluation_run=completed)
        except Exception as exc:
            await self._runs.fail(evaluation_run, exc)
            raise
