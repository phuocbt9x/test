"""create time rules table

Revision ID: 6753f936a929
Revises: c48d8ff20675
Create Date: 2026-01-08 10:58:31.534489

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "6753f936a929"
down_revision: Union[str, Sequence[str], None] = "c48d8ff20675"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "time_rules",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key, UUID auto-generated (gen_random_uuid())",
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, comment="User ID"),
        sa.Column(
            "camera_id", UUID(as_uuid=True), nullable=False, comment="Target camera ID"
        ),
        sa.Column(
            "rule_type",
            sa.VARCHAR(50),
            nullable=False,
            comment="Rule type: work_in, work_out, intrusion, etc.",
        ),
        sa.Column(
            "rule_name",
            sa.VARCHAR(100),
            nullable=False,
            comment="Rule name displayed in UI",
        ),
        sa.Column("start_time", sa.TIME, nullable=False, comment="Rule start time"),
        sa.Column("end_time", sa.TIME, nullable=False, comment="Rule end time"),
        sa.Column(
            "weekdays",
            sa.INTEGER,
            nullable=False,
            comment="Weekdays bitmask (Monday=1 to Sunday=7)",
        ),
        sa.Column(
            "notify_on_match",
            sa.BOOLEAN,
            nullable=False,
            server_default="false",
            comment="Notify when condition matches (DEFAULT FALSE)",
        ),
        sa.Column(
            "notify_on_mismatch",
            sa.BOOLEAN,
            nullable=False,
            server_default="true",
            comment="Notify on out-of-hours detection (DEFAULT TRUE)",
        ),
        sa.Column(
            "notify_on_absence",
            sa.BOOLEAN,
            nullable=False,
            server_default="false",
            comment="Absence notification flag",
        ),
        sa.Column(
            "line_user_ids", sa.TEXT, nullable=True, comment="Array of LINE user IDs"
        ),
        sa.Column(
            "line_group_id",
            sa.VARCHAR(100),
            nullable=True,
            comment="Target LINE group ID",
        ),
        sa.Column(
            "message_template",
            sa.TEXT,
            nullable=True,
            comment="Message template format (e.g., [name] < [time] > [camera])",
        ),
        sa.Column(
            "is_active",
            sa.BOOLEAN,
            nullable=False,
            server_default="true",
            comment="Active flag",
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_time_rules_user_id", "time_rules", ["user_id"])
    op.create_index("ix_time_rules_camera_id", "time_rules", ["camera_id"])
    op.create_index("ix_time_rules_is_active", "time_rules", ["is_active"])
    op.create_index("ix_time_rules_rule_type", "time_rules", ["rule_type"])
    op.create_index("ix_time_rules_deleted_at", "time_rules", ["deleted_at"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_time_rules_deleted_at", table_name="time_rules")
    op.drop_index("ix_time_rules_rule_type", table_name="time_rules")
    op.drop_index("ix_time_rules_is_active", table_name="time_rules")
    op.drop_index("ix_time_rules_camera_id", table_name="time_rules")
    op.drop_index("ix_time_rules_user_id", table_name="time_rules")

    # Drop table
    op.drop_table("time_rules")
