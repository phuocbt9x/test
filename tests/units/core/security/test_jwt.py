"""
Unit tests for JWT Token Management.

Tests cover:
- Token creation (access and refresh)
- Token verification and validation
- Token blacklisting and revocation
- User-level token revocation
- Error handling for expired/invalid tokens
"""
import pytest
import pytest_asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from jose import jwt

from src.core.security.jwt import JWTManager, TokenPayload, TokenResponse
from src.core.exceptions import AuthenticationException
from src.core.exceptions.types import ErrorCode
from src.core.configs import settings
from src.core.utils.timezone import utcnow


class TestJWTManager:
    """Test JWT Manager functionality."""

    # ==================== Token Creation Tests ====================

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "test-user-123"
        claims = {"email": "test@example.com", "roles": ["user"]}

        token = JWTManager.create_access_token(user_id, claims)

        assert token is not None
        assert isinstance(token, str)

        # Decode without verification to check structure
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False}
        )

        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert payload["email"] == "test@example.com"
        assert "roles" in payload
        assert "jti" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "test-user-456"

        token = JWTManager.create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False}
        )

        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "jti" in payload

    def test_create_token_pair(self):
        """Test creating access and refresh token pair."""
        user_id = "test-user-789"
        email = "user@example.com"
        username = "testuser"
        roles = ["user", "admin"]
        permissions = ["read:users", "write:posts"]

        token_pair = JWTManager.create_token_pair(
            user_id=user_id,
            email=email,
            username=username,
            roles=roles,
            permissions=permissions
        )

        assert isinstance(token_pair, TokenResponse)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS

        # Verify access token contains claims
        access_payload = jwt.decode(
            token_pair.access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False}
        )

        assert access_payload["email"] == email
        assert access_payload["username"] == username
        assert set(access_payload["roles"]) == set(roles)
        assert set(access_payload["permissions"]) == set(permissions)

    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiration time."""
        user_id = "test-user-custom"
        expires_delta = timedelta(hours=2)

        token = JWTManager.create_token(
            subject=user_id,
            token_type="access",
            expires_delta=expires_delta
        )

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False}
        )

        exp_time = payload["exp"]
        iat_time = payload["iat"]

        # Check expiration is approximately 2 hours from issued time
        assert (exp_time - iat_time) >= 7190  # Allow 10 seconds buffer

    def test_generate_unique_jti(self):
        """Test that each token gets a unique JWT ID."""
        user_id = "test-user-jti"

        token1 = JWTManager.create_access_token(user_id)
        token2 = JWTManager.create_access_token(user_id)

        payload1 = jwt.decode(token1, settings.JWT_SECRET_KEY, options={"verify_signature": False, "verify_aud": False})
        payload2 = jwt.decode(token2, settings.JWT_SECRET_KEY, options={"verify_signature": False, "verify_aud": False})

        assert payload1["jti"] != payload2["jti"]

    # ==================== Token Decoding Tests ====================

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        user_id = "test-user-decode"
        token = JWTManager.create_access_token(user_id)

        payload = JWTManager.decode_token(token, verify=True)

        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_decode_token_without_verification(self):
        """Test decoding without signature verification."""
        user_id = "test-user-no-verify"
        token = JWTManager.create_access_token(user_id)

        # Modify token (should still decode without verification)
        payload = JWTManager.decode_token(token, verify=False)

        assert payload["sub"] == user_id

    def test_decode_token_invalid_signature(self):
        """Test decoding token with invalid signature."""
        user_id = "test-user-invalid"
        token = JWTManager.create_access_token(user_id)

        # Tamper with token
        tampered_token = token[:-10] + "tampered12"

        with pytest.raises(AuthenticationException) as exc_info:
            JWTManager.decode_token(tampered_token, verify=True)

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        user_id = "test-user-expired"

        # Create token with negative expiry (already expired)
        token = JWTManager.create_token(
            subject=user_id,
            token_type="access",
            expires_delta=timedelta(seconds=-10)
        )

        with pytest.raises(AuthenticationException) as exc_info:
            JWTManager.decode_token(token, verify=True)

        assert exc_info.value.error_code == ErrorCode.TOKEN_EXPIRED
        assert "expired" in exc_info.value.message.lower()

    def test_decode_token_wrong_algorithm(self):
        """Test decoding token signed with wrong algorithm."""
        user_id = "test-user-algo"

        # Create token with different algorithm
        payload = {
            "sub": user_id,
            "type": "access",
            "jti": "test-jti",
            "exp": int((utcnow() + timedelta(minutes=15)).timestamp()),
            "iat": int(utcnow().timestamp()),
        }

        wrong_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS512")

        with pytest.raises(AuthenticationException) as exc_info:
            JWTManager.decode_token(wrong_token, verify=True)

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    # ==================== Token Verification Tests ====================

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, redis_client):
        """Test verifying a valid access token."""
        user_id = "test-user-verify"
        token = JWTManager.create_access_token(user_id, {"email": "test@example.com"})

        payload = await JWTManager.verify_token(token, token_type="access")

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id
        assert payload.type == "access"
        assert payload.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_token_wrong_type(self, redis_client):
        """Test verifying token with wrong type."""
        user_id = "test-user-type"
        refresh_token = JWTManager.create_refresh_token(user_id)

        with pytest.raises(AuthenticationException) as exc_info:
            await JWTManager.verify_token(refresh_token, token_type="access")

        assert exc_info.value.error_code == ErrorCode.INVALID_TOKEN_TYPE

    @pytest.mark.asyncio
    async def test_verify_token_blacklisted(self, redis_client):
        """Test verifying a blacklisted token."""
        user_id = "test-user-blacklist"
        token = JWTManager.create_access_token(user_id)

        # Decode to get JTI
        payload = JWTManager.decode_token(token, verify=False)
        jti = payload["jti"]

        # Mock Redis to return blacklisted
        redis_client.get.return_value = "1"

        with pytest.raises(AuthenticationException) as exc_info:
            await JWTManager.verify_token(token, token_type="access")

        assert exc_info.value.error_code == ErrorCode.TOKEN_REVOKED

    @pytest.mark.asyncio
    async def test_verify_token_invalid_payload_structure(self, redis_client):
        """Test verifying token with invalid payload structure."""
        # Create token with missing required fields
        payload = {
            "sub": "user-123",
            # Missing 'type', 'jti', etc.
        }

        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(AuthenticationException) as exc_info:
            await JWTManager.verify_token(token)

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    # ==================== Token Blacklisting Tests ====================

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_not_blacklisted(self, redis_client):
        """Test checking if token is not blacklisted."""
        jti = "test-jti-not-blacklisted"

        redis_client.get.return_value = None

        is_blacklisted = await JWTManager.is_token_blacklisted(jti)

        assert is_blacklisted is False

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_is_blacklisted(self, redis_client):
        """Test checking if token is blacklisted."""
        jti = "test-jti-is-blacklisted"

        redis_client.get.return_value = "1"

        is_blacklisted = await JWTManager.is_token_blacklisted(jti)

        assert is_blacklisted is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_redis_not_initialized(self):
        """Test blacklist check when Redis is not initialized."""
        from src.core.configs.redis import redis_manager

        original_initialized = redis_manager._initialized
        redis_manager._initialized = False

        jti = "test-jti-no-redis"
        is_blacklisted = await JWTManager.is_token_blacklisted(jti)

        # Should fail open (return False)
        assert is_blacklisted is False

        redis_manager._initialized = original_initialized

    @pytest.mark.asyncio
    async def test_blacklist_token_success(self, redis_client):
        """Test successfully blacklisting a token."""
        jti = "test-jti-blacklist"
        expires_in = 900

        result = await JWTManager.blacklist_token(jti, expires_in)

        assert result is True
        redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_blacklist_token_redis_error(self, redis_client):
        """Test blacklisting token when Redis fails."""
        jti = "test-jti-error"
        expires_in = 900

        redis_client.set.side_effect = Exception("Redis connection error")

        result = await JWTManager.blacklist_token(jti, expires_in)

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, redis_client):
        """Test revoking a token."""
        user_id = "test-user-revoke"
        token = JWTManager.create_access_token(user_id)

        result = await JWTManager.revoke_token(token)

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_missing_jti(self, redis_client):
        """Test revoking token with missing JTI."""
        # Create malformed token without JTI
        payload = {
            "sub": "user-123",
            "exp": int((utcnow() + timedelta(minutes=15)).timestamp()),
            "iat": int(utcnow().timestamp()),
            "type": "access",
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        result = await JWTManager.revoke_token(token)

        assert result is False

    # ==================== User Revocation Tests ====================

    @pytest.mark.asyncio
    async def test_revoke_all_user_tokens(self, redis_client):
        """Test revoking all tokens for a user."""
        user_id = "test-user-revoke-all"

        result = await JWTManager.revoke_all_user_tokens(user_id)

        assert result is True
        redis_client.set.assert_called_once()

        # Verify key and TTL
        call_args = redis_client.set.call_args
        assert f"revoked:user:{user_id}" in str(call_args)

    @pytest.mark.asyncio
    async def test_is_user_revoked_not_revoked(self, redis_client):
        """Test checking if user tokens are not revoked."""
        user_id = "test-user-not-revoked"
        issued_at = int(utcnow().timestamp())

        redis_client.get.return_value = None

        is_revoked = await JWTManager.is_user_revoked(user_id, issued_at)

        assert is_revoked is False

    @pytest.mark.asyncio
    async def test_is_user_revoked_token_issued_before_revocation(self, redis_client):
        """Test user revocation for tokens issued before revocation."""
        user_id = "test-user-old-token"
        issued_at = int(utcnow().timestamp())

        # Revocation timestamp is AFTER token was issued
        revoked_at = issued_at + 100
        redis_client.get.return_value = str(revoked_at)

        is_revoked = await JWTManager.is_user_revoked(user_id, issued_at)

        assert is_revoked is True

    @pytest.mark.asyncio
    async def test_is_user_revoked_token_issued_after_revocation(self, redis_client):
        """Test user revocation for tokens issued after revocation."""
        user_id = "test-user-new-token"
        issued_at = int(utcnow().timestamp())

        # Revocation timestamp is BEFORE token was issued
        revoked_at = issued_at - 100
        redis_client.get.return_value = str(revoked_at)

        is_revoked = await JWTManager.is_user_revoked(user_id, issued_at)

        assert is_revoked is False

    @pytest.mark.asyncio
    async def test_is_user_revoked_redis_error(self, redis_client):
        """Test user revocation check when Redis fails."""
        user_id = "test-user-redis-fail"
        issued_at = int(utcnow().timestamp())

        redis_client.get.side_effect = Exception("Redis error")

        is_revoked = await JWTManager.is_user_revoked(user_id, issued_at)

        # Should fail open
        assert is_revoked is False

    # ==================== Edge Cases ====================

    def test_create_token_pair_minimal_claims(self):
        """Test creating token pair with minimal claims."""
        user_id = "minimal-user"

        token_pair = JWTManager.create_token_pair(user_id=user_id)

        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None

        payload = jwt.decode(
            token_pair.access_token,
            options={"verify_signature": False}
        )

        assert payload["sub"] == user_id
        assert payload.get("email") is None
        assert payload.get("roles") == []

    @pytest.mark.asyncio
    async def test_verify_token_with_all_custom_claims(self, redis_client):
        """Test verifying token with all custom claims."""
        user_id = "full-claims-user"
        claims = {
            "email": "full@example.com",
            "username": "fulluser",
            "roles": ["admin", "user", "moderator"],
            "permissions": ["read:all", "write:all", "delete:all"]
        }

        token = JWTManager.create_access_token(user_id, claims)
        payload = await JWTManager.verify_token(token)

        assert payload.email == "full@example.com"
        assert payload.username == "fulluser"
        assert set(payload.roles) == set(claims["roles"])
        assert set(payload.permissions) == set(claims["permissions"])

    def test_token_issuer_and_audience(self):
        """Test that tokens include correct issuer and audience."""
        user_id = "iss-aud-user"
        token = JWTManager.create_access_token(user_id)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, options={"verify_signature": False, "verify_aud": False})

        assert payload["iss"] == settings.JWT_ISSUER
        assert payload["aud"] == settings.JWT_AUDIENCE
