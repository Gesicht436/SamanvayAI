"""Initial schema, extensions, audit log trigger, and Row-Level Security.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
    # Extension vector will be created if available in image
    op.execute("""
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector extension not installed in environment, skipping';
        END $$;
    """)

    # 2. Create core tables
    op.create_table(
        "organizations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("gstin", sa.Text(), nullable=True),
        sa.Column("headquarters", sa.Text(), nullable=True),
        sa.Column("segment", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("profile", postgresql.JSONB(), server_default="{}", nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("subject", sa.Text(), unique=True, nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("domains", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
    )

    op.create_table(
        "attribute_specs",
        sa.Column("subcategory", sa.Text(), nullable=False),
        sa.Column("attr", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("condition_expr", sa.Text(), nullable=True),
        sa.Column("order_def", postgresql.JSONB(), nullable=True),
        sa.Column("statutory", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("subcategory", "attr"),
    )

    op.create_table(
        "subcategory_specs",
        sa.Column("subcategory", sa.Text(), primary_key=True),
        sa.Column("segment", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("identity_mode", sa.Text(), server_default="PARAMETRIC", nullable=False),
        sa.Column("safety_critical", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("expiry_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("pooling_class", sa.Text(), nullable=True),
        sa.Column("depth", sa.Text(), nullable=True),
    )

    op.create_table(
        "golden_masters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.Text(), unique=True, nullable=False),
        sa.Column("descriptor", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="DRAFT", nullable=False),
        sa.Column("merged_into", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=True),
        sa.Column("major_category", sa.Text(), nullable=False),
        sa.Column("subcategory", sa.Text(), nullable=False),
        sa.Column("block_key", sa.Text(), nullable=False),
        sa.Column("identity_mode", sa.Text(), server_default="PARAMETRIC", nullable=False),
        sa.Column("segment", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("attributes", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_proprietary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("oem_name_norm", sa.Text(), nullable=True),
        sa.Column("oem_part_number_norm", sa.Text(), nullable=True),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("canonical_uom", sa.Text(), nullable=False),
        sa.Column("unspsc_code", sa.Text(), nullable=True),
        sa.Column("gem_category_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_golden_masters_block_key", "golden_masters", ["block_key"])

    op.create_table(
        "golden_aliases",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=False),
        sa.Column("alias_type", sa.Text(), nullable=False),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("value_raw", sa.Text(), nullable=False),
        sa.Column("value_norm", sa.Text(), nullable=False),
        sa.UniqueConstraint("alias_type", "org_id", "value_norm", name="uq_golden_alias"),
    )

    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name_norm", sa.Text(), unique=True, nullable=False),
        sa.Column("names_seen", postgresql.ARRAY(sa.Text()), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("capture_channel", sa.Text(), server_default="UPLOAD", nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("vendor_gstin", sa.Text(), nullable=True),
        sa.Column("invoice_no", sa.Text(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("invoice_key", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="UPLOADED", nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "file_hash", name="uq_document_org_hash"),
    )
    op.create_index("ix_documents_invoice_key", "documents", ["invoice_key"])

    op.create_table(
        "doc_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("ocr_engine", sa.Text(), nullable=True),
        sa.Column("raster_dpi", sa.Integer(), nullable=True),
        sa.Column("ocr_conf", sa.Numeric(4, 3), nullable=True),
        sa.Column("fields", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("raw_item_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_table(
        "raw_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Text(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("source_type", sa.Text(), server_default="LEGACY_MASTER", nullable=False),
        sa.Column("doc_line_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("doc_lines.id"), nullable=True),
        sa.Column("ocr_conf", sa.Numeric(4, 3), nullable=True),
        sa.Column("source_file_hash", sa.Text(), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("item_code", sa.Text(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("clean_text", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("original_uom", sa.Text(), nullable=True),
        sa.Column("original_qty", sa.Numeric(14, 3), nullable=True),
        sa.Column("canonical_uom", sa.Text(), nullable=True),
        sa.Column("canonical_qty", sa.Numeric(14, 3), nullable=True),
        sa.Column("unit_price_inr", sa.Numeric(14, 2), nullable=True),
        sa.Column("plant", sa.Text(), nullable=True),
        sa.Column("last_movement_date", sa.Date(), nullable=True),
        sa.Column("criticality", sa.Text(), nullable=True),
        sa.Column("min_stock", sa.Numeric(), nullable=True),
        sa.Column("max_stock", sa.Numeric(), nullable=True),
        sa.Column("item_condition", sa.Text(), server_default="NEW_UNUSED", nullable=False),
        sa.Column("has_mtc", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("subcategory", sa.Text(), nullable=True),
        sa.Column("block_key", sa.Text(), nullable=True),
        sa.Column("extracted", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("extraction_flags", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), nullable=True),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("match_prob", sa.Numeric(5, 4), nullable=True),
        sa.Column("status", sa.Text(), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "item_code", "source_file_hash", name="uq_raw_item_source"),
    )
    op.create_index("ix_raw_items_block_key", "raw_items", ["block_key"])
    op.create_index("ix_raw_items_golden_id", "raw_items", ["golden_id"])

    op.create_table(
        "match_candidates",
        sa.Column("raw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("raw_items.id"), primary_key=True),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("golden_masters.id"), primary_key=True),
        sa.Column("verdicts", postgresql.JSONB(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("prob", sa.Numeric(5, 4), nullable=True),
        sa.Column("tier", sa.Integer(), nullable=True),
    )

    op.create_table(
        "steward_tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("raw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("raw_items.id"), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("reason_codes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("maker", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("checker", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("state", sa.Text(), server_default="OPEN", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("checker IS NULL OR maker <> checker", name="chk_maker_ne_checker"),
    )

    op.create_table(
        "feedback_examples",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("raw_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.Boolean(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=True),
        sa.Column("steward", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.Text(), server_default="QUEUED", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "audit_log",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("this_hash", sa.Text(), nullable=False),
    )

    # 3. Append-only trigger for audit_log with advisory lock
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_audit_log_hash_chain()
        RETURNS TRIGGER AS $$
        DECLARE
            v_last_hash TEXT;
            v_prev_hash TEXT;
            v_payload TEXT;
        BEGIN
            -- Take transaction advisory lock for absolute linear sequencing
            PERFORM pg_advisory_xact_lock(727001);

            SELECT this_hash INTO v_last_hash FROM audit_log ORDER BY seq DESC LIMIT 1;
            IF v_last_hash IS NULL THEN
                v_prev_hash := repeat('0', 64);
            ELSE
                v_prev_hash := v_last_hash;
            END IF;

            NEW.prev_hash := v_prev_hash;
            v_payload := v_prev_hash || concat_ws('|',
                to_char(COALESCE(NEW.at, now()) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
                COALESCE(NEW.actor::text, ''),
                NEW.action,
                NEW.entity,
                NEW.entity_id,
                COALESCE(NEW.before::text, ''),
                COALESCE(NEW.after::text, ''),
                COALESCE(NEW.rationale, '')
            );
            NEW.this_hash := encode(digest(v_payload, 'sha256'), 'hex');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_log_before_insert_trigger
        BEFORE INSERT ON audit_log
        FOR EACH ROW
        EXECUTE FUNCTION trg_audit_log_hash_chain();

        CREATE OR REPLACE FUNCTION trg_audit_log_block_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit log is strictly append-only. UPDATE, DELETE, and TRUNCATE are prohibited.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_log_block_mutation_trigger
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW
        EXECUTE FUNCTION trg_audit_log_block_mutation();
    """)

    # 4. Enable Row-Level Security on tenant tables
    for tbl in ["documents", "raw_items"]:
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

    # doc_lines links to documents(id)
    op.execute("ALTER TABLE doc_lines ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies WHERE tablename = 'doc_lines' AND policyname = 'doc_lines_tenant_isolation'
            ) THEN
                CREATE POLICY doc_lines_tenant_isolation ON doc_lines
                    USING (EXISTS (
                        SELECT 1 FROM documents d
                        WHERE d.id = doc_lines.document_id AND d.org_id = current_setting('app.current_org', true)
                    ))
                    WITH CHECK (EXISTS (
                        SELECT 1 FROM documents d
                        WHERE d.id = doc_lines.document_id AND d.org_id = current_setting('app.current_org', true)
                    ));
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS feedback_examples CASCADE;")
    op.execute("DROP TABLE IF EXISTS steward_tasks CASCADE;")
    op.execute("DROP TABLE IF EXISTS match_candidates CASCADE;")
    op.execute("DROP TABLE IF EXISTS raw_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS doc_lines CASCADE;")
    op.execute("DROP TABLE IF EXISTS documents CASCADE;")
    op.execute("DROP TABLE IF EXISTS manufacturers CASCADE;")
    op.execute("DROP TABLE IF EXISTS golden_aliases CASCADE;")
    op.execute("DROP TABLE IF EXISTS golden_masters CASCADE;")
    op.execute("DROP TABLE IF EXISTS subcategory_specs CASCADE;")
    op.execute("DROP TABLE IF EXISTS attribute_specs CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TABLE IF EXISTS organizations CASCADE;")
