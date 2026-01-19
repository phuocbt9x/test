"""
src/core/events/__init__.py

Event System - Main exports
"""

from .base import Event, Listener, ShouldQueue
from .dispatcher import EventDispatcher, EventSubscriber
from .queue import QueueManager, QueueWorker
from .manager import EventManager, event_manager

__all__ = [
    "Event",
    "Listener",
    "ShouldQueue",
    "EventDispatcher",
    "EventSubscriber",
    "QueueManager",
    "QueueWorker",
    "EventManager",
    "event_manager",
]
