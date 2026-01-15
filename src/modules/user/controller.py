from fastapi import APIRouter, Depends, status
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.core import (
    __,
    get_read_db,
    get_write_db,
    BaseController,
    SuccessResponse,
    CurrentUser,
    require_superuser,
    limiter,
    storage_manager,
)
from src.utils import create_common_responses
from .schemas import (
    UserCreateRequest,
    UserResponse,
)
from .service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
controller = BaseController()


@router.post(
    "",
    response_model=SuccessResponse[UserResponse],
    openapi_extra=UserCreateRequest.openapi_extra(),
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user account (admin only). Supports file upload for avatar.",
    responses=create_common_responses(
        include_rate_limit=True,
        include_validation=True,
        include_unauthorized=True,
        include_forbidden=True,
        include_internal_error=True,
    ),
)
@limiter.limit("15/minute")
async def create(
    request: Request,
    payload: UserCreateRequest = Depends(UserCreateRequest.as_form),
    _: CurrentUser = Depends(require_superuser),
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> SuccessResponse[UserResponse]:
    service = UserService(
        storage_provider=storage_manager.get_instance(),
        read_session=read_session,
        write_session=write_session,
    )
    user = await service.create(payload)
    return controller.created(
        data=UserResponse.model_validate(user),
        message=__("user.created"),
    )
