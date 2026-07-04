"""JSON Schema validation for tool arguments.

Uses the ``jsonschema`` library when available; falls back to a lightweight
built-in validator that covers the common cases (type checking, required
fields).  This lets the tools package work without an additional hard
dependency while still providing strong validation in production.
"""

from __future__ import annotations

import re
from typing import Any

try:
    import jsonschema as _jsonschema  # type: ignore[import-untyped]
    _JSONSCHEMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _jsonschema = None  # type: ignore[assignment]
    _JSONSCHEMA_AVAILABLE = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class SchemaValidator:
    """Validates argument dicts against JSON Schema objects.

    Caches compiled validators (when ``jsonschema`` is available) so repeated
    calls for the same schema are nearly free.

    Usage::

        validator = SchemaValidator()
        error = validator.validate(schema, {"query": "hello"})
        if error:
            # arguments are invalid
            ...
    """

    def __init__(self) -> None:
        self._cache: dict[int, Any] = {}

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def validate(
        self,
        schema: dict[str, Any],
        arguments: dict[str, Any],
    ) -> str | None:
        """Validate *arguments* against *schema*.

        Args:
            schema: A JSON Schema ``"type": "object"`` definition.
            arguments: The parameter dict supplied by the LLM.

        Returns:
            ``None`` when valid; a human-readable error string otherwise.
        """
        if _JSONSCHEMA_AVAILABLE:
            return self._validate_with_jsonschema(schema, arguments)
        return self._validate_builtin(schema, arguments)

    # ------------------------------------------------------------------
    # jsonschema-backed path
    # ------------------------------------------------------------------

    def _validate_with_jsonschema(
        self,
        schema: dict[str, Any],
        arguments: dict[str, Any],
    ) -> str | None:
        schema_id = id(schema)
        validator = self._cache.get(schema_id)
        if validator is None:
            validator_cls = _jsonschema.Draft7Validator
            validator_cls.check_schema(schema)
            validator = validator_cls(schema)
            self._cache[schema_id] = validator

        errors = list(validator.iter_errors(arguments))
        if not errors:
            return None
        # Return the most specific (deepest) error message.
        best = min(errors, key=lambda e: len(e.absolute_path))
        path = " → ".join(str(p) for p in best.absolute_path) or "(root)"
        return f"[{path}] {best.message}"

    # ------------------------------------------------------------------
    # Built-in fallback validator
    # ------------------------------------------------------------------

    _TYPE_MAP: dict[str, type | tuple[type, ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    def _validate_builtin(
        self,
        schema: dict[str, Any],
        arguments: dict[str, Any],
    ) -> str | None:
        """Lightweight fallback: checks required fields and basic types."""
        if not isinstance(arguments, dict):
            return "arguments must be a JSON object"

        # Required fields
        for key in schema.get("required", []):
            if key not in arguments:
                return f"missing required parameter: '{key}'"

        props: dict[str, Any] = schema.get("properties", {})
        for key, value in arguments.items():
            if key not in props:
                if schema.get("additionalProperties") is False:
                    return f"unexpected parameter: '{key}'"
                continue
            prop_schema = props[key]
            error = self._check_property(key, value, prop_schema)
            if error:
                return error

        return None

    def _check_property(
        self,
        key: str,
        value: Any,  # noqa: ANN401
        prop_schema: dict[str, Any],
    ) -> str | None:
        json_type = prop_schema.get("type")
        if json_type:
            expected = self._TYPE_MAP.get(json_type)
            if expected and not isinstance(value, expected):
                # Special case: JSON integers are valid numbers
                if json_type == "integer" and isinstance(value, float) and value.is_integer():
                    pass
                else:
                    return (
                        f"parameter '{key}' must be of type {json_type}, "
                        f"got {type(value).__name__}"
                    )

        if "minimum" in prop_schema and isinstance(value, (int, float)):
            if value < prop_schema["minimum"]:
                return f"parameter '{key}' must be >= {prop_schema['minimum']}"

        if "maximum" in prop_schema and isinstance(value, (int, float)):
            if value > prop_schema["maximum"]:
                return f"parameter '{key}' must be <= {prop_schema['maximum']}"

        if "minLength" in prop_schema and isinstance(value, str):
            if len(value) < prop_schema["minLength"]:
                return f"parameter '{key}' must have length >= {prop_schema['minLength']}"

        if "maxLength" in prop_schema and isinstance(value, str):
            if len(value) > prop_schema["maxLength"]:
                return f"parameter '{key}' must have length <= {prop_schema['maxLength']}"

        if "pattern" in prop_schema and isinstance(value, str):
            if not re.search(prop_schema["pattern"], value):
                return f"parameter '{key}' does not match pattern {prop_schema['pattern']!r}"

        if "enum" in prop_schema and value not in prop_schema["enum"]:
            return f"parameter '{key}' must be one of {prop_schema['enum']}"

        return None


# Module-level singleton — tools can share one instance for schema caching.
_default_validator = SchemaValidator()


def validate_arguments(
    schema: dict[str, Any],
    arguments: dict[str, Any],
) -> str | None:
    """Module-level convenience wrapper around :class:`SchemaValidator`.

    Returns ``None`` when valid, an error string otherwise.
    """
    return _default_validator.validate(schema, arguments)
