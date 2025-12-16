"""
FastAPI Security Dependencies

Provides reusable dependencies for JWT authentication and authorization.
"""

from typing import Optional, List
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from src.core.security.jwt import JWTManager, TokenPayload
from src.core.exceptions import AuthenticationException, AuthorizationException
from src.core.exceptions.types import ErrorCode

from uuid import UUID
from src.core.configs.database import db
from src.modules.user.models import User
from sqlalchemy import select
from src.core.utils.timezone import utcnow

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(
    scheme_name="JWT",
    description="Enter JWT token",
    auto_error=False,  # Don't auto raise 403, we handle it
)


class CurrentUser:
    """
    Current authenticated user data.
    Extracted from JWT token.
    """

    def __init__(self, token_payload: TokenPayload):
        self.user_id: str = token_payload.sub
        self.email: Optional[str] = token_payload.email
        self.username: Optional[str] = token_payload.username
        self.roles: List[str] = token_payload.roles or []
        self.permissions: List[str] = token_payload.permissions or []
        self.token_payload: TokenPayload = token_payload

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)

    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if user has all specified roles"""
        return all(role in self.roles for role in roles)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions

    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(perm in self.permissions for perm in permissions)

    def __repr__(self) -> str:
        return f"<CurrentUser(id={self.user_id}, email={self.email})>"


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenPayload:
    """
    Extract and verify JWT token.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        Verified token payload

    Raises:
        AuthenticationException: If token is invalid or missing
    """
    if not credentials:
        raise AuthenticationException(
            message="Missing authentication token", error_code=ErrorCode.MISSING_TOKEN
        )

    token = credentials.credentials

    try:
        # Verify token
        payload = await JWTManager.verify_token(token, token_type="access")

        # Check if user's tokens have been revoked
        is_revoked = await JWTManager.is_user_revoked(payload.sub, payload.iat)

        if is_revoked:
            raise AuthenticationException(
                message="Token has been revoked", error_code=ErrorCode.TOKEN_REVOKED
            )

        return payload

    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise AuthenticationException(
            message="Invalid authentication token", error_code=ErrorCode.TOKEN_INVALID
        )


async def get_current_user(
    payload: TokenPayload = Depends(get_token_payload),
) -> CurrentUser:
    """
    Get current authenticated user from token.

    Use this dependency in endpoints that require authentication.

    Usage:
        @app.get("/me")
        async def get_me(user: CurrentUser = Depends(get_current_user)):
            return {"user_id": user.user_id}

    Args:
        payload: Verified token payload

    Returns:
        CurrentUser object
    """
    return CurrentUser(payload)


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Get current active user with database verification.

    Checks user status in database:
    - User exists
    - is_active flag
    - Account is not locked

    Args:
        current_user: Current user from token

    Returns:
        CurrentUser if active

    Raises:
        AuthenticationException: If user is inactive, locked, or not found
    """

    # Check user status in database (using read replica for performance)
    async with db.session(read_only=True) as session:
        user_id = UUID(current_user.user_id)
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalars().first()

        if not user:
            raise AuthenticationException(
                message="User account not found", error_code=ErrorCode.USER_NOT_FOUND
            )

        if not user.is_active:
            raise AuthenticationException(
                message="User account is inactive", error_code=ErrorCode.USER_INACTIVE
            )

        # Check if account is locked
        if user.locked_until and user.locked_until > utcnow():
            raise AuthenticationException(
                message="User account is locked. Please try again later.",
                error_code=ErrorCode.ACCOUNT_LOCKED,
            )

    return current_user


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """
    Optional authentication dependency.

    Returns user if token is provided and valid, None otherwise.
    Useful for endpoints that work for both authenticated and anonymous users.

    Usage:
        @app.get("/items")
        async def get_items(user: Optional[CurrentUser] = Depends(optional_auth)):
            if user:
                # Show personalized items
                pass
            else:
                # Show public items
                pass

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        CurrentUser if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        payload = await get_token_payload(credentials)
        return CurrentUser(payload)
    except Exception:
        return None


def require_roles(*roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            user: CurrentUser = Depends(require_roles("admin"))
        ):
            return {"message": "Admin access"}

    Args:
        *roles: Required roles (user must have at least one)

    Returns:
        Dependency function
    """

    async def check_roles(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not current_user.has_any_role(list(roles)):
            raise AuthorizationException(
                message=f"Required roles: {', '.join(roles)}",
                error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            )
        return current_user

    return check_roles


def require_permissions(*permissions: str):
    """
    Dependency factory for permission-based access control.

    Usage:
        @app.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            user: CurrentUser = Depends(require_permissions("users:delete"))
        ):
            pass

    Args:
        *permissions: Required permissions (user must have at least one)

    Returns:
        Dependency function
    """

    async def check_permissions(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not current_user.has_any_permission(list(permissions)):
            raise AuthorizationException(
                message=f"Required permissions: {', '.join(permissions)}",
                error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            )
        return current_user

    return check_permissions


def require_all_roles(*roles: str):
    """
    Require user to have ALL specified roles.

    Usage:
        @app.get("/super-admin")
        async def super_admin_endpoint(
            user: CurrentUser = Depends(require_all_roles("admin", "superuser"))
        ):
            pass
    """

    async def check_all_roles(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not current_user.has_all_roles(list(roles)):
            raise AuthorizationException(
                message=f"Required all roles: {', '.join(roles)}",
                error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            )
        return current_user

    return check_all_roles


async def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Extract token string from header.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Token string

    Raises:
        AuthenticationException: If token is missing
    """
    if not credentials:
        raise AuthenticationException(
            message="Missing authentication token", error_code=ErrorCode.MISSING_TOKEN
        )
    return credentials.credentials


# Convenience aliases
require_auth = get_current_user
require_active_user = get_current_active_user
require_superuser = require_roles("admin")
