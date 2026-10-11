"""Procurement optimization, Stream A/B workflows, and spare locator tables.

Revision ID: 0004_procurement_and_transfers
Revises: 0003_oem_supersession
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_procurement_and_transfers"
down_revision: str | None = "0003_oem_supersession"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Forward Indents (Stream B capital demand pooling indents)
    op.create_table(
        "forward_indents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("uom", sa.Text(), nullable=False),
        sa.Column("budget_unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("need_by", sa.Date(), nullable=False),
        sa.Column("delivery_site", sa.Text(), nullable=True),
        sa.Column("plant", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="OPEN", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('OPEN', 'POOLED', 'ORDERED', 'CANCELLED')",
            name="chk_forward_indents_status",
        ),
    )
    op.create_index("ix_forward_indents_org_id", "forward_indents", ["org_id"])
    op.create_index("ix_forward_indents_golden_id", "forward_indents", ["golden_id"])
    op.create_index("ix_forward_indents_status", "forward_indents", ["status"])

    # 2. Tender Pools (Joint CPSE forward procurement demand pools)
    op.create_table(
        "tender_pools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_org", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=False),
        sa.Column("status", sa.Text(), server_default="DRAFT", nullable=False),
        sa.Column("mou_ref", sa.Text(), nullable=True),
        sa.Column("total_qty", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("canonical_uom", sa.Text(), nullable=True),
        sa.Column("estimated_baseline_cost", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("estimated_pooled_cost", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("estimated_savings", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'POOLED', 'TENDERED', 'AWARDED', 'CANCELLED')",
            name="chk_tender_pools_status",
        ),
    )
    op.create_index("ix_tender_pools_lead_org", "tender_pools", ["lead_org"])
    op.create_index("ix_tender_pools_golden_id", "tender_pools", ["golden_id"])
    op.create_index("ix_tender_pools_status", "tender_pools", ["status"])

    # 3. Tender Pool Lines (Association between pools and indents)
    op.create_table(
        "tender_pool_lines",
        sa.Column("pool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tender_pools.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("indent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("forward_indents.id", ondelete="CASCADE"), primary_key=True),
    )

    # 4. Transfer Orders (Stream A inter-CPSE surplus redeployment requisitions)
    op.create_table(
        "transfer_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("from_org", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("to_org", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("from_plant", sa.Text(), nullable=True),
        sa.Column("to_plant", sa.Text(), nullable=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_lots.id"), nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("basis", sa.Text(), server_default="BOOK_VALUE", nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("avoided_purchase_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("transfer_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("net_benefit", sa.Numeric(14, 2), nullable=True),
        sa.Column("mtc_uploaded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("pmi_done", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("shelf_life_ok", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("state", sa.Text(), server_default="REQUESTED", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "basis IN ('BOOK_VALUE', 'LAST_PURCHASE_PRICE', 'AGREED')",
            name="chk_transfer_orders_basis",
        ),
        sa.CheckConstraint(
            "state IN ('DRAFT', 'REQUESTED', 'TECHNICAL_REVIEW', 'COMMERCIAL_REVIEW', 'APPROVED', 'REJECTED', 'DISPATCHED', 'COMPLETED')",
            name="chk_transfer_orders_state",
        ),
        sa.CheckConstraint(
            "reviewed_by IS NULL OR created_by <> reviewed_by",
            name="chk_transfer_maker_ne_checker",
        ),
        sa.CheckConstraint(
            "from_org <> to_org",
            name="chk_transfer_different_orgs",
        ),
    )
    op.create_index("ix_transfer_orders_from_org", "transfer_orders", ["from_org"])
    op.create_index("ix_transfer_orders_to_org", "transfer_orders", ["to_org"])
    op.create_index("ix_transfer_orders_lot_id", "transfer_orders", ["lot_id"])
    op.create_index("ix_transfer_orders_golden_id", "transfer_orders", ["golden_id"])
    op.create_index("ix_transfer_orders_state", "transfer_orders", ["state"])

    # 5. Row-Level Security Policies
    # forward_indents: org-isolated
    op.execute("ALTER TABLE forward_indents ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies WHERE tablename = 'forward_indents' AND policyname = 'forward_indents_tenant_isolation'
            ) THEN
                CREATE POLICY forward_indents_tenant_isolation ON forward_indents
                    USING (org_id = current_setting('app.current_org', true))
                    WITH CHECK (org_id = current_setting('app.current_org', true));
            END IF;
        END $$;
    """)

    # tender_pools: readable by participants or lead org
    op.execute("ALTER TABLE tender_pools ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies WHERE tablename = 'tender_pools' AND policyname = 'tender_pools_participant_isolation'
            ) THEN
                CREATE POLICY tender_pools_participant_isolation ON tender_pools
                    USING (
                        lead_org = current_setting('app.current_org', true)
                        OR EXISTS (
                            SELECT 1 FROM tender_pool_lines tpl
                            JOIN forward_indents fi ON fi.id = tpl.indent_id
                            WHERE tpl.pool_id = tender_pools.id AND fi.org_id = current_setting('app.current_org', true)
                        )
                    )
                    WITH CHECK (lead_org = current_setting('app.current_org', true));
            END IF;
        END $$;
    """)

    # transfer_orders: visible to from_org (owner/supplier) or to_org (requester)
    op.execute("ALTER TABLE transfer_orders ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies WHERE tablename = 'transfer_orders' AND policyname = 'transfer_orders_party_isolation'
            ) THEN
                CREATE POLICY transfer_orders_party_isolation ON transfer_orders
                    USING (
                        from_org = current_setting('app.current_org', true)
                        OR to_org = current_setting('app.current_org', true)
                    )
                    WITH CHECK (
                        from_org = current_setting('app.current_org', true)
                        OR to_org = current_setting('app.current_org', true)
                    );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS transfer_orders CASCADE;")
    op.execute("DROP TABLE IF EXISTS tender_pool_lines CASCADE;")
    op.execute("DROP TABLE IF EXISTS tender_pools CASCADE;")
    op.execute("DROP TABLE IF EXISTS forward_indents CASCADE;")
