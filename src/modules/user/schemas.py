"""
User Schemas (Pydantic)

Request/Response schemas for user operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ==================== Request Schemas ====================


class UserCreateRequest(BaseModel):
    """Schema for creating a new user"""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    password: str = Field(
        ..., min_length=8, max_length=100, description="User password"
    )
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.isalnum() and "_" not in v:
            raise ValueError("Username must be alphanumeric or contain underscores")
        return v.lower()


class UserUpdateRequest(BaseModel):
    """Schema for updating user profile"""

    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserPasswordChangeRequest(BaseModel):
    """Schema for changing password"""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )


# ==================== Response Schemas ====================


class UserResponse(BaseModel):
    """Schema for user response (without sensitive data)"""

    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserDetailResponse(UserResponse):
    """Detailed user response (for admin or self)"""

    failed_login_attempts: int
    locked_until: Optional[datetime]
    password_changed_at: Optional[datetime]


class UserListResponse(BaseModel):
    """Paginated user list response"""

    data: list[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
