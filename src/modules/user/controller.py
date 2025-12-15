"""
User Router

REST API endpoints for user management.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.controllers import BaseController, SuccessResponse, PaginatedResponse
from src.core.security.dependencies import get_current_active_user, require_superuser

from .dependencies import get_user_service
from .models import User
from .schemas import (
    UserCreateRequest,
    UserDetailResponse,
    UserPasswordChangeRequest,
    UserResponse,
    UserUpdateRequest,
)
from .service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
controller = BaseController()


@router.post(
    "",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user account (admin only)",
)
async def create_user(
    data: UserCreateRequest,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
) -> SuccessResponse[UserResponse]:
    """
    Create a new user (Admin only).

    **Note**: Regular user registration should use `/auth/register` endpoint.
    This endpoint is for admin user creation with custom settings.
    """
    user = await service.create_user(data)
    user_data = UserResponse.model_validate(user)
    return controller.created(data=user_data, message="User created successfully")


@router.get(
    "/me",
    response_model=SuccessResponse[UserDetailResponse],
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user",
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SuccessResponse[UserDetailResponse]:
    """Get current user's own profile"""
    user_data = UserDetailResponse.model_validate(current_user)
    return controller.success(data=user_data, message="User profile retrieved successfully")


@router.patch(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Update current user profile",
    description="Update the profile of the currently authenticated user",
)
async def update_current_user_profile(
    data: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> SuccessResponse[UserResponse]:
    """Update current user's own profile"""
    user = await service.update_user(current_user.id, data)
    user_data = UserResponse.model_validate(user)
    return controller.updated(data=user_data, message="Profile updated successfully")


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change the password of the currently authenticated user",
)
async def change_password(
    data: UserPasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """Change current user's password"""
    await service.change_password(current_user.id, data)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List users",
    description="Get paginated list of users (admin only)",
)
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[UserResponse]:
    """List all users with pagination (Admin only)"""
    result = await service.list_users(page, per_page)
    users_data = [UserResponse.model_validate(user) for user in result["users"]]
    return controller.paginated(
        data=users_data,
        page=page,
        per_page=per_page,
        total=result["total"],
        message="Users retrieved successfully"
    )


@router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserDetailResponse],
    summary="Get user by ID",
    description="Get detailed user information by ID (admin only)",
)
async def get_user_by_id(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
) -> SuccessResponse[UserDetailResponse]:
    """Get user by ID (Admin only)"""
    user = await service.get_user_by_id(user_id)
    user_data = UserDetailResponse.model_validate(user)
    return controller.success(data=user_data, message="User retrieved successfully")


@router.patch(
    "/{user_id}",
    response_model=SuccessResponse[UserResponse],
    summary="Update user",
    description="Update user information (admin only)",
)
async def update_user(
    user_id: UUID,
    data: UserUpdateRequest,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
) -> SuccessResponse[UserResponse]:
    """Update user by ID (Admin only)"""
    user = await service.update_user(user_id, data)
    user_data = UserResponse.model_validate(user)
    return controller.updated(data=user_data, message="User updated successfully")


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete user account (admin only)",
)
async def delete_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
) -> None:
    """Delete user by ID (Admin only)"""
    await service.delete_user(user_id)


@router.post(
    "/{user_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate user",
    description="Deactivate user account (admin only)",
)
async def deactivate_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
) -> None:
    """Deactivate user (Admin only)"""
    await service.deactivate_user(user_id)


@router.post(
    "/{user_id}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Activate user",
    description="Activate user account (admin only)",
)
async def activate_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_superuser)],
) -> None:
    """Activate user (Admin only)"""
    await service.activate_user(user_id)
