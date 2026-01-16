from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator, ValidationError
from fastapi import Form, File, UploadFile
from typing import Annotated

from src.core import (
    __,
    required,
    string,
    max_length,
    email_format,
    regex,
    password_strength,
    file,
    half_width,
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
        field = __("fields.user.name")
        v = required(v, field)
        v = string(v, field)
        v = half_width(v, field)
        return max_length(v, 100, field)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        field = __("fields.user.email")
        v = required(v, field)
        v = max_length(v, 254, field, trim=False)
        v = half_width(v, field)
        return email_format(v, field)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        field = __("fields.user.password")
        if not v:
            return v
        return password_strength(v, field)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, v: UploadFile | None) -> UploadFile | None:
        if v is None:
            return None
        field = __("fields.user.avatar")
        return file(
            v,
            field,
            max_size="10Mb",
            allowed_extensions=["jpg", "jpeg", "png"],
            allowed_mime_types=[
                "image/jpeg",
                "image/png",
            ],
        )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("fields.user.phone")
        v = v.strip()
        if not v:
            return None
        v = regex(v, r"^\+?\d{10,14}$", field)

        return max_length(v, 20, field, trim=False)

    @field_validator("line_user_id")
    @classmethod
    def validate_line_user_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("fields.user.line_user_id")
        v = string(v, field)
        return max_length(v, 100, field)

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
                                    "example": "StrongP@ss123",
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
