"""Seed default LLM connection profiles, models, and instances.

Idempotent — skips records that already exist (matched by unique keys).

Usage:
    from modules.llm_catalog.seed import seed_llm_catalog
    await seed_llm_catalog(session)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import LlmConnectionProfile, LlmModel, LlmModelBinding, LlmModelInstance


# ── Connection Profiles ──────────────────────────────────────

CONNECTION_PROFILES = [
    {
        "profile_key": "openai",
        "display_name": "OpenAI",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "is_enabled": True,
    },
    {
        "profile_key": "deepseek",
        "display_name": "DeepSeek",
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "is_enabled": True,
    },
    {
        "profile_key": "zhipu",
        "display_name": "智谱 GLM",
        "provider": "openai",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "is_enabled": True,
    },
    {
        "profile_key": "qwen",
        "display_name": "通义千问",
        "provider": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "is_enabled": True,
    },
    {
        "profile_key": "mimo",
        "display_name": "MiMo",
        "provider": "openai",
        "base_url": "https://api.xiaomimimo.com/v1",
        "is_enabled": True,
    },
]

# ── Models ───────────────────────────────────────────────────

MODELS = [
    # DeepSeek — pricing from https://api-docs.deepseek.com/quick_start/pricing (Jun 2026)
    # V4 Pro uses discount price (valid until May 31 2026), cache_write not separately priced.
    {
        "model_key": "deepseek-v4-flash",
        "type": "chat",
        "model_name": "deepseek-v4-flash",
        "display_name": "DeepSeek V4 Flash",
        "description": "DeepSeek V4 快速模型，支持思考/非思考模式，1M 上下文",
        "profile_key": "deepseek",
        "tags_json": ["deepseek", "chat", "fast"],
        "is_enabled": True,
        "input_price_per_mtok": 0.14,
        "output_price_per_mtok": 0.28,
        "cache_read_price_per_mtok": 0.0028,
    },
    {
        "model_key": "deepseek-v4-pro",
        "type": "chat",
        "model_name": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "description": "DeepSeek V4 旗舰模型，推理能力更强，1M 上下文",
        "profile_key": "deepseek",
        "tags_json": ["deepseek", "chat", "premium"],
        "is_enabled": True,
        "input_price_per_mtok": 0.435,
        "output_price_per_mtok": 0.87,
        "cache_read_price_per_mtok": 0.003625,
    },
    # 智谱 GLM — pricing from https://bigmodel.cn/pricing (Jun 2026)
    # [0-32K) tier used as default; cache storage free, cache hit priced.
    {
        "model_key": "GLM-5.1",
        "type": "chat",
        "model_name": "GLM-5.1",
        "display_name": "GLM-5.1",
        "description": "智谱最新旗舰模型，编码能力对标 Claude Opus 4.6，200K 上下文",
        "profile_key": "zhipu",
        "tags_json": ["zhipu", "chat", "premium"],
        "is_enabled": True,
        "input_price_per_mtok": 0.84,   # ¥6 / 1M approx
        "output_price_per_mtok": 3.36,  # ¥24 / 1M approx
        "cache_read_price_per_mtok": 0.18,  # ¥1.3 / 1M approx
    },
    {
        "model_key": "GLM-4.7-Flash",
        "type": "chat",
        "model_name": "GLM-4.7-Flash",
        "display_name": "GLM-4.7 Flash",
        "description": "智谱免费模型，200K 上下文，128K 输出",
        "profile_key": "zhipu",
        "tags_json": ["zhipu", "chat", "fast"],
        "is_enabled": True,
        # 免费模型，不填定价
    },
    # MiMo — pricing from official announcements (Jul 2026)
    {
        "model_key": "mimo-v2.5-pro",
        "type": "chat",
        "model_name": "mimo-v2.5-pro",
        "display_name": "MiMo V2.5 Pro",
        "description": "小米旗舰模型，Agentic 和长程连贯性大幅提升",
        "profile_key": "mimo",
        "tags_json": ["mimo", "chat", "premium"],
        "is_enabled": True,
        "input_price_per_mtok": 0.435,   # $0.435 / 1M (¥3 / 1M)
        "output_price_per_mtok": 0.87,  # $0.87 / 1M (¥6 / 1M)
        "cache_read_price_per_mtok": 0.0036,  # $0.0036 / 1M (¥0.025 / 1M)
    },
    {
        "model_key": "mimo-v2.5",
        "type": "chat",
        "model_name": "mimo-v2.5",
        "display_name": "MiMo V2.5",
        "description": "小米快速模型，兼顾速度和前沿性能",
        "profile_key": "mimo",
        "tags_json": ["mimo", "chat", "fast"],
        "is_enabled": True,
        "input_price_per_mtok": 0.14,   # $0.14 / 1M (¥1 / 1M)
        "output_price_per_mtok": 0.28,  # $0.28 / 1M (¥2 / 1M)
        "cache_read_price_per_mtok": 0.0028,  # $0.0028 / 1M (¥0.02 / 1M)
    },
    # 智谱 Embedding-3 — ¥0.5/百万Tokens, 256-2048 维可调, 8K 上下文
    {
        "model_key": "embedding-3",
        "type": "embedding",
        "model_name": "embedding-3",
        "display_name": "Embedding-3",
        "description": "智谱 Embedding-3 向量模型，维度 256-2048 可调，8K 上下文，中英文多语言优化",
        "profile_key": "zhipu",
        "tags_json": ["zhipu", "embedding"],
        "is_enabled": True,
        "input_price_per_mtok": 0.5,  # ¥0.5 / 百万Tokens
    },
]

# ── Model Instances ──────────────────────────────────────────────

INSTANCES = [
    # Embedding-3 @ 智谱
    {
        "instance_key": "embedding-3.zhipu.default",
        "model_key": "embedding-3",
        "provider_deployment_name": "embedding-3",
        "priority": 1,
        "weight": 100,
        "default_timeout_ms": 60000,
        "is_enabled": True,
        "is_healthy": True,
    },
    # MiMo V2.5 @ MiMo
    {
        "instance_key": "mimo-v2.5.mimo.default",
        "model_key": "mimo-v2.5",
        "provider_deployment_name": "mimo-v2.5",
        "priority": 1,
        "weight": 100,
        "default_timeout_ms": 60000,
        "is_enabled": True,
        "is_healthy": True,
    },
]

# ── Model Bindings ───────────────────────────────────────────────

BINDINGS = [
    {
        "binding_key": "gateway.default_embedding",
        "display_name": "Gateway Default Embedding",
        "capability": "embedding",
        "model_key": "embedding-3",
        "is_enabled": True,
    },
    {
        "binding_key": "gateway.default_chat",
        "display_name": "Gateway Default Chat",
        "capability": "text",
        "model_key": "mimo-v2.5",
        "is_enabled": True,
    },
]

async def seed_llm_catalog(session: AsyncSession) -> None:
    """Insert default connection profiles and models (idempotent)."""

    # 1. Connection Profiles
    profile_ids: dict[str, int] = {}
    for p in CONNECTION_PROFILES:
        existing = await session.execute(
            select(LlmConnectionProfile).where(LlmConnectionProfile.profile_key == p["profile_key"])
        )
        obj = existing.scalar_one_or_none()
        if obj is None:
            obj = LlmConnectionProfile(**p)
            session.add(obj)
            await session.flush()
        profile_ids[p["profile_key"]] = obj.id

    # 2. Models
    model_ids: dict[str, int] = {}
    for m in MODELS:
        existing = await session.execute(
            select(LlmModel).where(LlmModel.model_key == m["model_key"])
        )
        obj = existing.scalar_one_or_none()
        if obj is None:
            obj = LlmModel(
                model_key=m["model_key"],
                type=m["type"],
                model_name=m["model_name"],
                display_name=m["display_name"],
                description=m.get("description"),
                connection_profile_id=profile_ids[m["profile_key"]],
                tags_json=m.get("tags_json", []),
                is_enabled=m.get("is_enabled", True),
                input_price_per_mtok=m.get("input_price_per_mtok"),
                output_price_per_mtok=m.get("output_price_per_mtok"),
                cache_write_price_per_mtok=m.get("cache_write_price_per_mtok"),
                cache_read_price_per_mtok=m.get("cache_read_price_per_mtok"),
            )
            session.add(obj)
            await session.flush()
        else:
            # Update pricing fields on existing models (idempotent).
            pricing_updated = False
            for field in ("input_price_per_mtok", "output_price_per_mtok", "cache_write_price_per_mtok", "cache_read_price_per_mtok"):
                if field in m:
                    setattr(obj, field, m[field])
                    pricing_updated = True
            if pricing_updated:
                session.add(obj)
        model_ids[m["model_key"]] = obj.id

    # 3. Model Instances
    for inst in INSTANCES:
        existing = await session.execute(
            select(LlmModelInstance).where(LlmModelInstance.instance_key == inst["instance_key"])
        )
        obj = existing.scalar_one_or_none()
        if obj is None:
            obj = LlmModelInstance(
                instance_key=inst["instance_key"],
                model_id=model_ids[inst["model_key"]],
                provider_deployment_name=inst.get("provider_deployment_name"),
                priority=inst.get("priority", 1),
                weight=inst.get("weight", 100),
                default_timeout_ms=inst.get("default_timeout_ms", 30000),
                is_enabled=inst.get("is_enabled", True),
                is_healthy=inst.get("is_healthy", True),
            )
            session.add(obj)
            await session.flush()

    # 4. Model Bindings
    for b in BINDINGS:
        existing = await session.execute(
            select(LlmModelBinding).where(LlmModelBinding.binding_key == b["binding_key"])
        )
        obj = existing.scalar_one_or_none()
        if obj is None:
            obj = LlmModelBinding(
                binding_key=b["binding_key"],
                display_name=b["display_name"],
                capability=b["capability"],
                model_id=model_ids[b["model_key"]],
                is_enabled=b.get("is_enabled", True),
            )
            session.add(obj)
            await session.flush()

    await session.flush()
