"""
src/core/events/event.py

Base Event class for all application events.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field
from src.core.utils import utcnow


class Event(BaseModel):
    """
    Base Event class.

    All events should inherit from this class.

    Example:
        class UserRegistered(Event):
            user_id: UUID
            email: str
            name: str
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_time: datetime = Field(default_factory=utcnow)

    class Config:
        arbitrary_types_allowed = True

    def get_event_name(self) -> str:
        """Get event name (class name)."""
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return self.model_dump()

    @classmethod
    def get_listener_method(cls) -> str:
        """
        Get the listener method name for this event.

        Example: UserRegistered -> handle_user_registered
        """
        name = cls.__name__
        # Convert CamelCase to snake_case
        import re

        snake = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        snake = re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake).lower()
        return f"handle_{snake}"
