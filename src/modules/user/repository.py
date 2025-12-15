"""
User Repository

Data access layer for user operations following Repository Pattern.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select

from src.core.databases.base_repository import BaseRepository
from .models import User


class UserRepository(BaseRepository[User]):
    """User Repository with custom queries"""

    model = User

    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return await self.query().where(email=email.lower()).first()

    async def find_by_username(self, username: str) -> Optional[User]:
        """
        Find user by username.

        Args:
            username: Username

        Returns:
            User if found, None otherwise
        """
        return await self.query().where(username=username.lower()).first()

    async def find_by_email_or_username(
        self,
        identifier: str
    ) -> Optional[User]:
        """
        Find user by email or username.

        Useful for login where user can use either email or username.

        Args:
            identifier: Email or username

        Returns:
            User if found, None otherwise
        """
        query = select(User).where(
            or_(
                User.email == identifier.lower(),
                User.username == identifier.lower()
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def exists_by_email(self, email: str, exclude_id: Optional[UUID] = None) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check
            exclude_id: User ID to exclude from check (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query = select(User).where(User.email == email.lower())
        if exclude_id:
            query = query.where(User.id != exclude_id)

        result = await self.session.execute(query)
        return result.scalars().first() is not None

    async def exists_by_username(
        self,
        username: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if username already exists.

        Args:
            username: Username to check
            exclude_id: User ID to exclude from check (for updates)

        Returns:
            True if username exists, False otherwise
        """
        query = select(User).where(User.username == username.lower())
        if exclude_id:
            query = query.where(User.id != exclude_id)

        result = await self.session.execute(query)
        return result.scalars().first() is not None

    async def get_active_users(
        self,
        page: int = 1,
        per_page: int = 20
    ) -> dict:
        """
        Get paginated list of active users.

        Args:
            page: Page number
            per_page: Items per page

        Returns:
            Paginated user list
        """
        return await (
            self.query()
            .where(is_active=True)
            .order_by('created_at', desc=True)
            .paginate(page=page, per_page=per_page)
        )
