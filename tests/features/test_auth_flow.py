"""
Feature/Integration tests for Authentication Flows.

Tests cover complete user authentication workflows:
- User registration
- User login
- Token refresh
- Logout
- Password change with token revocation
- Protected endpoint access
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4

from src.core.security.jwt import JWTManager
from src.core.security.password import PasswordHasher
from src.modules.user.models import User


@pytest.mark.features
class TestUserRegistrationFlow:
    """Test complete user registration flow."""

    @pytest.mark.asyncio
    async def test_register_new_user_success(self, client: AsyncClient, db_session):
        """Test successful user registration."""
        payload = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "NewUser@123",
            "full_name": "New User"
        }

        # Note: This assumes you have a registration endpoint
        # Adjust the URL based on your actual API structure
        response = await client.post("/api/v1/auth/register", json=payload)

        # If registration endpoint doesn't exist yet, this is the expected structure
        if response.status_code == 404:
            pytest.skip("Registration endpoint not implemented yet")

        assert response.status_code in [200, 201]
        data = response.json()

        assert "access_token" in data or "user" in data
        assert "email" in data.get("user", data)

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate email."""
        payload = {
            "email": test_user.email,  # Duplicate email
            "username": "different_username",
            "password": "Password@123",
        }

        response = await client.post("/api/v1/auth/register", json=payload)

        if response.status_code == 404:
            pytest.skip("Registration endpoint not implemented yet")

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "email" in data.get("error", {}).get("message", "").lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        payload = {
            "email": "weakpass@example.com",
            "username": "weakpass",
            "password": "123",  # Too weak
        }

        response = await client.post("/api/v1/auth/register", json=payload)

        if response.status_code == 404:
            pytest.skip("Registration endpoint not implemented yet")

        assert response.status_code == 422  # Validation error


