from typing import List

from retrieval.engines.local_engine.document_loaders.base import Document
from retrieval.engines.local_engine.splitter.base_splitter import Splitter

# 默认分隔符：段落 → 换行 → 空格 → 字符
_DEFAULT_SEPARATORS = ["\n\n", "\n", " ", ""]


class RecursiveCharacterTextSplitter(Splitter):
    """递归字符切分器（纯 Python 实现，无 langchain 依赖）。

    按优先级依次尝试分隔符，在 chunk_size 约束下尽量保持语义完整。
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, file_info=None,
                 separators: List[str] | None = None):
        super().__init__(chunk_size, chunk_overlap, file_info)
        self.separators = separators or _DEFAULT_SEPARATORS

    def split_text(self, document_info: Document) -> List[str]:
        return self._split(document_info.content, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []

        # 找到能切分当前文本的分隔符
        separator = separators[-1]
        new_separators = []
        for i, _sep in enumerate(separators):
            if _sep == "":
                separator = _sep
                break
            if _sep in text:
                separator = _sep
                new_separators = separators[i + 1:]
                break

        # 按分隔符切分
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # 合并小片段
        current: List[str] = []
        current_len = 0
        for piece in splits:
            piece_len = len(piece)
            if current_len + piece_len + (len(separator) if current else 0) <= self.chunk_size:
                current.append(piece)
                current_len += piece_len + (len(separator) if len(current) > 1 else 0)
            else:
                if current:
                    merged = separator.join(current)
                    if merged.strip():
                        final_chunks.append(merged)
                # 单个片段超长 → 递归用更细的分隔符
                if piece_len > self.chunk_size and new_separators:
                    sub_chunks = self._split(piece, new_separators)
                    final_chunks.extend(sub_chunks)
                else:
                    current = [piece]
                    current_len = piece_len
                    continue
                current = []
                current_len = 0

        if current:
            merged = separator.join(current)
            if merged.strip():
                final_chunks.append(merged)

        # 处理 overlap
        if self.chunk_overlap > 0 and len(final_chunks) > 1:
            final_chunks = self._apply_overlap(final_chunks)

        return final_chunks

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """在相邻 chunk 之间添加 overlap。

        从上一个 chunk 尾部截取 overlap_text 拼接到当前 chunk 前面。
        注意：这会导致最终 chunk 长度膨胀为 chunk_size + chunk_overlap。
        对大多数 embedding 模型（token limit 通常远大于 chunk_size）无害，
        但如果需要严格限制长度，可在此处做二次截断。
        """
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            overlap_text = prev[-self.chunk_overlap:]
            # 尽量在句子/词边界截断
            for sep in ["。", ".", "！", "!", "？", "?", "；", ";", "，", ",", " ", "\n"]:
                idx = overlap_text.find(sep)
                if idx > 0:
                    overlap_text = overlap_text[idx + 1:]
                    break
            result.append(overlap_text + chunks[i])
        return result
