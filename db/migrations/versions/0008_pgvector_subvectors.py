"""Add item_subvectors table and conditional pgvector support for neural recall.

Revision ID: 0008_pgvector_subvectors
Revises: 0007_drawing_revision_equiv
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_pgvector_subvectors"
down_revision: str | None = "0007_drawing_revision_equiv"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Table item_subvectors
    op.create_table(
        "item_subvectors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "raw_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("text_repr", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "domain IN ('dim', 'met', 'pt', 'std')",
            name="chk_item_subvectors_domain",
        ),
    )
    op.create_index("ix_item_subvectors_raw_item_id", "item_subvectors", ["raw_item_id"])

    # 2. Conditionally add pgvector embedding column and HNSW index per domain
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE item_subvectors ADD COLUMN IF NOT EXISTS embedding vector(384);
                CREATE INDEX IF NOT EXISTS ix_item_subvectors_dim ON item_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'dim';
                CREATE INDEX IF NOT EXISTS ix_item_subvectors_met ON item_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'met';
                CREATE INDEX IF NOT EXISTS ix_item_subvectors_pt ON item_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'pt';
                CREATE INDEX IF NOT EXISTS ix_item_subvectors_std ON item_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'std';
            ELSE
                ALTER TABLE item_subvectors ADD COLUMN IF NOT EXISTS embedding JSONB;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("item_subvectors")
