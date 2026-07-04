import io
from pypdf import PdfReader
from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, Page

class PDFLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)
        
        content = ""
        page_list = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                content += text + "\n"
                page_info = Page(content=text, page_number=i+1)
                page_list.append(page_info)
                
        return Document(content=content, page_list=page_list, is_md=False)
