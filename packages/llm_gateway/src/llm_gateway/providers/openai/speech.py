from __future__ import annotations

from typing import Any

from ...config import ProviderConfig
from ...models import ProviderId
from ..shared.openai_transport import (
    build_openai_realtime_headers,
    build_openai_realtime_url,
    create_openai_client,
)
from ..shared.openai_compatible_speech import (
    OpenAICompatibleSpeechBatchAdapter,
    OpenAICompatibleSpeechStreamAdapter,
)
from .realtime import RealtimeSessionManager


class OpenAISpeechBatchAdapter(OpenAICompatibleSpeechBatchAdapter):
    def __init__(self, secrets: ProviderConfig, *, client: Any | None = None) -> None:
        super().__init__(
            secrets,
            provider=ProviderId.OPENAI,
            auth_error_message="OpenAI API key is not configured.",
            client=client,
            client_factory=(lambda resolved: create_openai_client(resolved)) if client is None else None,
        )


class OpenAISpeechStreamAdapter(OpenAICompatibleSpeechStreamAdapter):
    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        session_manager: RealtimeSessionManager | None = None,
    ) -> None:
        super().__init__(
            secrets,
            provider=ProviderId.OPENAI,
            auth_error_message="OpenAI API key is not configured.",
            url_builder=build_openai_realtime_url,
            headers_builder=build_openai_realtime_headers,
            session_manager=session_manager,
        )
