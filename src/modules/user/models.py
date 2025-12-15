"""
User Model

Represents a user in the system with authentication and profile information.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.databases.base_model import BaseModel


class User(BaseModel):
    """
    User Model

    Security Features:
    - Password hashing (handled at service layer)
    - Email uniqueness
    - Account activation/deactivation
    - Failed login attempt tracking
    - Account lockout mechanism
    """
    __tablename__ = "users"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="User unique identifier"
    )

    # Authentication Fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address (used for login)"
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username"
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password (bcrypt/argon2)"
    )

    # Profile Fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User's full name"
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Phone number"
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Profile picture URL"
    )

    # Account Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Account active status"
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email verification status"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Admin/superuser flag"
    )

    # Security Fields
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of failed login attempts"
    )

    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp"
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp"
    )

    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last password change timestamp"
    )

    # Metadata
    __table_args__ = (
        Index('ix_users_email_active', 'email', 'is_active'),
        Index('ix_users_username_active', 'username', 'is_active'),
        {'comment': 'User accounts with authentication and profile information'}
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
