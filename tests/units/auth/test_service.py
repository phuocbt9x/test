import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import jose.jwt as jwt
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import (
    AuthenticationException,
    ErrorCode,
    JWTManager,
    NotFoundException,
    validate_and_hash_password,
    verify_password,
    utcnow,
    BaseAppException,
)
from src.core.configs.setting import settings
from src.modules.auth.repository import AccessTokenRepository
from src.modules.auth.schemas.request import (
    LoginRequest,
    UpdateCurrentUserRequest,
)
from src.modules.auth.service import AuthService
from src.modules.user import UserRepository


@pytest.mark.units
class TestAuthService:
    async def test_login_with_invalid_credentials(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        with pytest.raises(BaseAppException) as exc_info:
            await service.login(
                LoginRequest(email="wrong@test.com", password="WrongPassword123!")
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.error_code == ErrorCode.USER_NOT_FOUND

    async def test_login_success(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        await user_repo.create(
            {
                "name": "Active User",
                "email": "active@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
                "is_active": True,
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        result = await service.login(
            LoginRequest(email="active@test.com", password="TestPassword123!")
        )

        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.user_info.email == "active@test.com"

    async def test_login_with_inactive_user(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        await user_repo.create(
            {
                "name": "Inactive User",
                "email": "inactive@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
                "is_active": False,
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        with pytest.raises(BaseAppException) as exc_info:
            await service.login(
                LoginRequest(email="inactive@test.com", password="TestPassword123!")
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.error_code == ErrorCode.AUTHENTICATION_FAILED

    async def test_get_current_user_success(self, test_session: AsyncSession):
        from src.modules.user import UserRepository
        from src.core import validate_and_hash_password

        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Current User",
                "email": "current@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        result = await service.get_current_user(str(user.id))

        assert result.id == user.id
        assert result.email == user.email

    async def test_get_current_user_not_found(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_current_user("00000000-0000-0000-0000-000000000000")

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.error_code == ErrorCode.RESOURCE_NOT_FOUND

    async def test_refresh_token_invalid_type(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        invalid_token = JWTManager.create_access_token(
            subject="test-id",
            additional_claims={"email": "test@test.com"},
        )

        with pytest.raises(AuthenticationException) as exc_info:
            await service.refresh_token(invalid_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.error_code == ErrorCode.INVALID_TOKEN_TYPE

    async def test_logout_success(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Logout User",
                "email": "logout@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.name,
        )

        result = await service.logout(token_pair.access_token)

        assert result.message is not None
        await test_session.commit()

    async def test_update_current_user_success(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Original Name",
                "email": "update@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        update_data = UpdateCurrentUserRequest(name="Updated Name")
        updated_user = await service.update_current_user(user.id, update_data)

        assert updated_user.name == "Updated Name"
        assert updated_user.email == "update@test.com"

    async def test_update_current_user_not_found(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        update_data = UpdateCurrentUserRequest(name="Updated Name")

        with pytest.raises(NotFoundException):
            await service.update_current_user(
                UUID("00000000-0000-0000-0000-000000000000"), update_data
            )

    async def test_update_current_user_not_found_with_empty_dict(
        self, test_session: AsyncSession
    ):
        service = AuthService(test_session, test_session)

        with pytest.raises(NotFoundException) as exc_info:
            await service.update_current_user(
                UUID("00000000-0000-0000-0000-000000000000"), {}
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.error_code == ErrorCode.RESOURCE_NOT_FOUND

    async def test_verify_token_in_db_access_token_found(
        self, test_session: AsyncSession
    ):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Test User",
                "email": "verify@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.name,
        )

        access_payload = JWTManager.decode_token(token_pair.access_token, verify=False)
        jti = access_payload.get("jti")
        exp = access_payload.get("exp")

        expires_at = datetime.fromtimestamp(exp, tz=utcnow().tzinfo)
        access_token_repo = AccessTokenRepository(test_session, test_session)
        await access_token_repo.create(
            {
                "user_id": user.id,
                "jti": jti,
                "expires_at": expires_at,
                "is_revoked": False,
            }
        )
        await test_session.commit()

        is_valid, token = await service.verify_token_in_db(jti, "access")

        assert is_valid is True
        assert token is not None
        assert token.jti == jti

    async def test_verify_token_in_db_token_not_found(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        is_valid, token = await service.verify_token_in_db("non-existent-jti", "access")

        assert is_valid is False
        assert token is None

    async def test_verify_token_in_db_token_revoked(self, test_session: AsyncSession):
        user_id = uuid4()
        jti = "revoked-jti"

        access_token_repo = AccessTokenRepository(test_session, test_session)
        await access_token_repo.create(
            {
                "user_id": user_id,
                "jti": jti,
                "expires_at": utcnow(),
                "is_revoked": True,
                "revoked_at": utcnow(),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        is_valid, token = await service.verify_token_in_db(jti, "access")

        assert is_valid is False
        assert token is not None
        assert token.is_revoked is True

    async def test_verify_token_in_db_token_expired(self, test_session: AsyncSession):
        user_id = uuid4()
        jti = "expired-jti"

        access_token_repo = AccessTokenRepository(test_session, test_session)
        await access_token_repo.create(
            {
                "user_id": user_id,
                "jti": jti,
                "expires_at": utcnow() - timedelta(days=1),
                "is_revoked": False,
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        is_valid, token = await service.verify_token_in_db(jti, "access")

        assert is_valid is False
        assert token is not None
        assert token.expires_at < utcnow()

    async def test_register_with_optional_fields(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        user = await service.user_repo.create(
            {
                "name": "Admin User",
                "email": "admin@test.com",
                "password": validate_and_hash_password("SecurePass123!"),
                "phone": "0312345678",
                "line_user_id": "line123",
                "is_admin": True,
                "is_active": True,
            }
        )
        await test_session.commit()

        assert user.phone == "0312345678"
        assert user.line_user_id == "line123"
        assert user.is_admin is True
        assert user.is_active is True

    async def test_refresh_access_token_success(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Refresh Test User",
                "email": "refresh@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        new_tokens = await service.refresh_access_token(tokens.refresh_token)

        assert new_tokens.access_token is not None
        assert new_tokens.refresh_token is not None
        assert new_tokens.access_token != tokens.access_token

    async def test_refresh_access_token_invalid_token_type(
        self, test_session: AsyncSession
    ):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Test User",
                "email": "invalidtype@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        with pytest.raises(AuthenticationException) as exc_info:
            await service.refresh_access_token(tokens.access_token)

        assert exc_info.value.error_code == ErrorCode.INVALID_TOKEN_TYPE

    async def test_refresh_access_token_missing_jti(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        exp_time = int((utcnow() + timedelta(days=7)).timestamp())
        iat_time = int(utcnow().timestamp())

        payload = {
            "sub": "test-id",
            "type": "refresh",
            "email": "test@test.com",
            "exp": exp_time,
            "iat": iat_time,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        token_without_jti = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(AuthenticationException) as exc_info:
            await service.refresh_access_token(token_without_jti)

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    async def test_refresh_access_token_token_not_in_db(
        self, test_session: AsyncSession
    ):
        service = AuthService(test_session, test_session)

        token = JWTManager.create_refresh_token(
            subject="test-id", additional_claims={"email": "test@test.com"}
        )

        with pytest.raises(AuthenticationException) as exc_info:
            await service.refresh_access_token(token)

        assert exc_info.value.error_code == ErrorCode.TOKEN_REVOKED

    async def test_refresh_access_token_inactive_user(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Inactive User",
                "email": "inactive-refresh@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
                "is_active": False,
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        await user_repo.update(user.id, {"is_active": False})
        await test_session.commit()

        with pytest.raises(AuthenticationException) as exc_info:
            await service.refresh_access_token(tokens.refresh_token)

        assert exc_info.value.error_code == ErrorCode.USER_INACTIVE

    async def test_verify_token_success(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Verify User",
                "email": "verify-token@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        payload = await service.verify_token(tokens.access_token, "access")

        assert payload.sub == str(user.id)
        assert payload.email == user.email

    async def test_verify_token_wrong_type(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Test User",
                "email": "wrongtype@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        with pytest.raises(AuthenticationException) as exc_info:
            await service.verify_token(tokens.access_token, "refresh")

        assert exc_info.value.error_code == ErrorCode.INVALID_TOKEN_TYPE

    async def test_verify_token_revoked(self, test_session: AsyncSession):
        from src.modules.user import UserRepository
        from src.core import validate_and_hash_password

        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Test User",
                "email": "revoked-verify@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        await service.access_token_repo.revoke_all_user_tokens(user.id)
        await test_session.commit()

        with pytest.raises(AuthenticationException) as exc_info:
            await service.verify_token(tokens.access_token, "access")

        assert exc_info.value.error_code == ErrorCode.TOKEN_REVOKED

    async def test_update_current_user_with_password_change(
        self, test_session: AsyncSession
    ):
        user_repo = UserRepository(test_session, test_session)
        old_password = "OldPassword123!"
        user = await user_repo.create(
            {
                "name": "Password User",
                "email": "password@test.com",
                "password": validate_and_hash_password(old_password),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        new_password = "NewPassword123!"
        update_data = UpdateCurrentUserRequest(password=new_password)
        updated_user = await service.update_current_user(user.id, update_data)

        assert updated_user.id == user.id
        assert verify_password(new_password, updated_user.password)
        assert not verify_password(old_password, updated_user.password)

        is_valid, _ = await service.verify_token_in_db(
            JWTManager.decode_token(tokens.access_token, verify=False).get("jti"),
            "access",
        )
        assert is_valid is False

    async def test_update_current_user_no_changes(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "No Change User",
                "email": "nochange@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        update_data = {}
        updated_user = await service.update_current_user(user.id, update_data)

        assert updated_user.id == user.id
        assert updated_user.name == "No Change User"

    async def test_update_current_user_ignores_email(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Email Test User",
                "email": "emailtest@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        update_data = {"email": "newemail@test.com", "name": "Updated Name"}
        updated_user = await service.update_current_user(user.id, update_data)

        assert updated_user.email == "emailtest@test.com"
        assert updated_user.name == "Updated Name"

    async def test_logout_invalid_token(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        result = await service.logout("invalid-token")

        assert "failed" in result.message.lower() or "logout" in result.message.lower()

    async def test_verify_token_without_token_type(self, test_session: AsyncSession):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Test User",
                "email": "notype@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        tokens = await service._create_token_pair(user)

        result = await service.verify_token(tokens.access_token)

        assert result.sub == str(user.id)
        assert result.email == user.email

    async def test_verify_token_without_jti_skips_db_check(
        self, test_session: AsyncSession
    ):
        service = AuthService(test_session, test_session)

        exp_time = int((utcnow() + timedelta(hours=1)).timestamp())
        iat_time = int(utcnow().timestamp())

        payload = {
            "sub": "test-user-id",
            "type": "access",
            "email": "test@test.com",
            "exp": exp_time,
            "iat": iat_time,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        token_without_jti = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception):
            await service.verify_token(token_without_jti, "access")

    async def test_create_token_pair_without_access_jti_or_exp(
        self, test_session: AsyncSession
    ):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Token Test User",
                "email": "token@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.name,
        )

        access_payload = JWTManager.decode_token(token_pair.access_token, verify=False)
        refresh_payload = JWTManager.decode_token(
            token_pair.refresh_token, verify=False
        )

        access_payload.pop("jti", None)
        access_payload.pop("exp", None)

        with patch.object(
            JWTManager,
            "decode_token",
            side_effect=[access_payload, refresh_payload],
        ):
            result = await service._create_token_pair(user)
            await test_session.commit()

            assert result.access_token is not None
            assert result.refresh_token is not None

    async def test_create_token_pair_without_refresh_jti_or_exp(
        self, test_session: AsyncSession
    ):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Token Test User 2",
                "email": "token2@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.name,
        )

        access_payload = JWTManager.decode_token(token_pair.access_token, verify=False)
        refresh_payload = JWTManager.decode_token(
            token_pair.refresh_token, verify=False
        )

        refresh_payload.pop("jti", None)
        refresh_payload.pop("exp", None)

        with patch.object(
            JWTManager,
            "decode_token",
            side_effect=[access_payload, refresh_payload],
        ):
            result = await service._create_token_pair(user)
            await test_session.commit()

            assert result.access_token is not None
            assert result.refresh_token is not None

    async def test_update_current_user_with_empty_dict(
        self, test_session: AsyncSession
    ):
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Empty Update User",
                "email": "empty@test.com",
                "password": validate_and_hash_password("TestPassword123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)

        updated_user = await service.update_current_user(user.id, {})

        assert updated_user.id == user.id
        assert updated_user.name == "Empty Update User"

    async def test_logout_with_missing_user_id(self, test_session: AsyncSession):
        service = AuthService(test_session, test_session)

        exp_time = int((utcnow() + timedelta(hours=1)).timestamp())
        payload = {
            "type": "access",
            "exp": exp_time,
            "iat": int(utcnow().timestamp()),
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        token_without_sub = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        result = await service.logout(token_without_sub)

        assert "failed" in result.message.lower() or "logout" in result.message.lower()
