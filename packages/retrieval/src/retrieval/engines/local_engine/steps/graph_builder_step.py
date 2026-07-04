from datetime import datetime, timezone
from loguru import logger

from retrieval.engines.local_engine.graph.extractors.factory import create_graph_extractor
from retrieval.engines.local_engine.graph.services.build import GraphBuildService
from .base_step import PipelineStep


class GraphBuilderStep(PipelineStep):
    """Build knowledge graph artifacts after standard indexing."""

    def execute(self):
        if not self.context.success or not self.context.graph_enabled or not self.context.text_list:
            return

        status = self.context.segment_info.status.graph
        config = self.context.segment_info.setting.graph
        status.backend = config.storage.backend
        status.graph_name = config.storage.graph_name

        try:
            status.startTime = datetime.now(timezone.utc)
            status.status = 3

            extractor = create_graph_extractor(config.extractor)
            build_service = GraphBuildService(
                repository=self.context.graph_repository,
                status=status,
                graph_name=config.storage.graph_name,
            )
            self.context.graph_summary = build_service.build(
                segments=self.context.text_list,
                extractor=extractor,
                file_path=self.context.file_info.file_path,
                file_name=self.context.file_info.file_name,
            )
            status.status = 1
            status.message = ""
        except Exception as exc:
            status.status = 2
            status.message = f"graph builder error: {str(exc)}"
            self.context.segment_info.errorMessage = str(exc)
            self.context.success = False
            logger.exception("Graph build failed: {}", exc)
        finally:
            status.endTime = datetime.now(timezone.utc)
