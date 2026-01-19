from fastapi import UploadFile
from src.core import (
    __,
    required,
    string,
    max_length,
    email_format,
    password_strength,
    confirmed,
    half_width,
    regex,
    image,
    phone_number,
)


def validate_user_name(v: str) -> str:
    field = __("fields.user.name")
    v = required(v, field)
    v = string(v, field)
    v = half_width(v, field)
    return max_length(v, 100, field)


def validate_user_email(v: str, trim: bool = False) -> str:
    field = __("fields.user.email")
    v = required(v, field)
    v = max_length(v, 254, field, trim=trim)
    v = half_width(v, field)
    return email_format(v, field)


def validate_user_password(v: str) -> str:
    field = __("fields.user.password")
    v = required(v, field)
    return password_strength(v, field)


def validate_user_confirm_password(v: str, password: str | None) -> str:
    field = __("fields.user.confirm_password")
    v = required(v, field)
    if password is None:
        return v
    return confirmed(v, password, field)


def validate_user_avatar(v: UploadFile | None) -> UploadFile | None:
    print("Validating avatar:", v)
    if v is None:
        return None

    field = __("fields.user.avatar")

    return image(
        v,
        field,
        max_size="10Mb",
        allowed_extensions=["jpg", "jpeg", "png"],
        allowed_mime_types=[
            "image/jpeg",
            "image/png",
            "image/jpg",
        ],
    )


def validate_user_phone(v: str | None, country: str = "JP") -> str | None:
    if v is None:
        return None
    field = __("fields.user.phone")
    v = v.strip()
    if not v:
        return None
    v = phone_number(v, field, country)
    return max_length(v, 20, field, trim=False)


def validate_user_phone_regex(v: str | None) -> str | None:
    if v is None:
        return None
    field = __("fields.user.phone")
    v = v.strip()
    if not v:
        return None
    v = regex(v, r"^\+?\d{10,14}$", field)
    return max_length(v, 20, field, trim=False)


def validate_user_line_id(v: str | None) -> str | None:
    if v is None:
        return None
    field = __("fields.user.line_user_id")
    v = string(v, field)
    return max_length(v, 100, field)
