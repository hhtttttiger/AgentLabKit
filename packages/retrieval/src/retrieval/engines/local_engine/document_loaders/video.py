from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, LoaderException

class VideoLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        raise LoaderException("Video processing not supported in pure mode.")
