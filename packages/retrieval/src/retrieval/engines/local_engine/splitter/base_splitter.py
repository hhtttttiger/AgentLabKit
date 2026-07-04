from abc import ABC, abstractmethod
from typing import List
from retrieval.engines.local_engine.document_loaders.base import Document

class Splitter(ABC):
    def __init__(self, chunk_size: int, chunk_overlap: int, file_info = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.file_info = file_info

    @abstractmethod
    def split_text(self, document_info: Document) -> List[str]:
        pass
