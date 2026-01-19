"""
src/core/events/decorators.py

Decorators for event listeners.
"""

from typing import Any, Callable, Type, List
from functools import wraps
from .event import Event


def event_listener(
    *events: Type[Event],
    priority: int = 0,
    queue: bool = False,
    queue_name: str | None = None,
    delay: int = 0,
) -> Callable:
    """
    Decorator to mark a function as an event listener.

    Args:
        *events: Event classes to listen to
        priority: Listener priority (higher runs first)
        queue: Whether to queue this listener
        queue_name: Queue name for queued listeners
        delay: Delay in seconds before executing

    Example:
        @event_listener(UserRegistered, priority=10)
        async def send_welcome_email(event: UserRegistered):
            # Send email
            pass

        @event_listener(UserRegistered, UserUpdated, queue=True)
        async def log_user_activity(event: Event):
            # Log activity
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Store metadata on function
        func._event_listener = True
        func._listened_events = events
        func._priority = priority
        func._should_queue = queue
        func._queue_name = queue_name
        func._delay = delay

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def subscribe(*events: Type[Event]) -> Callable:
    """
    Decorator to subscribe a class method to events.

    Used inside Listener classes.

    Example:
        class UserActivityListener(Listener):
            @subscribe(UserRegistered, UserUpdated)
            async def handle(self, event: Event):
                pass
    """

    def decorator(func: Callable) -> Callable:
        func._subscribed_events = events
        return func

    return decorator


class ListensTo:
    """
    Descriptor for automatically registering listener methods.

    Example:
        class NotificationListener:
            listens_to = ListensTo(UserRegistered, OrderPlaced)

            async def handle_user_registered(self, event: UserRegistered):
                pass

            async def handle_order_placed(self, event: OrderPlaced):
                pass
    """

    def __init__(self, *events: Type[Event]):
        self.events = events

    def __set_name__(self, owner: Type, name: str) -> None:
        self.name = name
        # Store events on class
        if not hasattr(owner, "_listens_to_events"):
            owner._listens_to_events = []
        owner._listens_to_events.extend(self.events)

    def __get__(self, obj: Any, objtype: Type | None = None) -> List[Type[Event]]:
        return self.events


def handles(*event_names: str) -> Callable:
    """
    Decorator to specify which event names a method handles.

    Useful when you want to handle events by name rather than class.

    Example:
        @handles("user.registered", "user.updated")
        async def on_user_event(event: Event):
            pass
    """

    def decorator(func: Callable) -> Callable:
        func._handles_events = event_names
        return func

    return decorator
