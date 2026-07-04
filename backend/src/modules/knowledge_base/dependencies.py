"""FastAPI dependency injection for Knowledge Base services."""

from __future__ import annotations

from fastapi import Request

from common.dependencies import DbSession


def _get_retrieval_service(request: Request):
    """从 app.state 获取 retrieval_service（可能为 None）。"""
    return getattr(request.app.state, "retrieval_service", None)


def get_kb_service(db: DbSession):
    from .services.kb_service import KnowledgeBaseService
    return KnowledgeBaseService(db)


def get_document_service(db: DbSession, request: Request):
    from .services.document_service import DocumentService
    queue = getattr(request.app.state, "doc_queue", None)
    return DocumentService(db, retrieval_service=_get_retrieval_service(request), queue=queue)


def get_search_service(db: DbSession, request: Request):
    from .services.search_service import SearchService
    return SearchService(db, retrieval_service=_get_retrieval_service(request))
