"""Four domain subvectors for optional ML recall (Phase 12 Part 2).

Revision ID: 0005_subvectors_and_erp
Revises: 0004_procurement_and_transfers
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_subvectors_and_erp"
down_revision: str | None = "0004_procurement_and_transfers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Table golden_subvectors
    op.create_table(
        "golden_subvectors",
        sa.Column(
            "golden_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("golden_masters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("text_repr", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("golden_id", "domain", name="pk_golden_subvectors"),
        sa.CheckConstraint(
            "domain IN ('dim', 'met', 'pt', 'std')",
            name="chk_golden_subvectors_domain",
        ),
    )
    op.create_index("ix_golden_subvectors_golden_id", "golden_subvectors", ["golden_id"])

    # 2. Conditionally add pgvector embedding column and HNSW index per domain
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE golden_subvectors ADD COLUMN IF NOT EXISTS embedding vector(384);
                CREATE INDEX IF NOT EXISTS ix_golden_subvectors_dim ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'dim';
                CREATE INDEX IF NOT EXISTS ix_golden_subvectors_met ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'met';
                CREATE INDEX IF NOT EXISTS ix_golden_subvectors_pt ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'pt';
                CREATE INDEX IF NOT EXISTS ix_golden_subvectors_std ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'std';
            ELSE
                ALTER TABLE golden_subvectors ADD COLUMN IF NOT EXISTS embedding JSONB;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS golden_subvectors CASCADE;")
