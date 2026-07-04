import gc
from .base_step import PipelineStep

class GCStep(PipelineStep):
    def execute(self):
        if self.context.doc_info:
             if hasattr(self.context.doc_info, 'content'):
                 self.context.doc_info.content = ""
             if hasattr(self.context.doc_info, 'page_list'):
                 self.context.doc_info.page_list = []
        gc.collect()
