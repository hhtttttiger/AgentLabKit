from __future__ import annotations

from typing import Any

from ...config import ProviderConfig
from ...models import ProviderId
from ..shared.openai_compatible_image import OpenAICompatibleImageAdapter
from ..shared.openai_transport import create_openai_client


class OpenAIImageAdapter(OpenAICompatibleImageAdapter):
    def __init__(self, secrets: ProviderConfig, *, client: Any | None = None) -> None:
        super().__init__(
            secrets,
            provider=ProviderId.OPENAI,
            auth_error_message="OpenAI API key is not configured.",
            client=client,
            client_factory=(lambda resolved: create_openai_client(resolved)) if client is None else None,
        )
