from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field
from fastapi import status
from src.core import (
    BaseAppException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    BadRequestException,
    UnauthorizedException,
    BusinessRuleException,
    RateLimitException,
    ExternalServiceException,
)


class ValidationErrorResponse(BaseModel):
    success: bool = Field(False, description="Response status")
    status_code: int = Field(description="HTTP status code")
    message: Optional[str] = Field(None, description="Error message")
    errors: Dict[str, List[str]] = Field(description="Field validation errors")


class GeneralErrorResponse(BaseModel):
    success: bool = Field(False, description="Response status")
    status_code: int = Field(description="HTTP status code")
    message: str = Field(description="Error message")
    errors: Optional[Dict[str, Any]] = Field(None, description="Error details")


_EXCEPTION_TO_STATUS_CODE: Dict[Type[BaseAppException], int] = {
    ValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationException: status.HTTP_401_UNAUTHORIZED,
    AuthorizationException: status.HTTP_403_FORBIDDEN,
    NotFoundException: status.HTTP_404_NOT_FOUND,
    ConflictException: status.HTTP_409_CONFLICT,
    BadRequestException: status.HTTP_400_BAD_REQUEST,
    UnauthorizedException: status.HTTP_401_UNAUTHORIZED,
    BusinessRuleException: status.HTTP_400_BAD_REQUEST,
    RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
    ExternalServiceException: status.HTTP_503_SERVICE_UNAVAILABLE,
}

_EXCEPTION_TO_MESSAGE: Dict[Type[BaseAppException], str] = {
    ValidationException: "Validation error",
    AuthenticationException: "Authentication failed",
    AuthorizationException: "Access denied",
    NotFoundException: "Resource not found",
    ConflictException: "Resource already exists",
    BadRequestException: "Bad request",
    UnauthorizedException: "Unauthorized",
    BusinessRuleException: "Bad request",
    RateLimitException: "Rate limit exceeded",
    ExternalServiceException: "External service error",
}

_STATUS_CODE_TO_MESSAGE: Dict[int, str] = {
    status.HTTP_422_UNPROCESSABLE_ENTITY: "Validation error",
    status.HTTP_409_CONFLICT: "Duplicate entry found",
    status.HTTP_503_SERVICE_UNAVAILABLE: "Database connection error",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected error occurred",
    status.HTTP_429_TOO_MANY_REQUESTS: "Rate limit exceeded",
}

_DEFAULT_ERROR_MESSAGE = "Unexpected error occurred"


def get_status_code_for_exception(exception_type: Type[BaseAppException]) -> int:
    return _EXCEPTION_TO_STATUS_CODE.get(
        exception_type, status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def get_response_description(
    exception_type: Type[BaseAppException] | None = None,
    status_code: int | None = None,
    custom_description: str | None = None,
) -> str:
    if custom_description:
        return custom_description

    if exception_type and exception_type in _EXCEPTION_TO_MESSAGE:
        return _EXCEPTION_TO_MESSAGE[exception_type]

    if status_code and status_code in _STATUS_CODE_TO_MESSAGE:
        return _STATUS_CODE_TO_MESSAGE[status_code]

    fallback_descriptions = {
        status.HTTP_400_BAD_REQUEST: "Bad request",
        status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        status.HTTP_403_FORBIDDEN: "Access denied",
        status.HTTP_404_NOT_FOUND: "Resource not found",
        status.HTTP_409_CONFLICT: "Resource already exists",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "Validation error",
        status.HTTP_429_TOO_MANY_REQUESTS: "Rate limit exceeded",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected error occurred",
        status.HTTP_503_SERVICE_UNAVAILABLE: "External service error",
    }

    return fallback_descriptions.get(
        status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
        _DEFAULT_ERROR_MESSAGE,
    )


def create_exception_responses(
    exceptions: List[Union[Type[BaseAppException], int]],
    custom_descriptions: Dict[Union[Type[BaseAppException], int], str] | None = None,
) -> Dict[Union[int, str], Dict[str, Any]]:
    if custom_descriptions is None:
        custom_descriptions = {}

    responses: Dict[Union[int, str], Dict[str, Any]] = {}

    for exception_or_status in exceptions:
        if isinstance(exception_or_status, int):
            status_code = exception_or_status
            description = custom_descriptions.get(
                status_code,
                get_response_description(status_code=status_code),
            )
        elif issubclass(exception_or_status, BaseAppException):
            status_code = get_status_code_for_exception(exception_or_status)
            description = custom_descriptions.get(
                exception_or_status,
                get_response_description(exception_type=exception_or_status),
            )
        else:
            continue

        model: Type[BaseModel]

        if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            model = ValidationErrorResponse
        else:
            model = GeneralErrorResponse

        responses[status_code] = {
            "model": model,
            "description": description,
        }

    return responses


def create_common_responses(
    include_validation: bool = True,
    include_unauthorized: bool = False,
    include_forbidden: bool = False,
    include_not_found: bool = False,
    include_conflict: bool = False,
    include_rate_limit: bool = False,
    include_bad_request: bool = False,
    include_internal_error: bool = False,
    custom_descriptions: Dict[Union[Type[BaseAppException], int], str] | None = None,
) -> Dict[Union[int, str], Dict[str, Any]]:
    exceptions: List[Union[Type[BaseAppException], int]] = []

    if include_validation:
        exceptions.append(ValidationException)
    if include_unauthorized:
        exceptions.append(UnauthorizedException)
    if include_forbidden:
        exceptions.append(AuthorizationException)
    if include_not_found:
        exceptions.append(NotFoundException)
    if include_conflict:
        exceptions.append(ConflictException)
    if include_rate_limit:
        exceptions.append(RateLimitException)
    if include_bad_request:
        exceptions.append(BadRequestException)
    if include_internal_error:
        exceptions.append(status.HTTP_500_INTERNAL_SERVER_ERROR)

    return create_exception_responses(exceptions, custom_descriptions)
