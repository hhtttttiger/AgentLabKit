from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from .session_service import ChatSessionService


def get_chat_session_service(request: Request) -> ChatSessionService:
    return ChatSessionService()


ChatSessionServiceDep = Annotated[ChatSessionService, Depends(get_chat_session_service)]
