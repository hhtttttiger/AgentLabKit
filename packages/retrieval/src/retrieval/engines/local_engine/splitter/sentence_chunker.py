from typing import List

from chonkie import SentenceChunker as ChonkieSentenceChunker

from retrieval.engines.local_engine.document_loaders.base import Document
from retrieval.engines.local_engine.splitter.base_splitter import Splitter

# 中英文句子分隔符
_DELIMITERS = [
    ". ", "! ", "? ",  # 英文
    "\n",
    "。", "！", "？", "；", "……",  # 中文
]


class SentenceChunker(Splitter):
    """按句子边界切分，不撕裂句子。

    使用 chonkie 的 SentenceChunker，基于句子检测在语义自然边界处断开，
    同时保证每个 chunk 不超过 chunk_size。
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, file_info=None):
        super().__init__(chunk_size, chunk_overlap, file_info)
        self._chunker = ChonkieSentenceChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            delim=_DELIMITERS,
        )

    def split_text(self, document_info: Document) -> List[str]:
        chunks = self._chunker.chunk(document_info.content)
        return [chunk.text for chunk in chunks]
