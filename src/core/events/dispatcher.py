from typing import Dict, List, Type, Callable, Any
from collections import defaultdict
from src.core.loggings import get_logger
from .base import Event, Listener, ShouldQueue
from .queue import QueueManager

logger = get_logger(__name__)


class EventDispatcher:
    """
    Event Dispatcher

    Manages event-listener mapping and dispatches events to their listeners.
    Supports both sync and async (queued) listeners.
    """

    def __init__(self, queue_manager: QueueManager):
        self._listeners: Dict[str, List[Type[Listener]]] = defaultdict(list)
        self._queue_manager = queue_manager
        self._initialized = False

    def listen(self, event: Type[Event], listener: Type[Listener]) -> None:
        event_name = event.__name__

        if listener not in self._listeners[event_name]:
            self._listeners[event_name].append(listener)
            logger.debug(
                f"Registered listener {listener.__name__} for event {event_name}"
            )

    def subscribe(self, subscriber: "EventSubscriber") -> None:
        subscriptions = subscriber.subscribe()

        for event_class, listener_classes in subscriptions.items():
            if not isinstance(listener_classes, list):
                listener_classes = [listener_classes]

            for listener_class in listener_classes:
                self.listen(event_class, listener_class)

    async def dispatch(self, event: Event) -> None:
        event_name = event.get_event_name()
        listeners = self._listeners.get(event_name, [])

        if not listeners:
            logger.debug(f"No listeners registered for event: {event_name}")
            return

        logger.info(f"Dispatching event {event_name} to {len(listeners)} listener(s)")

        for listener_class in listeners:
            await self._dispatch_to_listener(event, listener_class)

    async def _dispatch_to_listener(
        self, event: Event, listener_class: Type[Listener]
    ) -> None:
        listener = listener_class()
        should_queue = isinstance(listener, ShouldQueue) or getattr(
            listener, "should_queue", False
        )

        if should_queue:
            await self._queue_listener(event, listener)
        else:
            await self._execute_listener(event, listener)

    async def _execute_listener(self, event: Event, listener: Listener) -> None:
        try:
            logger.debug(
                f"Executing listener {listener.get_listener_name()} "
                f"for event {event.get_event_name()}"
            )
            await listener.handle(event)
            logger.debug(
                f"Listener {listener.get_listener_name()} completed successfully"
            )
        except Exception as e:
            logger.error(
                f"Listener {listener.get_listener_name()} failed: {e}", exc_info=True
            )
            listener.failed(event, e)

    async def _queue_listener(self, event: Event, listener: Listener) -> None:
        queue_name = getattr(listener, "queue", None) or "default"

        job_data = {
            "event": event.to_dict(),
            "listener": listener.get_listener_name(),
            "listener_class": f"{listener.__class__.__module__}.{listener.__class__.__name__}",
            "tries": getattr(listener, "tries", 3),
            "timeout": getattr(listener, "timeout", 60),
        }

        logger.debug(
            f"Queueing listener {listener.get_listener_name()} "
            f"for event {event.get_event_name()} on queue '{queue_name}'"
        )

        await self._queue_manager.push(queue_name, job_data)

    def get_listeners(self, event: Type[Event]) -> List[Type[Listener]]:
        return self._listeners.get(event.__name__, [])

    def has_listeners(self, event: Type[Event]) -> bool:
        return len(self.get_listeners(event)) > 0

    def forget(self, event: Type[Event]) -> None:
        event_name = event.__name__
        if event_name in self._listeners:
            del self._listeners[event_name]
            logger.debug(f"Removed all listeners for event: {event_name}")


class EventSubscriber:
    """
    Base class for Event Subscribers
    Subscribers group related event-listener mappings together.
    """

    def subscribe(self) -> Dict[Type[Event], List[Type[Listener]]]:
        raise NotImplementedError("Subscribers must implement subscribe()")
