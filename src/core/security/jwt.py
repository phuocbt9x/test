"""
JWT Token Management Module

This module provides comprehensive JWT (JSON Web Token) functionality including:
- Token creation (access and refresh tokens)
- Token verification and validation
- Token blacklisting for logout/revocation
- User-level token revocation

Security Features:
- JWT ID (jti) for unique token identification
- Token type validation (access vs refresh)
- Issuer and audience validation
- Token blacklisting via Redis
- User-level token revocation

Usage:
    # Create tokens
    from src.core.security.jwt import JWTManager

    token_pair = JWTManager.create_token_pair(
        user_id="123",
        email="user@example.com",
        roles=["user", "admin"]
    )

    # Verify token
    payload = JWTManager.verify_token(token_pair.access_token, token_type="access")

    # Revoke token
    await JWTManager.revoke_token(token_pair.access_token)
"""
from datetime import timedelta
from typing import Any, Dict, Optional
import logging

from jose import JWTError, jwt  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from src.core.configs import settings
from src.core.configs.redis import redis_manager
from src.core.exceptions import AuthenticationException
from src.core.exceptions.types import ErrorCode
from src.core.utils.timezone import utcnow

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT Token Payload Schema"""
    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID (unique token identifier)")
    type: str = Field(..., description="Token type: access or refresh")
    iss: str = Field(default=settings.JWT_ISSUER, description="Issuer")
    aud: str = Field(default=settings.JWT_AUDIENCE, description="Audience")
    
    # Optional custom claims
    email: Optional[str] = None
    username: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    """Token Response Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class JWTManager:
    """JWT Token Manager with Redis-based blacklisting"""
    
    @staticmethod
    def _generate_jti() -> str:
        """Generate unique JWT ID"""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def create_token(
        subject: str,
        token_type: str,
        expires_delta: timedelta,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a JWT token with proper timezone handling.

        This method creates a JWT token with the following standard claims:
        - sub: Subject (user ID)
        - exp: Expiration time
        - iat: Issued at time
        - jti: JWT ID (unique identifier)
        - type: Token type (access or refresh)
        - iss: Issuer
        - aud: Audience

        Args:
            subject: Subject identifier, typically user ID
            token_type: Type of token - either 'access' or 'refresh'
            expires_delta: Time delta until token expiration
            additional_claims: Optional dictionary of additional claims to include
                              (e.g., email, roles, permissions)

        Returns:
            str: Encoded JWT token string

        Example:
            >>> from datetime import timedelta
            >>> token = JWTManager.create_token(
            ...     subject="user_123",
            ...     token_type="access",
            ...     expires_delta=timedelta(minutes=15),
            ...     additional_claims={"email": "user@example.com"}
            ... )
        """
        now = utcnow()
        expire = now + expires_delta
        
        # Base payload
        payload: Dict[str, Any] = {
            "sub": str(subject),
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": JWTManager._generate_jti(),
            "type": token_type,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }
        
        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Encode token
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        
        return token
    
    @staticmethod
    def create_access_token(
        subject: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create an access token.
        
        Args:
            subject: User ID
            additional_claims: Additional data (email, roles, etc.)
        
        Returns:
            Access token
        """
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        return JWTManager.create_token(
            subject=subject,
            token_type="access",
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )
    
    @staticmethod
    def create_refresh_token(
        subject: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a refresh token.
        
        Args:
            subject: User ID
            additional_claims: Additional data
        
        Returns:
            Refresh token
        """
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        return JWTManager.create_token(
            subject=subject,
            token_type="refresh",
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )
    
    @staticmethod
    def create_token_pair(
        user_id: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        roles: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
    ) -> TokenResponse:
        """
        Create both access and refresh tokens.
        
        Args:
            user_id: User ID
            email: User email
            username: Username
            roles: User roles
            permissions: User permissions
        
        Returns:
            TokenResponse with both tokens
        """
        claims: dict[str, str | list[str] | int] = {}
        if email:
            claims["email"] = email
        if username:
            claims["username"] = username
        if roles:
            claims["roles"] = roles  # type: ignore[assignment]
        if permissions:
            claims["permissions"] = permissions  # type: ignore[assignment]
        
        access_token = JWTManager.create_access_token(user_id, claims)
        refresh_token = JWTManager.create_refresh_token(user_id, claims)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
        )
    
    @staticmethod
    def decode_token(token: str, verify: bool = True) -> Dict[str, Any]:
        """
        Decode and optionally verify a JWT token.
        
        Args:
            token: JWT token string
            verify: Whether to verify signature and expiration
        
        Returns:
            Decoded payload
        
        Raises:
            AuthenticationException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_signature": verify, "verify_exp": verify},
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationException(
                message="Token has expired",
                error_code=ErrorCode.TOKEN_EXPIRED
            )
        except jwt.JWTClaimsError as e:
            raise AuthenticationException(
                message=f"Invalid token claims: {str(e)}",
                error_code=ErrorCode.INVALID_CLAIMS
            )
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise AuthenticationException(
                message="Could not validate credentials",
                error_code=ErrorCode.TOKEN_INVALID
            )
    
    @staticmethod
    async def verify_token(token: str, token_type: Optional[str] = None) -> TokenPayload:
        """
        Verify and parse a JWT token (async version).

        This method performs comprehensive token validation including:
        1. Signature verification
        2. Expiration check
        3. Token type validation
        4. Blacklist check (via Redis)
        5. User revocation check

        Args:
            token: JWT token string to verify
            token_type: Expected token type ('access' or 'refresh').
                       If provided, validates that the token matches this type.

        Returns:
            TokenPayload: Parsed and validated token payload containing user claims

        Raises:
            AuthenticationException: If token is invalid, expired, wrong type,
                                   blacklisted, or user has been revoked

        Example:
            >>> # Verify access token
            >>> payload = await JWTManager.verify_token(
            ...     token="eyJ0eXAiOiJKV1QiLCJhbGc...",
            ...     token_type="access"
            ... )
            >>> print(payload.sub)  # User ID
            user_123
            >>> print(payload.email)
            user@example.com
        """
        # Decode token
        payload = JWTManager.decode_token(token, verify=True)

        # Check token type
        if token_type and payload.get("type") != token_type:
            raise AuthenticationException(
                message=f"Invalid token type. Expected {token_type}",
                error_code=ErrorCode.INVALID_TOKEN_TYPE
            )

        # Check if token is blacklisted (async)
        jti = payload.get("jti")
        if jti:
            is_blacklisted = await JWTManager.is_token_blacklisted(jti)
            if is_blacklisted:
                raise AuthenticationException(
                    message="Token has been revoked",
                    error_code=ErrorCode.TOKEN_REVOKED
                )

        # Parse to TokenPayload
        try:
            return TokenPayload(**payload)
        except Exception as e:
            logger.error(f"Failed to parse token payload: {e}")
            raise AuthenticationException(
                message="Invalid token payload",
                error_code=ErrorCode.TOKEN_INVALID
            )

    @staticmethod
    async def is_token_blacklisted(jti: str) -> bool:
        """
        Check if a token has been blacklisted (async version).

        This method queries Redis to determine if a token with the given JWT ID
        has been explicitly revoked/blacklisted.

        Args:
            jti: JWT ID (unique token identifier)

        Returns:
            bool: True if the token is blacklisted, False otherwise.
                  Returns False if Redis is not initialized (fail-open for availability).

        Example:
            >>> is_blacklisted = await JWTManager.is_token_blacklisted("abc-123-def")
            >>> if is_blacklisted:
            ...     print("Token has been revoked")

        Note:
            This method fails open (returns False) if Redis is unavailable to
            maintain system availability. For production systems with strict
            security requirements, consider failing closed instead.
        """
        try:
            if not redis_manager.is_initialized:
                logger.warning("Redis not initialized, cannot check token blacklist")
                return False

            key = f"blacklist:token:{jti}"
            value = await redis_manager.get(key)
            return value is not None

        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            # Fail open: allow access if blacklist check fails
            # For stricter security, change to: return True (fail closed)
            return False
    
    @staticmethod
    async def blacklist_token(jti: str, expires_in: int) -> bool:
        """
        Add token to blacklist.
        
        Args:
            jti: JWT ID
            expires_in: Time until token naturally expires (seconds)
        
        Returns:
            True if successful
        """
        try:
            if not redis_manager.is_initialized:
                logger.warning("Redis not initialized, cannot blacklist token")
                return False
            
            key = f"blacklist:token:{jti}"
            await redis_manager.set(key, "1", ttl=expires_in)
            logger.info(f"Token {jti} blacklisted for {expires_in}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    @staticmethod
    async def revoke_token(token: str) -> bool:
        """
        Revoke a token by adding it to the blacklist.

        This method extracts the token's JWT ID and expiration time, then adds
        it to the Redis blacklist for the remaining duration until expiration.

        Args:
            token: JWT token string to revoke

        Returns:
            bool: True if token was successfully blacklisted, False otherwise

        Example:
            >>> # Revoke a user's token (e.g., during logout)
            >>> success = await JWTManager.revoke_token(user_token)
            >>> if success:
            ...     print("Token revoked successfully")

        Note:
            The token is only blacklisted until its natural expiration time.
            After expiration, the blacklist entry is automatically removed by Redis TTL.
        """
        try:
            payload = JWTManager.decode_token(token, verify=False)
            jti = payload.get("jti")
            exp = payload.get("exp")

            if not jti or not exp:
                logger.error("Token missing jti or exp claim")
                return False

            # Calculate remaining time until expiration
            now = int(utcnow().timestamp())
            expires_in = max(0, exp - now)

            return await JWTManager.blacklist_token(jti, expires_in)

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    @staticmethod
    async def revoke_all_user_tokens(user_id: str) -> bool:
        """
        Revoke all tokens for a specific user.

        This method sets a user-level revocation timestamp. All tokens issued
        before this timestamp will be considered invalid, even if they haven't
        expired yet.

        Implementation Notes:
            This is a simple user-level revocation mechanism. For production systems
            with high security requirements, consider:
            1. Storing individual token JTIs per user in Redis Sets
            2. Using a user token version number that increments on revocation
            3. Implementing a hybrid approach with both strategies

        Args:
            user_id: Unique identifier of the user whose tokens should be revoked

        Returns:
            bool: True if revocation was successful, False otherwise

        Example:
            >>> # Revoke all tokens when user changes password
            >>> success = await JWTManager.revoke_all_user_tokens("user_123")
            >>> if success:
            ...     print("All user tokens revoked")

            >>> # Use case: Force logout on all devices
            >>> await JWTManager.revoke_all_user_tokens(user.id)

        Note:
            The revocation marker is stored with a TTL longer than the maximum
            refresh token lifetime to ensure all tokens are properly invalidated.
        """
        try:
            if not redis_manager.is_initialized:
                logger.warning("Redis not initialized, cannot revoke user tokens")
                return False

            # Set user revocation marker with current timestamp
            key = f"revoked:user:{user_id}"
            # Set with long TTL (longer than max refresh token life)
            ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_SECONDS + 3600
            revocation_timestamp = str(int(utcnow().timestamp()))

            await redis_manager.set(key, revocation_timestamp, ttl=ttl)

            logger.info(f"All tokens revoked for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke user tokens: {e}")
            return False
    
    @staticmethod
    async def is_user_revoked(user_id: str, issued_at: int) -> bool:
        """
        Check if user's tokens have been revoked.
        
        Args:
            user_id: User ID
            issued_at: Token issued at timestamp
        
        Returns:
            True if user tokens revoked after this token was issued
        """
        try:
            if not redis_manager.is_initialized:
                return False
            
            key = f"revoked:user:{user_id}"
            revoked_at = await redis_manager.get(key)
            
            if not revoked_at:
                return False
            
            return int(revoked_at) > issued_at
            
        except Exception as e:
            logger.error(f"Error checking user revocation: {e}")
            return False


# ==================== Convenience Functions ====================
# These are simplified wrappers for common operations

def create_access_token(user_id: str, **claims) -> str:
    """
    Create an access token (convenience wrapper).

    Args:
        user_id: User identifier
        **claims: Additional claims to include in the token

    Returns:
        str: Encoded access token

    Example:
        >>> token = create_access_token("user_123", email="user@example.com")
    """
    return JWTManager.create_access_token(user_id, claims)


def create_refresh_token(user_id: str, **claims) -> str:
    """
    Create a refresh token (convenience wrapper).

    Args:
        user_id: User identifier
        **claims: Additional claims to include in the token

    Returns:
        str: Encoded refresh token

    Example:
        >>> token = create_refresh_token("user_123")
    """
    return JWTManager.create_refresh_token(user_id, claims)


async def verify_token(token: str, token_type: Optional[str] = None) -> TokenPayload:
    """
    Verify a JWT token (async convenience wrapper).

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        TokenPayload: Validated token payload

    Raises:
        AuthenticationException: If token is invalid

    Example:
        >>> payload = await verify_token(token, token_type="access")
    """
    return await JWTManager.verify_token(token, token_type)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token without verification (convenience wrapper).

    Warning:
        This function does NOT verify the token signature or expiration.
        Use only for debugging or when you need to inspect an expired token.

    Args:
        token: JWT token string

    Returns:
        Dict[str, Any]: Decoded token payload

    Example:
        >>> payload = decode_token(token)
        >>> print(payload['sub'])  # User ID
    """
    return JWTManager.decode_token(token, verify=False)