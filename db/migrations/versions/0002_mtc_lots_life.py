"""MTC results, grade references, cert records, stock lots, life policies and alerts.

Revision ID: 0002_mtc_lots_life
Revises: 0001_initial_schema
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_mtc_lots_life"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Procurement lines
    op.create_table(
        "procurement_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=True),
        sa.Column("doc_line_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("doc_lines.id"), nullable=True),
        sa.Column("qty", sa.Numeric(14, 3), nullable=True),
        sa.Column("uom", sa.Text(), nullable=True),
        sa.Column("unit_price_inr", sa.Numeric(14, 2), nullable=True),
        sa.Column("vendor", sa.Text(), nullable=True),
        sa.Column("po_no", sa.Text(), nullable=True),
        sa.Column("grn_no", sa.Text(), nullable=True),
        sa.Column("received_on", sa.Date(), nullable=True),
    )

    # 2. Stock lots
    op.create_table(
        "stock_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=True),
        sa.Column(
            "procurement_line_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_lines.id"),
            nullable=True,
        ),
        sa.Column("plant", sa.Text(), nullable=True),
        sa.Column("qty_remaining", sa.Numeric(14, 3), nullable=True),
        sa.Column("batch_no", sa.Text(), nullable=True),
        sa.Column("mfg_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
    )
    op.create_index("ix_stock_lots_golden_id", "stock_lots", ["golden_id"])
    op.create_index("ix_stock_lots_batch_no", "stock_lots", ["batch_no"])

    # 3. Usage events
    op.create_table(
        "usage_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_lots.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
    )
    op.create_index("ix_usage_events_lot_id", "usage_events", ["lot_id"])

    # 4. Life policies
    op.create_table(
        "life_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_type", sa.Text(), sa.CheckConstraint("scope_type IN ('GOLDEN', 'CLASS')"), nullable=False),
        sa.Column("scope_value", sa.Text(), nullable=False),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column(
            "basis",
            sa.Text(),
            sa.CheckConstraint("basis IN ('SHELF_LIFE_DAYS', 'USAGE_COUNT', 'USAGE_HOURS')"),
            nullable=False,
        ),
        sa.Column("limit_value", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
    )

    # 5. Life alerts
    op.create_table(
        "life_alerts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_lots.id"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=True),
        sa.Column("risk", sa.Text(), nullable=True),
        sa.Column("projected_date", sa.Date(), nullable=True),
        sa.Column("recipient_role", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.Text(), unique=True, nullable=True),
        sa.Column(
            "state",
            sa.Text(),
            sa.CheckConstraint("state IN ('OPEN', 'ACKED', 'ESCALATED', 'CLOSED')"),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 6. Cert records
    op.create_table(
        "cert_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_lots.id"), nullable=True),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=True),
        sa.Column("cert_type", sa.Text(), nullable=False),
        sa.Column("cert_no", sa.Text(), nullable=True),
        sa.Column("issuer", sa.Text(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
    )

    # 7. Grade reference
    op.create_table(
        "grade_reference",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("grade", sa.Text(), nullable=False),
        sa.Column("product_form", sa.Text(), nullable=False),
        sa.Column("property", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), sa.CheckConstraint("kind IN ('CHEM', 'MECH')"), nullable=False),
        sa.Column("min_value", sa.Numeric(), nullable=True),
        sa.Column("max_value", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
        sa.UniqueConstraint("grade", "product_form", "property", name="uq_grade_reference_property"),
    )

    # 8. MTC results
    op.create_table(
        "mtc_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("cert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cert_records.id"), nullable=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_lots.id"), nullable=True),
        sa.Column("heat_no", sa.Text(), nullable=True),
        sa.Column("grade_claimed", sa.Text(), nullable=True),
        sa.Column("chemistry", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("mechanical", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("ce_iiw", sa.Numeric(5, 3), nullable=True),
        sa.Column("pren", sa.Numeric(5, 1), nullable=True),
        sa.Column("heat_treatment", sa.Text(), nullable=True),
        sa.Column("ndt", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("flags", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column(
            "conformance",
            sa.Text(),
            sa.CheckConstraint(
                "conformance IN ('CONFORMS', 'FAILS', 'INCOMPLETE', 'UNVERIFIED_REFERENCE', 'REQUIRES_REVIEW')"
            ),
            nullable=True,
        ),
        sa.Column("reference_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # 9. Enable Row-Level Security on tenant tables
    for tbl in ["procurement_lines", "stock_lots", "cert_records", "mtc_results"]:
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

    # usage_events and life_alerts isolate via stock_lots.org_id
    for child_tbl in ["usage_events", "life_alerts"]:
        op.execute(f"ALTER TABLE {child_tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies WHERE tablename = '{child_tbl}' AND policyname = '{child_tbl}_tenant_isolation'
                ) THEN
                    CREATE POLICY {child_tbl}_tenant_isolation ON {child_tbl}
                        USING (EXISTS (
                            SELECT 1 FROM stock_lots sl
                            WHERE sl.id = {child_tbl}.lot_id AND sl.org_id = current_setting('app.current_org', true)
                        ))
                        WITH CHECK (EXISTS (
                            SELECT 1 FROM stock_lots sl
                            WHERE sl.id = {child_tbl}.lot_id AND sl.org_id = current_setting('app.current_org', true)
                        ));
                END IF;
            END $$;
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mtc_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS grade_reference CASCADE;")
    op.execute("DROP TABLE IF EXISTS cert_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS life_alerts CASCADE;")
    op.execute("DROP TABLE IF EXISTS life_policies CASCADE;")
    op.execute("DROP TABLE IF EXISTS usage_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS stock_lots CASCADE;")
    op.execute("DROP TABLE IF EXISTS procurement_lines CASCADE;")
