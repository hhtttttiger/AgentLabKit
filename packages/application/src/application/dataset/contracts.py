from dataclasses import dataclass

@dataclass(frozen=True)
class SaveRunAsDatasetExampleCommand:
    dataset_id: str
    run_id: str

@dataclass(frozen=True)
class SaveRunAsDatasetExampleResult:
    dataset_id: str
    example_id: str
    source_run_id: str
