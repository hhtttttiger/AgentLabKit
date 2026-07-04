from __future__ import annotations

import json
from typing import Any

from fastapi.responses import JSONResponse

# JS 能精确表示的整数范围是 [-2^53, 2^53]；雪花 id（((now - epoch) << 22) | worker | seq，
# 当前值约 3e17）远超此范围。若以 JSON number 返回，前端 JSON.parse 会丢精度，导致回传的
# id（删除/编辑/跳转/按 id 过滤）与库中真实 id 不匹配 → 404。
#
# 统一在序列化阶段把"超出 JS 安全整数范围的正整数"转成字符串。本应用的雪花 id 是唯一会
# 超过此阈值的数值；分页/计数/时间戳(ms)/token 用量等均远小于 2^53，不受影响。
_JS_MAX_SAFE_INT = 2**53


def _stringify_bigints(value: Any) -> Any:
    # bool 是 int 的子类，必须先排除（True/False 不应被转成字符串）。
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return str(value) if value > _JS_MAX_SAFE_INT else value
    if isinstance(value, (float, str)):
        return value
    if isinstance(value, dict):
        return {key: _stringify_bigints(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_stringify_bigints(item) for item in value]
    return value


class SnowflakeJSONResponse(JSONResponse):
    """默认响应类：JSON 序列化前把超出 JS 安全整数范围的正整数（雪花 id）转为字符串。"""

    def render(self, content: Any) -> bytes:
        return json.dumps(
            _stringify_bigints(content),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
