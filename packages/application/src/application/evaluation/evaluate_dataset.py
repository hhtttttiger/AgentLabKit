from __future__ import annotations

import logging
import time
from dataclasses import replace

from evaluation.contracts_v2 import EvaluationContext, Evaluator
from evaluation.evidence import (
    compose_evaluation_evidence,
    REASON_TRACE_FINALIZATION_TIMEOUT,
    REASON_TRACE_UNAVAILABLE,
)

from ..ports.agents import AgentDefinitionReader
from ..ports.datasets import DatasetReader
from ..ports.evaluation import (
    EvaluationConfigurationReader, EvaluationRunStore, TraceFinalization,
    TraceReader,
)
from ..ports.execution import RunExecutor
from .contracts import EvaluateDatasetCommand, EvaluateDatasetResult

logger = logging.getLogger(__name__)


class EvaluateDataset:
    """Coordinate evaluation-run lifecycle; judging remains in Evaluation."""
    def __init__(self, datasets: DatasetReader, agents: AgentDefinitionReader,
                 executor: RunExecutor, evaluator: Evaluator,
                 runs: EvaluationRunStore, traces: TraceReader | None = None,
                 configurations: EvaluationConfigurationReader | None = None,
                 finalization: TraceFinalization | None = None,
                 trace_finalization_timeout_seconds: float = 10.0) -> None:
        self._datasets, self._agents = datasets, agents
        self._executor, self._evaluator = executor, evaluator
        self._runs, self._traces, self._configurations = runs, traces, configurations
        # Observability-owned finalization seam: awaits the worker's durable
        # ingest ACK before reading the candidate trace. Bounded — a timeout
        # composes truthfully unavailable evidence, never a failed run.
        self._finalization = finalization
        self._trace_finalization_timeout_seconds = trace_finalization_timeout_seconds

    async def execute(self, command: EvaluateDatasetCommand) -> EvaluateDatasetResult:
        configuration = command.configuration
        if configuration is None and command.evaluation_config_id is not None:
            if self._configurations is None:
                raise RuntimeError("evaluation configuration reader is not initialized")
            configuration = await self._configurations.get_configuration(command.evaluation_config_id)
        dataset_id = configuration.dataset_id if configuration else command.dataset_id
        agent_key = configuration.target_key if configuration else command.agent_key
        if not dataset_id or not agent_key:
            raise ValueError("dataset_id and agent_key are required")
        if configuration and configuration.target_type != "agent":
            raise ValueError(f"unsupported application target_type: {configuration.target_type}")
        examples = await self._datasets.get_examples(dataset_id)
        evaluation_run = await self._runs.start(
            dataset_id=dataset_id, agent_key=agent_key,
            total_examples=len(examples),
        )
        try:
            target = await self._agents.resolve(agent_key)
            for example in examples:
                run = await self._executor.execute(
                    input=example.input_text, target=target,
                    session_id=None, user_id=None, history=(),
                    metadata=dict(command.metadata),
                )
                t1_execution_done = time.monotonic()
                # Candidate evidence composes the candidate Run and candidate
                # Trace projection only; capture provenance never enters here.
                # Candidate trace_id only — never the dataset's source provenance.
                finalized = True
                if self._finalization is not None and run.trace_id:
                    finalized = await self._finalization.wait_until_persisted(
                        run.trace_id,
                        timeout_seconds=self._trace_finalization_timeout_seconds,
                    )
                t2_finalization = time.monotonic()
                projection = None
                if self._traces is not None and run.trace_id:
                    projection = await self._traces.get_trace_projection(run.trace_id)
                t3_trace_read = time.monotonic()
                spans = list(projection.spans) if projection is not None else []
                # Completeness rides with the projection: an absent span in a
                # truncated trace is never "no retrieval happened".
                evidence = compose_evaluation_evidence(
                    example=example, run=run, spans=spans,
                    trace_complete=(projection.complete if projection is not None else None),
                    trace_unavailable_reason=(
                        REASON_TRACE_FINALIZATION_TIMEOUT
                        if not finalized and projection is None
                        else REASON_TRACE_UNAVAILABLE
                    ),
                )
                # Ordering contract for the candidate evidence pipeline:
                # execution (T1) <= durable ingest ACK (T2) <= trace read (T3).
                logger.info(
                    "evaluation.evidence_timeline example_id=%s trace_id=%s "
                    "execution_done_t1=yes finalization_wait_ms=%.1f "
                    "trace_read_offset_ms=%.1f finalization_observed=%s",
                    example.example_id, run.trace_id,
                    (t2_finalization - t1_execution_done) * 1000,
                    (t3_trace_read - t2_finalization) * 1000,
                    finalized,
                )
                result = await self._evaluator.evaluate(EvaluationContext(
                    example=example, run=run, spans=spans,
                    extra={"trace_unavailable": not bool(spans)},
                    evidence=evidence,
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
