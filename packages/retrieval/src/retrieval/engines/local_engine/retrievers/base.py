from abc import ABC, abstractmethod
from typing import List

from retrieval.model import Index, SearchResult, Segment, SegmentInfo

class BaseRetriever(ABC):
    """
    检索器抽象基类
    """
    def __init__(self, segment_info: SegmentInfo):
        self.segment_info = segment_info

    def sync_dataset(self, segments: List[Segment], indexes: List[Index]) -> None:
        """Refresh the in-memory dataset used by the retriever."""
        return None

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        pass
