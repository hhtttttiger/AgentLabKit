from typing import Any, Protocol

class DatasetReader(Protocol):
    async def get_examples(self, dataset_id: str) -> list[Any]: ...

class DatasetWriter(Protocol):
    async def create_example_from_run(self, *, dataset_id: str, run: Any) -> Any: ...
