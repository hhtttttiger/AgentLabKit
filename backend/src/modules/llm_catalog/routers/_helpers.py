"""Shared router helpers — encryption and catalog cache refresh.

These access ``request.app.state`` and therefore belong in the HTTP layer.
"""

from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def _encrypt_api_key(request: Request, api_key: str | None) -> str | None:
    """Encrypt an API key using the gateway catalog encryption key."""
    if not api_key:
        return None
    settings = request.app.state.settings
    encryption_key = getattr(settings, "gateway_catalog_encrypt_key", None)
    if not encryption_key:
        logger.warning("Gateway catalog encryption key not configured; storing API key as plain text")
        return api_key
    from alkit_infra.encryption import encrypt_text, parse_key
    key = parse_key(encryption_key)
    return encrypt_text(api_key, key)


async def _refresh_catalog(request: Request) -> None:
    """Bump revision and force-refresh the gateway catalog cache."""
    catalog_service = getattr(request.app.state, "catalog_service", None)
    if catalog_service is not None:
        try:
            await catalog_service.get_snapshot(force_refresh=True)
        except Exception:
            logger.warning("Failed to refresh catalog cache", exc_info=True)
