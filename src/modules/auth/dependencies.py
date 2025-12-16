"""
Auth Dependencies

FastAPI dependencies for auth module.
"""
from typing import Annotated, Optional

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.database import get_db_session
from src.modules.user.service import UserService

from .service import AuthService


async def get_user_service_for_auth(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> UserService:
    """Helper dependency to get UserService for AuthService"""
    return UserService(session)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service_for_auth)],
) -> AuthService:
    """
    Dependency to get AuthService instance.
    
    Injects UserService following Dependency Inversion Principle (DIP).
    """
    return AuthService(session, user_service=user_service)


def get_device_info(user_agent: Optional[str] = Header(None)) -> Optional[str]:
    """Extract device info from User-Agent header"""
    return user_agent


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request"""
    # Check X-Forwarded-For header (if behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP in the list
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return None
