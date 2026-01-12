"""create users table

Revision ID: c04246f39bdb
Revises:
Create Date: 2026-01-08 10:57:53.041948

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "c04246f39bdb"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable uuid-ossp extension for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="User ID",
        ),
        sa.Column("name", sa.VARCHAR(100), nullable=False, comment="Name"),
        sa.Column("email", sa.VARCHAR(255), nullable=False, comment="Email address"),
        sa.Column(
            "password",
            sa.VARCHAR(255),
            nullable=False,
            comment="Hashed password",
        ),
        sa.Column("phone", sa.VARCHAR(20), nullable=True, comment="Phone number"),
        sa.Column(
            "line_user_id", sa.VARCHAR(100), nullable=True, comment="LINE user ID"
        ),
        sa.Column(
            "is_admin",
            sa.BOOLEAN,
            nullable=False,
            server_default="false",
            comment="Admin flag (default: FALSE)",
        ),
        sa.Column(
            "is_active",
            sa.BOOLEAN,
            nullable=False,
            server_default="true",
            comment="Active flag (default: TRUE)",
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
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_line_user_id", "users", ["line_user_id"])
    op.create_index("ix_users_phone", "users", ["phone"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_line_user_id", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")

    # Drop table
    op.drop_table("users")
