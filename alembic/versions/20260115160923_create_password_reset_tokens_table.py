"""create password reset tokens table

Revision ID: 9e361cf3e0cc
Revises: 308b0359341c
Create Date: 2026-01-15 16:09:23.692072

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "9e361cf3e0cc"
down_revision: Union[str, Sequence[str], None] = "308b0359341c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Token ID",
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="User ID",
        ),
        sa.Column(
            "token",
            sa.Text,
            nullable=False,
            unique=True,
            index=True,
            comment="Reset token (hashed)",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
            comment="Token expiration time",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            index=True,
            comment="Token usage time (NULL if unused)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
            comment="Creation timestamp",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("password_reset_tokens")
