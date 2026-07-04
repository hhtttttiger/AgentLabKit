from importlib import import_module
from typing import Dict, Tuple

from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader

# Loader 注册使用字符串元组 (module_path, class_name) + import_module 的懒加载模式。
# 原因：loader 依赖重型库（pypdf, pandas, python-pptx, python-docx, beautifulsoup4），
# 在 import factory 模块时就加载全部 loader 会导致不必要的内存占用。
# 懒加载确保只在处理对应文件类型时才导入相应的重型依赖。
FILE_TYPE_LOADER: Dict[str, Tuple[str, str]] = {
    "pdf": ("retrieval.engines.local_engine.document_loaders.pdf.pdf", "PDFLoader"),
    "doc": ("retrieval.engines.local_engine.document_loaders.doc.doc", "DocLoader"),
    "docx": ("retrieval.engines.local_engine.document_loaders.doc.docx_pandoc", "DocxPandocLoader"),
    "ppt": ("retrieval.engines.local_engine.document_loaders.ppt.pptx", "PPTLoader"),
    "pptx": ("retrieval.engines.local_engine.document_loaders.ppt.pptx", "PPTLoader"),
    "xlsx": ("retrieval.engines.local_engine.document_loaders.xlsx", "XLSXLoader"),
    "xlsm": ("retrieval.engines.local_engine.document_loaders.xlsx", "XLSXLoader"),
    "xls": ("retrieval.engines.local_engine.document_loaders.xlsx", "XLSXLoader"),
    "csv": ("retrieval.engines.local_engine.document_loaders.xlsx", "XLSXLoader"),
    "txt": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "md": ("retrieval.engines.local_engine.document_loaders.md", "MDLoader"),
    "json": ("retrieval.engines.local_engine.document_loaders.json", "JsonLoader"),
    "html": ("retrieval.engines.local_engine.document_loaders.html", "HtmlLoader"),
    "htm": ("retrieval.engines.local_engine.document_loaders.html", "HtmlLoader"),
    "cs": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "java": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "js": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "ts": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "xml": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "vtt": ("retrieval.engines.local_engine.document_loaders.txt", "TxtLoader"),
    "mp3": ("retrieval.engines.local_engine.document_loaders.audio", "AudioLoader"),
    "wav": ("retrieval.engines.local_engine.document_loaders.audio", "AudioLoader"),
    "flac": ("retrieval.engines.local_engine.document_loaders.audio", "AudioLoader"),
    "mp4": ("retrieval.engines.local_engine.document_loaders.video", "VideoLoader"),
    "mkv": ("retrieval.engines.local_engine.document_loaders.video", "VideoLoader"),
    "mov": ("retrieval.engines.local_engine.document_loaders.video", "VideoLoader"),
}

class LoaderFactory:
    @staticmethod
    def get_loader(file_type: str) -> ServiceLoader:
        loader_ref = FILE_TYPE_LOADER.get(file_type)

        if loader_ref is None:
            raise ValueError(f"No loader found for file type: {file_type}")

        module_name, class_name = loader_ref
        module = import_module(module_name)
        loader_class = getattr(module, class_name)
        return loader_class()
