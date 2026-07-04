from bs4 import BeautifulSoup
from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, Page

class HtmlLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        try:
            content = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
             content = file_bytes.decode('utf-8', errors='ignore')
             
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        page_list = [Page(content=text, page_number=1)]
        return Document(content=text, page_list=page_list, is_md=False)
