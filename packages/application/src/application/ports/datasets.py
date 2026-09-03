from collections.abc import Mapping
from typing import Any, Protocol

from evaluation.contracts_v2 import DatasetExample


class DatasetReader(Protocol):
    async def get_examples(self, dataset_id: str) -> list[Any]: ...


class DatasetExampleWriter(Protocol):
    """The smallest Dataset capability required by run capture."""

    async def create_example(
        self,
        *,
        dataset_id: str,
        input_text: Any,
        expected_output: Any | None,
        metadata: Mapping[str, Any],
        source_run_id: str,
        source_trace_id: str | None,
    ) -> DatasetExample: ...


# Kept as an import-compatible name for consumers of the scaffold.  New code
# should depend on the capability above, not on a Run-aware Dataset writer.
DatasetWriter = DatasetExampleWriter
