"""Workflow state store — checkpoint persistence for paused workflows.

Provides a protocol for state persistence and an in-memory implementation
for development/testing. Production implementations can back this with
Redis, PostgreSQL, or any other durable store.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from .contracts import StepResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WorkflowCheckpoint — serializable checkpoint state
# ---------------------------------------------------------------------------


class WorkflowCheckpoint:
    """Serializable state captured when a workflow pauses (e.g. at a human_gate)."""

    __slots__ = ("workflow_id", "step_results", "context_vars", "current_step_index")

    def __init__(
        self,
        workflow_id: str,
        step_results: list[StepResult],
        context_vars: dict[str, Any],
        current_step_index: int,
    ) -> None:
        self.workflow_id = workflow_id
        self.step_results = step_results
        self.context_vars = context_vars
        self.current_step_index = current_step_index


# ---------------------------------------------------------------------------
# WorkflowStateStore — persistence protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class WorkflowStateStore(Protocol):
    """Protocol for workflow checkpoint persistence.

    Implementations must support save, load, and clear operations.
    The engine calls ``save_checkpoint`` when a human_gate pauses execution,
    and ``load_checkpoint`` when ``resume_workflow`` is called.
    """

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Persist a workflow checkpoint.

        Args:
            checkpoint: The state to persist.
        """
        ...

    async def load_checkpoint(self, workflow_id: str) -> WorkflowCheckpoint | None:
        """Load a previously saved checkpoint.

        Args:
            workflow_id: The workflow to restore.

        Returns:
            The checkpoint if found, else ``None``.
        """
        ...

    async def clear_checkpoint(self, workflow_id: str) -> None:
        """Delete a checkpoint (e.g. after workflow completes).

        Args:
            workflow_id: The workflow whose checkpoint to clear.
        """
        ...


# ---------------------------------------------------------------------------
# InMemoryWorkflowStateStore — development/testing implementation
# ---------------------------------------------------------------------------


class InMemoryWorkflowStateStore:
    """In-memory checkpoint store for development and testing.

    Not suitable for production — checkpoints are lost on process restart.
    """

    def __init__(self) -> None:
        self._checkpoints: dict[str, WorkflowCheckpoint] = {}

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        self._checkpoints[checkpoint.workflow_id] = checkpoint
        logger.debug(
            "workflow_state_store saved checkpoint workflow_id=%s step_index=%d",
            checkpoint.workflow_id,
            checkpoint.current_step_index,
        )

    async def load_checkpoint(self, workflow_id: str) -> WorkflowCheckpoint | None:
        checkpoint = self._checkpoints.get(workflow_id)
        if checkpoint:
            logger.debug(
                "workflow_state_store loaded checkpoint workflow_id=%s step_index=%d",
                workflow_id,
                checkpoint.current_step_index,
            )
        else:
            logger.debug(
                "workflow_state_store no checkpoint found workflow_id=%s",
                workflow_id,
            )
        return checkpoint

    async def clear_checkpoint(self, workflow_id: str) -> None:
        self._checkpoints.pop(workflow_id, None)
        logger.debug(
            "workflow_state_store cleared checkpoint workflow_id=%s",
            workflow_id,
        )
