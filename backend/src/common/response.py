from __future__ import annotations

from typing import Any

from common.json_response import SnowflakeJSONResponse


def ok(data: Any = None, msg: str = "ok") -> dict:
    return {"success": True, "msg": msg, "data": data}


def fail(msg: str, status_code: int = 400, data: Any = None) -> SnowflakeJSONResponse:
    return SnowflakeJSONResponse(
        {"success": False, "msg": msg, "data": data},
        status_code=status_code,
    )


def paged(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "totalCount": total,
        "page": page,
        "pageSize": page_size,
    }
