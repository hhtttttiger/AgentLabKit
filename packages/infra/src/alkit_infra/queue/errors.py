from __future__ import annotations


class QueueError(Exception):
    """Base exception for queue operations."""


class QueueFullError(QueueError):
    """Raised when a queue has reached its maximum length."""


class QueueClosedError(QueueError):
    """Raised when operating on a closed queue."""


class DeadLetterError(QueueError):
    """Raised when a message exceeds max_retries and enters the dead-letter stream."""

    def __init__(self, message_id: str, queue_name: str, reason: str) -> None:
        self.message_id = message_id
        self.queue_name = queue_name
        self.reason = reason
        super().__init__(
            f"Message {message_id} dead-lettered on {queue_name}: {reason}"
        )
