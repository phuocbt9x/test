from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, computed_field
from src.core import storage_manager, __

EXAMPLE_DATETIME = "2024-01-01T00:00:00Z"


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None = None
    line_user_id: str | None = None
    avatar_path: str | None = None
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    def avatar_url(self) -> str | None:
        if self.avatar_path:
            return storage_manager.get_instance().get_url(self.avatar_path)
        return None

    @computed_field
    def type(self) -> str:
        return __("fields.user.admin") if self.is_admin else __("fields.user.user")

    @computed_field
    def status(self) -> str:
        return (
            __("fields.user.active") if self.is_active else __("fields.user.inactive")
        )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+819012345678",
                "line_user_id": "U1234567890abcdef",
                "avatar_path": "users/123e4567-e89b-12d3-a456-426614174000.jpg",
                "avatar_url": "https://example.com/avatar.jpg",
                "is_admin": False,
                "type": "User",
                "is_active": True,
                "status": "Active",
                "created_at": EXAMPLE_DATETIME,
                "updated_at": EXAMPLE_DATETIME,
            }
        },
    )


class UserDetailResponse(UserResponse):
    deleted_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+819012345678",
                "line_user_id": "U1234567890abcdef",
                "avatar_url": "https://example.com/avatar.jpg",
                "is_admin": False,
                "is_active": True,
                "created_at": EXAMPLE_DATETIME,
                "updated_at": EXAMPLE_DATETIME,
                "deleted_at": None,
            }
        },
    )
