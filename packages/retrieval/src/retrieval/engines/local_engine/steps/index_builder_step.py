from datetime import datetime, timezone
from loguru import logger
from typing import List
from retrieval.model import Index, IndexStatus
from retrieval.engines.local_engine.indexs.index import index_factory
from .base_step import PipelineStep

class IndexBuilderStep(PipelineStep):
    def execute(self):
        if not self.context.success or not self.context.text_list:
            return

        # 1. Determine which indexes to build from settings
        target_indexes = self.context.segment_info.setting.indexes
        if not target_indexes:
            target_indexes = ['embedding']

        # 2. Initialize status for these indexes if not already present
        # This allows for external status initialization if needed, but usually it's empty here
        current_indexes_status = self.context.segment_info.status.indexes
        
        # Check if we need to initialize status entries
        if not current_indexes_status:
            for idx_name in target_indexes:
                current_indexes_status.append(IndexStatus(name=idx_name))
            # Write back to context status
            self.context.segment_info.status.indexes = current_indexes_status

        # 3. Build indexes
        for item in self.context.segment_info.status.indexes:
            try:
                # Skip if already processed (though in a linear pipeline this shouldn't happen much)
                if item.status == 1:
                    continue
                    
                index_builder = index_factory(
                    item.name,
                    self.context.segment_info.setting.mode,
                    is_md=self.context.doc_info.is_md if self.context.doc_info else False
                )
                if index_builder is None:
                    continue

                item.startTime = datetime.now(timezone.utc)
                item.status = 3 

                index_list = index_builder(self.context.text_list)
                
                self.context.index_result.extend(index_list)
                
                item.status = 1 
                item.endTime = datetime.now(timezone.utc)

            except Exception as e:
                item.status = 2 
                item.endTime = datetime.now(timezone.utc)
                item.message = f'index builder error: {str(e)}'
                self.context.success = False
                logger.exception(f"Index build failed for {item.name}: {e}")
