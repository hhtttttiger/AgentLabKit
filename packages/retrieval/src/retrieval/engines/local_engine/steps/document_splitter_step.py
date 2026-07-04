import hashlib
from datetime import datetime, timezone
from retrieval.model import Segment
from retrieval.engines.local_engine.splitter.base_splitter import Splitter
from retrieval.engines.local_engine.splitter.splitter_factory import SplitterFactory
from .base_step import PipelineStep

class DocumentSplitterStep(PipelineStep):
    def execute(self):
        if not self.context.success or not self.context.doc_info:
            return

        self._split_document()

    def _split_document(self):
        try:
            self.context.segment_info.status.splitter.startTime = datetime.now(timezone.utc)
            self.context.segment_info.status.splitter.status = 3

            if self.context.doc_info.use_splitter:
                self._handle_splitter()
            else:
                self._handle_no_splitter_needed()              

            self.context.segment_info.status.splitter.status = 1
        except Exception as e:
            self._handle_error(e)
        finally:
            self.context.segment_info.status.splitter.endTime = datetime.now(timezone.utc)

    def _get_splitter(self) -> Splitter:
        setting = self.context.segment_info.setting
        factory = SplitterFactory(setting.maxLength, setting.overlap, self.context.file_info)
        
        is_md = self.context.doc_info.is_md if self.context.doc_info else False
        if is_md:
            return factory.get_splitter('md', 'md')
        
        return factory.get_splitter(
            setting.splitter.name,
            self.context.file_info.extension.lstrip('.').lower()
        )

    def _handle_no_splitter_needed(self):
        for page in self.context.doc_info.page_list:
            if page.content:
                self._add_segment(page.content, page.metadata)

    def _handle_splitter(self) -> None:
        content = self.context.doc_info.content
        if len(content) < self.context.segment_info.setting.maxLength:
            self._add_segment(content)
            return
            
        splitter = self._get_splitter()
        for text in splitter.split_text(self.context.doc_info):
            if text:
                self._add_segment(text)

    def _add_segment(self, text: str, metadata: dict = None) -> None:
        # 统一清洗文本
        cleaned_text = text.replace('　', ' ').replace('\u2002', '').strip()
        
        if cleaned_text:
            segment_metadata = dict(metadata or {})
            segment_metadata.setdefault("source", self.context.file_info.file_name if self.context.file_info else "")
            segment_metadata.setdefault("file_name", self.context.file_info.file_name if self.context.file_info else "")
            segment_metadata.setdefault("file_path", self.context.file_info.file_path if self.context.file_info else "")
            segment = Segment(
                id=self._generate_id(cleaned_text, len(self.context.text_list)),
                text=cleaned_text,
                metadata=segment_metadata
            )
            self.context.text_list.append(segment)

    def _handle_error(self, e):
        self.context.segment_info.status.splitter.status = 2
        self.context.segment_info.status.splitter.message = f'splitter error: {str(e)}'
        self.context.success = False

    def _generate_id(self, text: str, index: int) -> int:
        """生成确定性的 segment ID。

        基于文档路径 + 分段索引 + 文本哈希，同一文档重复处理产生相同 ID，
        保证索引幂等性（re-index 不会产生重复 segment）。

        ID 用 SHA-256 哈希并通过 & ((1 << 63) - 1) mask 到 63 位有符号整数范围，
        确保与 Snowflake ID（需要 i64）和 JavaScript Number.MAX_SAFE_INTEGER（2^53-1）
        兼容，防止前端 JSON 解析丢失精度导致删除/编辑 404。
        """
        source = self.context.file_info.file_path or self.context.file_info.file_name
        raw = f"{source}:{index}:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
        return int(hashlib.sha256(raw.encode()).hexdigest(), 16) & ((1 << 63) - 1)
