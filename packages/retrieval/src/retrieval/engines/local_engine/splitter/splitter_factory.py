from typing import Dict, Type
from retrieval.engines.local_engine.document_loaders.base import FileInfo
from retrieval.engines.local_engine.splitter.base_splitter import Splitter
from retrieval.engines.local_engine.splitter.recursive_character_textsplitter import RecursiveCharacterTextSplitter
from retrieval.engines.local_engine.splitter.sentence_chunker import SentenceChunker
from retrieval.engines.local_engine.splitter.markdown.md_header_splitter import MDHeaderSplitter

# Splitter 注册使用直接的类引用（eager import）。
# 原因：splitter 依赖轻量（仅 chonkie），全部加载几乎无开销，
# 且类引用对 IDE 跳转和类型检查友好。
# 对比 loader factory：loader 依赖重型库（pandas, pypdf 等），因此使用懒加载。

# 策略名 → splitter 类（由用户配置的 segment_setting.splitter.name 选择）
SPLITTER_BY_STRATEGY: Dict[str, Type[Splitter]] = {
    "default": SentenceChunker,
    "recursive": RecursiveCharacterTextSplitter,
    "semantic": RecursiveCharacterTextSplitter,
}

# 文件扩展名 → splitter 类（根据上传文件类型自动匹配，优先级高于策略名）
SPLITTER_BY_FILETYPE: Dict[str, Type[Splitter]] = {
    "md": MDHeaderSplitter,
    "doc": MDHeaderSplitter,
    "docx": MDHeaderSplitter,
}

class SplitterFactory:
    def __init__(self, chunk_size: int, chunk_overlap: int, file_info: FileInfo = None) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.file_info = file_info

    def get_splitter(self, splitter_name: str, file_type: str) -> Splitter:
        # 查找优先级：文件类型 > 策略名 > SentenceChunker（兜底）
        SplitterClass = (
            SPLITTER_BY_FILETYPE.get(file_type)
            or SPLITTER_BY_STRATEGY.get(splitter_name)
            or SentenceChunker
        )
        return SplitterClass(self.chunk_size, self.chunk_overlap, self.file_info)
