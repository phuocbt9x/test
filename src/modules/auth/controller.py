"""
Auth Router

REST API endpoints for authentication.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status

from src.core.controllers import BaseController, SuccessResponse
from src.core.security.dependencies import CurrentUser, get_current_active_user, get_token_from_header
from src.modules.user.schemas import UserResponse

from .dependencies import get_auth_service, get_client_ip, get_device_info
from .schemas import (
    ActiveSessionResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from .service import AuthService
from uuid import UUID

router = APIRouter(prefix="/auth", tags=["Authentication"])
controller = BaseController()


@router.post(
    "/register",
    response_model=SuccessResponse[LoginResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account and receive authentication tokens",
)
async def register(
    data: RegisterRequest,
    device_info: Annotated[Optional[str], Depends(get_device_info)],
    ip_address: Annotated[Optional[str], Depends(get_client_ip)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[LoginResponse]:
    """
    Register a new user.

    Returns authentication tokens immediately after registration.
    """
    user, tokens = await service.register(
        data=data,
        device_info=device_info,
        ip_address=ip_address,
    )

    login_data = LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
        }
    )

    return controller.created(data=login_data, message="User registered successfully")


@router.post(
    "/login",
    response_model=SuccessResponse[LoginResponse],
    summary="User login",
    description="Authenticate user and receive JWT tokens",
)
async def login(
    data: LoginRequest,
    device_info: Annotated[Optional[str], Depends(get_device_info)],
    ip_address: Annotated[Optional[str], Depends(get_client_ip)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[LoginResponse]:
    """
    Login with email/username and password.

    Returns access token and refresh token.
    """
    user, tokens = await service.login(
        data=data,
        device_info=device_info,
        ip_address=ip_address,
    )

    login_data = LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
    )

    return controller.success(data=login_data, message="Login successful")


@router.post(
    "/logout",
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout user by blacklisting current tokens",
)
async def logout(
    service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str, Depends(get_token_from_header)],
    _: Annotated[CurrentUser, Depends(get_current_active_user)],
    refresh_token: Optional[str] = None,
) -> SuccessResponse[None]:
    """
    Logout current user.

    Blacklists the access token and optionally revokes the refresh token.
    """
    await service.logout(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    return controller.success(message="Logged out successfully")


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    device_info: Annotated[Optional[str], Depends(get_device_info)],
    ip_address: Annotated[Optional[str], Depends(get_client_ip)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[TokenResponse]:
    """
    Refresh access token.

    Implements token rotation: old refresh token is revoked,
    new tokens are issued.
    """
    tokens = await service.refresh_access_token(
        refresh_token=data.refresh_token,
        device_info=device_info,
        ip_address=ip_address,
    )

    return controller.success(data=tokens, message="Token refreshed successfully")


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get current user",
    description="Get the currently authenticated user's information",
)
async def get_current_user(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[UserResponse]:
    """
    Get current authenticated user.
    
    Fetches full user data from database for complete profile information.
    """
    
    # Fetch full user data from database using service's repository
    user = await service.user_repo.get(UUID(current_user.user_id))
    
    if not user:
        from src.core.exceptions import NotFoundException
        raise NotFoundException(resource="User", resource_id=current_user.user_id)
    
    user_data = UserResponse.model_validate(user)
    return controller.success(data=user_data, message="User retrieved successfully")


@router.get(
    "/sessions",
    response_model=SuccessResponse[list[ActiveSessionResponse]],
    summary="Get active sessions",
    description="Get all active sessions (devices) for current user",
)
async def get_active_sessions(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[list[ActiveSessionResponse]]:
    """
    Get all active sessions for current user.

    Shows all devices/browsers where user is logged in.
    """
    
    sessions = await service.get_active_sessions(UUID(current_user.user_id))

    sessions_data = [
        ActiveSessionResponse(
            id=UUID(str(session.id)),
            device_info=session.device_info,
            ip_address=session.ip_address,
            created_at=session.created_at,
            last_used_at=session.used_at,
        )
        for session in sessions
    ]

    return controller.success(data=sessions_data, message="Active sessions retrieved successfully")


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke session",
    description="Revoke a specific session (logout from specific device)",
)
async def revoke_session(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """
    Revoke a specific session.

    Allows user to logout from a specific device.
    """

    await service.revoke_session(
        user_id=UUID(current_user.user_id),
        session_id=UUID(session_id),
    )


@router.post(
    "/revoke-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all sessions",
    description="Logout from all devices",
)
async def revoke_all_sessions(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """
    Revoke all user sessions.

    Useful when user suspects unauthorized access.
    """
    
    await service.revoke_all_user_tokens(
        user_id=UUID(current_user.user_id),
        reason="user_revoke_all"
    )
