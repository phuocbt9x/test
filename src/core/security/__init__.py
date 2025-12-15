"""
Security Module

Provides comprehensive security functionality including:
- Password hashing and verification
- JWT token management
- Authentication dependencies
- Authorization utilities

Usage:
    from src.core.security import (
        hash_password,
        verify_password,
        create_access_token,
        verify_token,
        get_current_user,
    )
"""

from .password import hash_password, verify_password
from .jwt import (
    JWTManager,
    TokenPayload,
    TokenResponse,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
)
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_token_payload,
    optional_auth,
    require_roles,
    require_permissions,
    require_all_roles,
    require_auth,
    require_active_user,
    CurrentUser,
)

__all__ = [
    # Password utilities
    "hash_password",
    "verify_password",

    # JWT management
    "JWTManager",
    "TokenPayload",
    "TokenResponse",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",

    # Authentication dependencies
    "get_current_user",
    "get_current_active_user",
    "get_token_payload",
    "optional_auth",
    "CurrentUser",

    # Authorization dependencies
    "require_roles",
    "require_permissions",
    "require_all_roles",
    "require_auth",
    "require_active_user",
]
