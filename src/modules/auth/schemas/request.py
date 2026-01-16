from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError
from fastapi import Form, File, UploadFile
from fastapi.exceptions import RequestValidationError
from typing import Annotated
from src.core import (
    __,
    string,
    max_length,
    between_length,
    email_format,
    phone_number,
    password_strength,
    confirmed,
)
from src.modules.shared import (
    validate_user_name,
    validate_user_email,
    validate_user_password,
    validate_user_confirm_password,
    validate_user_avatar,
    validate_user_phone_regex,
    validate_user_line_id,
)


def _get_example_password() -> str:
    return "SecurePass123!"


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str
    avatar: UploadFile | None = None
    phone: str | None = None
    line_user_id: str | None = None
    is_active: bool = True

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
    def validate_password(cls, v: str) -> str:
        return validate_user_password(v)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        password = info.data.get("password")
        return validate_user_confirm_password(v, password)

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
        password: Annotated[str, Form()],
        confirm_password: Annotated[str, Form()],
        avatar: Annotated[UploadFile | None, File()] = None,
        phone: Annotated[str | None, Form()] = None,
        line_user_id: Annotated[str | None, Form()] = None,
        is_active: Annotated[bool, Form()] = True,
    ) -> "RegisterRequest":
        try:
            return cls(
                name=name,
                email=email,
                password=password,
                confirm_password=confirm_password,
                avatar=avatar,
                phone=phone,
                line_user_id=line_user_id,
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
                            "required": [
                                "name",
                                "email",
                                "password",
                                "confirm_password",
                            ],
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
                                    "example": _get_example_password(),
                                },
                                "confirm_password": {
                                    "type": "string",
                                    "example": _get_example_password(),
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


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return validate_user_email(v, trim=False)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_user_password(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john@example.com",
                "password": _get_example_password(),
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10, description="Refresh token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }
    )


class UpdateCurrentUserRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    confirm_password: str | None = None
    phone: str | None = None
    line_user_id: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("field.name")
        v = string(v, field)
        return max_length(v, 100, field)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("field.email")
        v = max_length(v, 255, field, trim=False)
        return email_format(v, field)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("field.password")
        v = password_strength(v, field)
        return between_length(v, 8, 255, field)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str | None, info) -> str | None:
        if v is None:
            return None
        password = info.data.get("password")
        if password is None:
            return v
        return confirmed(v, password, __("field.confirm_password"))

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("field.phone")
        v = v.strip()
        if not v:
            return None
        v = phone_number(v, field, "JP")
        return max_length(v, 20, field, trim=False)

    @field_validator("line_user_id")
    @classmethod
    def validate_line_user_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        field = __("field.line_user_id")
        v = string(v, field)
        return max_length(v, 100, field)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "password": _get_example_password(),
                "confirm_password": _get_example_password(),
                "phone": "1234567890",
                "line_user_id": "line_user_123",
            }
        }
    )
