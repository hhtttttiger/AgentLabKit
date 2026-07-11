"""Vision Pipeline — 图片理解。

直接调用 OpenAI / Anthropic Vision API（绕过 Gateway，
因为 llm_gateway 暂不支持多模态输入）。
"""
from __future__ import annotations

import base64
import logging
from io import BytesIO

import httpx
from PySide6.QtGui import QPixmap

from core.config import LLMConfig

logger = logging.getLogger("desktop.vision")

# 超时（秒）
_TIMEOUT = 60


def pixmap_to_base64(pixmap: QPixmap, fmt: str = "PNG") -> str:
    """QPixmap → base64 字符串（不带 data URI 前缀）。"""
    buf = BytesIO()
    pixmap.save(buf, fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


async def analyze_image(
    llm_config: LLMConfig,
    image_b64: str,
    prompt: str = "请描述这张图片的内容。",
    mime_type: str = "image/png",
) -> str:
    """调用 Vision API 分析图片，返回文本描述。

    支持 OpenAI 和 Anthropic 两种 provider。
    """
    if llm_config.provider == "anthropic":
        return await _call_anthropic(llm_config, image_b64, prompt, mime_type)
    else:
        return await _call_openai(llm_config, image_b64, prompt, mime_type)


async def _call_openai(
    config: LLMConfig, image_b64: str, prompt: str, mime_type: str,
) -> str:
    """OpenAI Chat Completions with vision."""
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    # 选择支持 vision 的模型
    model = config.model
    # 如果用户配置的是纯文本模型，降级到 gpt-4o-mini
    if "mini" not in model and "4o" not in model and "vision" not in model:
        model = "gpt-4o-mini"

    data_uri = f"data:{mime_type};base64,{image_b64}"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri, "detail": "high"},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


async def _call_anthropic(
    config: LLMConfig, image_b64: str, prompt: str, mime_type: str,
) -> str:
    """Anthropic Messages API with vision."""
    url = f"{config.base_url.rstrip('/')}/messages"
    headers = {
        "x-api-key": config.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    model = config.model
    # 降级到支持 vision 的模型
    if "claude" not in model.lower():
        model = "claude-sonnet-4-20250514"

    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Anthropic 返回 content 是一个列表
    parts = data.get("content", [])
    text_parts = [p["text"] for p in parts if p.get("type") == "text"]
    return "\n".join(text_parts) if text_parts else "(无文本响应)"
