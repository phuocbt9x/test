"""
User Dependencies

FastAPI dependencies for user module.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.database import get_db_session
from src.core.security.dependencies import get_current_active_user

from .models import User
from .service import UserService


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> UserService:
    """Dependency to get UserService instance"""
    return UserService(session)


async def get_current_user_or_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
    target_user_id: UUID,
) -> User:
    """
    Check if current user is the target user or an admin.

    Used for endpoints where users can manage their own data,
    or admins can manage any user's data.

    Args:
        current_user: Currently authenticated user
        target_user_id: Target user ID being accessed

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user is not authorized
    """
    from fastapi import HTTPException, status

    if current_user.id != target_user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )

    return current_user
