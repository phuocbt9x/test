from typing import Any, Dict, List, Optional, Union
from fastapi import status
from .types import ErrorCode, ErrorDetail


class BaseAppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: ErrorCode = ErrorCode.BAD_REQUEST,
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
        message: str = "Validation error", 
        details: Optional[List[ErrorDetail]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
        )


class AuthenticationException(BaseAppException):
    def __init__(
        self, 
        message: str = "Authentication failed", 
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationException(BaseAppException):
    def __init__(
        self, 
        message: str = "Access denied", 
        error_code: ErrorCode = ErrorCode.FORBIDDEN
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
        )


class NotFoundException(BaseAppException):
    def __init__(
        self, 
        resource: str = "Resource", 
        resource_id: Optional[str] = None
    ):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )


class ConflictException(BaseAppException):
    """Resource conflict exception."""
    
    def __init__(
        self, 
        message: str = "Resource already exists", 
        error_code: ErrorCode = ErrorCode.CONFLICT
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
        )


class BusinessRuleException(BaseAppException):
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            details=details,
        )


class ExternalServiceException(BaseAppException):
    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            message=f"{service}: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


class RateLimitException(BaseAppException):
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        retry_after: Optional[int] = None
    ):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            headers=headers,
        )
