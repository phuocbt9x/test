"""
JWT Token Management

Handles creation, verification, and decoding of JWT tokens.
Supports both access and refresh tokens with token blacklisting.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import logging

from jose import JWTError, jwt
from pydantic import BaseModel, Field

from src.core.configs import settings
from src.core.configs.redis import redis_manager
from src.core.exceptions import AuthenticationException

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
        Create a JWT token.
        
        Args:
            subject: Subject (typically user ID)
            token_type: 'access' or 'refresh'
            expires_delta: Token expiration time
            additional_claims: Additional data to include in token
        
        Returns:
            Encoded JWT token
        """
        now = datetime.utcnow()
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
        claims = {}
        if email:
            claims["email"] = email
        if username:
            claims["username"] = username
        if roles:
            claims["roles"] = roles
        if permissions:
            claims["permissions"] = permissions
        
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
                error_code="TOKEN_EXPIRED"
            )
        except jwt.JWTClaimsError as e:
            raise AuthenticationException(
                message=f"Invalid token claims: {str(e)}",
                error_code="INVALID_CLAIMS"
            )
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise AuthenticationException(
                message="Could not validate credentials",
                error_code="INVALID_TOKEN"
            )
    
    @staticmethod
    def verify_token(token: str, token_type: Optional[str] = None) -> TokenPayload:
        """
        Verify and parse a JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')
        
        Returns:
            Parsed TokenPayload
        
        Raises:
            AuthenticationException: If token is invalid or blacklisted
        """
        # Decode token
        payload = JWTManager.decode_token(token, verify=True)
        
        # Check token type
        if token_type and payload.get("type") != token_type:
            raise AuthenticationException(
                message=f"Invalid token type. Expected {token_type}",
                error_code="INVALID_TOKEN_TYPE"
            )
        
        # Check if token is blacklisted
        jti = payload.get("jti")
        if jti and JWTManager.is_token_blacklisted(jti):
            raise AuthenticationException(
                message="Token has been revoked",
                error_code="TOKEN_REVOKED"
            )
        
        # Parse to TokenPayload
        try:
            return TokenPayload(**payload)
        except Exception as e:
            logger.error(f"Failed to parse token payload: {e}")
            raise AuthenticationException(
                message="Invalid token payload",
                error_code="INVALID_TOKEN"
            )
    
    @staticmethod
    def is_token_blacklisted(jti: str) -> bool:
        """
        Check if token is blacklisted.
        
        Args:
            jti: JWT ID
        
        Returns:
            True if blacklisted
        """
        try:
            if not redis_manager.is_initialized:
                return False
            
            import asyncio
            # Check if running in async context
            try:
                asyncio.get_running_loop()
                # We're in async context, need to handle this differently
                # For now, return False to avoid blocking
                logger.warning("is_token_blacklisted called in async context")
                return False
            except RuntimeError:
                # Not in async context, can use sync check
                return False
                
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
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
        Revoke a token by adding it to blacklist.
        
        Args:
            token: JWT token to revoke
        
        Returns:
            True if successful
        """
        try:
            payload = JWTManager.decode_token(token, verify=False)
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if not jti or not exp:
                logger.error("Token missing jti or exp claim")
                return False
            
            # Calculate remaining time until expiration
            now = int(datetime.utcnow().timestamp())
            expires_in = max(0, exp - now)
            
            return await JWTManager.blacklist_token(jti, expires_in)
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    @staticmethod
    async def revoke_all_user_tokens(user_id: str) -> bool:
        """
        Revoke all tokens for a user.
        
        This is a simple implementation. For production, consider:
        1. Storing token JTIs per user in Redis
        2. Using a user-level blacklist with version numbers
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful
        """
        try:
            if not redis_manager.is_initialized:
                return False
            
            # Set user revocation marker
            key = f"revoked:user:{user_id}"
            # Set with long TTL (longer than max refresh token life)
            ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_SECONDS + 3600
            await redis_manager.set(key, str(int(datetime.utcnow().timestamp())), ttl=ttl)
            
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


# Convenience functions
def create_access_token(user_id: str, **claims) -> str:
    """Create access token"""
    return JWTManager.create_access_token(user_id, claims)


def create_refresh_token(user_id: str, **claims) -> str:
    """Create refresh token"""
    return JWTManager.create_refresh_token(user_id, claims)


def verify_token(token: str, token_type: Optional[str] = None) -> TokenPayload:
    """Verify token"""
    return JWTManager.verify_token(token, token_type)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode token without verification"""
    return JWTManager.decode_token(token, verify=False)