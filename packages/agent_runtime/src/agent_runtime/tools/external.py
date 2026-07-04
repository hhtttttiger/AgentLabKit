"""External tool framework — reserved extension point for HTTP/gRPC tools.

Built-in tools execute directly inside the Python process.  External tools
delegate execution to a remote HTTP endpoint, which enables:

- Language-agnostic tool implementations (Node.js, Go, etc.)
- Isolation: a crashing tool server does not bring down the agent runtime
- Independent scaling and deployment of individual tools

Usage pattern
-------------
Subclass :class:`HttpToolHandler` and provide a :attr:`spec` with
``"external"`` in its tags:

.. code-block:: python

    class MyExternalTool(HttpToolHandler):
        spec = ToolSpec(
            name="my_external_tool",
            description="Calls an external service to do X.",
            parameters_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            tags=frozenset({"external", "read_only"}),
            timeout_seconds=15.0,
        )

        def __init__(self) -> None:
            super().__init__(
                config=ExternalToolConfig(
                    endpoint_url="http://my-tool-service/execute",
                    auth_header="X-Tool-Api-Key",
                    credential_key="MY_TOOL_SECRET",
                ),
            )

    registry.register(MyExternalTool.spec, MyExternalTool())

Credential injection
--------------------
:attr:`ExternalToolConfig.credential_key` names an environment variable whose
value is sent in :attr:`ExternalToolConfig.auth_header`.  In production, this
variable should be injected via Kubernetes secrets or a secrets manager.

Protocol
--------
The handler POSTs a JSON body::

    {
        "arguments": { ...tool arguments... },
        "context": {
            "session_id": "...",
            "trace_id": "...",
            "agent_key": "...",
        }
    }

and expects a JSON response::

    {
        "output": "text result",
        "structured_data": { ... },   // optional
        "error_message": null         // or an error string
    }

Timeout and retry are governed by :class:`~contracts.ToolSpec` fields and
enforced by :class:`~executor.ToolExecutor`, not by this handler.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from .contracts import ToolExecutionContext, ToolResult, ToolSpec

logger = logging.getLogger(__name__)

_EXTERNAL_TAG = "external"


@dataclass(frozen=True, slots=True)
class ExternalToolConfig:
    """Runtime configuration for an HTTP-based external tool.

    Attributes:
        endpoint_url: Full URL of the remote tool endpoint (POST).
        auth_header:  HTTP header name to carry the credential token.
                      ``None`` disables authentication (not recommended for
                      production).
        credential_key: Name of the environment variable that holds the secret
                        value sent in *auth_header*.  ``None`` if no auth header
                        is needed.
        extra_headers: Additional fixed HTTP headers (e.g. ``Content-Type`` is
                       always ``application/json`` and must not be listed here).
        request_timeout_seconds: Per-request HTTP timeout **in addition to** the
                                 :attr:`ToolSpec.timeout_seconds` budget managed
                                 by :class:`~executor.ToolExecutor`.  Set this
                                 lower than ``ToolSpec.timeout_seconds`` so the
                                 executor timeout takes precedence.
    """

    endpoint_url: str
    http_method: str = "POST"
    auth_header: str | None = None
    credential_key: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    request_timeout_seconds: float = 25.0


class HttpToolHandler:
    """Base class for external HTTP tool implementations.

    Subclasses must:
    1. Define a class-level :attr:`spec` with ``"external"`` in its *tags*.
    2. Call ``super().__init__(config=...)`` in their ``__init__``.

    The :meth:`execute` implementation posts arguments to the remote endpoint
    and maps the JSON response back to a :class:`~contracts.ToolResult`.  Error
    responses and HTTP failures are caught and returned as
    ``status="error"`` results — never raised — so the executor's error
    isolation layer sees them as normal outcomes.
    """

    #: Subclasses must override with a ToolSpec whose tags include "external".
    spec: ToolSpec

    def __init__(self, config: ExternalToolConfig) -> None:
        self._config = config
        self._validate_spec()

    # ------------------------------------------------------------------
    # Public interface (satisfies ToolHandler Protocol)
    # ------------------------------------------------------------------

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        """Delegate execution to the remote HTTP endpoint.

        Override this method only if you need custom request/response mapping.
        For most tools the default implementation is sufficient.
        """
        try:
            return await self._post(arguments, context)
        except Exception as exc:
            logger.warning(
                "external_tool_error name=%s error=%s",
                self.spec.name,
                exc,
            )
            return ToolResult(
                output="",
                status="error",
                error_message=f"External tool '{self.spec.name}' failed: {exc}",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        """Build and send the HTTP request; parse the response."""
        try:
            import httpx  # optional dependency; raise clearly if absent
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "httpx is required for external tool support. "
                "Install it with: pip install httpx"
            ) from exc

        headers = {
            "Content-Type": "application/json",
            **self._config.extra_headers,
        }
        token = self._resolve_credential()
        if token and self._config.auth_header:
            headers[self._config.auth_header] = token

        payload = {
            "arguments": arguments,
            "context": {
                "session_id": context.session_id,
                "trace_id": context.trace_id,
                "agent_key": context.agent_key,
            },
        }

        async with httpx.AsyncClient(
            timeout=self._config.request_timeout_seconds,
        ) as client:
            response = await client.request(
                self._config.http_method,
                self._config.endpoint_url,
                content=json.dumps(payload, ensure_ascii=False).encode(),
                headers=headers,
            )

        if response.status_code >= 400:
            return ToolResult(
                output="",
                status="error",
                error_message=(
                    f"External tool '{self.spec.name}' returned HTTP "
                    f"{response.status_code}: {response.text[:200]}"
                ),
            )

        data = response.json()
        error_msg: str | None = data.get("error_message")
        if error_msg:
            return ToolResult(output="", status="error", error_message=error_msg)

        return ToolResult(
            output=str(data.get("output", "")),
            structured_data=data.get("structured_data"),
            status="success",
        )

    def _resolve_credential(self) -> str | None:
        if not self._config.credential_key:
            return None
        value = os.environ.get(self._config.credential_key, "")
        if not value:
            logger.warning(
                "external_tool_missing_credential name=%s key=%s",
                self.spec.name,
                self._config.credential_key,
            )
        return value or None

    def _validate_spec(self) -> None:
        spec = getattr(self, "spec", None)
        if spec is None:
            raise TypeError(
                f"{type(self).__name__} must define a class-level 'spec' attribute."
            )
        if _EXTERNAL_TAG not in spec.tags:
            raise ValueError(
                f"{type(self).__name__}.spec.tags must include '{_EXTERNAL_TAG}'. "
                f"Current tags: {spec.tags!r}"
            )
