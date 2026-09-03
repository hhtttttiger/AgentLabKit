import pytest

from application_adapters.evaluation import BackendDatasetExampleWriter


@pytest.mark.asyncio
async def test_backend_dataset_writer_delegates_to_dataset_service(monkeypatch):
    calls = []

    class FakeService:
        def __init__(self, session):
            calls.append(("session", session))

        async def create_example(self, **kwargs):
            calls.append(kwargs)
            return "created-example"

    monkeypatch.setattr("application_adapters.evaluation.DatasetService", FakeService)

    class SessionContext:
        async def __aenter__(self): return "db-session"
        async def __aexit__(self, *args): pass

    writer = BackendDatasetExampleWriter(lambda: SessionContext())
    result = await writer.create_example(
        dataset_id="12", input_text="hello", expected_output=None,
        metadata={"source_run_id": "run-1"}, source_run_id="run-1",
        source_trace_id="trace-1",
    )

    assert result == "created-example"
    assert calls[0] == ("session", "db-session")
    assert calls[1]["dataset_id"] == "12"
    assert calls[1]["source_run_id"] == "run-1"
