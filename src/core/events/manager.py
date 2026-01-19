"""
src/core/events/manager.py

Event Manager - Singleton for managing event system.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Type, Optional, List
from threading import Lock

from .event import Event
from .listener import Listener
from .dispatcher import EventDispatcher

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    """Thread-safe Singleton metaclass."""

    _instances: dict[type, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class EventManager(metaclass=SingletonMeta):
    """
    Event Manager (Singleton).

    Central point for managing events and listeners.

    Usage:
        from src.core.events import event_manager, Event

        # Dispatch event
        await event_manager.dispatch(UserRegistered(user_id=123))

        # Register listener
        event_manager.listen(UserRegistered, SendWelcomeEmail)
    """

    def __init__(self) -> None:
        self._dispatcher = EventDispatcher()
        self._initialized = False

    def initialize(self, listeners_dir: str = "src/listeners") -> None:
        """
        Initialize event manager and auto-discover listeners.

        Args:
            listeners_dir: Directory containing listener modules
        """
        if self._initialized:
            logger.warning("EventManager already initialized")
            return

        logger.info("Initializing EventManager...")

        # Auto-discover and register listeners
        self._auto_discover_listeners(listeners_dir)

        self._initialized = True
        logger.info("EventManager initialized successfully")

    def _auto_discover_listeners(self, listeners_dir: str) -> None:
        """
        Auto-discover and register listeners from directory.

        Looks for:
        - Classes inheriting from Listener
        - Functions decorated with @event_listener

        Args:
            listeners_dir: Directory to search for listeners
        """
        listeners_path = Path(listeners_dir)

        if not listeners_path.exists():
            logger.warning(f"Listeners directory not found: {listeners_dir}")
            return

        logger.info(f"Auto-discovering listeners in: {listeners_dir}")

        # Import all Python files in listeners directory
        for file_path in listeners_path.rglob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                # Convert path to module notation
                module_path = (
                    str(file_path.with_suffix("")).replace("/", ".").replace("\\", ".")
                )

                # Dynamic import
                import importlib

                module = importlib.import_module(module_path)

                # Find and register listeners
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Register Listener classes
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Listener)
                        and attr is not Listener
                    ):
                        self._register_listener_class(attr)

                    # Register decorated functions
                    elif callable(attr) and hasattr(attr, "_event_listener"):
                        self._register_decorated_function(attr)

                logger.debug(f"Processed listener module: {module_path}")

            except Exception as e:
                logger.error(f"Failed to load listener module {file_path}: {e}")

    def _register_listener_class(self, listener_class: Type[Listener]) -> None:
        """
        Register a Listener class.

        Looks for _listens_to_events attribute or handle_* methods.
        """
        # Check if class has _listens_to_events attribute
        if hasattr(listener_class, "_listens_to_events"):
            events = listener_class._listens_to_events
            for event in events:
                self._dispatcher.listen(event, listener_class)
                logger.debug(
                    f"Registered {listener_class.__name__} for {event.__name__}"
                )

    def _register_decorated_function(self, func: Callable) -> None:
        """Register a function decorated with @event_listener."""
        events = func._listened_events

        for event in events:
            self._dispatcher.listen(event, func)
            logger.debug(f"Registered function {func.__name__} for {event.__name__}")

    async def dispatch(self, event: Event) -> List[Any]:
        """
        Dispatch an event to all registered listeners.

        Args:
            event: The event to dispatch

        Returns:
            List of results from listeners
        """
        return await self._dispatcher.dispatch(event)

    def listen(
        self, event: Type[Event] | str, listener: Type[Listener] | Listener | Callable
    ) -> None:
        """
        Register a listener for an event.

        Args:
            event: Event class or event name
            listener: Listener class, instance, or callable
        """
        self._dispatcher.listen(event, listener)

    def forget(self, event: Type[Event] | str) -> None:
        """
        Remove all listeners for an event.

        Args:
            event: Event class or event name
        """
        self._dispatcher.forget(event)

    def set_queue_adapter(self, adapter: Any) -> None:
        """
        Set the queue adapter for async listener execution.

        Args:
            adapter: Queue adapter instance
        """
        self._dispatcher.set_queue_adapter(adapter)

    def has_listeners(self, event: Type[Event] | str) -> bool:
        """
        Check if an event has any listeners.

        Args:
            event: Event class or event name

        Returns:
            True if event has listeners
        """
        return self._dispatcher.has_listeners(event)

    def get_listeners(self, event: Type[Event] | str) -> List[Listener]:
        """
        Get all listeners for an event.

        Args:
            event: Event class or event name

        Returns:
            List of listeners
        """
        return self._dispatcher.get_listeners(event)

    @property
    def dispatcher(self) -> EventDispatcher:
        """Get the underlying dispatcher."""
        return self._dispatcher

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized


# Singleton instance
event_manager = EventManager()


# Convenience functions
async def dispatch(event: Event) -> List[Any]:
    """
    Dispatch an event (convenience function).

    Args:
        event: The event to dispatch

    Returns:
        List of results from listeners
    """
    return await event_manager.dispatch(event)


def listen(
    event: Type[Event] | str, listener: Type[Listener] | Listener | Callable
) -> None:
    """
    Register a listener (convenience function).

    Args:
        event: Event class or event name
        listener: Listener class, instance, or callable
    """
    event_manager.listen(event, listener)


def forget(event: Type[Event] | str) -> None:
    """
    Remove all listeners for an event (convenience function).

    Args:
        event: Event class or event name
    """
    event_manager.forget(event)
