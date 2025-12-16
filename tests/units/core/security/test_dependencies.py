"""
Unit tests for Security Dependencies.

Tests cover:
- Token payload extraction
- Current user dependency
- Active user verification
- Optional authentication
- Role-based access control
- Permission-based access control
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core.security.dependencies import (
    CurrentUser,
    get_token_payload,
    get_current_user,
    get_current_active_user,
    optional_auth,
    require_roles,
    require_permissions,
    require_all_roles,
    get_token_from_header,
)
from src.core.security.jwt import JWTManager, TokenPayload
from src.core.exceptions import AuthenticationException, AuthorizationException
from src.core.exceptions.types import ErrorCode
from src.modules.user.models import User
from src.core.utils.timezone import utcnow
from datetime import timedelta


class TestCurrentUser:
    """Test CurrentUser class."""

    def test_current_user_initialization(self):
        """Test CurrentUser initialization from token payload."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            email="test@example.com",
            username="testuser",
            roles=["user", "admin"],
            permissions=["read:posts", "write:posts"]
        )

        current_user = CurrentUser(payload)

        assert current_user.user_id == "user-123"
        assert current_user.email == "test@example.com"
        assert current_user.username == "testuser"
        assert current_user.roles == ["user", "admin"]
        assert current_user.permissions == ["read:posts", "write:posts"]

    def test_has_role(self):
        """Test checking if user has a specific role."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["user", "moderator"]
        )
        user = CurrentUser(payload)

        assert user.has_role("user") is True
        assert user.has_role("moderator") is True
        assert user.has_role("admin") is False

    def test_has_any_role(self):
        """Test checking if user has any of the specified roles."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["user"]
        )
        user = CurrentUser(payload)

        assert user.has_any_role(["user", "admin"]) is True
        assert user.has_any_role(["admin", "moderator"]) is False
        assert user.has_any_role([]) is False

    def test_has_all_roles(self):
        """Test checking if user has all specified roles."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["user", "admin", "moderator"]
        )
        user = CurrentUser(payload)

        assert user.has_all_roles(["user", "admin"]) is True
        assert user.has_all_roles(["user", "admin", "moderator"]) is True
        assert user.has_all_roles(["user", "superadmin"]) is False

    def test_has_permission(self):
        """Test checking if user has a specific permission."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            permissions=["read:posts", "write:posts"]
        )
        user = CurrentUser(payload)

        assert user.has_permission("read:posts") is True
        assert user.has_permission("delete:posts") is False

    def test_has_any_permission(self):
        """Test checking if user has any of the specified permissions."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            permissions=["read:posts"]
        )
        user = CurrentUser(payload)

        assert user.has_any_permission(["read:posts", "write:posts"]) is True
        assert user.has_any_permission(["delete:posts", "admin:all"]) is False

    def test_current_user_repr(self):
        """Test CurrentUser string representation."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            email="test@example.com"
        )
        user = CurrentUser(payload)

        repr_str = repr(user)
        assert "CurrentUser" in repr_str
        assert "user-123" in repr_str
        assert "test@example.com" in repr_str


