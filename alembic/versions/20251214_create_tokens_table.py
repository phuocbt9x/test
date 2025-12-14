"""
Alembic migration for tokens table
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'tokens',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(64), nullable=False, index=True),
        sa.Column('jti', sa.String(128), nullable=False, unique=True, index=True),
        sa.Column('token_type', sa.String(16), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('token', sa.Text, nullable=False),
        sa.Column('revoked', sa.Boolean, nullable=False, default=False),
    )

def downgrade():
    op.drop_table('tokens')
