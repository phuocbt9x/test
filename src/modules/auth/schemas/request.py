from pydantic import BaseModel, Field, field_validator, ConfigDict
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
)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str
    phone: str | None = None
    line_user_id: str | None = None
    is_admin: bool = False
    is_active: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        field = __("field.name")
        v = required(v, field)
        v = string(v, field)
        return max_length(v, 100, field)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        field = __("field.email")
        v = required(v, field)
        v = max_length(v, 255, field, trim=False)
        return email_format(v, field)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        field = __("field.password")
        v = password_strength(v, field)
        return between_length(v, 8, 255, field)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        field = __("field.confirm_password")
        password = info.data.get("password")
        if password is None:
            return v
        return confirmed(v, password, field)

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
        field = __("field.line_user_id")
        if v is None:
            return v
        v = string(v, field)
        return max_length(v, 100, field)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "phone": "1234567890",
                "line_user_id": "line_user_123",
            }
        }
    )


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        field = __("auth.fields.email")
        v = required(v, field)
        v = max_length(v, 254, field, trim=False)
        v = half_width(v, field)
        return email_format(v, field)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        field = __("auth.fields.password")
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
