"""Integration tests for Ingest Service (CSV, XLSX, idempotency, audit trail)."""

import io

import openpyxl
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_async_engine
from api.services.ingest import (
    ingest_tabular_document,
    parse_tabular_bytes,
)


def create_sample_csv(salt: str = "") -> bytes:
    content = (
        f"Item Code,Description,UoM,Qty,Unit Price,Category\n"
        f"OIL-VALVE-{salt}01,वाल्व 2″ SS 304 GT #150,NOS,10,25000,VALVES\n"
        f"OIL-REBAR-{salt}02,TMT REBAR 12MM DIA,M,1000,65,REBAR\n"
        f"OIL-FAST-{salt}03,HEX BOLT STD M16X50,SET,50,150,FASTENERS\n"
        f"OIL-ERR-{salt}04,,NOS,5,100,MISC\n"
    )
    return content.encode("utf-8")


def create_sample_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master"
    ws.append(["Item Code", "Description", "UoM", "Qty", "Unit Price", "Category"])
    ws.append(["STEEL-BEAM-01", "ISMB 300 HEAVY BEAM", "M", 50, 4200, "SECTIONS"])
    ws.append(["STEEL-PIPE-02", "CS PIPE 4INCH SCH 40", "MTR", 200, 1500, "PIPES"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_csv_tabular_data():
    csv_bytes = create_sample_csv()
    parsed = parse_tabular_bytes(csv_bytes, "test_oil_master.csv")

    assert parsed.total_rows == 4
    assert parsed.valid_rows == 3  # 1 row has missing description
    assert parsed.error_rows == 1

    # Row 1: Hindi Valve
    r1 = parsed.rows[0]
    assert r1.item_code == "OIL-VALVE-01"
    assert "VALVE" in r1.clean_text
    assert "GATE" in r1.clean_text
    assert r1.canonical_uom == "EA"

    # Row 4: Missing description
    r4 = parsed.rows[3]
    assert "MISSING_DESCRIPTION" in r4.errors


def test_parse_xlsx_tabular_data():
    xlsx_bytes = create_sample_xlsx()
    parsed = parse_tabular_bytes(xlsx_bytes, "steel_master.xlsx")

    assert parsed.total_rows == 2
    assert parsed.valid_rows == 2
    assert parsed.error_rows == 0

    r1 = parsed.rows[0]
    assert r1.item_code == "STEEL-BEAM-01"
    assert r1.canonical_uom == "MT"  # ISMB 300 converted to MT


@pytest.mark.asyncio
async def test_database_ingest_idempotency_and_audit():
    import uuid

    engine = get_async_engine()
    salt = uuid.uuid4().hex[:8]
    csv_bytes = create_sample_csv(salt=salt)
    filename = f"batch_{salt}.csv"
    org_id = "OIL-1"

    async with AsyncSession(engine) as session:
        # 1. First Ingestion
        res1 = await session.run_sync(lambda _: None)  # sync hook if needed
        res1 = await ingest_tabular_document(
            db=session,
            org_id=org_id,
            file_bytes=csv_bytes,
            filename=filename,
            doc_type="LEGACY_MASTER",
        )
        await session.commit()

        assert res1.is_duplicate is False
        assert res1.inserted_rows == 4

        # Verify audit log wrote record for this document in exact same transaction
        audit_res = await session.execute(
            text("SELECT action, entity, entity_id, this_hash FROM audit_log WHERE entity_id = :doc_id"),
            {"doc_id": str(res1.document_id)},
        )
        audit_row = audit_res.fetchone()
        assert audit_row is not None
        assert audit_row.action == "INGEST_DOCUMENT"
        assert len(audit_row.this_hash) == 64

        # 2. Second Ingestion with IDENTICAL bytes (Idempotency Test)
        res2 = await ingest_tabular_document(
            db=session,
            org_id=org_id,
            file_bytes=csv_bytes,
            filename=filename,
            doc_type="LEGACY_MASTER",
        )
        await session.commit()

        assert res2.is_duplicate is True
        assert res2.document_id == res1.document_id
        assert res2.inserted_rows == 0
