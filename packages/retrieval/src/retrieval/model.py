from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# --- 基础状态类 ---
class TaskStatus(BaseModel):
    """通用任务状态"""
    status: int = 0  # 0: Pending, 1: Success, 2: Failed, 3: Running
    message: str = ""
    startTime: datetime | None = None
    endTime: datetime | None = None

class IndexStatus(TaskStatus):
    """索引构建状态"""
    name: str = ""

class GraphBuildStatus(TaskStatus):
    """图谱构建状态"""
    backend: str = "memory"
    graph_name: str = "rag_graph"

# --- 配置类 (Config) ---
class LoaderConfig(BaseModel):
    """加载器配置"""
    name: str = ""
    extractor: str = ""
    kwargs: Optional[dict] = None

class SplitterConfig(BaseModel):
    """分割器配置"""
    name: str = "default"

class GraphExtractorConfig(BaseModel):
    """图谱抽取配置"""
    mode: str = "hybrid"
    enable_llm_enrichment: bool = False
    max_triplets_per_segment: int = 20
    confidence_threshold: float = 0.0

class GraphStorageConfig(BaseModel):
    """图谱存储配置"""
    backend: str = "memory"
    graph_name: str = "rag_graph"
    schema_name: str = Field(default="public", alias="schema")
    dsn: str = ""
    create_if_missing: bool = True

class GraphSearchConfig(BaseModel):
    """图谱检索配置"""
    default_top_k: int = 5
    default_max_hops: int = 2

class GraphInspectionConfig(BaseModel):
    """图谱查看配置"""
    default_limit: int = 100

class GraphConfig(BaseModel):
    """GraphRAG 配置"""
    enabled: bool = False
    extractor: GraphExtractorConfig = Field(default_factory=GraphExtractorConfig)
    storage: GraphStorageConfig = Field(default_factory=GraphStorageConfig)
    search: GraphSearchConfig = Field(default_factory=GraphSearchConfig)
    inspection: GraphInspectionConfig = Field(default_factory=GraphInspectionConfig)

class SegmentSetting(BaseModel):
    """RAG处理配置"""
    provider: str = "local"
    provider_config: Dict = Field(default_factory=dict)
    
    documentOCR: Optional[bool] = False
    ocrMode: Optional[str] = 'read'
    mode: str = "default"
    maxLength: int = 1024
    overlap: int = 128  # ~12% of maxLength; prevents cross-boundary semantic loss
    
    # 组件配置
    loader: LoaderConfig = Field(default_factory=LoaderConfig)
    splitter: SplitterConfig = Field(default_factory=SplitterConfig)
    
    # 需要构建的索引列表
    indexes: List[str] = Field(default_factory=lambda: ["embedding"])
    graph: GraphConfig = Field(default_factory=GraphConfig)

# --- 状态类 (Status) ---
class SegmentStatus(BaseModel):
    """RAG处理状态"""
    loader: TaskStatus = Field(default_factory=TaskStatus)
    splitter: TaskStatus = Field(default_factory=TaskStatus)
    indexes: List[IndexStatus] = Field(default_factory=list)
    graph: GraphBuildStatus = Field(default_factory=GraphBuildStatus)

# --- 核心模型 ---
class Segment(BaseModel):
    """文档分片"""
    id: int
    text: str
    metadata: dict = Field(default_factory=dict)
    word_segmentation: str | None = None
    keywords: List[str] = Field(default_factory=list)
    detected_script: str | None = None

class Index(BaseModel):
    """索引结果"""
    segment_id: int = 0
    type: str = ""
    index: str = ""
    context: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SegmentInfo(BaseModel):
    """RAG处理上下文信息"""
    status: SegmentStatus = Field(default_factory=SegmentStatus)
    setting: SegmentSetting = Field(default_factory=SegmentSetting)
    errorMessage: str = ''

# --- 输入/输出模型 ---
class DocumentSource(BaseModel):
    """文档输入源 — 替代对 file_path 的直接依赖，支持 bytes/text 多种输入"""
    content: bytes | None = None          # 原始文件字节
    text: str | None = None               # 预提取的文本内容
    file_name: str = ""                   # 文件名（用于扩展名检测）
    file_path: str | None = None          # 可选路径（向后兼容）
    content_type: str | None = None       # MIME 类型
    metadata: Dict = Field(default_factory=dict)

class SearchResult(BaseModel):
    """检索结果"""
    id: str               # 片段唯一标识
    text: str             # 文本内容
    source: str = ""      # 来源（文件名或 URL）
    score: float = 0.0    # 相关性评分
    metadata: dict = Field(default_factory=dict)   # 扩展元数据

class GraphNode(BaseModel):
    """图节点"""
    id: str
    name: str
    label: str = "Entity"
    properties: Dict = Field(default_factory=dict)
    segment_ids: List[int] = Field(default_factory=list)

class GraphEdge(BaseModel):
    """图边"""
    id: str
    source_id: str
    target_id: str
    relation: str
    properties: Dict = Field(default_factory=dict)
    segment_ids: List[int] = Field(default_factory=list)

class GraphSummary(BaseModel):
    """图谱摘要"""
    graph_name: str = "rag_graph"
    backend: str = "memory"
    node_count: int = 0
    edge_count: int = 0
    labels: Dict[str, int] = Field(default_factory=dict)
    relations: Dict[str, int] = Field(default_factory=dict)

class GraphSubgraph(BaseModel):
    """子图视图"""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)

class GraphSearchResult(BaseModel):
    """图谱检索结果"""
    id: str
    text: str
    score: float = 0.0
    source: str = ""
    segment_id: int | None = None
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    paths: List[List[str]] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
