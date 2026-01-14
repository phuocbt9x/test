from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from starlette.requests import Request
from src.core import (
    BaseController,
    ErrorResponse,
    SuccessResponse,
    get_read_db,
    get_write_db,
    get_current_user,
    get_token_from_header,
    CurrentUser,
    __,
    limiter,
)
from src.utils import create_common_responses
from src.modules.auth.schemas import UpdateCurrentUserRequest

from .schemas import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    UserResponse,
    LogoutResponse,
    RegisterResponse,
    TokenResponse,
)
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
controller = BaseController()


@router.post(
    "/register",
    response_model=SuccessResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with username, email and password",
    response_description="Returns access token, refresh token and user information",
)
async def register(
    request: RegisterRequest,
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[RegisterResponse]:
    service = AuthService(read_session, write_session)
    result = await service.register(request)
    return controller.created(data=result, message=__("auth.register.success"))


@router.post(
    "/login",
    response_model=SuccessResponse[RegisterResponse],
    summary="User login",
    description="Authenticate user with username/email and password to receive access token",
    response_description="Returns access token, refresh token and user information",
    responses=create_common_responses(
        include_validation=True,
        include_rate_limit=True,
        include_internal_error=True,
        include_not_found=True,
        include_unauthorized=True,
    ),
)
@limiter.limit("1/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[RegisterResponse]:
    service = AuthService(read_session, write_session)
    result = await service.login(payload)
    return controller.success(data=result, message=__("auth.login.success"))


@router.post(
    "/logout",
    response_model=SuccessResponse[LogoutResponse],
    summary="User logout",
    description="Logout current user and revoke all tokens",
    response_description="Returns success message",
)
async def logout(
    access_token: str = Depends(get_token_from_header),
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[LogoutResponse] | ErrorResponse:
    service = AuthService(read_session, write_session)
    result = await service.logout(access_token)
    return controller.success(data=result, message=__("auth.logout.success"))


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Refresh access token",
    description="Generate new access token using refresh token",
    response_description="Returns new access token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[TokenResponse] | ErrorResponse:
    service = AuthService(read_session, write_session)
    result = await service.refresh_token(request.refresh_token)
    return controller.success(data=result, message=__("auth.refresh.success"))


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get current user",
    description="Get authenticated user information from access token",
    response_description="Returns current user profile",
)
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[UserResponse] | ErrorResponse:
    service = AuthService(read_session, write_session)
    result = await service.get_current_user(current_user.user_id)
    return controller.success(data=result, message=__("auth.me.success"))


@router.patch(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Update current user profile",
    description="Update the profile of the currently authenticated user",
    response_description="Returns updated user profile",
)
async def update_current_user_profile(
    request: UpdateCurrentUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[UserResponse] | ErrorResponse:
    service = AuthService(read_session, write_session)
    result = await service.update_current_user(UUID(current_user.user_id), request)
    return controller.success(
        data=UserResponse.model_validate(result),
        message=__("auth.update_me.success"),
    )
