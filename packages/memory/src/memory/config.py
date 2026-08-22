from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LONG_TERM_MEMORY_",
        env_nested_delimiter="__",
        extra="ignore",
        env_file_encoding="utf-8",
    )

    enabled: bool = True
    """是否启用长期记忆（始终初始化，与其他模块保持一致）。"""

    provider: str = "mem0"
    """记忆 provider 后端。可选: native | mem0"""

    extraction_model: str = ""
    """用于记忆提取的 LLM 模型 binding key。留空则使用默认。"""

    embedding_model: str = ""
    """用于记忆向量化的 embedding 模型。留空则使用默认。"""

    max_memories_per_user: int = Field(default=1000, ge=100, le=100000)
    """单用户最大记忆条数。"""

    consolidation_threshold: int = Field(default=50, ge=10, le=10000)
    """触发整合的 episodoc 记忆阈值。"""

    retrieval_top_k: int = Field(default=5, ge=1, le=100)
    """每次检索返回的最大记忆数。"""

    relevance_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    """记忆检索最低相关度阈值。"""

    # Mem0 专用配置
    mem0_config_path: str = ""
    """Mem0 配置文件路径（JSON）。留空使用默认配置。"""
