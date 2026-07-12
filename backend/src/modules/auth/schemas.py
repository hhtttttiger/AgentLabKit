from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict

from common.schemas import CamelModel


class LoginRequest(CamelModel):
    username: str
    password: str


class TokenResponse(CamelModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"


class UserCreate(CamelModel):
    username: str
    password: str
    display_name: str | None = None
    email: str | None = None
    role: str = "member"


class UserUpdate(CamelModel):
    display_name: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(CamelModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    email: str | None
    role: str
    is_active: bool
    last_login_at_utc: datetime | None
    created_at_utc: datetime
    updated_at_utc: datetime


class ChangePasswordRequest(CamelModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(CamelModel):
    display_name: str | None = None
    email: str | None = None
