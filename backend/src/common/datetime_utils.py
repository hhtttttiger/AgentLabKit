"""Shared datetime parsing utilities for FastAPI query parameters."""

from __future__ import annotations

from datetime import datetime


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime string, tolerating a trailing 'Z'."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
