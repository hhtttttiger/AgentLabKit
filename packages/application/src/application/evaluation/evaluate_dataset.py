from __future__ import annotations

from dataclasses import replace

from evaluation.contracts_v2 import EvaluationContext

from ..ports.agents import AgentDefinitionReader
from ..ports.datasets import DatasetReader
from ..ports.evaluation import EvaluationRunStore, EvaluationRunner, TraceReader
from ..ports.execution import RunExecutor
from .contracts import EvaluateDatasetCommand, EvaluateDatasetResult


class EvaluateDataset:
    """Coordinate evaluation-run lifecycle; judging remains in Evaluation."""
    def __init__(self, datasets: DatasetReader, agents: AgentDefinitionReader,
                 executor: RunExecutor, evaluator: EvaluationRunner,
                 runs: EvaluationRunStore, traces: TraceReader | None = None) -> None:
        self._datasets, self._agents = datasets, agents
        self._executor, self._evaluator = executor, evaluator
        self._runs, self._traces = runs, traces

    async def execute(self, command: EvaluateDatasetCommand) -> EvaluateDatasetResult:
        examples = await self._datasets.get_examples(command.dataset_id)
        evaluation_run = await self._runs.start(
            dataset_id=command.dataset_id, agent_key=command.agent_key,
            total_examples=len(examples),
        )
        try:
            target = await self._agents.resolve(command.agent_key)
            for example in examples:
                run = await self._executor.execute(
                    input=example.input_text, target=target,
                    session_id=None, user_id=None, history=(),
                    metadata=command.metadata,
                )
                spans = []
                if self._traces is not None and run.trace_id:
                    spans = (await self._traces.get_spans(run.trace_id)) or []
                result = await self._evaluator.evaluate(EvaluationContext(
                    example=example, run=run, spans=spans,
                    extra={"trace_unavailable": not bool(spans)},
                ))
                if not result.example_id:
                    result = replace(result, example_id=example.example_id)
                await self._runs.record_result(evaluation_run, result)
            return EvaluateDatasetResult(
                evaluation_run=await self._runs.complete(evaluation_run)
            )
        except Exception as exc:
            await self._runs.fail(evaluation_run, exc)
            raise
