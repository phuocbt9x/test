from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError
from fastapi import Form, File, UploadFile
from fastapi.exceptions import RequestValidationError
from typing import Annotated
from src.core import (
    __,
    required,
    string,
    max_length,
    between_length,
    email_format,
    phone_number,
    password_strength,
    confirmed,
    half_width,
    regex,
    file,
)


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
        v = required(v, field)
        return password_strength(v, field)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        password = info.data.get("password")
        field = __("fields.user.confirm_password")
        v = required(v, field)
        return confirmed(v, password, __("fields.user.confirm_password"))

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
                                    "example": "StrongP@ss123",
                                },
                                "confirm_password": {
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
        field = __("fields.user.email")
        v = required(v, field)
        v = max_length(v, 254, field, trim=False)
        v = half_width(v, field)
        return email_format(v, field)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        field = __("fields.user.password")
        v = required(v, field)
        return password_strength(v, field)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "john@example.com", "password": "SecurePass123!"}
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
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "phone": "1234567890",
                "line_user_id": "line_user_123",
            }
        }
    )
