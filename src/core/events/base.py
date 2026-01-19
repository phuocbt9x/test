from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Event(ABC):
    """
    Base Event class

    All events must inherit from this class.
    Events are immutable data containers that represent something that happened.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())

    def get_event_name(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_name": self.get_event_name(),
            "data": self._serialize_data(),
        }

    @abstractmethod
    def _serialize_data(self) -> Dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        pass


class Listener(ABC):
    """
    Base Listener class

    All listeners must inherit from this class.
    Listeners handle events and contain the business logic.
    """

    should_queue: bool = False
    queue: Optional[str] = None
    tries: int = 3
    timeout: int = 60

    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass

    def failed(self, event: Event, exception: Exception) -> None:
        pass

    def get_listener_name(self) -> str:
        return self.__class__.__name__


class ShouldQueue(ABC):
    """
    Marker interface for listeners that should be queued

    Usage:
        class SendWelcomeEmail(Listener, ShouldQueue):
            pass
    """

    pass
