"""
Configuration Module

Provides centralized configuration management including:
- Application settings
- Database configuration
- Redis/Cache management
- Logging configuration

Usage:
    from src.core.configs import (
        settings,
        db,
        get_db,
        redis_manager,
        cached,
    )
"""

from .setting import settings, Environment, JWTAlgorithm
from .logging import logging_settings
from .database import Base, db, get_db, get_read_db, get_write_db, DatabaseManager
from .redis import redis_manager, RedisManager
from .cache import (
    cached,
    cache_invalidate,
    cache_key,
    cache_key_hash,
    RateLimiter,
    DistributedLock,
    RedisQueue,
    SessionStore,
)

__all__ = [
    # Settings
    "settings",
    "logging_settings",
    "Environment",
    "JWTAlgorithm",
    # Database
    "Base",
    "db",
    "get_db",
    "get_read_db",
    "get_write_db",
    "DatabaseManager",
    # Redis
    "redis_manager",
    "RedisManager",
    # Cache utilities
    "cached",
    "cache_invalidate",
    "cache_key",
    "cache_key_hash",
    # Redis utilities
    "RateLimiter",
    "DistributedLock",
    "RedisQueue",
    "SessionStore",
]
