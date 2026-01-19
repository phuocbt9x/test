"""
src/core/events/dispatcher.py

Event Dispatcher - handles event dispatching to listeners.
"""

import asyncio
import logging
from typing import Any, Dict, List, Type, Optional, Callable
from .event import Event
from .listener import Listener

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Event Dispatcher.

    Dispatches events to registered listeners.
    Supports both sync and async (queue-ready) execution.
    """

    def __init__(self) -> None:
        # event_name -> list of listener instances
        self._listeners: Dict[str, List[Listener]] = {}

        # event_name -> list of callable handlers
        self._handlers: Dict[str, List[Callable]] = {}

        # Queue adapter (for future queue integration)
        self._queue_adapter: Optional[Any] = None

    def listen(
        self, event: Type[Event] | str, listener: Type[Listener] | Listener | Callable
    ) -> None:
        """
        Register a listener for an event.

        Args:
            event: Event class or event name
            listener: Listener class, instance, or callable

        Example:
            dispatcher.listen(UserRegistered, SendWelcomeEmail)
            dispatcher.listen(UserRegistered, SendWelcomeEmail())
            dispatcher.listen("UserRegistered", send_email_handler)
        """
        event_name = event if isinstance(event, str) else event.__name__

        # Handle callable
        if callable(listener) and not isinstance(listener, type):
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            self._handlers[event_name].append(listener)
            logger.debug(f"Registered callable handler for event: {event_name}")
            return

        # Handle Listener class or instance
        if event_name not in self._listeners:
            self._listeners[event_name] = []

        # If it's a class, instantiate it
        if isinstance(listener, type) and issubclass(listener, Listener):
            listener = listener()

        if isinstance(listener, Listener):
            self._listeners[event_name].append(listener)
            logger.debug(
                f"Registered listener {listener.__class__.__name__} for event: {event_name}"
            )

    def forget(self, event: Type[Event] | str) -> None:
        """
        Remove all listeners for an event.

        Args:
            event: Event class or event name
        """
        event_name = event if isinstance(event, str) else event.__name__

        if event_name in self._listeners:
            del self._listeners[event_name]

        if event_name in self._handlers:
            del self._handlers[event_name]

        logger.debug(f"Removed all listeners for event: {event_name}")

    async def dispatch(self, event: Event) -> List[Any]:
        """
        Dispatch an event to all registered listeners.

        Args:
            event: The event to dispatch

        Returns:
            List of results from listeners
        """
        event_name = event.get_event_name()
        results: List[Any] = []

        logger.info(f"Dispatching event: {event_name} (ID: {event.event_id})")

        # Get all listeners and handlers
        listeners = self._listeners.get(event_name, [])
        handlers = self._handlers.get(event_name, [])

        # Sort listeners by priority
        sorted_listeners = sorted(
            listeners, key=lambda l: l.get_priority(), reverse=True
        )

        # Execute listeners
        for listener in sorted_listeners:
            try:
                if listener.should_queue():
                    # Queue for async execution (future implementation)
                    result = await self._queue_listener(listener, event)
                else:
                    # Execute synchronously
                    result = await listener.handle(event)

                results.append(result)

            except Exception as e:
                logger.error(
                    f"Listener {listener.__class__.__name__} failed for event {event_name}: {e}",
                    exc_info=True,
                )

                try:
                    await listener.failed(event, e)
                except Exception as failed_error:
                    logger.error(
                        f"Listener failed handler also failed: {failed_error}",
                        exc_info=True,
                    )

        # Execute callable handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)

                results.append(result)

            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} failed for event {event_name}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Event {event_name} dispatched to {len(sorted_listeners) + len(handlers)} listeners"
        )

        return results

    async def _queue_listener(self, listener: Listener, event: Event) -> Any:
        """
        Queue a listener for async execution.

        For now, executes synchronously. In the future, this will
        push to Redis queue or message broker.

        Args:
            listener: The listener to queue
            event: The event to handle

        Returns:
            Result from listener
        """
        if self._queue_adapter:
            # Future: Push to queue
            # await self._queue_adapter.push({
            #     'listener': listener.__class__.__name__,
            #     'event': event.to_dict(),
            #     'queue': listener.get_queue_name(),
            #     'delay': listener.get_delay()
            # })
            logger.info(
                f"Queuing listener {listener.__class__.__name__} "
                f"(queue: {listener.get_queue_name()}, delay: {listener.get_delay()}s)"
            )
            return None
        else:
            # Fallback to sync execution
            logger.warning(
                f"Queue adapter not configured, executing {listener.__class__.__name__} synchronously"
            )
            return await listener.handle(event)

    def set_queue_adapter(self, adapter: Any) -> None:
        """
        Set the queue adapter for async listener execution.

        Args:
            adapter: Queue adapter (e.g., RedisQueue, RabbitMQ)
        """
        self._queue_adapter = adapter
        logger.info(f"Queue adapter set: {adapter.__class__.__name__}")

    def has_listeners(self, event: Type[Event] | str) -> bool:
        """
        Check if an event has any listeners.

        Args:
            event: Event class or event name

        Returns:
            True if event has listeners
        """
        event_name = event if isinstance(event, str) else event.__name__
        return (
            event_name in self._listeners and len(self._listeners[event_name]) > 0
        ) or (event_name in self._handlers and len(self._handlers[event_name]) > 0)

    def get_listeners(self, event: Type[Event] | str) -> List[Listener]:
        """
        Get all listeners for an event.

        Args:
            event: Event class or event name

        Returns:
            List of listeners
        """
        event_name = event if isinstance(event, str) else event.__name__
        return self._listeners.get(event_name, [])
