"""Tests for observability.sanitizer — PII redaction and attribute bounding."""
from __future__ import annotations

import json

from observability.sanitizer import (
    bounded_attributes,
    content_preview,
    redact_text,
    sanitize_value,
)


# ── redact_text ────────────────────────────────────────────────────────


class TestRedactText:
    def test_email_redacted(self) -> None:
        result = redact_text("contact alice@example.com for details")
        assert "alice@example.com" not in result
        assert "a***@example.com" in result

    def test_phone_redacted(self) -> None:
        result = redact_text("call +1 555 123 4567 now")
        # Middle digits are masked, first/last preserved
        assert "***" in result or "**" in result
        assert "4567" not in result or result != "call +1 555 123 4567 now"

    def test_long_id_redacted(self) -> None:
        result = redact_text("user id 12345678901234")
        # Digits are masked in the middle
        assert "******" in result or "**" in result
        assert "12345678901234" not in result

    def test_plain_text_unchanged(self) -> None:
        assert redact_text("hello world") == "hello world"


# ── sanitize_value ─────────────────────────────────────────────────────


class TestSanitizeValue:
    def test_secret_key_redacted(self) -> None:
        data = {"api_key": "sk-abc123", "name": "test"}
        result = sanitize_value(data)
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"

    def test_nested_secret_redacted(self) -> None:
        data = {"config": {"authorization": "Bearer tok", "debug": True}}
        result = sanitize_value(data)
        assert result["config"]["authorization"] == "[REDACTED]"
        assert result["config"]["debug"] is True

    def test_depth_limit(self) -> None:
        data = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "deep"}}}}}}}
        result = sanitize_value(data)
        assert result["a"]["b"]["c"]["d"]["e"]["f"] == "[max-depth]"

    def test_list_truncated_at_50(self) -> None:
        data = list(range(100))
        result = sanitize_value(data)
        assert len(result) == 50  # truncated to 50 items

    def test_dict_truncated_at_50(self) -> None:
        data = {f"key_{i}": i for i in range(60)}
        result = sanitize_value(data)
        assert result.get("_truncated") is True

    def test_none_passthrough(self) -> None:
        assert sanitize_value(None) is None

    def test_int_passthrough(self) -> None:
        assert sanitize_value(42) == 42

    def test_bool_passthrough(self) -> None:
        assert sanitize_value(True) is True

    def test_string_redacted(self) -> None:
        result = sanitize_value("contact alice@test.com")
        assert "alice@test.com" not in result


# ── content_preview ────────────────────────────────────────────────────


class TestContentPreview:
    def test_string_preview(self) -> None:
        result = content_preview("hello world")
        assert result["preview"] == "hello world"
        assert len(result["sha256"]) == 64

    def test_dict_preview(self) -> None:
        result = content_preview({"key": "value"})
        assert "key" in result["preview"]
        assert "sha256" in result

    def test_max_chars(self) -> None:
        long_text = "x" * 1000
        result = content_preview(long_text, max_chars=100)
        assert len(result["preview"]) <= 100


# ── bounded_attributes ─────────────────────────────────────────────────


class TestBoundedAttributes:
    def test_within_limit(self) -> None:
        attrs = {"key": "value", "count": 42}
        result = bounded_attributes(attrs, max_bytes=1024)
        assert result == {"key": "value", "count": 42}

    def test_truncated_when_exceeds_limit(self) -> None:
        attrs = {f"key_{i}": "x" * 100 for i in range(100)}
        result = bounded_attributes(attrs, max_bytes=500)
        encoded = json.dumps(result).encode()
        assert len(encoded) <= 500 or result.get("_truncated") is True

    def test_empty_input(self) -> None:
        result = bounded_attributes({}, max_bytes=1024)
        assert result == {}

    def test_secret_keys_redacted(self) -> None:
        attrs = {"api_key": "secret123", "name": "test"}
        result = bounded_attributes(attrs, max_bytes=1024)
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"
