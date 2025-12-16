"""
Auth Models

Token management models for JWT blacklist and refresh token storage.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.databases.base_model import BaseModel


class TokenBlacklist(BaseModel):
    """
    Token Blacklist Model

    Stores revoked JWT tokens in the database for security.

    Use Cases:
    - User logout (revoke access and refresh tokens)
    - Password change (revoke all user tokens)
    - Admin forced logout
    - Security breach response

    Implementation Notes:
    - Tokens are stored until their natural expiration
    - Cleanup job should periodically remove expired tokens
    - Index on jti for fast lookup during authentication
    - Index on user_id for bulk revocation
    """

    __tablename__ = "token_blacklist"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Blacklist entry unique identifier",
    )

    # Token Information
    jti: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        comment="JWT ID (unique token identifier)",
    )

    token_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Token type: access or refresh"
    )

    # User Reference (for bulk revocation)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User who owned this token",
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Token expiration timestamp (for cleanup)",
    )

    # Revocation Metadata
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="When the token was revoked",
    )

    revocation_reason: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Reason for revocation: logout, password_change, admin, security",
    )

    # Optional: Store partial token for debugging (not full token!)
    token_signature: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Last 8 chars of token for debugging (not full token!)",
    )

    # Metadata
    __table_args__ = (
        Index("ix_token_blacklist_jti_expires", "jti", "expires_at"),
        Index("ix_token_blacklist_user_expires", "user_id", "expires_at"),
        Index("ix_token_blacklist_expires_at", "expires_at"),
        UniqueConstraint("jti", name="uq_token_blacklist_jti"),
        {"comment": "Blacklisted JWT tokens for security and logout"},
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(jti={self.jti}, type={self.token_type}, user_id={self.user_id})>"


class RefreshToken(BaseModel):
    """
    Refresh Token Model

    Stores active refresh tokens for enhanced security and session management.

    Security Features:
    - Token rotation: Each refresh generates new tokens
    - Family tracking: Detects token reuse attacks
    - Device tracking: Monitor active sessions
    - Revocation: Can revoke specific tokens or all user tokens

    Implementation:
    - Only refresh tokens are stored (not access tokens for performance)
    - Access tokens are stateless and verified by signature only
    - Cleanup job removes expired tokens
    """

    __tablename__ = "refresh_tokens"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Refresh token unique identifier",
    )

    # Token Information
    jti: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        comment="JWT ID from refresh token",
    )

    # User Reference
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User who owns this token",
    )

    # Token Metadata
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Token expiration timestamp",
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Token revocation status",
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When the token was revoked"
    )

    # Session Tracking
    device_info: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="User agent or device information"
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address when token was created (IPv6 compatible)",
    )

    # Token Family (for rotation detection)
    family_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Token family ID for rotation tracking",
    )

    parent_jti: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="JTI of the token that was refreshed"
    )

    # Usage Tracking
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the token was used for refresh",
    )

    # Metadata
    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked", "expires_at"),
        Index("ix_refresh_tokens_family", "family_id", "created_at"),
        UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        {"comment": "Active refresh tokens for session management"},
    )

    def __repr__(self) -> str:
        return f"<RefreshToken(jti={self.jti}, user_id={self.user_id}, revoked={self.is_revoked})>"
