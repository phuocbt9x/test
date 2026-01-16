import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.features
class TestAuthEndpoints:
    async def test_register_success(self, test_client: AsyncClient):
        response = await test_client.post(
            "/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert "user_info" in data["data"]
        assert data["data"]["user_info"]["email"] == "test@example.com"

    async def test_register_validation_errors(self, test_client: AsyncClient):
        response = await test_client.post(
            "/auth/register",
            json={
                "name": "",
                "email": "invalid-email",
                "password": "123",
                "confirm_password": "456",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "errors" in data
        assert "message" in data

    async def test_register_duplicate_email(self, test_client: AsyncClient):
        await test_client.post(
            "/auth/register",
            json={
                "name": "First User",
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        response = await test_client.post(
            "/auth/register",
            json={
                "name": "Second User",
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "errors" in data

    async def test_login_success(self, test_client: AsyncClient):
        await test_client.post(
            "/auth/register",
            json={
                "name": "Login User",
                "email": "login@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        response = await test_client.post(
            "/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    async def test_login_invalid_credentials(self, test_client: AsyncClient):
        response = await test_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == status.HTTP_404_NOT_FOUND
        assert "message" in data

    async def test_login_validation_errors(self, test_client: AsyncClient):
        response = await test_client.post(
            "/auth/login",
            json={
                "email": "invalid-email",
                "password": "123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert data["success"] is False
        assert "errors" in data

    async def test_get_me_requires_authentication(self, test_client: AsyncClient):
        response = await test_client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == status.HTTP_401_UNAUTHORIZED

    async def test_get_me_success(self, test_client: AsyncClient):
        register_response = await test_client.post(
            "/auth/register",
            json={
                "name": "Me User",
                "email": "me@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        token_data = register_response.json()["data"]
        access_token = token_data["access_token"]

        response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "me@example.com"

    async def test_logout_success(self, test_client: AsyncClient):
        register_response = await test_client.post(
            "/auth/register",
            json={
                "name": "Logout User",
                "email": "logout@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        token_data = register_response.json()["data"]
        access_token = token_data["access_token"]

        response = await test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    async def test_refresh_token_success(self, test_client: AsyncClient):
        register_response = await test_client.post(
            "/auth/register",
            json={
                "name": "Refresh User",
                "email": "refresh@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        token_data = register_response.json()["data"]
        refresh_token = token_data["refresh_token"]

        response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    async def test_update_profile_success(self, test_client: AsyncClient):
        register_response = await test_client.post(
            "/auth/register",
            json={
                "name": "Original Name",
                "email": "profile@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        token_data = register_response.json()["data"]
        access_token = token_data["access_token"]

        response = await test_client.patch(
            "/auth/me",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Name"

    async def test_register_with_optional_fields(self, test_client: AsyncClient):
        response = await test_client.post(
            "/auth/register",
            json={
                "name": "Optional User",
                "email": "optional@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "phone": "0312345678",
                "line_user_id": "line123",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_info"]["phone"] == "0312345678"
        assert data["data"]["user_info"]["line_user_id"] == "line123"
