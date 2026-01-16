from fastapi import APIRouter, Depends, status, BackgroundTasks
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
    PaginatedResponse,
)
from src.utils import create_common_responses
from .schemas import (
    UserListRequest,
    UserCreateRequest,
    UserResponse,
)
from .service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
controller = BaseController()


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Retrieve a list of users (admin only). Supports filtering, sorting, and pagination.",
    responses=create_common_responses(
        include_unauthorized=True,
        include_forbidden=True,
        include_internal_error=True,
    ),
)
async def index(
    payload: UserListRequest = Depends(UserListRequest.as_query),
    _: CurrentUser = Depends(require_superuser),
    read_session: AsyncSession = Depends(get_read_db),
    write_session: AsyncSession = Depends(get_write_db),
) -> PaginatedResponse[UserResponse]:
    service = UserService(
        storage_provider=storage_manager.get_instance(),
        read_session=read_session,
        write_session=write_session,
    )
    data = await service.list(payload)

    return controller.paginated(
        data=data.get("data", []),
        message=__("messages.data_retrieved"),
        total=data.get("total", 0),
        page=data.get("page", 1),
        per_page=data.get("per_page", 10),
    )


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
    background_tasks: BackgroundTasks,
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
    user = await service.create(payload, background_tasks)
    return controller.created(
        data=UserResponse.model_validate(user),
        message=__("messages.Created successfully"),
    )
