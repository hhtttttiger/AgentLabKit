from typing import TYPE_CHECKING, List, Optional
from retrieval.engines.local_engine.document_loaders.base import Document, FileInfo
from retrieval.model import SegmentInfo, Segment, Index, GraphSummary, SegmentSetting
from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository

if TYPE_CHECKING:
    from retrieval.utils.terminology import TerminologyMatcher

class PipelineContext:
    def __init__(self):
        self.file_info: Optional[FileInfo] = None
        self.segment_info: Optional[SegmentInfo] = None
        self.doc_info: Optional[Document] = None
        self.text_list: List[Segment] = []
        self.index_result: List[Index] = []
        self.graph_repository: Optional[BaseGraphRepository] = None
        self.graph_summary: Optional[GraphSummary] = None
        self.embedding_provider: Optional[str] = None
        self.embedding_model: Optional[str] = None
        self.embedding_dimensions: Optional[int] = None
        self.terminology_matcher: Optional["TerminologyMatcher"] = None
        self.graph_enabled: bool = False
        self.success = True

    def apply_defaults(self, setting: SegmentSetting) -> None:
        """应用 segment 设置的默认值并初始化术语匹配器。

        LocalRagEngine 和 DocumentProcessor 共享此初始化逻辑，
        避免重复代码。
        """
        from retrieval.utils.terminology import TerminologyMatcher, load_glossary_terms

        if not setting.splitter.name:
            setting.splitter.name = "default"

        self.graph_enabled = setting.graph.enabled

        terminology_terms = setting.provider_config.get("terminology_terms", [])
        glossary_terms = load_glossary_terms(terminology_terms)
        if glossary_terms:
            self.terminology_matcher = TerminologyMatcher.build(glossary_terms)
