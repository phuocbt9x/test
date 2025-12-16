"""
Unit tests for User Service.

Tests cover:
- User creation with validation
- Email/username uniqueness checks
- Password hashing
- User retrieval
- User updates
- Password changes
- Account lockout logic
"""

import pytest
from uuid import uuid4
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.service import UserService
from src.modules.user.models import User
from src.modules.user.schemas import (
    UserCreateRequest,
    UserUpdateRequest,
    UserPasswordChangeRequest,
)
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    BadRequestException,
)
from src.core.security.password import PasswordHasher
from src.core.utils.timezone import utcnow


@pytest.mark.units
class TestUserServiceCreate:
    """Test user creation."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session: AsyncSession):
        """Test successful user creation."""
        service = UserService(db_session)

        data = UserCreateRequest(
            email="newuser@example.com",
            username="newuser",
            password="NewUser@123",
            full_name="New User",
            phone="+1234567890",
        )

        user = await service.create_user(data)

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_superuser is False
        # Password should be hashed
        assert user.password_hash != data.password
        assert PasswordHasher.verify(data.password, user.password_hash)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating user with duplicate email."""
        service = UserService(db_session)

        data = UserCreateRequest(
            email=test_user.email,  # Duplicate
            username="differentusername",
            password="Password@123",
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.create_user(data)

        assert "email" in exc_info.value.message.lower()
        assert "already" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating user with duplicate username."""
        service = UserService(db_session)

        data = UserCreateRequest(
            email="different@example.com",
            username=test_user.username,  # Duplicate
            password="Password@123",
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.create_user(data)

        assert "username" in exc_info.value.message.lower()
        assert "already" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_user_email_lowercase(self, db_session: AsyncSession):
        """Test that email is stored in lowercase."""
        service = UserService(db_session)

        data = UserCreateRequest(
            email="MixedCase@Example.Com",
            username="mixeduser",
            password="Password@123",
        )

        user = await service.create_user(data)

        assert user.email == "mixedcase@example.com"

    @pytest.mark.asyncio
    async def test_create_user_username_lowercase(self, db_session: AsyncSession):
        """Test that username is stored in lowercase."""
        service = UserService(db_session)

        data = UserCreateRequest(
            email="username@example.com",
            username="MixedCaseUser",
            password="Password@123",
        )

        user = await service.create_user(data)

        assert user.username == "mixedcaseuser"


@pytest.mark.units
class TestUserServiceRetrieval:
    """Test user retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test getting user by ID."""
        service = UserService(db_session)

        user = await service.get_user_by_id(test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session: AsyncSession):
        """Test getting non-existent user."""
        service = UserService(db_session)

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_user_by_id(uuid4())

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test getting user by email."""
        service = UserService(db_session)

        user = await service.get_user_by_email(test_user.email)

        assert user is not None
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Test getting user by non-existent email."""
        service = UserService(db_session)

        with pytest.raises(NotFoundException):
            await service.get_user_by_email("nonexistent@example.com")

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test getting user by username."""
        service = UserService(db_session)

        user = await service.get_user_by_username(test_user.username)

        assert user is not None
        assert user.username == test_user.username

    @pytest.mark.asyncio
    async def test_get_user_by_email_or_username_email(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test getting user by email or username (using email)."""
        service = UserService(db_session)

        user = await service.get_user_by_email_or_username(test_user.email)

        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_email_or_username_username(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test getting user by email or username (using username)."""
        service = UserService(db_session)

        user = await service.get_user_by_email_or_username(test_user.username)

        assert user is not None
        assert user.id == test_user.id


@pytest.mark.units
class TestUserServiceUpdate:
    """Test user update operations."""

    @pytest.mark.asyncio
    async def test_update_user_success(self, db_session: AsyncSession, test_user: User):
        """Test updating user."""
        service = UserService(db_session)

        data = UserUpdateRequest(full_name="Updated Name", phone="+9876543210")

        user = await service.update_user(test_user.id, data)

        assert user.full_name == "Updated Name"
        assert user.phone == "+9876543210"
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, db_session: AsyncSession):
        """Test updating non-existent user."""
        service = UserService(db_session)

        data = UserUpdateRequest(full_name="New Name")

        with pytest.raises(NotFoundException):
            await service.update_user(uuid4(), data)

    @pytest.mark.asyncio
    async def test_update_user_partial(self, db_session: AsyncSession, test_user: User):
        """Test partial user update."""
        service = UserService(db_session)

        original_email = test_user.email

        data = UserUpdateRequest(full_name="Only Name Changed")

        user = await service.update_user(test_user.id, data)

        assert user.full_name == "Only Name Changed"
        assert user.email == original_email  # Unchanged


@pytest.mark.units
class TestUserServicePasswordChange:
    """Test password change operations."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test successful password change."""
        service = UserService(db_session)

        data = UserPasswordChangeRequest(
            old_password="Test@1234",  # From conftest
            new_password="NewPassword@123",
        )

        user = await service.change_password(test_user.id, data)

        assert user is not None
        # Verify new password works
        assert PasswordHasher.verify(data.new_password, user.password_hash)
        # Verify old password no longer works
        assert not PasswordHasher.verify(data.old_password, user.password_hash)

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test password change with wrong old password."""
        service = UserService(db_session)

        data = UserPasswordChangeRequest(
            old_password="WrongPassword@123", new_password="NewPassword@123"
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await service.change_password(test_user.id, data)

        assert (
            "incorrect" in exc_info.value.message.lower()
            or "invalid" in exc_info.value.message.lower()
        )

    @pytest.mark.asyncio
    async def test_change_password_same_as_old(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test changing password to same password."""
        service = UserService(db_session)

        data = UserPasswordChangeRequest(
            old_password="Test@1234",
            new_password="Test@1234",  # Same as old
        )

        with pytest.raises(BadRequestException) as exc_info:
            await service.change_password(test_user.id, data)

        assert "same" in exc_info.value.message.lower()


@pytest.mark.units
class TestUserServiceAccountLockout:
    """Test account lockout logic."""

    @pytest.mark.asyncio
    async def test_increment_failed_login_attempts(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test incrementing failed login attempts."""
        service = UserService(db_session)

        original_attempts = test_user.failed_login_attempts

        await service.increment_failed_login_attempts(test_user.id)

        # Refresh user
        updated_user = await service.get_user_by_id(test_user.id)

        assert updated_user.failed_login_attempts == original_attempts + 1

    @pytest.mark.asyncio
    async def test_reset_failed_login_attempts(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test resetting failed login attempts."""
        service = UserService(db_session)

        # First increment some attempts
        await service.increment_failed_login_attempts(test_user.id)
        await service.increment_failed_login_attempts(test_user.id)

        # Then reset
        await service.reset_failed_login_attempts(test_user.id)

        updated_user = await service.get_user_by_id(test_user.id)

        assert updated_user.failed_login_attempts == 0
        assert updated_user.locked_until is None

    @pytest.mark.asyncio
    async def test_lock_account(self, db_session: AsyncSession, test_user: User):
        """Test locking user account."""
        service = UserService(db_session)

        lockout_duration = 15  # minutes

        await service.lock_account(test_user.id, duration_minutes=lockout_duration)

        updated_user = await service.get_user_by_id(test_user.id)

        assert updated_user.locked_until is not None
        assert updated_user.locked_until > utcnow()

    @pytest.mark.asyncio
    async def test_is_account_locked_true(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test checking if account is locked (when it is)."""
        service = UserService(db_session)

        # Lock the account
        await service.lock_account(test_user.id, duration_minutes=15)

        is_locked = await service.is_account_locked(test_user.id)

        assert is_locked is True

    @pytest.mark.asyncio
    async def test_is_account_locked_false(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test checking if account is locked (when it's not)."""
        service = UserService(db_session)

        is_locked = await service.is_account_locked(test_user.id)

        assert is_locked is False

    @pytest.mark.asyncio
    async def test_is_account_locked_expired(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test account lock expiration."""
        service = UserService(db_session)

        # Manually set locked_until to past
        test_user.locked_until = utcnow() - timedelta(minutes=10)
        db_session.add(test_user)
        await db_session.commit()

        is_locked = await service.is_account_locked(test_user.id)

        assert is_locked is False


@pytest.mark.units
class TestUserServicePagination:
    """Test user listing with pagination."""

    @pytest.mark.asyncio
    async def test_get_active_users(
        self, db_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test getting active users."""
        service = UserService(db_session)

        result = await service.get_active_users(page=1, per_page=10)

        assert "data" in result
        assert "total" in result
        assert len(result["data"]) >= 2
        assert all(u.is_active for u in result["data"])

    @pytest.mark.asyncio
    async def test_get_active_users_pagination(self, db_session: AsyncSession):
        """Test active users pagination."""
        service = UserService(db_session)

        # Create multiple active users
        for i in range(5):
            await service.repository.create(
                {
                    "id": uuid4(),
                    "email": f"active{i}@example.com",
                    "username": f"active{i}",
                    "password_hash": "hash",
                    "is_active": True,
                }
            )
        await db_session.commit()

        result = await service.get_active_users(page=1, per_page=3)

        assert len(result["data"]) <= 3
        assert result["page"] == 1
        assert result["per_page"] == 3


@pytest.mark.units
class TestUserServiceVerification:
    """Test user verification operations."""

    @pytest.mark.asyncio
    async def test_verify_user(self, db_session: AsyncSession, test_user: User):
        """Test verifying a user."""
        service = UserService(db_session)

        # Ensure user is initially unverified
        test_user.is_verified = False
        db_session.add(test_user)
        await db_session.commit()

        await service.verify_user(test_user.id)

        updated_user = await service.get_user_by_id(test_user.id)

        assert updated_user.is_verified is True

    @pytest.mark.asyncio
    async def test_deactivate_user(self, db_session: AsyncSession, test_user: User):
        """Test deactivating a user."""
        service = UserService(db_session)

        # Ensure user is active
        test_user.is_active = True
        db_session.add(test_user)
        await db_session.commit()

        await service.deactivate_user(test_user.id)

        updated_user = await service.get_user_by_id(test_user.id)

        assert updated_user.is_active is False

    @pytest.mark.asyncio
    async def test_activate_user(self, db_session: AsyncSession, inactive_user: User):
        """Test activating an inactive user."""
        service = UserService(db_session)

        await service.activate_user(inactive_user.id)

        updated_user = await service.get_user_by_id(inactive_user.id)

        assert updated_user.is_active is True
