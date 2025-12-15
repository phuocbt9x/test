"""Create users and tokens tables

Revision ID: 001
Revises:
Create Date: 2025-12-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='User unique identifier'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='User email address (used for login)'),
        sa.Column('username', sa.String(length=50), nullable=False, comment='Unique username'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='Hashed password (bcrypt/argon2)'),
        sa.Column('full_name', sa.String(length=100), nullable=True, comment="User's full name"),
        sa.Column('phone', sa.String(length=20), nullable=True, comment='Phone number'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='Profile picture URL'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Account active status'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, comment='Email verification status'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, comment='Admin/superuser flag'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, comment='Number of failed login attempts'),
        sa.Column('locked_until', sa.DateTime(), nullable=True, comment='Account locked until this timestamp'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True, comment='Last successful login timestamp'),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True, comment='Last password change timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        comment='User accounts with authentication and profile information'
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'], unique=False)
    op.create_index('ix_users_username_active', 'users', ['username', 'is_active'], unique=False)

    # Create token_blacklist table
    op.create_table(
        'token_blacklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Blacklist entry unique identifier'),
        sa.Column('jti', sa.String(length=36), nullable=False, comment='JWT ID (unique token identifier)'),
        sa.Column('token_type', sa.String(length=20), nullable=False, comment='Token type: access or refresh'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='User who owned this token'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='Token expiration timestamp (for cleanup)'),
        sa.Column('revoked_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, comment='When the token was revoked'),
        sa.Column('revocation_reason', sa.String(length=50), nullable=True, comment='Reason for revocation: logout, password_change, admin, security'),
        sa.Column('token_signature', sa.String(length=100), nullable=True, comment='Last 8 chars of token for debugging (not full token!)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti', name='uq_token_blacklist_jti'),
        comment='Blacklisted JWT tokens for security and logout'
    )
    op.create_index('ix_token_blacklist_jti', 'token_blacklist', ['jti'], unique=True)
    op.create_index('ix_token_blacklist_user_id', 'token_blacklist', ['user_id'], unique=False)
    op.create_index('ix_token_blacklist_expires_at', 'token_blacklist', ['expires_at'], unique=False)
    op.create_index('ix_token_blacklist_jti_expires', 'token_blacklist', ['jti', 'expires_at'], unique=False)
    op.create_index('ix_token_blacklist_user_expires', 'token_blacklist', ['user_id', 'expires_at'], unique=False)

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Refresh token unique identifier'),
        sa.Column('jti', sa.String(length=36), nullable=False, comment='JWT ID from refresh token'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='User who owns this token'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='Token expiration timestamp'),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, comment='Token revocation status'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True, comment='When the token was revoked'),
        sa.Column('device_info', sa.String(length=255), nullable=True, comment='User agent or device information'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP address when token was created (IPv6 compatible)'),
        sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Token family ID for rotation tracking'),
        sa.Column('parent_jti', sa.String(length=36), nullable=True, comment='JTI of the token that was refreshed'),
        sa.Column('used_at', sa.DateTime(), nullable=True, comment='When the token was used for refresh'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti', name='uq_refresh_tokens_jti'),
        comment='Active refresh tokens for session management'
    )
    op.create_index('ix_refresh_tokens_jti', 'refresh_tokens', ['jti'], unique=True)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'], unique=False)
    op.create_index('ix_refresh_tokens_is_revoked', 'refresh_tokens', ['is_revoked'], unique=False)
    op.create_index('ix_refresh_tokens_family_id', 'refresh_tokens', ['family_id'], unique=False)
    op.create_index('ix_refresh_tokens_user_active', 'refresh_tokens', ['user_id', 'is_revoked', 'expires_at'], unique=False)
    op.create_index('ix_refresh_tokens_family', 'refresh_tokens', ['family_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('token_blacklist')
    op.drop_table('users')
