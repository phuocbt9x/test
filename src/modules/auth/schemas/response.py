from pydantic import BaseModel, Field, computed_field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Annotated
from src.core import storage_manager
from src.utils import (
    get_example_authentication_token,
    get_example_uuid,
    get_example_name,
    get_example_email,
    get_example_phone,
    get_example_path,
    get_example_avatar_url,
    get_example_line_id,
    get_example_timestamp,
)


class TokenResponse(BaseModel):
    access_token: Annotated[str, Field(examples=[get_example_authentication_token()])]
    token_type: str = "bearer"
    refresh_token: Annotated[str, Field(examples=[get_example_authentication_token()])]
    expires_in: Annotated[int, Field(examples=[3600])]


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Annotated[UUID, Field(examples=[get_example_uuid()])]
    name: Annotated[str, Field(examples=[get_example_name()])]
    email: Annotated[str, Field(examples=[get_example_email()])]
    phone: Annotated[str | None, Field(examples=[get_example_phone()])]
    line_user_id: Annotated[str | None, Field(examples=[get_example_line_id()])]
    is_admin: Annotated[bool, Field(examples=[False])]
    is_active: Annotated[bool, Field(examples=[True])]
    avatar_path: Annotated[str | None, Field(examples=[get_example_path()])]
    created_at: Annotated[datetime, Field(examples=[get_example_timestamp()])]
    updated_at: Annotated[datetime, Field(examples=[get_example_timestamp()])]

    @computed_field(examples=[get_example_avatar_url()])
    def avatar_url(self) -> str | None:
        if self.avatar_path:
            return storage_manager.get_instance().get_url(self.avatar_path)
        return None


class RegisterResponse(TokenResponse):
    user_info: UserInfo


class LogoutResponse(BaseModel):
    message: Annotated[str, Field(examples=["Successfully logged out"])]
