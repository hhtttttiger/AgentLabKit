from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from llm_gateway.usage.contracts import UsageAttemptRecord, UsageRequestRecord
from llm_gateway.usage.recorder import NullUsageRecorder, SqlAlchemyUsageRecorder, _truncate


class TestNullUsageRecorder:
    @pytest.mark.asyncio
    async def test_record_request_does_not_raise(self):
        recorder = NullUsageRecorder()
        record = _make_request_record()
        await recorder.record_request(record)

    @pytest.mark.asyncio
    async def test_record_attempt_does_not_raise(self):
        recorder = NullUsageRecorder()
        record = _make_attempt_record()
        await recorder.record_attempt(record)


class TestSqlAlchemyUsageRecorder:
    @pytest.mark.asyncio
    async def test_record_request_calls_session_add_and_commit(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_request_record()
        await recorder.record_request(record)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_attempt_calls_session_add_and_commit(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_attempt_record()
        await recorder.record_attempt(record)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_request_swallows_exceptions(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("DB error"))
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_request_record()
        await recorder.record_request(record)  # should not raise

    @pytest.mark.asyncio
    async def test_record_attempt_swallows_exceptions(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("DB error"))
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_attempt_record()
        await recorder.record_attempt(record)  # should not raise

    @pytest.mark.asyncio
    async def test_record_request_orm_entity_has_correct_fields(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_request_record(card_key="gpt-4o", capability="image")
        await recorder.record_request(record)

        entity = mock_session.add.call_args[0][0]
        assert entity.card_key == "gpt-4o"
        assert entity.capability == "image"
        assert entity.success is True

    @pytest.mark.asyncio
    async def test_record_request_truncates_request_id_to_schema_limit(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_request_record(request_id="r" * 120)
        await recorder.record_request(record)

        entity = mock_session.add.call_args[0][0]
        assert entity.request_id == "r" * 64

    @pytest.mark.asyncio
    async def test_record_request_updates_existing_row_for_same_request_id(self):
        existing = MagicMock()
        existing.updated_at_utc = None
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.scalar = AsyncMock(return_value=existing)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_request_record(total_output_tokens=77, total_duration_ms=3456)
        await recorder.record_request(record)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_awaited_once()
        assert existing.total_output_tokens == 77
        assert existing.total_duration_ms == 3456
        assert existing.updated_at_utc is not None

    @pytest.mark.asyncio
    async def test_record_attempt_orm_entity_has_correct_fields(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_attempt_record(instance_key="inst-abc", input_tokens=42)
        await recorder.record_attempt(record)

        entity = mock_session.add.call_args[0][0]
        assert entity.instance_key == "inst-abc"
        assert entity.input_tokens == 42

    @pytest.mark.asyncio
    async def test_record_attempt_truncates_request_id_to_schema_limit(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.add = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        recorder = SqlAlchemyUsageRecorder(mock_factory)
        record = _make_attempt_record(request_id="r" * 120)
        await recorder.record_attempt(record)

        entity = mock_session.add.call_args[0][0]
        assert entity.request_id == "r" * 64


class TestTruncate:
    def test_none_returns_none(self):
        assert _truncate(None, 100) is None

    def test_short_string_unchanged(self):
        assert _truncate("hello", 100) == "hello"

    def test_long_string_truncated(self):
        assert _truncate("a" * 200, 100) == "a" * 100

    def test_exact_length_unchanged(self):
        assert _truncate("a" * 100, 100) == "a" * 100


def _make_request_record(**overrides) -> UsageRequestRecord:
    now = datetime.now(timezone.utc)
    defaults = dict(
        request_id="req-001",
        card_key="gpt-4.1",
        capability="text",
        success=True,
        attempt_count=1,
        final_instance_key="inst-001",
        error_code=None,
        error_message=None,
        total_input_tokens=100,
        total_output_tokens=50,
        total_estimated_cost=0.005,
        total_duration_ms=1200,
        started_at_utc=now,
        completed_at_utc=now,
    )
    defaults.update(overrides)
    return UsageRequestRecord(**defaults)


def _make_attempt_record(**overrides) -> UsageAttemptRecord:
    now = datetime.now(timezone.utc)
    defaults = dict(
        request_id="req-001",
        card_key="gpt-4.1",
        instance_key="inst-001",
        attempt_no=1,
        success=True,
        error_code=None,
        error_message=None,
        input_tokens=100,
        output_tokens=50,
        estimated_cost=0.005,
        duration_ms=1200,
        started_at_utc=now,
        completed_at_utc=now,
    )
    defaults.update(overrides)
    return UsageAttemptRecord(**defaults)
