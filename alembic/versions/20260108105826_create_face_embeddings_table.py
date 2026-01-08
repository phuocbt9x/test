"""create face embeddings table

Revision ID: c48d8ff20675
Revises: fc294b392fc7
Create Date: 2026-01-08 10:58:26.861883

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "c48d8ff20675"
down_revision: Union[str, Sequence[str], None] = "fc294b392fc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "face_embeddings",
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
        sa.Column("name", sa.VARCHAR(100), nullable=False, comment="Name"),
        sa.Column(
            "embedding",
            Vector(512),
            nullable=False,
            comment="512-dimensional vector for face recognition (pgvector)",
        ),
        sa.Column(
            "image_url",
            sa.TEXT,
            nullable=False,
            comment="URL of original or cropped image",
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
    )

    # Create indexes
    op.create_index("ix_face_embeddings_deleted_at", "face_embeddings", ["deleted_at"])
    op.create_index("ix_face_embeddings_user_id", "face_embeddings", ["user_id"])

    # Create ivfflat index for vector similarity search
    op.execute("""
        CREATE INDEX idx_face_embeddings_embedding ON face_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_face_embeddings_user_id", table_name="face_embeddings")
    op.drop_index("ix_face_embeddings_deleted_at", table_name="face_embeddings")

    # Drop table
    op.drop_table("face_embeddings")
