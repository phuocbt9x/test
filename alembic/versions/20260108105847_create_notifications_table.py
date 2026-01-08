"""create notifications table

Revision ID: 2910f34053e7
Revises: 8003242e9a74
Create Date: 2026-01-08 10:58:47.473339

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "2910f34053e7"
down_revision: Union[str, Sequence[str], None] = "8003242e9a74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key, UUID auto-generated (gen_random_uuid())",
        ),
        sa.Column(
            "detection_id",
            UUID(as_uuid=True),
            nullable=False,
            comment="Source detection ID (detections.id)",
        ),
        sa.Column(
            "rule_id",
            UUID(as_uuid=True),
            nullable=False,
            comment="Triggered time rule ID (time_rules.id)",
        ),
        sa.Column(
            "line_user_id",
            sa.VARCHAR(100),
            nullable=True,
            comment="Target LINE user ID",
        ),
        sa.Column(
            "message", sa.TEXT, nullable=False, comment="Actual message content sent"
        ),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Notification sent timestamp (DEFAULT CURRENT_TIMESTAMP)",
        ),
        sa.ForeignKeyConstraint(
            ["detection_id"], ["detections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["rule_id"], ["time_rules.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_notifications_sent_at", "notifications", ["sent_at"])
    op.create_index("idx_notifications_detection_id", "notifications", ["detection_id"])
    op.create_index("idx_notifications_rule_id", "notifications", ["rule_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_notifications_rule_id", table_name="notifications")
    op.drop_index("idx_notifications_detection_id", table_name="notifications")
    op.drop_index("idx_notifications_sent_at", table_name="notifications")
    op.drop_table("notifications")
