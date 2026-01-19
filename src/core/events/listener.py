"""
src/core/events/listener.py

Base Listener class for event listeners.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from .event import Event


class Listener(ABC):
    """
    Base Listener class.

    All event listeners should inherit from this class.

    Example:
        class SendWelcomeEmail(Listener):
            async def handle(self, event: UserRegistered) -> None:
                # Send email logic
                pass

            def should_queue(self) -> bool:
                return True  # Queue this listener
    """

    @abstractmethod
    async def handle(self, event: Event) -> Any:
        """
        Handle the event.

        Args:
            event: The event to handle

        Returns:
            Any result from handling the event
        """
        pass

    def should_queue(self) -> bool:
        """
        Determine if this listener should be queued.

        Returns:
            True if listener should run in queue, False for sync
        """
        return False

    def get_queue_name(self) -> Optional[str]:
        """
        Get the queue name for this listener.

        Returns:
            Queue name or None for default queue
        """
        return None

    def get_priority(self) -> int:
        """
        Get listener priority (higher = runs first).

        Returns:
            Priority number (default: 0)
        """
        return 0

    def get_delay(self) -> int:
        """
        Get delay in seconds before executing (for queued listeners).

        Returns:
            Delay in seconds (default: 0)
        """
        return 0

    async def failed(self, event: Event, exception: Exception) -> None:
        """
        Handle listener failure.

        Args:
            event: The event that was being handled
            exception: The exception that occurred
        """
        pass


class SyncListener(Listener):
    """Listener that always runs synchronously."""

    def should_queue(self) -> bool:
        return False


class QueuedListener(Listener):
    """Listener that always runs in queue."""

    def should_queue(self) -> bool:
        return True
