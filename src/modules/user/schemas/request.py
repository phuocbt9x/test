from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator, ValidationError
from fastapi import Form, File, UploadFile, Query
from typing import Annotated
from src.modules.shared import (
    validate_user_name,
    validate_user_email,
    validate_user_password,
    validate_user_avatar,
    validate_user_phone_regex,
    validate_user_line_id,
)


class UserListRequest(BaseModel):
    search: str | None = None
    type: int | None = None
    status: int | None = None
    sort_by: str = "id"
    sort_order: str = "desc"
    page: int = 1
    per_page: int = 20

    @classmethod
    def as_query(
        cls,
        search: str | None = Query(None),
        type: int | None = Query(None, description="1 for admin, 0 for regular user"),
        status: int | None = Query(None, description="1 for active, 0 for inactive"),
        sort_by: str = Query("id"),
        sort_order: str = Query("desc"),
        page: int = Query(1, ge=1, description="Page number must be >= 1"),
        per_page: int = Query(20, ge=1, description="Items per page"),
    ) -> "UserListRequest":
        return cls(
            search=search,
            type=type,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )


class UserCreateRequest(BaseModel):
    name: str
    email: str
    password: str | None = None
    avatar: UploadFile | None = None
    phone: str | None = None
    line_user_id: str | None = None
    is_admin: bool = False
    is_active: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_user_name(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return validate_user_email(v, trim=False)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if not v:
            return v
        return validate_user_password(v)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, v: UploadFile | None) -> UploadFile | None:
        return validate_user_avatar(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return validate_user_phone_regex(v)

    @field_validator("line_user_id")
    @classmethod
    def validate_line_user_id(cls, v: str | None) -> str | None:
        return validate_user_line_id(v)

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form()],
        email: Annotated[str, Form()],
        password: Annotated[str | None, Form()] = None,
        avatar: Annotated[UploadFile | None, File()] = None,
        phone: Annotated[str | None, Form()] = None,
        line_user_id: Annotated[str | None, Form()] = None,
        is_admin: Annotated[bool, Form()] = False,
        is_active: Annotated[bool, Form()] = False,
    ) -> "UserCreateRequest":
        try:
            return cls(
                name=name,
                email=email,
                password=password,
                avatar=avatar,
                phone=phone,
                line_user_id=line_user_id,
                is_admin=is_admin,
                is_active=is_active,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())

    @classmethod
    def openapi_extra(cls) -> dict:
        return {
            "requestBody": {
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "required": ["name", "email"],
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "example": "John Doe",
                                },
                                "email": {
                                    "type": "string",
                                    "example": "john@example.com",
                                },
                                "password": {
                                    "type": "string",
                                    "example": "StrongP@ss123!",
                                },
                                "avatar": {
                                    "type": "string",
                                    "format": "binary",
                                },
                                "phone": {
                                    "type": "string",
                                    "example": "+819012345678",
                                },
                                "line_user_id": {
                                    "type": "string",
                                    "example": "U1234567890abcdef1234567890abcdef",
                                },
                                "is_admin": {
                                    "type": "boolean",
                                    "example": False,
                                },
                                "is_active": {
                                    "type": "boolean",
                                    "example": True,
                                },
                            },
                        }
                    }
                }
            }
        }
