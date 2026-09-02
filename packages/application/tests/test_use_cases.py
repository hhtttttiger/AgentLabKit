from dataclasses import dataclass

import pytest

from application.dataset import SaveRunAsDatasetExample, SaveRunAsDatasetExampleCommand
from application.evaluation import EvaluateDataset, EvaluateDatasetCommand
from application.execution import ExecuteAgent, ExecuteAgentCommand, ReplayRun, ReplayRunCommand


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
    assert executor.calls[0]["metadata"]["session_id"] == "s1"


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
        async def complete(self, run): self.finished = True; return run
        async def fail(self, run, error): raise AssertionError("must not fail lifecycle")

    class Evaluator:
        async def evaluate(self, context): raise RuntimeError("evaluator failed")

    result = await EvaluateDataset(Datasets(), Agents(), Executor(), Evaluator(), Store()).execute(
        EvaluateDatasetCommand("dataset", "agent")
    )
    assert result.evaluation_run is not None
