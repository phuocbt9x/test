"""
User Service

Business logic layer for user operations following Service Pattern.
Implements SOLID principles and handles all user-related business rules.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from src.core.security.password import PasswordHasher
from src.core.utils.timezone import utcnow

from .models import User
from .repository import UserRepository
from .schemas import UserCreateRequest, UserPasswordChangeRequest, UserUpdateRequest


class UserService:
    """
    User Service

    Handles business logic for user operations:
    - User creation with validation
    - User updates
    - Password management
    - Account lockout logic

    Design Patterns:
    - Service Layer Pattern
    - Dependency Injection
    - Single Responsibility Principle
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)
        self.password_hasher = PasswordHasher()

    async def create_user(self, data: UserCreateRequest) -> User:
        """
        Create a new user.

        Business Rules:
        - Email must be unique
        - Username must be unique
        - Password is hashed before storage
        - New users are active but unverified by default

        Args:
            data: User creation data

        Returns:
            Created user

        Raises:
            ConflictException: If email or username already exists
        """
        # Check email uniqueness
        if await self.repository.exists_by_email(data.email):
            raise ConflictException(
                message=f"Email '{data.email}' is already registered"
            )

        # Check username uniqueness
        if await self.repository.exists_by_username(data.username):
            raise ConflictException(
                message=f"Username '{data.username}' is already taken"
            )

        # Hash password
        password_hash = self.password_hasher.hash(data.password)

        # Create user
        user_data = {
            "email": data.email.lower(),
            "username": data.username.lower(),
            "password_hash": password_hash,
            "full_name": data.full_name,
            "phone": data.phone,
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "failed_login_attempts": 0,
        }

        user = await self.repository.create(user_data)
        await self.session.commit()

        return user

    async def get_user_by_id(self, user_id: UUID) -> User:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User

        Raises:
            NotFoundException: If user not found
        """
        user = await self.repository.get(user_id)
        if not user:
            raise NotFoundException(resource="User", resource_id=str(user_id))
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (returns None if not found)"""
        return await self.repository.find_by_email(email)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (returns None if not found)"""
        return await self.repository.find_by_username(username)

    async def update_user(self, user_id: UUID, data: UserUpdateRequest) -> User:
        """
        Update user profile.

        Business Rules:
        - Only allowed fields can be updated
        - Email and username changes require separate validation (not in this method)

        Args:
            user_id: User UUID
            data: Update data

        Returns:
            Updated user

        Raises:
            NotFoundException: If user not found
            BadRequestException: If validation fails
        """
        user = await self.get_user_by_id(user_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate update data if needed
        # For example, phone number format validation
        if "phone" in update_data and update_data["phone"]:
            # Basic phone validation (can be extended)
            phone = update_data["phone"].strip()
            if phone and (len(phone) < 10 or len(phone) > 20):
                raise BadRequestException(
                    message="Phone number must be between 10 and 20 characters"
                )
            update_data["phone"] = phone

        if update_data:
            updated_user = await self.repository.update(user_id, update_data)
            await self.session.commit()
            return updated_user or user

        return user

    async def change_password(
        self, user_id: UUID, data: UserPasswordChangeRequest
    ) -> User:
        """
        Change user password.

        Business Rules:
        - Current password must be correct
        - New password must be different from current
        - All user tokens should be revoked after password change

        Args:
            user_id: User UUID
            data: Password change data

        Returns:
            Updated user

        Raises:
            NotFoundException: If user not found
            UnauthorizedException: If current password is incorrect
            BadRequestException: If new password is same as current
        """
        user = await self.get_user_by_id(user_id)

        # Verify current password
        if not self.password_hasher.verify(data.current_password, user.password_hash):
            raise UnauthorizedException(message="Current password is incorrect")

        # Check new password is different
        if data.current_password == data.new_password:
            raise BadRequestException(
                message="New password must be different from current password"
            )

        # Validate new password strength
        is_valid, error = self.password_hasher.validate_password_strength(
            data.new_password
        )
        if not is_valid:
            from src.core.exceptions import ValidationException

            raise ValidationException(
                message=error or "New password does not meet security requirements"
            )

        # Hash new password
        from src.core.security.password import validate_and_hash_password

        new_password_hash = validate_and_hash_password(data.new_password)

        # Update password
        await self.repository.update(
            user_id,
            {
                "password_hash": new_password_hash,
                "password_changed_at": utcnow(),
                "failed_login_attempts": 0,  # Reset failed attempts
                "locked_until": None,  # Unlock account on password change
            },
        )
        await self.session.commit()

        # Revoke all user tokens after password change (security best practice)
        # Note: This requires AuthService - consider event-based architecture for better decoupling
        try:
            from src.modules.auth.repository import RefreshTokenRepository

            refresh_token_repo = RefreshTokenRepository(self.session)
            await refresh_token_repo.revoke_all_user_tokens(user_id)
            await self.session.commit()
        except Exception:
            # Log but don't fail password change if token revocation fails
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to revoke tokens for user {user_id} after password change",
                exc_info=True,
            )

        return user

    async def deactivate_user(self, user_id: UUID) -> User:
        """Deactivate user account"""
        user = await self.get_user_by_id(user_id)
        await self.repository.update(user_id, {"is_active": False})
        await self.session.commit()
        return user

    async def activate_user(self, user_id: UUID) -> User:
        """Activate user account"""
        user = await self.get_user_by_id(user_id)
        await self.repository.update(
            user_id,
            {
                "is_active": True,
                "failed_login_attempts": 0,
                "locked_until": None,
            },
        )
        await self.session.commit()
        return user

    async def list_users(self, page: int = 1, per_page: int = 20) -> dict:
        """Get paginated list of users"""
        return await self.repository.get_active_users(page, per_page)

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user (soft delete recommended in production).

        Args:
            user_id: User UUID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If user not found
        """
        await self.get_user_by_id(user_id)
        success = await self.repository.delete(user_id)
        await self.session.commit()
        return success
