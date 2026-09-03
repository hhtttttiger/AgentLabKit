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

    # The adapter owns this write transaction; closing a session is not commit.
    # This fake deliberately exposes commit on the session returned by the
    # context manager, matching AsyncSession semantics.
    class Session:
        committed = False
        async def commit(self): self.committed = True

    session = Session()
    class SessionContext:
        async def __aenter__(self): return session
        async def __aexit__(self, *args): pass

    writer = BackendDatasetExampleWriter(lambda: SessionContext())
    result = await writer.create_example(
        dataset_id="12", input_text="hello", expected_output=None,
        metadata={"source_run_id": "run-1"}, source_run_id="run-1",
        source_trace_id="trace-1",
    )

    assert result == "created-example"
    assert calls[0] == ("session", session)
    assert calls[1]["dataset_id"] == "12"
    assert calls[1]["source_run_id"] == "run-1"
    assert session.committed is True


@pytest.mark.asyncio
async def test_capture_write_survives_closing_original_session(monkeypatch):
    persisted = []

    class Session:
        def __init__(self):
            self.pending = []

        async def commit(self):
            persisted.extend(self.pending)
            self.pending.clear()

        async def read(self):
            return list(persisted)

    class Context:
        def __init__(self, session): self.session = session
        async def __aenter__(self): return self.session
        async def __aexit__(self, *args): pass

    class Service:
        def __init__(self, session): self.session = session
        async def create_example(self, **kwargs):
            self.session.pending.append(kwargs)
            return kwargs

    monkeypatch.setattr("application_adapters.evaluation.DatasetService", Service)
    sessions = []
    def factory():
        session = Session()
        sessions.append(session)
        return Context(session)

    await BackendDatasetExampleWriter(factory).create_example(
        dataset_id="12", input_text="hello", expected_output=None,
        metadata={}, source_run_id="run-1", source_trace_id=None,
    )
    assert persisted[0]["input_text"] == "hello"
    assert sessions[0].pending == []
    # A newly opened session observes committed state, not the original
    # session's uncommitted identity map.
    fresh_context = factory()
    fresh = await fresh_context.__aenter__()
    assert (await fresh.read())[0]["input_text"] == "hello"
    await fresh_context.__aexit__(None, None, None)
