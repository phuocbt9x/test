"""
FastAPI Security Dependencies

Provides reusable dependencies for JWT authentication and authorization.
"""

from typing import Optional, List
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .jwt import JWTManager, TokenPayload
from src.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ErrorCode,
)
from src.core.i18n import __
from src.core.utils import utcnow
from src.core.configs.database import get_read_db, get_write_db

logger = logging.getLogger(__name__)

security = HTTPBearer(
    scheme_name="JWT",
    description="Enter JWT token",
    auto_error=False,
)


class CurrentUser:
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
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> TokenPayload:
    if not credentials:
        raise AuthenticationException(
            message=__("auth.authentication_failed"),
            error_code=ErrorCode.AUTHENTICATION_FAILED,
        )

    token = credentials.credentials

    try:
        payload = JWTManager.decode_token(token, verify=True)

        if payload.get("type") != "access":
            raise AuthenticationException(
                message="Invalid token type. Expected access token",
                error_code=ErrorCode.INVALID_TOKEN_TYPE,
            )

        jti = payload.get("jti")
        if jti:
            from src.modules.auth import AccessTokenRepository
            from src.modules.user import UserRepository

            access_token_repo = AccessTokenRepository(read_session, write_session)
            token_record = await access_token_repo.find_by_jti(jti)

            if not token_record:
                raise AuthenticationException(
                    message=__("auth.token.not_found"),
                    error_code=ErrorCode.TOKEN_NOT_FOUND,
                )

            if token_record.is_revoked:
                raise AuthenticationException(
                    message=__("auth.token.revoked"),
                    error_code=ErrorCode.TOKEN_REVOKED,
                )

            if token_record.expires_at < utcnow():
                raise AuthenticationException(
                    message=__("auth.token.expired"),
                    error_code=ErrorCode.TOKEN_EXPIRED,
                )

            user_repo = UserRepository(read_session, write_session)
            user = await user_repo.get(token_record.user_id)

            if not user:
                raise AuthenticationException(
                    message=__("auth.account.not_found"),
                    error_code=ErrorCode.USER_NOT_FOUND,
                )

            if not user.is_active:
                raise AuthenticationException(
                    message=__("auth.account.inactive"),
                    error_code=ErrorCode.USER_INACTIVE,
                )

        return TokenPayload(**payload)

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
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    request.state.current_user = current_user
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
                pass
            else:
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
                message=__("auth.unauthorized"),
                error_code=ErrorCode.UNAUTHORIZED,
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
                message=__("auth.unauthorized"),
                error_code=ErrorCode.UNAUTHORIZED,
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
            message=__("auth.authentication_failed"),
            error_code=ErrorCode.AUTHENTICATION_FAILED,
        )
    return credentials.credentials


require_auth = get_current_user
require_active_user = get_current_active_user
require_superuser = require_roles("admin")
