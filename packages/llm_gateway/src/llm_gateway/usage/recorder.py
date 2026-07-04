from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alkit_db import next_snowflake_id

from .contracts import UsageAttemptRecord, UsageRequestRecord
from .orm_models import ModelAttemptLogOrm, ModelRequestLogOrm

logger = logging.getLogger(__name__)

REQUEST_ID_MAX_LENGTH = 64


@runtime_checkable
class UsageRecorder(Protocol):
    async def record_request(self, record: UsageRequestRecord) -> None: ...
    async def record_attempt(self, record: UsageAttemptRecord) -> None: ...


class SqlAlchemyUsageRecorder:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_request(self, record: UsageRequestRecord) -> None:
        try:
            now = datetime.now(timezone.utc)
            request_id = _truncate(record.request_id, REQUEST_ID_MAX_LENGTH) or "unknown"
            async with self._session_factory() as session:
                existing = await session.scalar(
                    select(ModelRequestLogOrm).where(ModelRequestLogOrm.request_id == request_id)
                )
                if existing is None:
                    entity = ModelRequestLogOrm(
                        id=next_snowflake_id(),
                        request_id=request_id,
                        model_key=record.model_key,
                        capability=_truncate(record.capability, 32) or "text",
                        success=record.success,
                        attempt_count=record.attempt_count,
                        final_instance_key=record.final_instance_key,
                        error_code=_truncate(record.error_code, 64),
                        error_message=_truncate(record.error_message, 2048),
                        total_input_tokens=record.total_input_tokens,
                        total_output_tokens=record.total_output_tokens,
                        total_estimated_cost=record.total_estimated_cost,
                        cache_write_tokens=record.cache_write_tokens,
                        cache_read_tokens=record.cache_read_tokens,
                        total_duration_ms=record.total_duration_ms,
                        started_at_utc=record.started_at_utc,
                        completed_at_utc=record.completed_at_utc,
                        created_at_utc=now,
                        updated_at_utc=None,
                    )
                    session.add(entity)
                else:
                    existing.model_key = record.model_key
                    existing.capability = _truncate(record.capability, 32) or "text"
                    existing.success = record.success
                    existing.attempt_count = record.attempt_count
                    existing.final_instance_key = record.final_instance_key
                    existing.error_code = _truncate(record.error_code, 64)
                    existing.error_message = _truncate(record.error_message, 2048)
                    existing.total_input_tokens = record.total_input_tokens
                    existing.total_output_tokens = record.total_output_tokens
                    existing.total_estimated_cost = record.total_estimated_cost
                    existing.cache_write_tokens = record.cache_write_tokens
                    existing.cache_read_tokens = record.cache_read_tokens
                    existing.total_duration_ms = record.total_duration_ms
                    existing.started_at_utc = record.started_at_utc
                    existing.completed_at_utc = record.completed_at_utc
                    existing.updated_at_utc = now
                await session.commit()
        except Exception:
            logger.warning("Failed to record usage request", exc_info=True)

    async def record_attempt(self, record: UsageAttemptRecord) -> None:
        try:
            now = datetime.now(timezone.utc)
            async with self._session_factory() as session:
                entity = ModelAttemptLogOrm(
                    id=next_snowflake_id(),
                    request_id=_truncate(record.request_id, REQUEST_ID_MAX_LENGTH) or "unknown",
                    model_key=record.model_key,
                    instance_key=record.instance_key,
                    attempt_no=record.attempt_no,
                    success=record.success,
                    error_code=_truncate(record.error_code, 64),
                    error_message=_truncate(record.error_message, 2048),
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    estimated_cost=record.estimated_cost,
                    cache_write_tokens=record.cache_write_tokens,
                    cache_read_tokens=record.cache_read_tokens,
                    duration_ms=record.duration_ms,
                    started_at_utc=record.started_at_utc,
                    completed_at_utc=record.completed_at_utc,
                    created_at_utc=now,
                    updated_at_utc=None,
                )
                session.add(entity)
                await session.commit()
        except Exception:
            logger.warning("Failed to record usage attempt", exc_info=True)


class NullUsageRecorder:
    """No-op recorder for environments without database."""

    async def record_request(self, record: UsageRequestRecord) -> None:
        pass

    async def record_attempt(self, record: UsageAttemptRecord) -> None:
        pass


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length] if len(value) > max_length else value
