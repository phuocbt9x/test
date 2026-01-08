"""create settings table

Revision ID: dc2bf6ccfc1a
Revises: 2910f34053e7
Create Date: 2026-01-08 10:58:52.158554

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "dc2bf6ccfc1a"
down_revision: Union[str, Sequence[str], None] = "2910f34053e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "settings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key",
        ),
        sa.Column(
            "line_access_token",
            sa.TEXT,
            nullable=True,
            comment="LINE notification access token",
        ),
        sa.Column(
            "notify_sound",
            sa.BOOLEAN,
            nullable=False,
            server_default="true",
            comment="Notification sound ON/OFF (DEFAULT TRUE)",
        ),
        sa.Column(
            "ai_threshold",
            sa.FLOAT,
            nullable=False,
            server_default="0.8",
            comment="Minimum AI judgment score (DEFAULT 0.8)",
        ),
        sa.Column(
            "image_retention_days",
            sa.INTEGER,
            nullable=False,
            server_default="30",
            comment="Image retention period in days (DEFAULT 30)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Record creation timestamp (DEFAULT CURRENT_TIMESTAMP)",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Record update timestamp (DEFAULT CURRENT_TIMESTAMP)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("settings")
