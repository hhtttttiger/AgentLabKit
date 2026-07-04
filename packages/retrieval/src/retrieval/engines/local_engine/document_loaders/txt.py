from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, Page

class TxtLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        try:
            content = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = file_bytes.decode('gbk')
            except UnicodeDecodeError:
                 content = file_bytes.decode('utf-8', errors='ignore')

        page = Page(content=content, page_number=1)
        return Document(content=content, page_list=[page], is_md=False)
