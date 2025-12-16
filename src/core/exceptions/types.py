from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    # Validation Errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_INPUT = "INVALID_INPUT"
    
    # Authentication & Authorization (401, 403)
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"
    INVALID_TOKEN_TYPE = "INVALID_TOKEN_TYPE"
    INVALID_CLAIMS = "INVALID_CLAIMS"
    MISSING_TOKEN = "MISSING_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_INACTIVE = "USER_INACTIVE"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    
    # Resource Errors (404, 409)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    CONFLICT = "CONFLICT"
    
    # Database Errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_INTEGRITY_ERROR = "DATABASE_INTEGRITY_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    
    # Business Logic Errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    OPERATION_FAILED = "OPERATION_FAILED"
    INVALID_STATE = "INVALID_STATE"
    
    # External Service Errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    THIRD_PARTY_API_ERROR = "THIRD_PARTY_API_ERROR"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Server Errors (5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Specific error code")


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Always false for errors")
    error: Dict[str, Any] = Field(..., description="Error information")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    path: Optional[str] = Field(None, description="Request path")
    request_id: Optional[str] = Field(None, description="Request tracking ID")