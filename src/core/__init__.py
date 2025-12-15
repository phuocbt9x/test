"""
Core Module - Main Package Exports

This module provides the main public API for the application core functionality.
All commonly used utilities, configurations, and dependencies are exported here.

Usage:
    # Import everything you need from core
    from src.core import (
        settings,
        db,
        get_db,
        redis_manager,
        cached,
        get_logger,
        BaseModel,
        BaseRepository,
        hash_password,
        verify_password,
        create_access_token,
        get_current_user,
        utcnow,
    )

    # Or import specific submodules
    from src.core.configs import settings
    from src.core.security import JWTManager
    from src.core.utils import utcnow, now
"""

# Configuration & Settings
from src.core.configs import (
    settings,
    logging_settings,
    Environment,
    JWTAlgorithm,
    db,
    get_db,
    get_read_db,
    get_write_db,
    DatabaseManager,
    redis_manager,
    RedisManager,
    cached,
    cache_invalidate,
    cache_key,
    cache_key_hash,
    RateLimiter,
    DistributedLock,
    RedisQueue,
    SessionStore,
)

# Middlewares
from src.core.middlewares import setup_middlewares, limiter

# Logging
from src.core.loggings import (
    get_logger,
    setup_logging,
    JSONFormatter,
    ColoredFormatter,
    LoggingContext,
    DataMasker,
)

# Exceptions
from src.core.exceptions import (
    setup_exception_handlers,
    BaseAppException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    RateLimitException,
)

# Routers
from src.core.routers import auto_load_routers, print_routes_table

# Database
from src.core.databases import BaseModel, BaseRepository

# Security
from src.core.security import (
    hash_password,
    verify_password,
    JWTManager,
    TokenPayload,
    TokenResponse,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    get_current_user,
    get_current_active_user,
    get_token_payload,
    optional_auth,
    require_auth,
    require_active_user,
    require_roles,
    require_permissions,
    require_all_roles,
    CurrentUser,
)

# Utilities
from src.core.utils import (
    utcnow,
    now,
    to_timezone,
    to_utc,
    get_timezone,
    format_datetime,
)

__all__ = [
    # ========== Configuration & Settings ==========
    "settings",
    "logging_settings",
    "Environment",
    "JWTAlgorithm",

    # ========== Database ==========
    "db",
    "DatabaseManager",
    "get_db",
    "get_read_db",
    "get_write_db",
    "BaseModel",
    "BaseRepository",

    # ========== Redis & Cache ==========
    "redis_manager",
    "RedisManager",
    "cached",
    "cache_invalidate",
    "cache_key",
    "cache_key_hash",
    "RateLimiter",
    "DistributedLock",
    "RedisQueue",
    "SessionStore",

    # ========== Middlewares ==========
    "setup_middlewares",
    "limiter",

    # ========== Logging ==========
    "get_logger",
    "setup_logging",
    "JSONFormatter",
    "ColoredFormatter",
    "LoggingContext",
    "DataMasker",

    # ========== Exceptions ==========
    "setup_exception_handlers",
    "BaseAppException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "NotFoundException",
    "ConflictException",
    "RateLimitException",

    # ========== Routers ==========
    "auto_load_routers",
    "print_routes_table",

    # ========== Security - Password ==========
    "hash_password",
    "verify_password",

    # ========== Security - JWT ==========
    "JWTManager",
    "TokenPayload",
    "TokenResponse",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",

    # ========== Security - Authentication ==========
    "get_current_user",
    "get_current_active_user",
    "get_token_payload",
    "optional_auth",
    "require_auth",
    "require_active_user",
    "CurrentUser",

    # ========== Security - Authorization ==========
    "require_roles",
    "require_permissions",
    "require_all_roles",

    # ========== Utilities - Timezone ==========
    "utcnow",
    "now",
    "to_timezone",
    "to_utc",
    "get_timezone",
    "format_datetime",
]
