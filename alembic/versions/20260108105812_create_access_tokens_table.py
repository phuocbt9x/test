"""create access tokens table

Revision ID: 5c787c9952c4
Revises: c04246f39bdb
Create Date: 2026-01-08 10:58:12.489704

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "5c787c9952c4"
down_revision: Union[str, Sequence[str], None] = "c04246f39bdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "access_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Token ID",
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, comment="User ID"),
        sa.Column("jti", sa.VARCHAR(500), nullable=False, comment="JWT token ID"),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            comment="Expiration timestamp",
        ),
        sa.Column(
            "is_revoked",
            sa.BOOLEAN,
            nullable=False,
            server_default="false",
            comment="Revocation flag",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Record creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Record update timestamp",
        ),
        sa.Column(
            "revoked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Token revocation timestamp",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_access_tokens_jti", "access_tokens", ["jti"], unique=True)
    op.create_index("ix_access_tokens_expires_at", "access_tokens", ["expires_at"])
    op.create_index("ix_access_tokens_is_revoked", "access_tokens", ["is_revoked"])
    op.create_index("ix_access_tokens_user_id", "access_tokens", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_access_tokens_user_id", table_name="access_tokens")
    op.drop_index("ix_access_tokens_is_revoked", table_name="access_tokens")
    op.drop_index("ix_access_tokens_expires_at", table_name="access_tokens")
    op.drop_index("ix_access_tokens_jti", table_name="access_tokens")
    op.drop_table("access_tokens")
