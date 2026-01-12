"""create cameras table

Revision ID: fc294b392fc7
Revises: 1d54ec830229
Create Date: 2026-01-08 10:58:22.040686

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "fc294b392fc7"
down_revision: Union[str, Sequence[str], None] = "1d54ec830229"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cameras",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key, UUID auto-generated (gen_random_uuid())",
        ),
        sa.Column(
            "name", sa.VARCHAR(100), nullable=False, comment="Camera display name"
        ),
        sa.Column(
            "location",
            sa.VARCHAR(255),
            nullable=False,
            comment="Camera installation location (e.g., classroom name, entrance)",
        ),
        sa.Column(
            "rtsp_url", sa.TEXT, nullable=False, comment="Camera RTSP connection URL"
        ),
        sa.Column(
            "is_online",
            sa.BOOLEAN,
            nullable=False,
            server_default="true",
            comment="Online/offline status flag (DEFAULT TRUE)",
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
        sa.Column(
            "deleted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Soft delete timestamp",
        ),
    )

    # Create indexes
    op.create_index("ix_cameras_deleted_at", "cameras", ["deleted_at"])
    op.create_index("ix_cameras_is_online", "cameras", ["is_online"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_cameras_is_online", table_name="cameras")
    op.drop_index("ix_cameras_deleted_at", table_name="cameras")

    # Drop table
    op.drop_table("cameras")
