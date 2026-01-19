from pydantic import BaseModel, Field, field_validator, ValidationError
from fastapi import UploadFile, Form, File
from fastapi.exceptions import RequestValidationError
from typing import Annotated
from src.utils import (
    validate_user_name,
    validate_user_email,
    validate_user_password,
    validate_user_confirm_password,
    validate_user_avatar,
    validate_user_phone_regex,
    validate_user_line_id,
    get_example_password,
    get_example_name,
    get_example_email,
    get_example_phone,
    get_example_line_id,
    get_example_authentication_token,
)


class LoginRequest(BaseModel):
    email: Annotated[
        str, Field(description="Email address", examples=[get_example_email()])
    ]
    password: Annotated[
        str, Field(description="Password", examples=[get_example_password()])
    ]

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return validate_user_email(v, trim=False)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_user_password(v)


class RefreshTokenRequest(BaseModel):
    refresh_token: Annotated[
        str,
        Field(
            description="Refresh token", examples=[get_example_authentication_token()]
        ),
    ]


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str
    avatar: UploadFile | None = None
    phone: str | None = None
    line_user_id: str | None = None

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
        name: Annotated[
            str,
            Form(description="Full name of the user", examples=[get_example_name()]),
        ],
        email: Annotated[
            str, Form(description="Email address", examples=[get_example_email()])
        ],
        password: Annotated[
            str, Form(description="Password", examples=[get_example_password()])
        ],
        confirm_password: Annotated[
            str,
            Form(description="Confirm password", examples=[get_example_password()]),
        ],
        avatar: Annotated[
            UploadFile | None, File(description="User avatar image file")
        ] = None,
        phone: Annotated[
            str | None, Form(description="Phone number", examples=[get_example_phone()])
        ] = None,
        line_user_id: Annotated[
            str | None,
            Form(description="Line user ID", examples=[get_example_line_id()]),
        ] = None,
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
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())


class UpdateCurrentUserRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    avatar: UploadFile | None = None
    phone: str | None = None
    line_user_id: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_user_name(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_user_email(v, trim=False)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_user_password(v)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, v: UploadFile | None) -> UploadFile | None:
        if v is None:
            return v
        return validate_user_avatar(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_user_phone_regex(v)

    @field_validator("line_user_id")
    @classmethod
    def validate_line_user_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_user_line_id(v)

    @classmethod
    def as_form(
        cls,
        name: Annotated[
            str | None,
            Form(
                description="Full name of the user",
                json_schema_extra={"example": get_example_name()},
            ),
        ] = None,
        email: Annotated[
            str | None,
            Form(
                description="Email address",
                json_schema_extra={"example": get_example_email()},
            ),
        ] = None,
        password: Annotated[
            str | None,
            Form(
                description="Password (leave empty to keep current)",
                json_schema_extra={"example": get_example_password()},
            ),
        ] = None,
        avatar: Annotated[
            UploadFile | None, File(description="Profile avatar image")
        ] = None,
        phone: Annotated[
            str | None,
            Form(
                description="Phone number",
                json_schema_extra={"example": get_example_phone()},
            ),
        ] = None,
        line_user_id: Annotated[
            str | None,
            Form(
                description="Line user ID",
                json_schema_extra={"example": get_example_line_id()},
            ),
        ] = None,
    ) -> "UpdateCurrentUserRequest":
        try:
            return cls(
                name=name,
                email=email,
                password=password,
                avatar=avatar,
                phone=phone,
                line_user_id=line_user_id,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())
