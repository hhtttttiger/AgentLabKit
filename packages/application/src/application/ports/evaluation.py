from collections.abc import Sequence
from typing import Any, Protocol

from evaluation.contracts_v2 import EvaluationResult, EvaluationRun, TraceProjection

class EvaluationRunReader(Protocol):
    async def get_run(self, run_id: str) -> EvaluationRun | None: ...
    async def list_results(self, run_id: str) -> Sequence[EvaluationResult]: ...

class EvaluationConfigurationReader(Protocol):
    async def get_configuration(self, config_id: str): ...

class TraceReader(Protocol):
    """Authoritative candidate-trace projection reads.

    Returns None when the trace projection does not exist (yet); a
    projection carries its completeness truth (dropped spans) so consumers
    can tell "no retrieval happened" from "spans were truncated".
    """

    async def get_trace_projection(self, trace_id: str) -> TraceProjection | None: ...


class TraceFinalization(Protocol):
    """Observability-owned finalization seam (publish/flush ≠ persisted).

    Resolves once the authoritative trace projection is durably persisted
    and trace reads have read-your-writes; returns False on bounded timeout.
    Consumers never poll storage, inspect Redis, or know worker internals;
    coroutine cancellation propagates immediately.
    """

    async def wait_until_persisted(
        self, trace_id: str, *, timeout_seconds: float,
    ) -> bool: ...

class EvaluationRunStore(Protocol):
    async def start(self, *, dataset_id: str, agent_key: str, total_examples: int) -> Any: ...
    async def record_result(self, evaluation_run: Any, result: EvaluationResult) -> None: ...
    async def complete(self, evaluation_run: Any) -> Any: ...
    async def fail(self, evaluation_run: Any, error: Exception) -> Any: ...
