import json
from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, Page, LoaderException

class JsonLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        content = file_bytes.decode('utf-8')
        json_data = json.loads(content)
        text = json.dumps(json_data, indent=2, ensure_ascii=False)

        page_list = [Page(content=text, page_number=1)]
        return Document(content=text, page_list=page_list, is_md=False)
