"""Built-in time_now tool.

Returns the current UTC date and time in ISO 8601 format.  Useful for agents
that need to reason about deadlines, opening hours, or time-sensitive policies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..contracts import ToolExecutionContext, ToolResult, ToolSpec


_SPEC = ToolSpec(
    name="time_now",
    description=(
        "Return the current UTC date and time in ISO 8601 format "
        "(e.g. '2026-04-03T07:48:52Z').  Use this when the user asks "
        "about the current time, date, or when you need a timestamp."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "timezone_offset_hours": {
                "type": "number",
                "description": (
                    "Optional UTC offset in hours (e.g. 8 for UTC+8). "
                    "When provided the result includes the local time too."
                ),
            },
        },
        "additionalProperties": False,
    },
    returns_description="Current UTC datetime string in ISO 8601 format.",
    tags=frozenset({"utility", "read_only"}),
    timeout_seconds=2.0,
    max_retries=0,
    is_idempotent=False,  # result changes each call
)


class TimeNowTool:
    """Returns the current UTC timestamp.

    This tool is stateless and requires no constructor arguments.
    """

    spec: ToolSpec = _SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        now_utc = datetime.now(tz=timezone.utc)
        utc_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        offset = arguments.get("timezone_offset_hours")
        if offset is not None:
            try:
                from datetime import timedelta

                local_tz = timezone(timedelta(hours=float(offset)))
                local_dt = now_utc.astimezone(local_tz)
                local_str = local_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                output = f"UTC: {utc_str}  Local (UTC{offset:+g}): {local_str}"
            except (TypeError, ValueError):
                output = utc_str
        else:
            output = utc_str

        return ToolResult(
            output=output,
            structured_data={"utc": utc_str},
            status="success",
        )
