"""
User Repository

Data access layer for user operations following Repository Pattern.
Uses BaseRepository methods for consistency and code reuse.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select

from src.core.orm.base_repository import BaseRepository
from .models import User


class UserRepository(BaseRepository[User]):
    """User Repository with custom queries"""

    model = User

    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address.

        Performance: Uses indexed query on email column.
        Uses BaseRepository query builder for consistency.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return await self.query().where(email=email.lower()).first()

    async def find_by_email_or_name(self, identifier: str) -> Optional[User]:
        """
        Find user by email or name.

        Useful for login where user can use either email or name.

        Args:
            identifier: Email or name

        Returns:
            User if found, None otherwise
        """
        query = select(User).where(
            or_(User.email == identifier.lower(), User.name == identifier.lower())
        )
        result = await self.read_session.execute(query)
        return result.scalars().first()

    async def exists_by_email(
        self, email: str, exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if email already exists.

        Performance: Uses BaseRepository exists() method for optimal performance.

        Args:
            email: Email to check
            exclude_id: User ID to exclude from check (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query_builder = self.query().where(email=email.lower())
        if exclude_id:
            # Need to manually add exclude condition since BaseRepository.where doesn't support !=
            from sqlalchemy import select

            query = select(User).where(
                User.email == email.lower(), User.id != exclude_id
            )
            result = await self.read_session.execute(query)
            return result.scalars().first() is not None
        return await query_builder.exists()

    async def get_active_users(self, page: int = 1, per_page: int = 20) -> dict:
        """
        Get paginated list of active users.

        Performance: Uses BaseRepository paginate() method with indexed query.
        Uses BaseRepository query builder for consistency.

        Args:
            page: Page number
            per_page: Items per page

        Returns:
            Paginated user list with metadata (includes 'users' key for compatibility)
        """
        # Use BaseRepository paginate method
        result = await (
            self.query()
            .where(is_active=True)
            .order_by("created_at", order="desc")
            .paginate(page=page, per_page=per_page)
        )

        # Add 'users' key for compatibility with service layer expectations
        result["users"] = result["data"]
        return result
