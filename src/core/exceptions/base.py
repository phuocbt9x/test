from typing import Any, Dict, List, Optional, Union
from fastapi import status
from src.core.i18n import __
from .types import ErrorCode, ErrorDetail


class BaseAppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        details: Optional[Union[List[ErrorDetail], Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []
        self.headers = headers
        super().__init__(self.message)


class ValidationException(BaseAppException):
    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None,
        errors: Optional[Dict[str, List[str]]] = None,
    ):
        if errors:
            details_list = []
            for field, messages in errors.items():
                for msg in messages:
                    details_list.append(
                        ErrorDetail(field=field, message=msg, code="validation_error")
                    )
            details = details_list

        if message is None:
            message = __("exceptions.validation_error")

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
        )


class AuthenticationException(BaseAppException):
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED,
    ):
        if message is None:
            message = __("exceptions.authentication_failed")

        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationException(BaseAppException):
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.FORBIDDEN,
    ):
        if message is None:
            message = __("exceptions.access_denied")

        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
        )


class NotFoundException(BaseAppException):
    def __init__(self, resource: str = "Resource", resource_id: Optional[str] = None):
        if resource_id:
            message = __(
                "exceptions.resource_not_found_with_id",
                resource=resource,
                resource_id=resource_id,
            )
        else:
            message = __("exceptions.resource_not_found", resource=resource)

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )


class ConflictException(BaseAppException):
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.CONFLICT,
    ):
        if message is None:
            message = __("exceptions.resource_already_exists")

        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
        )


class BusinessRuleException(BaseAppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            details=details,
        )


class ExternalServiceException(BaseAppException):
    def __init__(self, service: str, message: Optional[str] = None):
        if message is None:
            message = __("exceptions.external_service_error")

        super().__init__(
            message=f"{service}: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


class RateLimitException(BaseAppException):
    def __init__(
        self, message: Optional[str] = None, retry_after: Optional[int] = None
    ):
        if message is None:
            message = __("exceptions.rate_limit_exceeded")

        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            headers=headers,
        )


class BadRequestException(BaseAppException):
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        if message is None:
            message = __("exceptions.bad_request")

        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            details=details,
        )


class UnauthorizedException(BaseAppException):
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED,
    ):
        if message is None:
            message = __("exceptions.unauthorized")

        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )
