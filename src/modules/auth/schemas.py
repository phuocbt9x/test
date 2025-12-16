"""
Auth Schemas (Pydantic)

Request/Response schemas for authentication operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ==================== Request Schemas ====================


class LoginRequest(BaseModel):
    """Schema for user login"""

    email: str = Field(..., description="Email or username")
    password: str = Field(..., min_length=1, description="User password")


class RegisterRequest(BaseModel):
    """Schema for user registration"""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    password: str = Field(
        ..., min_length=8, max_length=100, description="User password"
    )
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing access token"""

    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Schema for logout (optional: can be done without body)"""

    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke")


# ==================== Response Schemas ====================


class TokenResponse(BaseModel):
    """Schema for token response"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class LoginResponse(TokenResponse):
    """Schema for login response with user info"""

    user: dict = Field(..., description="User information")


class MessageResponse(BaseModel):
    """Generic message response"""

    message: str


class ActiveSessionResponse(BaseModel):
    """Schema for active session info"""

    id: UUID
    device_info: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
