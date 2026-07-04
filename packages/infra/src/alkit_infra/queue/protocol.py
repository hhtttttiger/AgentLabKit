from __future__ import annotations

from typing import Protocol, runtime_checkable

from .message import Message


@runtime_checkable
class QueueBackend(Protocol):
    """Minimal async queue contract.

    Implementations must support publishing messages, consuming them
    in batches, and acknowledging / negative-acknowledging processing.
    """

    async def publish(self, queue_name: str, message: Message) -> str:
        """Publish *message* to *queue_name*.

        Returns a provider-specific message identifier (e.g. Redis stream
        entry ID).  If ``message.scheduled_at`` is in the future the
        message is stored in a scheduling layer and delivered at the
        appointed time.
        """
        ...

    async def publish_batch(
        self, queue_name: str, messages: list[Message]
    ) -> list[str]:
        """Publish multiple messages atomically.

        Returns a list of message identifiers in the same order.
        """
        ...

    async def consume(
        self,
        queue_name: str,
        consumer_name: str,
        *,
        batch_size: int = 10,
        poll_timeout_ms: int = 5000,
    ) -> list[tuple[str, Message]]:
        """Fetch a batch of pending messages.

        Returns ``(entry_id, Message)`` pairs.  The caller **must**
        call :meth:`ack` or :meth:`nack` for each entry.
        """
        ...

    async def ack(
        self, queue_name: str, consumer_name: str, entry_id: str
    ) -> None:
        """Acknowledge successful processing of a message."""
        ...

    async def nack(
        self,
        queue_name: str,
        consumer_name: str,
        entry_id: str,
        *,
        requeue: bool = True,
    ) -> None:
        """Negative-acknowledge a message.

        If *requeue* is ``True`` the message is re-published for retry
        (with exponential back-off delay).  Otherwise it is moved to the
        dead-letter stream.
        """
        ...

    async def queue_length(self, queue_name: str) -> int:
        """Return the number of pending (unconsumed) messages."""
        ...

    async def purge(self, queue_name: str) -> int:
        """Remove all messages from *queue_name*.  Returns count purged."""
        ...

    async def close(self) -> None:
        """Release resources held by this backend."""
        ...
