from faker import Faker
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from fastapi import status

from src.core import (
    CurrentUser,
    JWTManager,
    TokenPayload,
    validate_and_hash_password,
)
from src.modules.auth.controller import (
    login,
    logout,
    me,
    refresh_token,
    update_current_user_profile,
)
from src.modules.auth.schemas.request import (
    LoginRequest,
    RefreshTokenRequest,
    UpdateCurrentUserRequest,
)
from src.modules.auth.service import AuthService
from src.modules.user import UserRepository


@pytest.mark.units
class TestAuthController:
    async def test_register_controller(
        self,
        test_client: AsyncClient,
        override_auth,
        fake: Faker,
        create_test_image,
    ):
        files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "line_user_id": fake.lexify(text="U?????????????????????"),
            },
            files=files,
        )

        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["data"]["name"]
        assert result["data"]["email"]

    async def test_login_controller(self, test_session: AsyncSession, mock_request):
        email = f"logincontroller{uuid4().hex[:8]}@test.com"
        user_repo = UserRepository(test_session, test_session)
        await user_repo.create(
            {
                "name": "Login Controller",
                "email": email,
                "password": validate_and_hash_password("SecurePass123!"),
            }
        )
        await test_session.commit()

        request = LoginRequest(email=email, password="SecurePass123!")

        result = await login(
            request=mock_request,
            payload=request,
            read_session=test_session,
            write_session=test_session,
        )

        assert result.success is True
        assert result.data is not None
        assert result.data.access_token is not None

    async def test_logout_controller(self, test_session: AsyncSession):
        email = f"logoutcontroller{uuid4().hex[:8]}@test.com"
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Logout Controller",
                "email": email,
                "password": validate_and_hash_password("SecurePass123!"),
            }
        )
        await test_session.commit()

        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.name,
        )

        result = await logout(
            access_token=token_pair.access_token,
            read_session=test_session,
            write_session=test_session,
        )

        assert result.success is True
        assert result.data is not None

    async def test_refresh_token_controller(self, test_session: AsyncSession):
        email = f"refreshcontroller{uuid4().hex[:8]}@test.com"
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Refresh Controller",
                "email": email,
                "password": validate_and_hash_password("SecurePass123!"),
            }
        )
        await test_session.commit()

        service = AuthService(test_session, test_session)
        tokens = await service._create_token_pair(user)
        await test_session.commit()

        request = RefreshTokenRequest(refresh_token=tokens.refresh_token)

        result = await refresh_token(
            request, read_session=test_session, write_session=test_session
        )

        assert result.success is True
        assert result.data is not None
        assert result.data.access_token is not None

    async def test_me_controller(self, test_session: AsyncSession):
        email = f"mecontroller{uuid4().hex[:8]}@test.com"
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Me Controller",
                "email": email,
                "password": validate_and_hash_password("SecurePass123!"),
            }
        )
        await test_session.commit()

        token_payload = TokenPayload(
            sub=str(user.id),
            exp=9999999999,
            iat=1000000000,
            jti="test-jti",
            type="access",
            email=user.email,
            username=user.name,
            roles=["user"],
        )
        current_user = CurrentUser(token_payload)

        result = await me(
            current_user=current_user,
            read_session=test_session,
            write_session=test_session,
        )

        assert result.success is True
        assert result.data is not None
        assert result.data.email == user.email

    async def test_update_current_user_profile_controller(
        self, test_session: AsyncSession
    ):
        email = f"updatecontroller{uuid4().hex[:8]}@test.com"
        user_repo = UserRepository(test_session, test_session)
        user = await user_repo.create(
            {
                "name": "Update Controller",
                "email": email,
                "password": validate_and_hash_password("SecurePass123!"),
            }
        )
        await test_session.commit()

        token_payload = TokenPayload(
            sub=str(user.id),
            exp=9999999999,
            iat=1000000000,
            jti="test-jti",
            type="access",
            email=user.email,
            username=user.name,
            roles=["user"],
        )
        current_user = CurrentUser(token_payload)

        request = UpdateCurrentUserRequest(name="Updated Controller Name")

        result = await update_current_user_profile(
            request=request,
            current_user=current_user,
            read_session=test_session,
            write_session=test_session,
        )

        assert result.success is True
        assert result.data is not None
        assert result.data.name == "Updated Controller Name"
