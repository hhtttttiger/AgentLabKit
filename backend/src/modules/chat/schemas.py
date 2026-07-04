from __future__ import annotations

from datetime import datetime

from pydantic import Field

from common.schemas import CamelModel


class CreateSessionRequest(CamelModel):
    title: str
    model_type: str = Field(pattern=r"^(agent|model)$")
    model_id: str


class UpdateSessionRequest(CamelModel):
    title: str | None = None
    model_type: str | None = Field(default=None, pattern=r"^(agent|model)$")
    model_id: str | None = None


class SaveMessageItem(CamelModel):
    role: str
    content: str
    status: str = "sent"
    error_message: str | None = None
    trace_json: dict | None = None


class SaveTurnRequest(CamelModel):
    user_message: SaveMessageItem
    assistant_message: SaveMessageItem


class ChatSessionResponse(CamelModel):
    id: int
    user_id: str
    title: str
    model_type: str
    model_id: str
    message_count: int
    created_at_utc: datetime
    updated_at_utc: datetime


class ChatMessageResponse(CamelModel):
    id: int
    session_id: int
    role: str
    content: str
    status: str
    error_message: str | None = None
    trace_json: dict | None = None
    created_at_utc: datetime


class SaveTurnResponse(CamelModel):
    user_message_id: int
    assistant_message_id: int
