from retrieval.model import GraphStorageConfig
from retrieval.engines.local_engine.graph.repository.age import AgeGraphRepository
from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository
from retrieval.engines.local_engine.graph.repository.in_memory import InMemoryGraphRepository


def create_graph_repository(config: GraphStorageConfig) -> BaseGraphRepository:
    backend = config.backend.lower()
    if backend == "age":
        return AgeGraphRepository(
            dsn=config.dsn,
            graph_name=config.graph_name,
            schema=config.schema_name,
            create_if_missing=config.create_if_missing,
        )

    return InMemoryGraphRepository(graph_name=config.graph_name)
