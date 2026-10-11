"""Database integration tests: Audit Log Append-Only Triggers and Row-Level Security (RLS).
Runs against the PostgreSQL container using `uv run pytest tests/test_database_features.py`.
"""

import uuid

import pytest
from sqlalchemy import text

from api.database import SyncSessionLocal


@pytest.fixture
def db_session():
    """Yield a fresh session for each test function."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_audit_log_triggers_and_immutability(db_session):
    """Verify that audit log computes hash chain on insert and blocks updates/deletes."""
    # Fetch current head hash before insert
    last_head = db_session.execute(text("SELECT this_hash FROM audit_log ORDER BY seq DESC LIMIT 1;")).fetchone()
    expected_prev = last_head[0] if last_head else "0" * 64

    # 1. Insert first audit entry
    insert_sql = text("""
        INSERT INTO audit_log (action, entity, entity_id, rationale, prev_hash, this_hash)
        VALUES ('CREATE_MASTER', 'golden_masters', 'master-1', 'Initial master creation', '', '')
        RETURNING seq, prev_hash, this_hash;
    """)
    res1 = db_session.execute(insert_sql).fetchone()
    db_session.commit()

    seq1, prev_hash1, this_hash1 = res1
    assert prev_hash1 == expected_prev, f"Audit record prev_hash must link to head hash {expected_prev}"
    assert len(this_hash1) == 64, "Calculated this_hash must be a valid 64-character SHA-256 hex string"

    # 2. Insert second audit entry and verify chain linkage
    res2 = db_session.execute(insert_sql).fetchone()
    db_session.commit()
    seq2, prev_hash2, _this_hash2 = res2

    assert prev_hash2 == this_hash1, "Second record prev_hash must match first record this_hash"

    assert seq2 == seq1 + 1, "Sequence numbers must increment linearly"

    # 3. Verify UPDATE is blocked by trigger
    with pytest.raises(Exception) as exc_update:
        db_session.execute(text(f"UPDATE audit_log SET action = 'TAMPERED' WHERE seq = {seq1};"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_update.value).lower()

    # 4. Verify DELETE is blocked by trigger
    with pytest.raises(Exception) as exc_delete:
        db_session.execute(text(f"DELETE FROM audit_log WHERE seq = {seq1};"))
        db_session.commit()
    db_session.rollback()
    assert "strictly append-only" in str(exc_delete.value).lower()


def test_row_level_security_isolation(db_session):
    """Verify that tenant tables enforce RLS isolation across organizations (OIL-1 vs POWER-1)."""
    # Ensure organizations exist
    db_session.execute(
        text("""
        INSERT INTO organizations (id, name, segment, profile)
        VALUES ('TEST-OIL', 'Test Oil', '{}', '{}'), ('TEST-POWER', 'Test Power', '{}', '{}')
        ON CONFLICT (id) DO NOTHING;
    """)
    )
    db_session.commit()

    # Create and configure non-superuser role 'samanvay_app'
    db_session.execute(
        text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'samanvay_app') THEN
                CREATE ROLE samanvay_app WITH LOGIN NOSUPERUSER NOBYPASSRLS;
            END IF;
            GRANT USAGE, CREATE ON SCHEMA public TO samanvay_app;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO samanvay_app;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO samanvay_app;
        END $$;
    """)
    )
    db_session.commit()

    item_id_oil = str(uuid.uuid4())
    item_id_power = str(uuid.uuid4())

    # Insert items as samanvay_app with appropriate session org
    db_session.execute(text("SET ROLE samanvay_app;"))
    db_session.execute(text("SET search_path = public;"))
    db_session.execute(text("SET app.current_org = 'TEST-OIL';"))
    db_session.execute(
        text("""
        INSERT INTO raw_items (id, org_id, source_type, raw_payload, raw_description, status)
        VALUES (:id, 'TEST-OIL', 'LEGACY_MASTER', '{}', 'OIL VALVE 100NB', 'PENDING');
    """),
        {"id": item_id_oil},
    )
    db_session.commit()

    db_session.execute(text("SET ROLE samanvay_app;"))
    db_session.execute(text("SET search_path = public;"))
    db_session.execute(text("SET app.current_org = 'TEST-POWER';"))
    db_session.execute(
        text("""
        INSERT INTO raw_items (id, org_id, source_type, raw_payload, raw_description, status)
        VALUES (:id, 'TEST-POWER', 'LEGACY_MASTER', '{}', 'POWER TRANSFORMER 100KVA', 'PENDING');
    """),
        {"id": item_id_power},
    )
    db_session.commit()

    # Query as TEST-OIL: must see ONLY the oil item
    db_session.execute(text("SET ROLE samanvay_app;"))
    db_session.execute(text("SET search_path = public;"))
    db_session.execute(text("SET app.current_org = 'TEST-OIL';"))
    rows_oil = db_session.execute(
        text("SELECT id, org_id FROM raw_items WHERE id IN (:o, :p);"), {"o": item_id_oil, "p": item_id_power}
    ).fetchall()
    assert len(rows_oil) == 1
    assert rows_oil[0][1] == "TEST-OIL"

    # Query as TEST-POWER: must see ONLY the power item
    db_session.execute(text("SET ROLE samanvay_app;"))
    db_session.execute(text("SET search_path = public;"))
    db_session.execute(text("SET app.current_org = 'TEST-POWER';"))
    rows_power = db_session.execute(
        text("SELECT id, org_id FROM raw_items WHERE id IN (:o, :p);"), {"o": item_id_oil, "p": item_id_power}
    ).fetchall()
    assert len(rows_power) == 1
    assert rows_power[0][1] == "TEST-POWER"

    # Query with unset app.current_org: must see 0 rows (fail closed)
    db_session.execute(text("SET ROLE samanvay_app;"))
    db_session.execute(text("SET search_path = public;"))
    db_session.execute(text("RESET app.current_org;"))
    rows_empty = db_session.execute(
        text("SELECT id FROM raw_items WHERE id IN (:o, :p);"), {"o": item_id_oil, "p": item_id_power}
    ).fetchall()
    assert len(rows_empty) == 0, "Unset tenant context must return zero rows (fail closed)"

    # Reset role back to postgres
    db_session.execute(text("RESET ROLE;"))
    db_session.commit()
