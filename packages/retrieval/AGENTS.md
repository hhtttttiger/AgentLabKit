# Retrieval — 系统级 RAG 底层能力包

> **定位**：`retrieval` 是 AgentLabKit 平台的**底层能力包**，提供文档处理、文本分块、Embedding 生成、向量检索、GraphRAG 等核心 RAG 能力。系统中任何需要 RAG 的业务模块（如知识库）必须依赖此包，不得自行实现。

## 系统中的角色

```
┌──────────────────────────────────────────────────┐
│           业务模块 (knowledge_base 等)              │
│  只做 CRUD + 编排，通过适配器桥接到底层能力包        │
└──────────────────────┬───────────────────────────┘
                       │ 通过接口依赖
                       ▼
┌──────────────────────────────────────────────────┐
│              retrieval (本包)                      │
│  DocumentProcessor · BaseEmbeddingProvider         │
│  BaseVectorStore · BaseRagEngine · GraphRAG        │
└──────────────────────────────────────────────────┘
```

**接入方式**：业务模块通过 `retrieval.interface` 中定义的抽象接口依赖本包，具体实现由业务模块的适配器层提供（如 `PgVectorStore`、`GatewayEmbeddingProvider`）。

## 特性

- **纯 Python 实现**: 移除复杂的外部依赖，易于集成和部署
- **管道架构 (Pipeline)**: 清晰的步骤处理流程 (加载 → 分割 → 清理 → 索引构建 → 图构建)
- **模块化设计**: 易于扩展新的文档加载器 (Loaders) 和文本分割器 (Splitters)
- **接口抽象**: `BaseRetrievalService`、`BaseEmbeddingProvider`、`BaseVectorStore` 定义清晰边界
- **混合检索**: 支持 vector / fulltext / hybrid 三种检索模式，hybrid 使用 RRF 融合向量 + pg_trgm 全文检索
- **GraphRAG 扩展**: 支持知识图谱构建、图检索、图查看接口
- **AGE 可插拔存储**: 图仓储抽象支持内存实现与 PostgreSQL + Apache AGE 实现
- **多格式支持**: PDF, DOCX, PPTX, Excel, Markdown, JSON, HTML, TXT 等

## 目录结构

```text
retrieval/
├── interface.py            # 抽象接口定义 (BaseRetrievalService, BaseRagEngine 等)
├── model.py                # 数据模型 (Segment, DocumentSource, SearchResult 等)
├── engine.py               # 引擎入口 (RagEngine)
├── providers/
│   └── embedding.py        # Embedding 抽象 (BaseEmbeddingProvider)
├── stores/
│   └── base.py             # 向量存储抽象 (BaseVectorStore)
├── engines/
│   └── local_engine/
│       ├── processing.py       # DocumentProcessor (无状态文档处理器)
│       ├── context.py          # PipelineContext (管道执行上下文)
│       ├── document_loaders/   # 文档加载器 (PDF, Office, Text 等)
│       ├── splitter/           # 文本分割器 (Recursive, Markdown 等)
│       ├── steps/              # 管道步骤 (加载、分割、索引、图谱等)
│       └── graph/              # GraphRAG 子系统
└── utils/                  # 通用工具
```

## 核心接口

### 1. BaseRetrievalService (`interface.py`)

知识库级操作的最高层抽象，backend 的 `KnowledgeRetrievalService` 实现此接口：

- `aindex_document(kb_id, doc_id, source, setting)` → 处理并索引文档
- `aremove_document(kb_id, doc_id)` → 移除文档的所有分段和索引
- `asearch(kb_id, query, top_k)` → 跨文档检索

### 2. BaseEmbeddingProvider (`providers/embedding.py`)

Embedding 生成抽象，backend 通过 `GatewayEmbeddingProvider` 适配到 `llm_gateway`：

- `aembed(text)` → 生成单条 embedding
- `aembed_batch(texts)` → 批量生成 embedding

### 3. BaseVectorStore (`stores/base.py`)

向量存储抽象，backend 通过 `PgVectorStore` 适配到 pgvector：

- `aupsert(collection, records)` → 写入/更新向量
- `aquery(collection, vector, top_k)` → 相似度检索
- `adelete(collection, ids)` → 删除向量
- `adelete_by_document(collection, doc_id)` → 按文档 ID 清理（幂等 re-index 用，可选）
- `aquery_fulltext(collection, query, top_k)` → 全文检索（pg_trgm，可选）

### 4. DocumentProcessor (`engines/local_engine/processing.py`)

无状态文档处理器，输入 `DocumentSource` → 输出 `ProcessingResult`（segments + indexes + graph 数据）。

### 5. BaseRagEngine / BaseGraphRagEngine (`interface.py`)

独立 RAG 引擎的抽象（用于非知识库场景的轻量使用）。

## 快速开始

### 作为底层能力包被业务模块使用

```python
# 在业务模块的适配器中 (如 knowledge_base/retrieval_service.py)
from retrieval.interface import BaseRetrievalService
from retrieval.engines.local_engine.processing import DocumentProcessor
from retrieval.providers.embedding import BaseEmbeddingProvider
from retrieval.stores.base import BaseVectorStore

class MyRetrievalService(BaseRetrievalService):
    def __init__(self, embedding_provider, vector_store):
        self._processor = DocumentProcessor(embedding_provider=embedding_provider)
        self._embedding = embedding_provider
        self._vector_store = vector_store

    async def aindex_document(self, kb_id, doc_id, source, setting=None):
        result = await self._processor.aprocess(source, setting)
        # ... 持久化 segments, 生成 embeddings, 存入 vector store
```

### 独立使用（测试 / 轻量场景）

```python
from retrieval.engine import RagEngine
from retrieval.model import SegmentSetting

engine = RagEngine("documents/sample.pdf")
engine.activate()
results = engine.search("sample question", top_k=3)
```

## 扩展指南

### 添加新的 Embedding Provider

实现 `BaseEmbeddingProvider` 接口，在业务模块的 `providers/` 目录下创建适配器。

### 添加新的向量存储

实现 `BaseVectorStore` 接口，在业务模块的 `stores/` 目录下创建适配器。

### GraphRAG 约束

- `search()` 保持原语义，不自动混入图检索；图检索统一走 `graph_search()`
- 图谱能力通过 `SegmentSetting.graph` 显式开启，默认关闭
- `AgeGraphRepository` 需要 PostgreSQL 安装 Apache AGE 扩展

### 添加新的加载器

在 `engines/local_engine/document_loaders/` 下实现 `ServiceLoader` 接口，在 `DocumentLoaderStep` 中注册。

## 测试

```bash
python3 -m pytest packages/retrieval/tests -q
```
