import os
from datetime import datetime, timezone
from retrieval.engines.local_engine.document_loaders.base import Document, LoaderException
from retrieval.engines.local_engine.document_loaders.base_loader import ServiceLoader
from retrieval.engines.local_engine.document_loaders.loader_factory import LoaderFactory
from retrieval.engines.local_engine.steps.base_step import PipelineStep

class DocumentLoaderStep(PipelineStep):
    def execute(self):
        if not self.context.file_info or not self.context.file_info.file_path:
            self.success = False
            return

        self._load_document()

    def _load_document(self):
        try:
            self.context.segment_info.status.loader.startTime = datetime.now(timezone.utc)
            self.context.segment_info.status.loader.status = 3 

            file_path = self.context.file_info.file_path
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            loader: ServiceLoader = self._get_loader()
            
            kwargs = self.context.segment_info.setting.loader.kwargs or {}
            
            self.context.doc_info = loader.load(file_bytes, self.context.file_info, **kwargs)
            
            if not self.context.doc_info.content:
                raise LoaderException("Document content is empty")

            self._clean_content()
            self.context.segment_info.status.loader.status = 1

        except Exception as e:
            self._handle_error(e)
        finally:
            self.context.segment_info.status.loader.endTime = datetime.now(timezone.utc)

    def _get_loader(self) -> ServiceLoader:
        return LoaderFactory.get_loader(
            self.context.file_info.extension.lstrip('.').lower()
        )

    def _clean_content(self):
        if self.context.doc_info and self.context.doc_info.content:
            self.context.doc_info.content = self.context.doc_info.content.replace('\u0000', '').replace('\x00', '')
            for page in self.context.doc_info.page_list:
                page.content = page.content.replace('\u0000', '').replace('\x00', '')

    def _handle_error(self, e):
        self.context.segment_info.status.loader.status = 2 
        self.context.segment_info.errorMessage = str(e)
        self.context.segment_info.status.loader.message = f'loader error: {str(e)}'
        self.context.success = False
