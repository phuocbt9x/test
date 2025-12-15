from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from fastapi import status
from datetime import datetime

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper"""
    success: bool = Field(default=True, description="Response status")
    message: str = Field(default="Success", description="Response message")
    data: Optional[T] = Field(default=None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "123", "name": "Example"},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""
    success: bool = Field(default=False, description="Response status")
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "email", "issue": "Invalid format"},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total: int = Field(description="Total items count")
    total_pages: int = Field(description="Total pages count")
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper"""
    success: bool = Field(default=True, description="Response status")
    message: str = Field(default="Success", description="Response message")
    data: List[T] = Field(default_factory=list, description="Response data items")
    meta: PaginationMeta = Field(description="Pagination metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Data retrieved successfully",
                "data": [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}],
                "meta": {
                    "page": 1,
                    "per_page": 20,
                    "total": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class BaseController:
    """
    Base controller class providing standard response methods.

    This class ensures consistent API responses across all controllers.
    All controller classes should inherit from this base class.
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK
    ) -> SuccessResponse:
        """
        Create a standard success response.

        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code

        Returns:
            SuccessResponse instance
        """
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def created(
        data: Any = None,
        message: str = "Resource created successfully"
    ) -> SuccessResponse:
        """
        Create a standard 201 Created response.

        Args:
            data: Created resource data
            message: Success message

        Returns:
            SuccessResponse instance
        """
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def updated(
        data: Any = None,
        message: str = "Resource updated successfully"
    ) -> SuccessResponse:
        """
        Create a standard update response.

        Args:
            data: Updated resource data
            message: Success message

        Returns:
            SuccessResponse instance
        """
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def deleted(message: str = "Resource deleted successfully") -> SuccessResponse:
        """
        Create a standard delete response.

        Args:
            message: Success message

        Returns:
            SuccessResponse instance
        """
        return SuccessResponse(
            success=True,
            message=message,
            data=None,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = "Data retrieved successfully"
    ) -> PaginatedResponse:
        """
        Create a standard paginated response.

        Args:
            data: List of items
            page: Current page number
            per_page: Items per page
            total: Total items count
            message: Success message

        Returns:
            PaginatedResponse instance
        """
        total_pages = (total + per_page - 1) // per_page

        meta = PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

        return PaginatedResponse(
            success=True,
            message=message,
            data=data,
            meta=meta,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> ErrorResponse:
        """
        Create a standard error response.

        Args:
            message: Error message
            error_code: Error code
            details: Additional error details
            status_code: HTTP status code

        Returns:
            ErrorResponse instance
        """
        return ErrorResponse(
            success=False,
            message=message,
            error_code=error_code,
            details=details,
            timestamp=datetime.utcnow()
        )
