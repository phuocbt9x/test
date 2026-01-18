import re
import json
import uuid as uuidlib
import phonenumbers
from starlette.datastructures import UploadFile
from datetime import datetime
from typing import Any, Sequence, Optional, Union, Type, Dict
from urllib.parse import urlparse
from ipaddress import ip_address, IPv4Address, IPv6Address
from email_validator import validate_email, EmailNotValidError
from fastapi import HTTPException, status
from sqlalchemy import select
from src.core.i18n import __
from src.core.configs.database import get_read_db
from phonenumbers import NumberParseException
from src.core.utils.helper import parse_size


_COMPILED_PATTERNS = {
    "alpha_dash": re.compile(r"^[\w-]+$"),
    "mac_address": re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"),
    "phone_fallback": re.compile(
        r"^[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$"
    ),
    "whitespace": re.compile(r"\s"),
    "password_uppercase": re.compile(r"[A-Z]"),
    "password_lowercase": re.compile(r"[a-z]"),
    "password_digits": re.compile(r"\d"),
    "password_special": re.compile(r"[!@#$%^&*(),.?\":{}|<>]"),
    "half_width": re.compile(r"^[\x00-\x7F]+$"),
}

_DEFAULT_IMAGE_FORMATS = ["jpg", "jpeg", "png", "gif", "webp"]
_IMAGE_FORMAT_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


def _validate_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(__("validation.string", attribute=field))
    return value


def _trim_if_needed(value: str, trim: bool) -> str:
    return value.strip() if trim else value


def required(value: Any, field: str) -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(__("validation.required", attribute=field))
    return value


def present(value: Any, field: str) -> Any:
    if value is None:
        raise ValueError(__("validation.present", attribute=field))
    return value


def filled(value: Any, field: str) -> Any:
    if not value:
        raise ValueError(__("validation.filled", attribute=field))
    return value