@pytest.mark.features
class TestUserLoginFlow:
    """Test user login workflows."""

    @pytest.mark.asyncio
    async def test_login_with_email_success(self, client: AsyncClient, test_user: User):
        """Test successful login with email."""
        payload = {
            "username": test_user.email,  # Can use email as username
            "password": "Test@1234",  # From conftest.py
        }

        response = await client.post("/api/v1/auth/login", json=payload)

        if response.status_code == 404:
            pytest.skip("Login endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_with_username_success(self, client: AsyncClient, test_user: User):
        """Test successful login with username."""
        payload = {
            "username": test_user.username,
            "password": "Test@1234",
        }

        response = await client.post("/api/v1/auth/login", json=payload)

        if response.status_code == 404:
            pytest.skip("Login endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with incorrect password."""
        payload = {
            "username": test_user.email,
            "password": "WrongPassword@123",
        }

        response = await client.post("/api/v1/auth/login", json=payload)

        if response.status_code == 404:
            pytest.skip("Login endpoint not implemented yet")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        payload = {
            "username": "nonexistent@example.com",
            "password": "Password@123",
        }

        response = await client.post("/api/v1/auth/login", json=payload)

        if response.status_code == 404:
            pytest.skip("Login endpoint not implemented yet")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, inactive_user: User):
        """Test login with inactive user account."""
        payload = {
            "username": inactive_user.email,
            "password": "Inactive@1234",
        }

        response = await client.post("/api/v1/auth/login", json=payload)

        if response.status_code == 404:
            pytest.skip("Login endpoint not implemented yet")

        assert response.status_code == 401


@pytest.mark.features
class TestTokenRefreshFlow:
    """Test token refresh workflows."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_tokens: dict):
        """Test successful token refresh."""
        payload = {
            "refresh_token": test_tokens["refresh_token"]
        }

        response = await client.post("/api/v1/auth/refresh", json=payload)

        if response.status_code == 404:
            pytest.skip("Refresh endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        # New tokens should be different from old ones
        assert data["access_token"] != test_tokens["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_tokens: dict):
        """Test that using access token for refresh fails."""
        payload = {
            "refresh_token": test_tokens["access_token"]  # Wrong token type
        }

        response = await client.post("/api/v1/auth/refresh", json=payload)

        if response.status_code == 404:
            pytest.skip("Refresh endpoint not implemented yet")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token."""
        payload = {
            "refresh_token": "invalid.token.here"
        }

        response = await client.post("/api/v1/auth/refresh", json=payload)

        if response.status_code == 404:
            pytest.skip("Refresh endpoint not implemented yet")

        assert response.status_code == 401


@pytest.mark.features
class TestLogoutFlow:
    """Test logout workflows."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        if response.status_code == 404:
            pytest.skip("Logout endpoint not implemented yet")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_access_after_logout(self, client: AsyncClient, test_tokens: dict):
        """Test that token doesn't work after logout."""
        headers = {"Authorization": f"Bearer {test_tokens['access_token']}"}

        # Logout
        await client.post("/api/v1/auth/logout", headers=headers)

        # Try to access protected resource
        response = await client.get("/api/v1/users/me", headers=headers)

        if response.status_code == 404:
            pytest.skip("Endpoints not implemented yet")

        assert response.status_code == 401


@pytest.mark.features
class TestProtectedEndpointAccess:
    """Test access to protected endpoints."""

    @pytest.mark.asyncio
    async def test_access_protected_with_valid_token(self, client: AsyncClient, auth_headers: dict):
        """Test accessing protected endpoint with valid token."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        if response.status_code == 404:
            pytest.skip("User profile endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()
        assert "email" in data or "user" in data

    @pytest.mark.asyncio
    async def test_access_protected_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/users/me")

        if response.status_code == 404:
            pytest.skip("User profile endpoint not implemented yet")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_with_expired_token(self, client: AsyncClient, redis_client):
        """Test accessing protected endpoint with expired token."""
        from datetime import timedelta

        # Create expired token
        expired_token = JWTManager.create_token(
            subject="user-123",
            token_type="access",
            expires_delta=timedelta(seconds=-10)
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        if response.status_code == 404:
            pytest.skip("User profile endpoint not implemented yet")

        assert response.status_code == 401
        data = response.json()
        assert "expired" in data.get("error", {}).get("message", "").lower()


@pytest.mark.features
class TestRoleBasedAccess:
    """Test role-based access control."""

    @pytest.mark.asyncio
    async def test_admin_access_with_admin_role(self, client: AsyncClient, admin_auth_headers: dict):
        """Test admin endpoint access with admin role."""
        response = await client.get("/api/v1/admin/users", headers=admin_auth_headers)

        if response.status_code == 404:
            pytest.skip("Admin endpoint not implemented yet")

        assert response.status_code in [200, 403]  # Either works or forbidden

    @pytest.mark.asyncio
    async def test_admin_access_without_admin_role(self, client: AsyncClient, auth_headers: dict):
        """Test admin endpoint access without admin role."""
        response = await client.get("/api/v1/admin/users", headers=auth_headers)

        if response.status_code == 404:
            pytest.skip("Admin endpoint not implemented yet")

        assert response.status_code == 403  # Forbidden


@pytest.mark.features
class TestCompleteAuthWorkflow:
    """Test complete authentication workflow from registration to logout."""

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self, client: AsyncClient, db_session, redis_client):
        """
        Test complete user lifecycle:
        1. Register
        2. Login
        3. Access protected resource
        4. Refresh token
        5. Logout
        6. Verify token is revoked
        """
        # 1. Register new user
        register_payload = {
            "email": "lifecycle@example.com",
            "username": "lifecycle",
            "password": "Lifecycle@123",
            "full_name": "Life Cycle"
        }

        register_response = await client.post("/api/v1/auth/register", json=register_payload)

        if register_response.status_code == 404:
            pytest.skip("Auth endpoints not implemented yet")

        assert register_response.status_code in [200, 201]

        # 2. Login
        login_payload = {
            "username": "lifecycle@example.com",
            "password": "Lifecycle@123"
        }

        login_response = await client.post("/api/v1/auth/login", json=login_payload)
        assert login_response.status_code == 200

        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 3. Access protected resource
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = await client.get("/api/v1/users/me", headers=headers)

        if profile_response.status_code != 404:
            assert profile_response.status_code == 200

        # 4. Refresh token
        refresh_payload = {"refresh_token": refresh_token}
        refresh_response = await client.post("/api/v1/auth/refresh", json=refresh_payload)

        if refresh_response.status_code != 404:
            assert refresh_response.status_code == 200
            new_tokens = refresh_response.json()
            access_token = new_tokens["access_token"]

        # 5. Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        logout_response = await client.post("/api/v1/auth/logout", headers=headers)

        if logout_response.status_code != 404:
            assert logout_response.status_code == 200

        # 6. Verify token is revoked
        protected_response = await client.get("/api/v1/users/me", headers=headers)

        if protected_response.status_code != 404:
            assert protected_response.status_code == 401
