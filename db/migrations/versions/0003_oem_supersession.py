"""OEM part supersession and catalogue onboarding wizard tables.

Revision ID: 0003_oem_supersession
Revises: 0002_mtc_lots_life
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_oem_supersession"
down_revision: str | None = "0002_mtc_lots_life"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. OEM Part Supersession reference table (global)
    op.create_table(
        "oem_part_supersessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("manufacturer", sa.Text(), nullable=False),
        sa.Column("old_pn", sa.Text(), nullable=False),
        sa.Column("new_pn", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("manufacturer", "old_pn", name="uq_oem_supersession_mfr_old_pn"),
    )
    op.create_index("ix_oem_supersession_lookup", "oem_part_supersessions", ["manufacturer", "old_pn"])

    # 2. OEM Catalogue Onboard Batches (tenant-partitioned)
    op.create_table(
        "oem_catalogue_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("oem_name", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.Text(), server_default="UPLOADED", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_oem_batches_org_id", "oem_catalogue_batches", ["org_id"])

    # 3. OEM Proposals (tenant-partitioned)
    op.create_table(
        "oem_proposals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oem_catalogue_batches.id"), nullable=False),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("oem_name", sa.Text(), nullable=False),
        sa.Column("raw_part_number", sa.Text(), nullable=False),
        sa.Column("norm_part_number", sa.Text(), nullable=False),
        sa.Column("effective_part_number", sa.Text(), nullable=False),
        sa.Column("superseded_from", sa.Text(), nullable=True),
        sa.Column("drawing_no", sa.Text(), nullable=True),
        sa.Column("parent_equipment_model", sa.Text(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("subcategory", sa.Text(), nullable=True),
        sa.Column("evidence_spans", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.Text(), server_default="PROPOSED", nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=True),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("steward_tasks.id"), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_oem_proposals_batch_id", "oem_proposals", ["batch_id"])
    op.create_index("ix_oem_proposals_status", "oem_proposals", ["status"])

    # 4. Enable Row-Level Security on tenant tables
    for tbl in ["oem_catalogue_batches", "oem_proposals"]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies WHERE tablename = '{tbl}' AND policyname = '{tbl}_tenant_isolation'
                ) THEN
                    CREATE POLICY {tbl}_tenant_isolation ON {tbl}
                        USING (org_id = current_setting('app.current_org', true))
                        WITH CHECK (org_id = current_setting('app.current_org', true));
                END IF;
            END $$;
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS oem_proposals CASCADE;")
    op.execute("DROP TABLE IF EXISTS oem_catalogue_batches CASCADE;")
    op.execute("DROP TABLE IF EXISTS oem_part_supersessions CASCADE;")
