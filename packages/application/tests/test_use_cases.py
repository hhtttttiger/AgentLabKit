from dataclasses import dataclass

import pytest

from application.dataset import (
    CaptureRunAsDatasetExample,
    CaptureRunAsDatasetExampleCommand,
    CaptureSourceRunNotFound,
    RunNotCapturable,
    SaveRunAsDatasetExample,
    SaveRunAsDatasetExampleCommand,
)
from application.evaluation import EvaluateDataset, EvaluateDatasetCommand
from application.execution import (
    ExecuteAgent,
    ExecuteAgentCommand,
    ReplayRun,
    ReplayRunCommand,
    ReplayTargetUnavailable,
)
from application.execution.run_projection import RunRecord


@dataclass
class Run:
    run_id: str
    input: str = "hello"
    trace_id: str = "trace"
    target: object = "agent-v1"


class Agents:
    async def resolve(self, key):
        return f"target:{key}"


class Executor:
    def __init__(self):
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        return Run("runtime-owned-id", input=kwargs["input"], target=kwargs["target"])


@pytest.mark.asyncio
async def test_execute_delegates_identity_and_inputs():
    executor = Executor()
    result = await ExecuteAgent(executor, Agents()).execute(
        ExecuteAgentCommand("support", "hi", session_id="s1")
    )
    assert result.run.run_id == "runtime-owned-id"
    assert executor.calls[0]["session_id"] == "s1"
    assert "session_id" not in executor.calls[0]["metadata"]


@pytest.mark.asyncio
async def test_replay_requests_new_runtime_run_without_copying_source():
    executor = Executor()
    source = Run("source-id")

    class Runs:
        async def get_run(self, run_id):
            return source

    result = await ReplayRun(Runs(), executor).execute(ReplayRunCommand("source-id"))
    assert result.new_run_id != result.source_run_id
    assert executor.calls[0]["metadata"]["replay_of_run_id"] == "source-id"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_replay_resolves_exact_target_version_and_preserves_source():
    executor = Executor()
    source = RunRecord(
        run_id="source-id", input={}, status="completed", target_type="agent",
        target_key="support", target_version="3", metadata={"secret": "no-copy"},
    )

    class Runs:
        async def get_run(self, run_id):
            return source

    class Targets:
        def __init__(self): self.calls = []
        async def resolve(self, key, version=None):
            self.calls.append((key, version))
            return f"resolved:{key}:{version}"

    targets = Targets()
    result = await ReplayRun(Runs(), executor, targets).execute(
        ReplayRunCommand("source-id", user_id="caller", metadata={"replay_of_run_id": "spoof", "x": 1})
    )
    assert targets.calls == [("support", "3")]
    assert executor.calls[0]["input"] == {}
    assert executor.calls[0]["session_id"] is None
    assert executor.calls[0]["user_id"] == "caller"
    assert executor.calls[0]["history"] == ()
    assert executor.calls[0]["metadata"] == {"replay_of_run_id": "source-id", "x": 1}
    assert source.metadata == {"secret": "no-copy"}
    assert result.source_run_id == "source-id"


@pytest.mark.asyncio
async def test_replay_does_not_fallback_when_historical_version_is_missing():
    source = RunRecord(
        run_id="source-id", input="hello", status="completed", target_type="agent",
        target_key="support", target_version="3",
    )

    class Runs:
        async def get_run(self, run_id): return source

    class Targets:
        async def resolve(self, key, version=None): return None

    executor = Executor()
    with pytest.raises(ReplayTargetUnavailable):
        await ReplayRun(Runs(), executor, Targets()).execute(ReplayRunCommand("source-id"))
    assert executor.calls == []


@pytest.mark.asyncio
async def test_capture_completed_run_maps_facts_and_authoritative_provenance():
    from evaluation.contracts_v2 import DatasetExample

    source = RunRecord(
        run_id="run-id", trace_id="trace-id", status="completed", input="",
        output="actual", target_type="agent", target_key="support", target_version="7",
    )

    class Runs:
        async def get_run(self, run_id): return source

    class Datasets:
        def __init__(self): self.kwargs = None
        async def create_example(self, **kwargs):
            self.kwargs = kwargs
            return DatasetExample(
                example_id="dataset-owned-id", dataset_id=kwargs["dataset_id"],
                input_text=kwargs["input_text"], expected_output=kwargs["expected_output"],
                metadata=dict(kwargs["metadata"]), source_run_id=kwargs["source_run_id"],
                source_trace_id=kwargs["source_trace_id"],
            )

    datasets = Datasets()
    result = await CaptureRunAsDatasetExample(Runs(), datasets).execute(
        CaptureRunAsDatasetExampleCommand(
            "dataset", "run-id", metadata={"source_run_id": "spoof", "label": "x"}
        )
    )
    assert result.example.example_id != source.run_id
    assert datasets.kwargs["input_text"] == ""
    assert datasets.kwargs["expected_output"] is None
    assert datasets.kwargs["metadata"]["source_run_id"] == "run-id"
    assert datasets.kwargs["metadata"]["source_trace_id"] == "trace-id"
    assert datasets.kwargs["metadata"]["source_target_version"] == "7"


