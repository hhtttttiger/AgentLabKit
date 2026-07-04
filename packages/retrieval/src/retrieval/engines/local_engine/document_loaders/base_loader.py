from abc import ABC, abstractmethod
from retrieval.engines.local_engine.document_loaders.base import Document, FileInfo

class ServiceLoader(ABC):
    @abstractmethod
    def load(self, file_bytes: bytes, file_info: FileInfo, **kwargs) -> Document:
        pass
