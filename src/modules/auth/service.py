"""
Auth Service

Business logic layer for authentication operations.
Implements JWT with database-backed blacklist instead of Redis.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs import settings
from src.core.exceptions import (
    AuthenticationException,
    UnauthorizedException,
)
from src.core.security.jwt import JWTManager, TokenPayload
from src.core.security.password import PasswordHasher
from src.core.utils.timezone import utcnow
from src.modules.user.models import User
from src.modules.user.repository import UserRepository

from .models import RefreshToken
from .repository import RefreshTokenRepository, TokenBlacklistRepository
from .schemas import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    """
    Authentication Service

    Handles:
    - User login/logout
    - Token generation and validation
    - JWT blacklisting (DB-based)
    - Refresh token rotation
    - Session management

    Design Patterns:
    - Service Layer Pattern
    - Repository Pattern for data access
    - Strategy Pattern for password hashing
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.blacklist_repo = TokenBlacklistRepository(session)
        self.refresh_token_repo = RefreshTokenRepository(session)
        self.password_hasher = PasswordHasher()

    async def register(
        self,
        data: RegisterRequest,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> tuple[User, TokenResponse]:
        """
        Register a new user and return tokens.

        Business Rules:
        - Email must be unique
        - Username must be unique
        - Password is hashed before storage
        - User gets access + refresh token immediately

        Args:
            data: Registration data
            device_info: User agent/device info
            ip_address: Client IP

        Returns:
            Tuple of (created user, tokens)

        Raises:
            ConflictException: If email or username exists
        """
        from src.modules.user.service import UserService
        from src.modules.user.schemas import UserCreateRequest

        # Create user via UserService
        user_service = UserService(self.session)
        user_data = UserCreateRequest(
            email=data.email,
            username=data.username,
            password=data.password,
            full_name=data.full_name,
        )
        user = await user_service.create_user(user_data)

        # Generate tokens
        tokens = await self._create_token_pair(
            user=user,
            device_info=device_info,
            ip_address=ip_address,
        )

        await self.session.commit()
        return user, tokens

    async def login(
        self,
        data: LoginRequest,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> tuple[User, TokenResponse]:
        """
        Authenticate user and return tokens.

        Business Rules:
        - User can login with email or username
        - Password must match
        - Account must be active
        - Failed login attempts are tracked
        - Account locks after max failed attempts

        Args:
            data: Login credentials
            device_info: User agent/device info
            ip_address: Client IP

        Returns:
            Tuple of (user, tokens)

        Raises:
            UnauthorizedException: If credentials invalid or account locked
        """
        # Find user by email or username
        user = await self.user_repo.find_by_email_or_username(data.email)

        if not user:
            raise UnauthorizedException(message="Invalid email or password")

        # Check if account is locked
        if user.locked_until and user.locked_until > utcnow():
            raise UnauthorizedException(
                message="Account is locked. Try again later."
            )

        # Verify password
        if not self.password_hasher.verify(data.password, user.password_hash):
            # Increment failed login attempts
            await self._handle_failed_login(user)
            await self.session.commit()
            raise UnauthorizedException(message="Invalid email or password")

        # Check if account is active
        if not user.is_active:
            raise UnauthorizedException(message="Account is deactivated")

        # Reset failed login attempts and update last login
        await self.user_repo.update(
            user.id,
            {
                "failed_login_attempts": 0,
                "locked_until": None,
                "last_login_at": utcnow(),
            }
        )

        # Generate tokens
        tokens = await self._create_token_pair(
            user=user,
            device_info=device_info,
            ip_address=ip_address,
        )

        await self.session.commit()
        return user, tokens

    async def logout(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> None:
        """
        Logout user by blacklisting tokens.

        Args:
            access_token: Access token to blacklist
            refresh_token: Refresh token to revoke (optional)

        Raises:
            AuthenticationException: If token is invalid
        """
        # Blacklist access token
        await self._blacklist_token(
            token=access_token,
            reason="logout"
        )

        # Revoke refresh token if provided
        if refresh_token:
            try:
                payload = JWTManager.decode_token(refresh_token, verify=False)
                jti = payload.get("jti")
                if jti:
                    await self.refresh_token_repo.revoke_token(jti)
            except Exception:
                pass  # Ignore errors for refresh token

        await self.session.commit()

    async def refresh_access_token(
        self,
        refresh_token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Implements token rotation for security:
        - Old refresh token is revoked
        - New refresh token is issued
        - New access token is issued

        Args:
            refresh_token: Current refresh token
            device_info: User agent/device info
            ip_address: Client IP

        Returns:
            New token pair

        Raises:
            AuthenticationException: If refresh token is invalid or revoked
        """
        # Verify refresh token
        payload = await self.verify_token(refresh_token, token_type="refresh")

        # Check if refresh token exists in DB and is not revoked
        refresh_token_record = await self.refresh_token_repo.find_by_jti(payload.jti)

        if not refresh_token_record:
            raise AuthenticationException(
                message="Refresh token not found",
                error_code="INVALID_REFRESH_TOKEN"
            )

        if refresh_token_record.is_revoked:
            raise AuthenticationException(
                message="Refresh token has been revoked",
                error_code="TOKEN_REVOKED"
            )

        if refresh_token_record.expires_at < utcnow():
            raise AuthenticationException(
                message="Refresh token has expired",
                error_code="TOKEN_EXPIRED"
            )

        # Get user
        user = await self.user_repo.get(refresh_token_record.user_id)
        if not user or not user.is_active:
            raise AuthenticationException(
                message="User not found or inactive",
                error_code="USER_INACTIVE"
            )

        # Revoke old refresh token
        await self.refresh_token_repo.revoke_token(payload.jti)

        # Create new token pair (token rotation)
        tokens = await self._create_token_pair(
            user=user,
            device_info=device_info or refresh_token_record.device_info,
            ip_address=ip_address or refresh_token_record.ip_address,
            family_id=refresh_token_record.family_id,
            parent_jti=payload.jti,
        )

        # Mark old token as used
        refresh_token_record.used_at = utcnow()

        await self.session.commit()
        return tokens

    async def verify_token(
        self,
        token: str,
        token_type: Optional[str] = None
    ) -> TokenPayload:
        """
        Verify JWT token and check blacklist (DB-based).

        Args:
            token: JWT token
            token_type: Expected token type

        Returns:
            Token payload

        Raises:
            AuthenticationException: If token is invalid or blacklisted
        """
        # Decode and verify token signature
        payload = JWTManager.decode_token(token, verify=True)

        # Check token type
        if token_type and payload.get("type") != token_type:
            raise AuthenticationException(
                message=f"Invalid token type. Expected {token_type}",
                error_code="INVALID_TOKEN_TYPE"
            )

        # Check if token is blacklisted (DB check)
        jti = payload.get("jti")
        if jti:
            is_blacklisted = await self.blacklist_repo.is_token_blacklisted(jti)
            if is_blacklisted:
                raise AuthenticationException(
                    message="Token has been revoked",
                    error_code="TOKEN_REVOKED"
                )

        # Parse to TokenPayload
        return TokenPayload(**payload)

    async def revoke_all_user_tokens(self, user_id: UUID, reason: str = "user_action") -> int:
        """
        Revoke all tokens for a user (e.g., on password change).

        Args:
            user_id: User ID
            reason: Revocation reason

        Returns:
            Number of tokens revoked
        """
        count = await self.refresh_token_repo.revoke_all_user_tokens(user_id)
        await self.session.commit()
        return count

    async def get_active_sessions(self, user_id: UUID) -> list[RefreshToken]:
        """Get all active sessions for a user"""
        return await self.refresh_token_repo.get_user_active_sessions(user_id)

    async def revoke_session(self, user_id: UUID, session_id: UUID) -> bool:
        """
        Revoke a specific session.

        Args:
            user_id: User ID (for authorization)
            session_id: Refresh token ID

        Returns:
            True if revoked successfully
        """
        # Get refresh token
        token = await self.refresh_token_repo.get(session_id)
        if not token or token.user_id != user_id:
            return False

        # Revoke it
        success = await self.refresh_token_repo.revoke_token(token.jti)
        await self.session.commit()
        return success

    # ==================== Private Helper Methods ====================

    async def _create_token_pair(
        self,
        user: User,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        family_id: Optional[UUID] = None,
        parent_jti: Optional[str] = None,
    ) -> TokenResponse:
        """
        Create access and refresh token pair.

        Args:
            user: User object
            device_info: User agent/device info
            ip_address: Client IP
            family_id: Token family ID for rotation
            parent_jti: Parent token JTI

        Returns:
            Token response with both tokens
        """
        # Create tokens using JWTManager
        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.username,
            roles=["admin"] if user.is_superuser else ["user"],
        )

        # Extract refresh token JTI and expiration
        refresh_payload = JWTManager.decode_token(token_pair.refresh_token, verify=False)
        refresh_jti = refresh_payload.get("jti")
        refresh_exp = refresh_payload.get("exp")

        # Store refresh token in database
        if refresh_jti and refresh_exp:
            expires_at = datetime.fromtimestamp(refresh_exp)
            await self.refresh_token_repo.store_refresh_token(
                jti=refresh_jti,
                user_id=user.id,
                expires_at=expires_at,
                device_info=device_info,
                ip_address=ip_address,
                family_id=family_id or uuid4(),  # Create new family if not provided
                parent_jti=parent_jti,
            )

        return token_pair

    async def _blacklist_token(
        self,
        token: str,
        reason: str = "logout"
    ) -> None:
        """
        Add token to blacklist.

        Args:
            token: JWT token
            reason: Revocation reason
        """
        try:
            payload = JWTManager.decode_token(token, verify=False)
            jti = payload.get("jti")
            user_id = payload.get("sub")
            exp = payload.get("exp")
            token_type = payload.get("type", "access")

            if jti and user_id and exp:
                expires_at = datetime.fromtimestamp(exp)
                # Store last 8 chars of token for debugging
                token_signature = token[-8:] if len(token) > 8 else None

                await self.blacklist_repo.blacklist_token(
                    jti=jti,
                    user_id=UUID(user_id),
                    token_type=token_type,
                    expires_at=expires_at,
                    reason=reason,
                    token_signature=token_signature,
                )
        except Exception:
            # Log error but don't fail logout
            pass

    async def _handle_failed_login(self, user: User) -> None:
        """
        Handle failed login attempt.

        Increments failed login counter and locks account if needed.

        Args:
            user: User object
        """
        failed_attempts = user.failed_login_attempts + 1
        update_data = {"failed_login_attempts": failed_attempts}

        # Lock account if max attempts exceeded
        if failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            lockout_duration = timedelta(seconds=settings.ACCOUNT_LOCKOUT_DURATION)
            update_data["locked_until"] = utcnow() + lockout_duration

        await self.user_repo.update(user.id, update_data)
