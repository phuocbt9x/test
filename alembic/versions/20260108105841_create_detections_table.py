"""create detections table

Revision ID: 8003242e9a74
Revises: 6753f936a929
Create Date: 2026-01-08 10:58:41.379306

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "8003242e9a74"
down_revision: Union[str, Sequence[str], None] = "6753f936a929"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "detections",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key, UUID auto-generated (gen_random_uuid())",
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            nullable=False,
            comment="Foreign key to users.id",
        ),
        sa.Column(
            "camera_id",
            UUID(as_uuid=True),
            nullable=False,
            comment="Target camera ID (cameras.id)",
        ),
        sa.Column(
            "confidence",
            sa.FLOAT,
            nullable=False,
            comment="Face recognition confidence score",
        ),
        sa.Column(
            "image_url", sa.TEXT, nullable=False, comment="Image URL at detection time"
        ),
        sa.Column(
            "detected_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Detection timestamp (DEFAULT CURRENT_TIMESTAMP)",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_detections_detected_at", "detections", ["detected_at"])
    op.create_index("idx_detections_user_id", "detections", ["user_id"])
    op.create_index("idx_detections_camera_id", "detections", ["camera_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_detections_camera_id", table_name="detections")
    op.drop_index("idx_detections_user_id", table_name="detections")
    op.drop_index("idx_detections_detected_at", table_name="detections")
    op.drop_table("detections")