@pytest.mark.asyncio
@pytest.mark.parametrize("input_value", ["", 0, {}, [], None])
async def test_capture_preserves_falsey_input(input_value):
    source = RunRecord(run_id="run-id", status="completed", input=input_value)

    class Runs:
        async def get_run(self, run_id): return source

    class Datasets:
        async def create_example(self, **kwargs):
            from evaluation.contracts_v2 import DatasetExample
            return DatasetExample("example-id", kwargs["dataset_id"], kwargs["input_text"])

    result = await CaptureRunAsDatasetExample(Runs(), Datasets()).execute(
        CaptureRunAsDatasetExampleCommand("dataset", "run-id")
    )
    assert result.example.input_text is input_value


@pytest.mark.asyncio
async def test_capture_rejects_missing_and_non_completed_runs():
    class Runs:
        async def get_run(self, run_id):
            return None if run_id == "missing" else RunRecord(run_id=run_id, status="running")

    class Datasets:
        async def create_example(self, **kwargs): raise AssertionError("not called")

    uc = CaptureRunAsDatasetExample(Runs(), Datasets())
    with pytest.raises(CaptureSourceRunNotFound):
        await uc.execute(CaptureRunAsDatasetExampleCommand("dataset", "missing"))
    for status in ("running", "failed", "cancelled"):
        class StatusRuns:
            async def get_run(self, run_id): return RunRecord(run_id=run_id, status=status)
        with pytest.raises(RunNotCapturable):
            await CaptureRunAsDatasetExample(StatusRuns(), Datasets()).execute(
                CaptureRunAsDatasetExampleCommand("dataset", "run")
            )


@pytest.mark.asyncio
async def test_capture_allows_duplicate_actions_and_explicit_expected_output():
    from evaluation.contracts_v2 import DatasetExample
    source = RunRecord(run_id="run-id", status="completed", input="hello", output="actual")

    class Runs:
        async def get_run(self, run_id): return source
    class Datasets:
        def __init__(self): self.calls = 0
        async def create_example(self, **kwargs):
            self.calls += 1
            return DatasetExample(f"example-{self.calls}", kwargs["dataset_id"], kwargs["input_text"], kwargs["expected_output"])

    datasets = Datasets()
    uc = CaptureRunAsDatasetExample(Runs(), datasets)
    first = await uc.execute(CaptureRunAsDatasetExampleCommand("dataset", "run-id", expected_output="golden"))
    second = await uc.execute(CaptureRunAsDatasetExampleCommand("dataset", "run-id"))
    assert first.example.expected_output == "golden"
    assert second.example.expected_output is None
    assert datasets.calls == 2


@pytest.mark.asyncio
async def test_dataset_capture_uses_dataset_owned_identity():
    source = Run("run-id")

    class Runs:
        async def get_run(self, run_id):
            return source

    class Datasets:
        async def create_example_from_run(self, **kwargs):
            return type("Example", (), {"example_id": "dataset-example-id"})()

    result = await SaveRunAsDatasetExample(Runs(), Datasets()).execute(
        SaveRunAsDatasetExampleCommand("dataset", "run-id")
    )
    assert result.example_id != result.source_run_id


@pytest.mark.asyncio
async def test_evaluation_keeps_case_errors_out_of_run_lifecycle():
    class Datasets:
        async def get_examples(self, dataset_id):
            return [type("Example", (), {"example_id": "example-1", "input_text": "x"})()]

    class Store:
        def __init__(self): self.finished = False
        async def start(self, **kwargs): return object()
        async def record_result(self, run, result): pass
        async def complete(self, run): self.finished = True; return run
        async def fail(self, run, error): raise AssertionError("must not fail lifecycle")

    class Evaluator:
        async def evaluate(self, context):
            from evaluation.contracts_v2 import EvaluationResult
            return EvaluationResult(passed=True)

    result = await EvaluateDataset(Datasets(), Agents(), Executor(), Evaluator(), Store()).execute(
        EvaluateDatasetCommand("dataset", "agent")
    )
    assert result.evaluation_run is not None
