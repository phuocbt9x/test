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

    from src.core.security.jwt import JWTManager

    token_pair = JWTManager.create_token_pair(
        user_id="123",
        email="user@example.com",
        roles=["user", "admin"]
    )


    payload = JWTManager.verify_token(token_pair.access_token, token_type="access")


    await JWTManager.revoke_token(token_pair.access_token)
"""

from datetime import timedelta
from typing import Any, Dict, Optional
import logging

from jose import JWTError, jwt  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from src.core.configs import settings
from src.core.exceptions import AuthenticationException, ErrorCode
from src.core.i18n import __
from src.core.utils import utcnow

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

        payload: Dict[str, Any] = {
            "sub": str(subject),
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": JWTManager._generate_jti(),
            "type": token_type,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        if additional_claims:
            payload.update(additional_claims)

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
                message=__("auth.token.expired"), error_code=ErrorCode.TOKEN_EXPIRED
            )
        except jwt.JWTClaimsError:
            raise AuthenticationException(
                message=__("auth.token.invalid_claims"),
                error_code=ErrorCode.INVALID_CLAIMS,
            )
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise AuthenticationException(
                message=__("auth.token.invalid"),
                error_code=ErrorCode.TOKEN_INVALID,
            )

    @staticmethod
    def verify_token_structure(
        token: str, token_type: Optional[str] = None
    ) -> TokenPayload:
        """
        Verify JWT token structure and signature.

        This method performs JWT structure validation including:
        1. Signature verification
        2. Expiration check
        3. Token type validation
        4. Claims validation (issuer, audience)

        Note:
            Database validation (revocation check, user status) is handled
            separately in dependencies.py for better separation of concerns.

        Args:
            token: JWT token string to verify
            token_type: Expected token type ('access' or 'refresh').
                       If provided, validates that the token matches this type.

        Returns:
            TokenPayload: Parsed and validated token payload containing user claims

        Raises:
            AuthenticationException: If token is invalid, expired, or wrong type

        Example:
            >>>
            >>> payload = JWTManager.verify_token_structure(
            ...     token="eyJ0eXAiOiJKV1QiLCJhbGc...",
            ...     token_type="access"
            ... )
            >>> print(payload.sub)
            user_123
        """
        payload = JWTManager.decode_token(token, verify=True)

        if token_type and payload.get("type") != token_type:
            raise AuthenticationException(
                message=__("auth.token.invalid_type", type=token_type),
                error_code=ErrorCode.INVALID_TOKEN_TYPE,
            )

        try:
            return TokenPayload(**payload)
        except Exception as e:
            logger.error(f"Failed to parse token payload: {e}")
            raise AuthenticationException(
                message=__("auth.token.invalid"), error_code=ErrorCode.TOKEN_INVALID
            )


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


def verify_token_structure(
    token: str, token_type: Optional[str] = None
) -> TokenPayload:
    """
    Verify JWT token structure (convenience wrapper).

    Note: This only verifies the token structure. Database validation
    should be performed separately in the authentication flow.

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        TokenPayload: Validated token payload

    Raises:
        AuthenticationException: If token is invalid

    Example:
        >>> payload = verify_token_structure(token, token_type="access")
    """
    return JWTManager.verify_token_structure(token, token_type)


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
        >>> print(payload['sub'])
    """
    return JWTManager.decode_token(token, verify=False)
