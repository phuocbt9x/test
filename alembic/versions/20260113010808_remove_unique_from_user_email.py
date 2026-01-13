"""remove unique constraint from user email

Revision ID: a1b2c3d4e5f6
Revises: dc2bf6ccfc1a
Create Date: 2026-01-13 01:08:08.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "dc2bf6ccfc1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unique constraint from users.email column."""
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=False)


def downgrade() -> None:
    """Restore unique constraint on users.email column."""
    op.drop_index("ix_users_email", table_name="users")

    # Remove duplicate emails before creating unique index
    # Keep only the first record (by created_at) for each email
    op.execute(
        sa.text("""
        DELETE FROM users
        WHERE id NOT IN (
            SELECT DISTINCT ON (email) id
            FROM users
            ORDER BY email, created_at ASC
        )
    """)
    )

    op.create_index("ix_users_email", "users", ["email"], unique=True)
