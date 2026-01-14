from typing import Any, Dict, Generic, List, Optional, TypeVar, get_args
from pydantic import BaseModel, Field, ConfigDict
from fastapi import status
from datetime import datetime
from src.core.i18n import __
from src.core.utils import utcnow

T = TypeVar("T")

DESCRIPTION_RESPONSE_MESSAGE: Dict[str, str] = {
    "success": "Response status",
    "message": "Response message",
    "data": "Response data",
    "meta": "Pagination metadata",
    "timestamp": "Response timestamp",
    "error_code": "Application specific error code",
    "details": "Error details",
}


def _get_example_from_type(model_type: Any) -> Any:
    if hasattr(model_type, "model_config"):
        config = model_type.model_config
        if isinstance(config, dict) and "json_schema_extra" in config:
            extra = config["json_schema_extra"]
            if isinstance(extra, dict) and "example" in extra:
                return extra["example"]
            elif callable(extra):
                try:
                    result = extra({}, model_type)
                    if isinstance(result, dict) and "example" in result:
                        return result["example"]
                except Exception:
                    pass
    if hasattr(model_type, "Config") and hasattr(
        model_type.Config, "json_schema_extra"
    ):
        extra = model_type.Config.json_schema_extra
        if isinstance(extra, dict) and "example" in extra:
            return extra["example"]
    return None


def _generate_success_response_example(
    schema: Dict[str, Any], model_class: Any
) -> Dict[str, Any]:
    example = {
        "success": True,
        "message": __("messages.operation_completed"),
        "data": None,
        "timestamp": "2024-01-15T10:30:00Z",
    }

    if hasattr(model_class, "__origin__") or hasattr(model_class, "__args__"):
        args = get_args(model_class)
        if args:
            generic_type = args[0]
            data_example = _get_example_from_type(generic_type)
            if data_example:
                example["data"] = data_example
    else:
        if hasattr(model_class, "__orig_bases__"):
            for base in model_class.__orig_bases__:
                if hasattr(base, "__args__") and base.__args__:
                    generic_type = base.__args__[0]
                    data_example = _get_example_from_type(generic_type)
                    if data_example:
                        example["data"] = data_example
                        break

    return {"example": example}


def _generate_paginated_response_example(model_class: Any) -> Dict[str, Any]:
    example = {
        "success": True,
        "message": __("messages.data_retrieved"),
        "data": [],
        "meta": {
            "page": 1,
            "per_page": 20,
            "total": 100,
            "total_pages": 5,
            "has_next": True,
            "has_prev": False,
        },
        "timestamp": "2024-01-15T10:30:00Z",
    }

    if hasattr(model_class, "__origin__") or hasattr(model_class, "__args__"):
        args = get_args(model_class)
        if args:
            generic_type = args[0]
            item_example = _get_example_from_type(generic_type)
            if item_example:
                example["data"] = [item_example]
    else:
        if hasattr(model_class, "__orig_bases__"):
            for base in model_class.__orig_bases__:
                if hasattr(base, "__args__") and base.__args__:
                    generic_type = base.__args__[0]
                    item_example = _get_example_from_type(generic_type)
                    if item_example:
                        example["data"] = [item_example]
                        break

    return {"example": example}


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = Field(
        default=True, description=DESCRIPTION_RESPONSE_MESSAGE["success"]
    )
    message: str = Field(
        default_factory=lambda: __("messages.operation_completed"),
        description=DESCRIPTION_RESPONSE_MESSAGE["message"],
        json_schema_extra={"example": __("messages.operation_completed")},
    )
    data: Optional[T] = Field(
        default=None, description=DESCRIPTION_RESPONSE_MESSAGE["data"]
    )
    timestamp: datetime = Field(
        default_factory=utcnow, description=DESCRIPTION_RESPONSE_MESSAGE["timestamp"]
    )

    model_config = ConfigDict(
        json_schema_extra=_generate_success_response_example  # type: ignore[typeddict-item]
    )


class ErrorResponse(BaseModel):
    success: bool = Field(
        default=False, description=DESCRIPTION_RESPONSE_MESSAGE["success"]
    )
    message: str = Field(description=DESCRIPTION_RESPONSE_MESSAGE["message"])
    error_code: Optional[str] = Field(
        default=None,
        description=DESCRIPTION_RESPONSE_MESSAGE["error_code"],
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description=DESCRIPTION_RESPONSE_MESSAGE["details"],
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
        description=DESCRIPTION_RESPONSE_MESSAGE["timestamp"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": __("messages.validation_error"),
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "email", "issue": "Invalid format"},
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )


class PaginationMeta(BaseModel):
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total: int = Field(description="Total items count")
    total_pages: int = Field(description="Total pages count")
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False,
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = Field(
        default=True, description=DESCRIPTION_RESPONSE_MESSAGE["success"]
    )
    message: str = Field(
        default_factory=lambda: __("messages.operation_completed"),
        description=DESCRIPTION_RESPONSE_MESSAGE["message"],
        json_schema_extra={"example": __("messages.data_retrieved")},
    )
    data: List[T] = Field(
        default_factory=list,
        description=DESCRIPTION_RESPONSE_MESSAGE["data"],
    )
    meta: PaginationMeta = Field(description=DESCRIPTION_RESPONSE_MESSAGE["meta"])
    timestamp: datetime = Field(
        default_factory=utcnow,
        description=DESCRIPTION_RESPONSE_MESSAGE["timestamp"],
    )

    model_config = ConfigDict(
        json_schema_extra=_generate_paginated_response_example  # type: ignore[typeddict-item]
    )


class BaseController:
    @staticmethod
    def success(
        data: Any = None,
        message: str | None = None,
        status_code: int = status.HTTP_200_OK,
    ) -> SuccessResponse:
        return SuccessResponse(
            success=True,
            message=message or __("messages.operation_completed"),
            data=data,
            timestamp=utcnow(),
        )

    @staticmethod
    def created(data: Any = None, message: str | None = None) -> SuccessResponse:
        return SuccessResponse(
            success=True,
            message=message or __("messages.created_successfully"),
            data=data,
            timestamp=utcnow(),
        )

    @staticmethod
    def updated(data: Any = None, message: str | None = None) -> SuccessResponse:
        return SuccessResponse(
            success=True,
            message=message or __("messages.updated_successfully"),
            data=data,
            timestamp=utcnow(),
        )

    @staticmethod
    def deleted(message: str | None = None) -> SuccessResponse:
        return SuccessResponse(
            success=True,
            message=message or __("messages.deleted_successfully"),
            data=None,
            timestamp=utcnow(),
        )

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str | None = None,
    ) -> PaginatedResponse:
        total_pages = (total + per_page - 1) // per_page

        meta = PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        return PaginatedResponse(
            success=True,
            message=message or __("messages.data_retrieved"),
            data=data,
            meta=meta,
            timestamp=utcnow(),
        )

    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> ErrorResponse:
        return ErrorResponse(
            success=False,
            message=message,
            error_code=error_code,
            details=details,
            timestamp=utcnow(),
        )
