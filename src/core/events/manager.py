from src.core.loggings import get_logger
from typing import Type, List, Dict, Optional
from pathlib import Path
import importlib.util
import inspect

from .base import Event, Listener
from .dispatcher import EventDispatcher, EventSubscriber
from .queue import QueueManager

logger = get_logger(__name__)


class EventManager:
    """
    Event Manager

    Facade for the event system. Provides simple interface for:
    - Registering events and listeners
    - Dispatching events
    - Auto-discovering event subscribers
    """

    _instance: Optional["EventManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._queue_manager = QueueManager()
            self._dispatcher = EventDispatcher(self._queue_manager)
            self._subscribers_loaded = False

    async def init(self, auto_discover: bool = True) -> None:
        if self._initialized:
            logger.warning("EventManager already initialized")
            return

        logger.info("Initializing EventManager...")

        if auto_discover:
            await self._discover_subscribers()

        self._initialized = True
        logger.info("EventManager initialized successfully")

    def listen(self, event: Type[Event], listener: Type[Listener]) -> None:
        self._dispatcher.listen(event, listener)

    def subscribe(self, subscriber: EventSubscriber) -> None:
        self._dispatcher.subscribe(subscriber)

    async def dispatch(self, event: Event) -> None:
        await self._dispatcher.dispatch(event)

    async def dispatch_sync(self, event: Event) -> None:
        event_name = event.get_event_name()
        listeners = self._dispatcher.get_listeners(type(event))

        for listener_class in listeners:
            listener = listener_class()
            try:
                await listener.handle(event)
            except Exception as e:
                logger.error(
                    f"Sync listener {listener.get_listener_name()} "
                    f"failed for event {event_name}: {e}",
                    exc_info=True,
                )
                listener.failed(event, e)

    def get_listeners(self, event: Type[Event]) -> List[Type[Listener]]:
        return self._dispatcher.get_listeners(event)

    def has_listeners(self, event: Type[Event]) -> bool:
        return self._dispatcher.has_listeners(event)

    def forget(self, event: Type[Event]) -> None:
        self._dispatcher.forget(event)

    async def _discover_subscribers(self) -> None:
        subscribers_dir = Path("src/events/subscribers")

        if not subscribers_dir.exists():
            logger.debug("Subscribers directory not found, skipping auto-discovery")
            return

        logger.info("Discovering event subscribers...")

        subscriber_files = list(subscribers_dir.glob("**/*.py"))

        for file_path in subscriber_files:
            if file_path.name.startswith("_"):
                continue

            try:
                module_path = (
                    str(file_path.relative_to(Path.cwd()))
                    .replace("/", ".")
                    .replace("\\", ".")[:-3]
                )
                spec = importlib.util.spec_from_file_location(module_path, file_path)

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, EventSubscriber)
                            and obj is not EventSubscriber
                        ):
                            subscriber = obj()
                            self.subscribe(subscriber)
                            logger.info(f"Registered subscriber: {name}")

            except Exception as e:
                logger.error(
                    f"Failed to load subscriber from {file_path}: {e}", exc_info=True
                )

        self._subscribers_loaded = True

    @property
    def queue_manager(self) -> QueueManager:
        return self._queue_manager

    @property
    def dispatcher(self) -> EventDispatcher:
        return self._dispatcher

    @property
    def is_initialized(self) -> bool:
        return self._initialized


event_manager = EventManager()
