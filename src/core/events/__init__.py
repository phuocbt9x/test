"""
src/core/events/__init__.py

Event System for FastAPI application.

Usage:
    # Define an event
    from src.core.events import Event

    class UserRegistered(Event):
        user_id: UUID
        email: str
        name: str

    # Define a listener
    from src.core.events import Listener

    class SendWelcomeEmail(Listener):
        async def handle(self, event: UserRegistered) -> None:
            # Send email logic
            pass

    # Dispatch event
    from src.core.events import dispatch

    await dispatch(UserRegistered(
        user_id=user.id,
        email=user.email,
        name=user.name
    ))

    # Or use decorator
    from src.core.events import event_listener

    @event_listener(UserRegistered, priority=10)
    async def send_welcome_email(event: UserRegistered):
        # Send email
        pass
"""

from .event import Event
from .listener import Listener, SyncListener, QueuedListener
from .dispatcher import EventDispatcher
from .decorators import event_listener, subscribe, ListensTo, handles
from .manager import EventManager, event_manager, dispatch, listen, forget

__all__ = [
    # Core classes
    "Event",
    "Listener",
    "SyncListener",
    "QueuedListener",
    "EventDispatcher",
    "EventManager",
    # Decorators
    "event_listener",
    "subscribe",
    "ListensTo",
    "handles",
    # Singleton & convenience functions
    "event_manager",
    "dispatch",
    "listen",
    "forget",
]