class TestGetTokenPayload:
    """Test get_token_payload dependency."""

    @pytest.mark.asyncio
    async def test_get_token_payload_success(self, redis_client):
        """Test successful token payload extraction."""
        user_id = "test-user"
        token = JWTManager.create_access_token(user_id, {"email": "test@example.com"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        payload = await get_token_payload(credentials)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id
        assert payload.type == "access"
        assert payload.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_token_payload_missing_credentials(self):
        """Test token extraction with missing credentials."""
        with pytest.raises(AuthenticationException) as exc_info:
            await get_token_payload(None)

        assert exc_info.value.error_code == ErrorCode.MISSING_TOKEN
        assert "Missing" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_token_payload_invalid_token(self, redis_client):
        """Test token extraction with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )

        with pytest.raises(AuthenticationException) as exc_info:
            await get_token_payload(credentials)

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    @pytest.mark.asyncio
    async def test_get_token_payload_expired_token(self, redis_client):
        """Test token extraction with expired token."""
        user_id = "expired-user"
        # Create expired token
        token = JWTManager.create_token(
            subject=user_id,
            token_type="access",
            expires_delta=timedelta(seconds=-10)
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(AuthenticationException) as exc_info:
            await get_token_payload(credentials)

        assert exc_info.value.error_code == ErrorCode.TOKEN_EXPIRED

    @pytest.mark.asyncio
    async def test_get_token_payload_revoked_token(self, redis_client):
        """Test token extraction with revoked token."""
        user_id = "revoked-user"
        token = JWTManager.create_access_token(user_id)

        # Revoke token
        await JWTManager.revoke_token(token)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(AuthenticationException) as exc_info:
            await get_token_payload(credentials)

        assert exc_info.value.error_code == ErrorCode.TOKEN_REVOKED

    @pytest.mark.asyncio
    async def test_get_token_payload_user_tokens_revoked(self, redis_client):
        """Test token extraction when all user tokens are revoked."""
        user_id = "user-all-revoked"
        token = JWTManager.create_access_token(user_id)

        # Revoke all user tokens
        await JWTManager.revoke_all_user_tokens(user_id)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(AuthenticationException) as exc_info:
            await get_token_payload(credentials)

        assert exc_info.value.error_code == ErrorCode.TOKEN_REVOKED


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful current user extraction."""
        payload = TokenPayload(
            sub="user-123",
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            email="test@example.com",
            username="testuser"
        )

        current_user = await get_current_user(payload)

        assert isinstance(current_user, CurrentUser)
        assert current_user.user_id == "user-123"
        assert current_user.email == "test@example.com"


class TestGetCurrentActiveUser:
    """Test get_current_active_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, db_session, test_user):
        """Test getting current active user with database verification."""
        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            email=test_user.email
        )
        current_user = CurrentUser(payload)

        # Mock db session
        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            active_user = await get_current_active_user(current_user)

            assert active_user.user_id == str(test_user.id)

    @pytest.mark.asyncio
    async def test_get_current_active_user_not_found(self, db_session):
        """Test when user is not found in database."""
        payload = TokenPayload(
            sub=str(uuid4()),  # Non-existent user
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access"
        )
        current_user = CurrentUser(payload)

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with pytest.raises(AuthenticationException) as exc_info:
                await get_current_active_user(current_user)

            assert exc_info.value.error_code == ErrorCode.USER_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, db_session, inactive_user):
        """Test when user is inactive."""
        payload = TokenPayload(
            sub=str(inactive_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access"
        )
        current_user = CurrentUser(payload)

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with pytest.raises(AuthenticationException) as exc_info:
                await get_current_active_user(current_user)

            assert exc_info.value.error_code == ErrorCode.USER_INACTIVE

    @pytest.mark.asyncio
    async def test_get_current_active_user_locked(self, db_session, test_user):
        """Test when user account is locked."""
        # Lock the user account
        test_user.locked_until = utcnow() + timedelta(hours=1)
        db_session.add(test_user)
        await db_session.commit()

        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access"
        )
        current_user = CurrentUser(payload)

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with pytest.raises(AuthenticationException) as exc_info:
                await get_current_active_user(current_user)

            assert exc_info.value.error_code == ErrorCode.ACCOUNT_LOCKED


class TestOptionalAuth:
    """Test optional_auth dependency."""

    @pytest.mark.asyncio
    async def test_optional_auth_with_valid_token(self, redis_client):
        """Test optional auth with valid token."""
        user_id = "optional-user"
        token = JWTManager.create_access_token(user_id)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await optional_auth(credentials)

        assert user is not None
        assert isinstance(user, CurrentUser)
        assert user.user_id == user_id

    @pytest.mark.asyncio
    async def test_optional_auth_without_credentials(self):
        """Test optional auth without credentials."""
        user = await optional_auth(None)

        assert user is None

    @pytest.mark.asyncio
    async def test_optional_auth_with_invalid_token(self):
        """Test optional auth with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token"
        )

        user = await optional_auth(credentials)

        assert user is None


class TestRequireRoles:
    """Test require_roles dependency factory."""

    @pytest.mark.asyncio
    async def test_require_roles_success(self, db_session, admin_user):
        """Test role requirement with authorized user."""
        payload = TokenPayload(
            sub=str(admin_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["admin", "user"]
        )
        current_user = CurrentUser(payload)

        check_roles = require_roles("admin")

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            result = await check_roles(current_user)

            assert result == current_user

    @pytest.mark.asyncio
    async def test_require_roles_insufficient_permissions(self, db_session, test_user):
        """Test role requirement with insufficient roles."""
        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["user"]
        )
        current_user = CurrentUser(payload)

        check_roles = require_roles("admin")

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with pytest.raises(AuthorizationException) as exc_info:
                await check_roles(current_user)

            assert exc_info.value.error_code == ErrorCode.INSUFFICIENT_PERMISSIONS


class TestRequirePermissions:
    """Test require_permissions dependency factory."""

    @pytest.mark.asyncio
    async def test_require_permissions_success(self, db_session, test_user):
        """Test permission requirement with authorized user."""
        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            permissions=["read:users", "write:users"]
        )
        current_user = CurrentUser(payload)

        check_perms = require_permissions("read:users")

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            result = await check_perms(current_user)

            assert result == current_user

    @pytest.mark.asyncio
    async def test_require_permissions_insufficient(self, db_session, test_user):
        """Test permission requirement with insufficient permissions."""
        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            permissions=["read:users"]
        )
        current_user = CurrentUser(payload)

        check_perms = require_permissions("delete:users")

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with pytest.raises(AuthorizationException) as exc_info:
                await check_perms(current_user)

            assert exc_info.value.error_code == ErrorCode.INSUFFICIENT_PERMISSIONS


class TestRequireAllRoles:
    """Test require_all_roles dependency factory."""

    @pytest.mark.asyncio
    async def test_require_all_roles_success(self, db_session, test_user):
        """Test requiring all roles with authorized user."""
        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["user", "admin", "moderator"]
        )
        current_user = CurrentUser(payload)

        check_all = require_all_roles("user", "admin")

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            result = await check_all(current_user)

            assert result == current_user

    @pytest.mark.asyncio
    async def test_require_all_roles_missing_one(self, db_session, test_user):
        """Test requiring all roles when user is missing one."""
        payload = TokenPayload(
            sub=str(test_user.id),
            exp=int((utcnow() + timedelta(minutes=15)).timestamp()),
            iat=int(utcnow().timestamp()),
            jti="test-jti",
            type="access",
            roles=["user"]
        )
        current_user = CurrentUser(payload)

        check_all = require_all_roles("user", "admin")

        with patch('src.core.security.dependencies.db.session') as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with pytest.raises(AuthorizationException) as exc_info:
                await check_all(current_user)

            assert exc_info.value.error_code == ErrorCode.INSUFFICIENT_PERMISSIONS


class TestGetTokenFromHeader:
    """Test get_token_from_header utility."""

    @pytest.mark.asyncio
    async def test_get_token_from_header_success(self):
        """Test extracting token from header."""
        token = "test.jwt.token"
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_token_from_header(credentials)

        assert result == token

    @pytest.mark.asyncio
    async def test_get_token_from_header_missing(self):
        """Test extracting token when credentials are missing."""
        with pytest.raises(AuthenticationException) as exc_info:
            await get_token_from_header(None)

        assert exc_info.value.error_code == ErrorCode.MISSING_TOKEN
