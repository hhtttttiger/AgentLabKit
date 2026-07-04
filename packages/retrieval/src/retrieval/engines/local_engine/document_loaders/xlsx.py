import io
import pandas as pd
from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.base import Document, Page, LoaderException

class XLSXLoader(ServiceLoader):
    def load(self, file_bytes: bytes, file_info, **kwargs) -> Document:
        stream = io.BytesIO(file_bytes)
        dfs = pd.read_excel(stream, sheet_name=None)

        content = ""
        page_list = []

        for sheet_name, df in dfs.items():
            text = f"Sheet: {sheet_name}\n"
            text += df.to_string()
            content += text + "\n\n"
            page_list.append(Page(content=text, page_number=1))

        return Document(content=content, page_list=page_list, is_md=False)
