from __future__ import annotations

from enum import Enum


class AgentErrorCode(str, Enum):
    GATEWAY_ERROR = "gateway_error"
    INVALID_REQUEST = "invalid_request"
    INVALID_MODEL_RESPONSE = "invalid_model_response"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    RUNTIME_ERROR = "runtime_error"


class AgentError(Exception):
    def __init__(
        self,
        code: AgentErrorCode,
        message: str,
        *,
        model: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.model = model
        self.trace_id = trace_id
