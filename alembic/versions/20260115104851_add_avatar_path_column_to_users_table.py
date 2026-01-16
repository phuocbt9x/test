"""add avatar_path column to users table

Revision ID: 308b0359341c
Revises: a1b2c3d4e5f6
Create Date: 2026-01-15 10:48:51.291627

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "308b0359341c"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "avatar_path",
            sa.Text(),
            nullable=True,
            comment="URL of the user's avatar image",
        ),
    )
    op.alter_column("users", "password", nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "avatar_path")
    op.execute("UPDATE users SET password = '' WHERE password IS NULL")
    op.alter_column("users", "password", nullable=False)
