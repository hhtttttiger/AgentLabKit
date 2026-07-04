from abc import ABC, abstractmethod
from retrieval.engines.local_engine.context import PipelineContext

class PipelineStep(ABC):
    def __init__(self, context: PipelineContext):
        self.context = context
        self.success = True

    @property
    def name(self) -> str:
        """Human-readable step identifier (e.g. 'DocumentLoaderStep')."""
        return self.__class__.__name__

    @abstractmethod
    def execute(self):
        pass
