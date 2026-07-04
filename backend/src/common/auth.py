from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import Settings

_bearer = HTTPBearer(auto_error=False)
_settings: Settings | None = None


def configure_auth(settings: Settings) -> None:
    global _settings
    _settings = settings


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None or _settings is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = jwt.decode(
            credentials.credentials,
            _settings.jwt_secret_key,
            algorithms=[_settings.jwt_algorithm],
            audience=_settings.jwt_audience,
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return {"user_id": payload["sub"], "username": payload.get("username", "")}


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Router-level auth guard: only validates the token, does not inject user info.

    Use as ``dependencies=[Depends(require_auth)]`` on routers where individual
    endpoints do not need the ``user_id``.  For endpoints that do, keep using
    ``CurrentUser`` as a parameter (which also enforces auth).
    """
    if credentials is None or _settings is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        jwt.decode(
            credentials.credentials,
            _settings.jwt_secret_key,
            algorithms=[_settings.jwt_algorithm],
            audience=_settings.jwt_audience,
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


CurrentUser = Annotated[dict, Depends(_get_current_user)]
