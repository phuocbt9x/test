"""alter_datetime_columns_add_timezone

Revision ID: 22a4ebd31d7d
Revises: 001
Create Date: 2025-12-15 10:14:50.554105

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '22a4ebd31d7d'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add timezone to datetime columns."""
    # Users table
    op.execute("ALTER TABLE users ALTER COLUMN locked_until TYPE TIMESTAMP WITH TIME ZONE USING locked_until AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE users ALTER COLUMN last_login_at TYPE TIMESTAMP WITH TIME ZONE USING last_login_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE users ALTER COLUMN password_changed_at TYPE TIMESTAMP WITH TIME ZONE USING password_changed_at AT TIME ZONE 'UTC'")

    # TokenBlacklist table
    op.execute("ALTER TABLE token_blacklist ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE token_blacklist ALTER COLUMN revoked_at TYPE TIMESTAMP WITH TIME ZONE USING revoked_at AT TIME ZONE 'UTC'")

    # RefreshToken table
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN revoked_at TYPE TIMESTAMP WITH TIME ZONE USING revoked_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN used_at TYPE TIMESTAMP WITH TIME ZONE USING used_at AT TIME ZONE 'UTC'")


def downgrade() -> None:
    """Downgrade schema: Remove timezone from datetime columns."""
    # Users table
    op.execute("ALTER TABLE users ALTER COLUMN locked_until TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE users ALTER COLUMN last_login_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE users ALTER COLUMN password_changed_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # TokenBlacklist table
    op.execute("ALTER TABLE token_blacklist ALTER COLUMN expires_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE token_blacklist ALTER COLUMN revoked_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # RefreshToken table
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN expires_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN revoked_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN used_at TYPE TIMESTAMP WITHOUT TIME ZONE")