def string(value: Any, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    return _trim_if_needed(value, trim)


def integer(value: Any, field: str) -> int:
    if not isinstance(value, int):
        raise ValueError(__("validation.integer", attribute=field))
    return value


def numeric(value: Any, field: str) -> Union[int, float]:
    if not isinstance(value, (int, float)):
        raise ValueError(__("validation.numeric", attribute=field))
    return value


def boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(__("validation.boolean", attribute=field))
    return value


def array(value: Any, field: str) -> Sequence:
    if not isinstance(value, (list, tuple)):
        raise ValueError(__("validation.array", attribute=field))
    return value


def min_length(value: str, min_len: int, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if len(value) < min_len:
        raise ValueError(__("validation.min.string", attribute=field, min=min_len))
    return value


def max_length(value: str, max_len: int, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if len(value) > max_len:
        raise ValueError(__("validation.max.string", attribute=field, max=max_len))
    return value


def between_length(
    value: str, min_len: int, max_len: int, field: str, trim: bool = True
) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not (min_len <= len(value) <= max_len):
        raise ValueError(
            __("validation.between.string", attribute=field, min=min_len, max=max_len)
        )
    return value


def exact_length(value: str, length: int, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if len(value) != length:
        raise ValueError(__("validation.exact_length", attribute=field, length=length))
    return value


def min_value(
    value: Union[int, float], min_val: Union[int, float], field: str
) -> Union[int, float]:
    if not isinstance(value, (int, float)):
        raise ValueError(__("validation.numeric", attribute=field))
    if value < min_val:
        raise ValueError(__("validation.min.numeric", attribute=field, min=min_val))
    return value


def max_value(
    value: Union[int, float], max_val: Union[int, float], field: str
) -> Union[int, float]:
    if not isinstance(value, (int, float)):
        raise ValueError(__("validation.numeric", attribute=field))
    if value > max_val:
        raise ValueError(__("validation.max.numeric", attribute=field, max=max_val))
    return value


def between_value(
    value: Union[int, float],
    min_val: Union[int, float],
    max_val: Union[int, float],
    field: str,
) -> Union[int, float]:
    if not isinstance(value, (int, float)):
        raise ValueError(__("validation.numeric", attribute=field))
    if not (min_val <= value <= max_val):
        raise ValueError(
            __("validation.between.numeric", attribute=field, min=min_val, max=max_val)
        )
    return value


def alpha(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not value.isalpha():
        raise ValueError(__("validation.alpha", attribute=field))
    return value


def alpha_num(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not value.isalnum():
        raise ValueError(__("validation.alpha_num", attribute=field))
    return value


def alpha_dash(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not _COMPILED_PATTERNS["alpha_dash"].match(value):
        raise ValueError(__("validation.alpha_dash", attribute=field))
    return value


def lowercase(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if value != value.lower():
        raise ValueError(__("validation.lowercase", attribute=field))
    return value


def uppercase(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if value != value.upper():
        raise ValueError(__("validation.uppercase", attribute=field))
    return value


def no_whitespace(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if _COMPILED_PATTERNS["whitespace"].search(value):
        raise ValueError(__("validation.no_whitespace", attribute=field))
    return value


def regex(value: str, pattern: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        if not re.match(pattern, value):
            raise ValueError(__("validation.regex", attribute=field))
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e
    return value


def email_format(
    value: str, field: str, check_deliverability: bool = False, trim: bool = True
) -> str:
    value = _validate_string(value, field)
    if trim:
        value = value.strip().lower()
    try:
        validated = validate_email(value, check_deliverability=check_deliverability)
        return validated.normalized
    except EmailNotValidError as e:
        raise ValueError(__("validation.email", attribute=field)) from e


def url(
    value: str, field: str, schemes: Optional[Sequence[str]] = None, trim: bool = True
) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if schemes is None:
        schemes = ["http", "https", "ftp"]
    try:
        parsed = urlparse(value)
        if not parsed.scheme or parsed.scheme not in schemes or not parsed.netloc:
            raise ValueError(__("validation.url", attribute=field))
        return value
    except Exception:
        raise ValueError(__("validation.url", attribute=field))


def ip(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        ip_address(value)
        return value
    except (ValueError, Exception):
        raise ValueError(__("validation.ip", attribute=field))


def ipv4(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        addr = ip_address(value)
        if not isinstance(addr, IPv4Address):
            raise ValueError(__("validation.ipv4", attribute=field))
        return value
    except (ValueError, Exception):
        raise ValueError(__("validation.ipv4", attribute=field))


def ipv6(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        addr = ip_address(value)
        if not isinstance(addr, IPv6Address):
            raise ValueError(__("validation.ipv6", attribute=field))
        return value
    except (ValueError, Exception):
        raise ValueError(__("validation.ipv6", attribute=field))


def mac_address(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not _COMPILED_PATTERNS["mac_address"].match(value):
        raise ValueError(__("validation.mac_address", attribute=field))
    return value


def uuid(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        uuidlib.UUID(value)
        return value
    except (ValueError, AttributeError, TypeError):
        raise ValueError(__("validation.uuid", attribute=field))


def date_format(
    value: str, field: str, fmt: str = "%Y-%m-%d", trim: bool = True
) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        datetime.strptime(value, fmt)
        return value
    except (ValueError, Exception):
        raise ValueError(__("validation.date_format", attribute=field, format=fmt))


def date(value: str, field: str, fmt: str = "%Y-%m-%d", trim: bool = True) -> str:
    return date_format(value, field, fmt, trim=trim)


def json_string(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        json.loads(value)
        return value
    except json.JSONDecodeError:
        raise ValueError(__("validation.json", attribute=field))


def same(value: Any, other: Any, field: str, other_field: str) -> Any:
    if value != other:
        raise ValueError(__("validation.same", attribute=field, other=other_field))
    return value


def different(value: Any, other: Any, field: str, other_field: str) -> Any:
    if value == other:
        raise ValueError(__("validation.different", attribute=field, other=other_field))
    return value


def confirmed(value: str, confirmation: str, field: str) -> str:
    if value != confirmation:
        raise ValueError(__("validation.confirmed", attribute=field))
    return value


def in_list(value: Any, valid_list: Sequence, field: str) -> Any:
    if value not in valid_list:
        raise ValueError(__("validation.in", attribute=field))
    return value


def not_in_list(value: Any, invalid_list: Sequence, field: str) -> Any:
    if value in invalid_list:
        raise ValueError(__("validation.not_in", attribute=field))
    return value


def distinct(values: Sequence, field: str) -> Sequence:
    if not isinstance(values, (list, tuple)):
        raise ValueError(__("validation.array", attribute=field))
    if len(values) != len(set(values)):
        raise ValueError(__("validation.distinct", attribute=field))
    return values


def starts_with(
    value: str, prefixes: Sequence[str], field: str, trim: bool = True
) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise ValueError(__("validation.starts_with", attribute=field, values=prefixes))
    return value


def ends_with(
    value: str, suffixes: Sequence[str], field: str, trim: bool = True
) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    if not any(value.endswith(suffix) for suffix in suffixes):
        raise ValueError(__("validation.ends_with", attribute=field, values=suffixes))
    return value


def accepted(value: Any, field: str) -> Any:
    if value not in [True, "yes", "on", 1, "1"]:
        raise ValueError(__("validation.accepted", attribute=field))
    return value


def declined(value: Any, field: str) -> Any:
    if value not in [False, "no", "off", 0, "0"]:
        raise ValueError(__("validation.declined", attribute=field))
    return value


def phone_number(
    value: str, field: str, country_code: Optional[str] = None, trim: bool = True
) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)
    try:
        try:
            parsed = phonenumbers.parse(value, country_code)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError(__("validation.phone", attribute=field))
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except NumberParseException:
            raise ValueError(__("validation.phone", attribute=field))
    except ImportError:
        cleaned = (
            value.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )
        if not _COMPILED_PATTERNS["phone_fallback"].match(cleaned):
            raise ValueError(__("validation.phone", attribute=field))
        return value


def password_strength(
    value: str,
    field: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digits: bool = True,
    require_special: bool = False,
    trim: bool = False,
) -> str:
    value = _validate_string(value, field)
    if trim:
        value = value.strip()

    rules = [
        (len(value) >= min_length, "password_length"),
        (
            not require_uppercase
            or _COMPILED_PATTERNS["password_uppercase"].search(value),
            "password_uppercase",
        ),
        (
            not require_lowercase
            or _COMPILED_PATTERNS["password_lowercase"].search(value),
            "password_lowercase",
        ),
        (
            not require_digits or _COMPILED_PATTERNS["password_digits"].search(value),
            "password_digits",
        ),
        (
            not require_special or _COMPILED_PATTERNS["password_special"].search(value),
            "password_special",
        ),
    ]

    for passed, _ in rules:
        if not passed:
            raise ValueError(__("validation.password_strength", attribute=field))

    return value


def _get_primary_key_fields(model: Type[Any]) -> list:
    primary_key = model.__table__.primary_key
    if not primary_key:
        return []
    return [col.name for col in primary_key.columns]


def _build_exclude_conditions(model: Type[Any], exclude: Dict[str, Any]) -> list:
    conditions = []
    for field_name, field_value in exclude.items():
        if not hasattr(model, field_name):
            continue
        column = getattr(model, field_name)
        conditions.append(column != field_value)
    return conditions


async def unique(
    value: Any,
    model: Type[Any],
    field: str,
    field_label: Optional[str] = None,
    exclude: Optional[Dict[str, Any]] = None,
    exclude_id: Optional[Any] = None,
) -> Any:
    async for read_session in get_read_db():
        stmt = select(model).where(getattr(model, field) == value)
        if exclude:
            conditions = _build_exclude_conditions(model, exclude)
            if conditions:
                for condition in conditions:
                    stmt = stmt.where(condition)
        elif exclude_id is not None:
            pk_fields = _get_primary_key_fields(model)
            if len(pk_fields) == 1:
                pk_field = pk_fields[0]
                stmt = stmt.where(getattr(model, pk_field) != exclude_id)
        if hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        result = await read_session.execute(stmt.limit(1))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=[
                    {
                        "field": field,
                        "message": __(
                            "validation.unique", attribute=field_label or field
                        ),
                        "type": "unique",
                    }
                ],
            )
        return value


async def exists(
    value: Any,
    model: Type[Any],
    field: str,
    field_label: Optional[str] = None,
    exclude: Optional[Dict[str, Any]] = None,
) -> Any:
    async for read_session in get_read_db():
        stmt = select(model).where(getattr(model, field) == value)
        if exclude:
            conditions = _build_exclude_conditions(model, exclude)
            if conditions:
                for condition in conditions:
                    stmt = stmt.where(condition)
        if hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        result = await read_session.execute(stmt.limit(1))
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=[
                    {
                        "field": field,
                        "message": __(
                            "validation.exists", attribute=field_label or field
                        ),
                        "type": "value_error",
                    }
                ],
            )
        return value


def file(
    value: Any,
    field: str,
    max_size: Optional[int | str] = None,
    allowed_extensions: Optional[Sequence[str]] = None,
    allowed_mime_types: Optional[Sequence[str]] = None,
) -> Any:
    if value is None:
        raise ValueError(__("validation.file", attribute=field))

    if not isinstance(value, UploadFile):
        raise ValueError(__("validation.file", attribute=field))

    if not (
        hasattr(value, "filename")
        and (hasattr(value, "file") or hasattr(value, "read"))
    ):
        raise ValueError(__("validation.file", attribute=field))

    filename = getattr(value, "filename", "")
    if not filename:
        raise ValueError(__("validation.file", attribute=field))

    if max_size:
        max_bytes = parse_size(max_size) if isinstance(max_size, str) else max_size
        if hasattr(value, "size") and value.size is not None:
            if value.size > max_bytes:
                raise ValueError(
                    __("validation.max.file", attribute=field, max=max_size)
                )

    if allowed_extensions:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed_exts = [e.lower().lstrip(".") for e in allowed_extensions]

        if ext not in allowed_exts:
            raise ValueError(
                __(
                    "validation.mimes",
                    attribute=field,
                    values=", ".join(allowed_extensions),
                )
            )

    if allowed_mime_types:
        if not hasattr(value, "content_type") or not value.content_type:
            raise ValueError(__("validation.file", attribute=field))

        if value.content_type not in allowed_mime_types:
            raise ValueError(
                __(
                    "validation.mimetypes",
                    attribute=field,
                    values=", ".join(allowed_mime_types),
                )
            )

    return value


def image(
    value: Any,
    field: str,
    max_size: Optional[int | str] = None,
    allowed_extensions: Optional[Sequence[str]] = None,
    allowed_mime_types: Optional[Sequence[str]] = None,
) -> Any:
    if value is None:
        raise ValueError(__("validation.image", attribute=field))

    if not isinstance(value, UploadFile):
        raise ValueError(__("validation.image", attribute=field))

    if not (
        hasattr(value, "filename")
        and (hasattr(value, "file") or hasattr(value, "read"))
    ):
        raise ValueError(__("validation.image", attribute=field))

    filename = getattr(value, "filename", "")
    if not filename:
        raise ValueError(__("validation.image", attribute=field))

    if max_size:
        max_bytes = parse_size(max_size) if isinstance(max_size, str) else max_size
        if hasattr(value, "size") and value.size is not None:
            if value.size > max_bytes:
                raise ValueError(
                    __("validation.max.file", attribute=field, max=max_size)
                )

    if allowed_extensions is None:
        allowed_extensions = _DEFAULT_IMAGE_FORMATS

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_exts = [f.lower().lstrip(".") for f in allowed_extensions]

    if ext not in allowed_exts:
        raise ValueError(__("validation.image", attribute=field))

    if hasattr(value, "content_type") and value.content_type:
        if allowed_mime_types is not None:
            if value.content_type not in allowed_mime_types:
                raise ValueError(
                    __(
                        "validation.mimetypes",
                        attribute=field,
                        values=", ".join(allowed_mime_types),
                    )
                )
        else:
            allowed_mimes = set()
            for fmt in allowed_exts:
                if fmt in _IMAGE_FORMAT_TO_MIME:
                    allowed_mimes.add(_IMAGE_FORMAT_TO_MIME[fmt])

            if allowed_mimes and value.content_type not in allowed_mimes:
                raise ValueError(__("validation.image", attribute=field))

    return value


def half_width(value: str, field: str, trim: bool = True) -> str:
    value = _validate_string(value, field)
    value = _trim_if_needed(value, trim)

    if not _COMPILED_PATTERNS["half_width"].match(value):
        raise ValueError(__("validation.half_width", attribute=field))

    return value
