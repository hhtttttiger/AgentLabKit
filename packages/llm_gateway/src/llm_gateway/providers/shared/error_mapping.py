"""Map OpenAI / Anthropic SDK exceptions to GatewayError."""

from __future__ import annotations

import openai

from ...errors import GatewayError, GatewayErrorCode


def _extract_retry_after(exc: Exception) -> float | None:
    """Extract Retry-After seconds from an SDK exception, if available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    header = response.headers.get("retry-after") or response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return float(header)
    except (ValueError, TypeError):
        return None


def map_sdk_error(
    exc: Exception,
    *,
    provider: str,
    model: str,
) -> GatewayError:
    """Translate an OpenAI / Anthropic SDK exception into a GatewayError.

    If *exc* is already a GatewayError, return it unchanged.
    """
    if isinstance(exc, GatewayError):
        return exc

    retry_after = _extract_retry_after(exc)

    # --- OpenAI SDK: RateLimitError (HTTP 429) ---
    if isinstance(exc, openai.RateLimitError):
        return GatewayError(
            GatewayErrorCode.PROVIDER_RATE_LIMITED,
            str(exc),
            provider=provider,
            model=model,
            retry_after=retry_after,
        )

    # --- OpenAI SDK: AuthenticationError (HTTP 401) ---
    if isinstance(exc, openai.AuthenticationError):
        return GatewayError(
            GatewayErrorCode.PROVIDER_AUTH_FAILED,
            str(exc),
            provider=provider,
            model=model,
        )

    # --- OpenAI SDK: APITimeoutError ---
    if isinstance(exc, openai.APITimeoutError):
        return GatewayError(
            GatewayErrorCode.PROVIDER_TIMEOUT,
            str(exc),
            provider=provider,
            model=model,
        )

    # --- OpenAI SDK: NotFoundError (HTTP 404) ---
    if isinstance(exc, openai.NotFoundError):
        return GatewayError(
            GatewayErrorCode.MODEL_NOT_FOUND,
            str(exc),
            provider=provider,
            model=model,
        )

    # --- OpenAI SDK: APIStatusError — catch 429/5xx that aren't typed subclasses ---
    if isinstance(exc, openai.APIStatusError):
        if exc.status_code == 429:
            return GatewayError(
                GatewayErrorCode.PROVIDER_RATE_LIMITED,
                str(exc),
                provider=provider,
                model=model,
                retry_after=retry_after,
            )
        if exc.status_code >= 500:
            return GatewayError(
                GatewayErrorCode.UPSTREAM_ERROR,
                str(exc),
                provider=provider,
                model=model,
            )

    # --- Anthropic SDK errors ---
    try:
        from anthropic import (  # type: ignore[import-untyped]
            APIStatusError as AnthropicAPIStatusError,
            APITimeoutError as AnthropicAPITimeoutError,
            AuthenticationError as AnthropicAuthenticationError,
            NotFoundError as AnthropicNotFoundError,
            RateLimitError as AnthropicRateLimitError,
        )

        if isinstance(exc, AnthropicRateLimitError):
            return GatewayError(
                GatewayErrorCode.PROVIDER_RATE_LIMITED,
                str(exc),
                provider=provider,
                model=model,
                retry_after=retry_after,
            )
        if isinstance(exc, AnthropicAuthenticationError):
            return GatewayError(
                GatewayErrorCode.PROVIDER_AUTH_FAILED,
                str(exc),
                provider=provider,
                model=model,
            )
        if isinstance(exc, AnthropicAPITimeoutError):
            return GatewayError(
                GatewayErrorCode.PROVIDER_TIMEOUT,
                str(exc),
                provider=provider,
                model=model,
            )
        if isinstance(exc, AnthropicNotFoundError):
            return GatewayError(
                GatewayErrorCode.MODEL_NOT_FOUND,
                str(exc),
                provider=provider,
                model=model,
            )
        if isinstance(exc, AnthropicAPIStatusError):
            if exc.status_code == 429:
                return GatewayError(
                    GatewayErrorCode.PROVIDER_RATE_LIMITED,
                    str(exc),
                    provider=provider,
                    model=model,
                    retry_after=retry_after,
                )
            if exc.status_code >= 500:
                return GatewayError(
                    GatewayErrorCode.UPSTREAM_ERROR,
                    str(exc),
                    provider=provider,
                    model=model,
                )
    except ImportError:
        pass

    # --- Network / connection errors ---
    if isinstance(exc, (openai.APIConnectionError, ConnectionError, TimeoutError)):
        return GatewayError(
            GatewayErrorCode.PROVIDER_TIMEOUT,
            str(exc),
            provider=provider,
            model=model,
        )

    # --- Fallback: anything else is an upstream error ---
    return GatewayError(
        GatewayErrorCode.UPSTREAM_ERROR,
        str(exc),
        provider=provider,
        model=model,
    )
