import re
from typing import List, Tuple

from retrieval.engines.local_engine.document_loaders.base import Document
from retrieval.engines.local_engine.splitter.base_splitter import Splitter

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

_DEFAULT_HEADERS: List[Tuple[str, str]] = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]


class MDHeaderSplitter(Splitter):
    """按 Markdown 标题层级切分（纯 Python 实现，无 langchain 依赖）。

    每个 chunk 以标题行开头，包含该标题下的正文内容，
    直到遇到同级或更高级的下一个标题。
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, file_info=None,
                 headers_to_split_on: List[Tuple[str, str]] | None = None):
        super().__init__(chunk_size, chunk_overlap, file_info)
        self.headers = headers_to_split_on or _DEFAULT_HEADERS
        # 按标题级别从高到低排序（# 最优先）
        self.header_levels = {h[0]: h[1] for h in self.headers}
        self.min_level = min(len(h[0]) for h in self.headers) if self.headers else 1

    def split_text(self, document_info: Document) -> List[str]:
        text = document_info.content
        chunks: List[str] = []
        current_header = ""
        current_content: List[str] = []

        for line in text.split("\n"):
            match = _HEADER_RE.match(line)
            if match:
                prefix = match.group(1)
                # 只处理指定级别的标题
                if prefix in self.header_levels:
                    # 保存上一个 chunk
                    if current_content:
                        chunk_text = current_header + "\n".join(current_content)
                        if chunk_text.strip():
                            chunks.append(chunk_text.strip())
                    current_header = line.strip() + "\n"
                    current_content = []
                    continue
            current_content.append(line)

        # 最后一个 chunk
        if current_content:
            chunk_text = current_header + "\n".join(current_content)
            if chunk_text.strip():
                chunks.append(chunk_text.strip())

        # 对超长 chunk 做二次切分
        final: List[str] = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                final.append(chunk)
            else:
                # 超长 chunk 按段落再切
                final.extend(self._split_long_chunk(chunk))

        return final

    def _split_long_chunk(self, text: str) -> List[str]:
        """对超长 chunk 按段落二次切分。"""
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            candidate = (current + "\n\n" + para).strip() if current else para
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current.strip():
                    yield current.strip()
                current = para
        if current.strip():
            yield current.strip()
