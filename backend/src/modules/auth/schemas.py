from __future__ import annotations

from common.schemas import CamelModel


class LoginRequest(CamelModel):
    username: str
    password: str


class TokenResponse(CamelModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
