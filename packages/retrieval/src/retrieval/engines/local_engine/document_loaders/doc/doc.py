from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, LoaderException

class DocLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        raise LoaderException("DOC format not supported in pure Python mode. Please convert to DOCX or PDF.")
