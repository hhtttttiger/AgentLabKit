from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_KEY = re.compile(
    r"(authorization|api[-_]?key|access[-_]?token|refresh[-_]?token|"
    r"secret|password|passwd|cookie|credential|(?:^|[._-])token(?:$|[._-]))",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-])[^@\s]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_PHONE = re.compile(r"(?<!\d)(\+?\d[\d ()-]{7,}\d)(?!\d)")
_LONG_ID = re.compile(r"(?<!\d)(\d{6})\d{6,12}(\d{2,4}[0-9Xx]?)(?!\d)")


def redact_text(value: str) -> str:
    value = _EMAIL.sub(r"\1***\2", value)
    value = _PHONE.sub(lambda m: _mask_middle(m.group(1)), value)
    return _LONG_ID.sub(r"\1******\2", value)


def content_preview(value: Any, *, max_chars: int = 256) -> dict[str, str]:
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return {
        "preview": redact_text(raw)[:max_chars],
        "sha256": hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest(),
    }


def sanitize_value(value: Any, *, depth: int = 0) -> Any:
    if depth >= 6:
        return "[max-depth]"
    if isinstance(value, str):
        return redact_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for index, (key, child) in enumerate(value.items()):
            if index >= 50:
                result["_truncated"] = True
                break
            key_text = str(key)
            result[key_text] = (
                "[REDACTED]"
                if _SECRET_KEY.search(key_text)
                else sanitize_value(child, depth=depth + 1)
            )
        return result
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [sanitize_value(item, depth=depth + 1) for item in list(value)[:50]]
    return redact_text(str(value))


def bounded_attributes(attributes: Mapping[str, Any], *, max_bytes: int) -> dict[str, Any]:
    sanitized = sanitize_value(attributes)
    if not isinstance(sanitized, dict):
        return {}
    encoded = json.dumps(sanitized, ensure_ascii=False, default=str).encode("utf-8")
    if len(encoded) <= max_bytes:
        return sanitized

    bounded: dict[str, Any] = {}
    for key, value in sanitized.items():
        candidate = {**bounded, key: value}
        if len(json.dumps(candidate, ensure_ascii=False, default=str).encode("utf-8")) > max_bytes:
            bounded["_truncated"] = True
            break
        bounded[key] = value
    return bounded


def _mask_middle(value: str) -> str:
    digits = [index for index, char in enumerate(value) if char.isdigit()]
    if len(digits) < 6:
        return value
    chars = list(value)
    for index in digits[2:-2]:
        chars[index] = "*"
    return "".join(chars)


__all__ = ["bounded_attributes", "content_preview", "redact_text", "sanitize_value"]
