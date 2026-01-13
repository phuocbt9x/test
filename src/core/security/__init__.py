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
        verify_token_structure,
        get_current_user,
    )
"""

from .password import (
    hash_password,
    verify_password,
    PasswordHasher,
    validate_and_hash_password,
)
from .jwt import (
    JWTManager,
    TokenPayload,
    TokenResponse,
    create_access_token,
    create_refresh_token,
    verify_token_structure,
    decode_token,
)
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_token_payload,
    get_token_from_header,
    optional_auth,
    require_roles,
    require_permissions,
    require_all_roles,
    require_auth,
    require_active_user,
    require_superuser,
    CurrentUser,
)

__all__ = [
    "hash_password",
    "verify_password",
    "PasswordHasher",
    "validate_and_hash_password",
    "JWTManager",
    "TokenPayload",
    "TokenResponse",
    "create_access_token",
    "create_refresh_token",
    "verify_token_structure",
    "decode_token",
    "get_current_user",
    "get_current_active_user",
    "get_token_payload",
    "get_token_from_header",
    "optional_auth",
    "CurrentUser",
    "require_roles",
    "require_permissions",
    "require_all_roles",
    "require_auth",
    "require_active_user",
    "require_superuser",
]
