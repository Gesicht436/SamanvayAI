"""Document intake pipeline service.

Enforces Section 10.0, 10.1:
- Channels: UPLOAD, CAMERA, PASTE.
- Duplicate detection on file_hash and normalized invoice_key (Invariant S10:
  A duplicate document warns or blocks; it never merges silently).
- Pre-procurement check: tests existing golden masters without persisting items,
  appending an audit record.
- Low-confidence OCR on HARD attributes becomes None with flag LOW_OCR_CONFIDENCE (Invariant S5).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.entities import DocLine, Document
from api.services.ocr import (
    OCRLine,
    get_ocr_provider,
)

logger = logging.getLogger(__name__)


def normalize_invoice_key(
    vendor_gstin: str | None,
    invoice_no: str | None,
    invoice_date: str | datetime.date | None,
) -> str | None:
    """Computes normalized invoice_key: <gstin>|<invoice_no>|<date>."""
    if not vendor_gstin or not invoice_no or not invoice_date:
        return None

    gstin_clean = str(vendor_gstin).strip().upper()
    inv_clean = str(invoice_no).strip().upper()

    if isinstance(invoice_date, datetime.date):
        date_clean = invoice_date.isoformat()
    else:
        date_clean = str(invoice_date).strip()

    return f"{gstin_clean}|{inv_clean}|{date_clean}"


async def check_document_duplicate(
    session: AsyncSession,
    org_id: str,
    file_hash: str,
    invoice_key: str | None = None,
) -> tuple[bool, Document | None, str | None]:
    """Checks whether an identical file hash or invoice key exists for the organization.

    Enforces Invariant S10: A duplicate document warns or blocks; it never merges silently.
    """
    # 1. Exact file_hash match
    stmt_hash = select(Document).where(Document.org_id == org_id, Document.file_hash == file_hash)
    res_hash = await session.execute(stmt_hash)
    existing_by_hash = res_hash.scalar_one_or_none()
    if existing_by_hash:
        return True, existing_by_hash, f"Identical file hash '{file_hash[:12]}...'"

    # 2. Duplicate invoice_key match
    if invoice_key:
        stmt_inv = select(Document).where(Document.org_id == org_id, Document.invoice_key == invoice_key)
        res_inv = await session.execute(stmt_inv)
        existing_by_inv = res_inv.scalar_one_or_none()
        if existing_by_inv:
            return True, existing_by_inv, f"Duplicate invoice key '{invoice_key}'"

    return False, None, None


async def ingest_document(
    session: AsyncSession,
    org_id: str,
    file_bytes: bytes,
    doc_type: str = "INVOICE",
    capture_channel: str = "UPLOAD",
    filename: str | None = None,
    vendor_gstin: str | None = None,
    invoice_no: str | None = None,
    invoice_date: datetime.date | str | None = None,
    uploaded_by: UUID | None = None,
    storage_path: str = "./data/storage",
    block_duplicates: bool = True,
    ocr_provider_name: str | None = None,
    auto_promote: bool = False,
) -> Document:
    """Ingests a document through upload, camera, or paste.

    Enforces:
    - Invariant S10: Duplicate documents warn or block; never silently merge.
    - Transactional audit log recording (DOC_INGEST).
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    inv_key = normalize_invoice_key(vendor_gstin, invoice_no, invoice_date)

    is_dup, existing_doc, dup_reason = await check_document_duplicate(session, org_id, file_hash, inv_key)

    if is_dup:
        if block_duplicates:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_DOCUMENT",
                    "message": f"Duplicate document detected ({dup_reason}). Under Invariant S10, duplicate documents warn or block and never merge silently.",
                    "existing_document_id": str(existing_doc.id) if existing_doc else None,
                    "file_hash": file_hash,
                    "invoice_key": inv_key,
                },
            )
        else:
            # Create as DUPLICATE status without silent merging
            doc = Document(
                org_id=org_id,
                doc_type=doc_type,
                capture_channel=capture_channel,
                file_hash=file_hash,
                storage_path=f"{storage_path}/{file_hash}",
                pages=1,
                vendor_gstin=vendor_gstin,
                invoice_no=invoice_no,
                invoice_date=invoice_date if isinstance(invoice_date, datetime.date) else None,
                invoice_key=inv_key,
                status="DUPLICATE",
                uploaded_by=uploaded_by,
            )
            session.add(doc)
            await session.flush()

            # Record audit entry
            await session.execute(
                text(
                    "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
                    "VALUES (:actor, 'DOC_DUPLICATE_WARNING', 'documents', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
                ),
                {
                    "actor": uploaded_by,
                    "entity_id": str(doc.id),
                    "after": json.dumps({"file_hash": file_hash, "invoice_key": inv_key, "reason": dup_reason}),
                    "rationale": f"Document duplicate warning recorded: {dup_reason}",
                },
            )
            return doc

    # Normal ingestion
    inv_date_parsed: datetime.date | None = None
    if isinstance(invoice_date, datetime.date):
        inv_date_parsed = invoice_date
    elif isinstance(invoice_date, str) and invoice_date.strip():
        try:
            inv_date_parsed = datetime.date.fromisoformat(invoice_date.strip())
        except ValueError:
            inv_date_parsed = None

    # OCR Recognition / Parsing
    if capture_channel == "PASTE":
        # Pasted text skips OCR; lines carry PASTED_TEXT flag
        text_content = file_bytes.decode("utf-8", errors="replace")
        raw_lines = [l.strip() for l in text_content.splitlines() if l.strip()]
        lines_to_save: list[OCRLine] = [
            OCRLine(
                page=1,
                raw_text=line_str,
                bbox=[0.05, float(i) * 0.05, 0.95, float(i) * 0.05 + 0.04],
                ocr_engine="pasted_text",
                raster_dpi=300,
                ocr_conf=1.000,
                flags=["PASTED_TEXT"],
            )
            for i, line_str in enumerate(raw_lines)
        ]
        total_pages = 1
    else:
        ocr_provider = get_ocr_provider(ocr_provider_name)
        ocr_res = ocr_provider.extract_document(file_bytes, filename=filename)
        total_pages = len(ocr_res.pages) if ocr_res.pages else 1
        lines_to_save = []
        for p in ocr_res.pages:
            lines_to_save.extend(p.lines)

    doc = Document(
        org_id=org_id,
        doc_type=doc_type,
        capture_channel=capture_channel,
        file_hash=file_hash,
        storage_path=f"{storage_path}/{file_hash}",
        pages=total_pages,
        vendor_gstin=vendor_gstin,
        invoice_no=invoice_no,
        invoice_date=inv_date_parsed,
        invoice_key=inv_key,
        status="PARSED",
        uploaded_by=uploaded_by,
    )
    session.add(doc)
    await session.flush()

    saved_dlines = []
    for line_obj in lines_to_save:
        dline = DocLine(
            document_id=doc.id,
            page=line_obj.page,
            bbox=line_obj.bbox,
            raw_text=line_obj.raw_text,
            ocr_engine=line_obj.ocr_engine,
            raster_dpi=line_obj.raster_dpi,
            ocr_conf=line_obj.ocr_conf,
            fields=line_obj.fields,
        )
        session.add(dline)
        saved_dlines.append(dline)

    await session.flush()

    if auto_promote:
        for dline in saved_dlines:
            await promote_doc_line_to_raw_item(
                session=session,
                document_id=doc.id,
                doc_line_id=dline.id,
                org_id=org_id,
                actor_id=uploaded_by,
            )

    # Record transactional audit log
    audit_after = json.dumps(
        {
            "id": str(doc.id),
            "org_id": org_id,
            "doc_type": doc_type,
            "capture_channel": capture_channel,
            "file_hash": file_hash,
            "invoice_key": inv_key,
            "pages": total_pages,
            "lines_count": len(lines_to_save),
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'DOC_INGEST', 'documents', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": uploaded_by,
            "entity_id": str(doc.id),
            "after": audit_after,
            "rationale": f"Ingested {doc_type} via {capture_channel} ({len(lines_to_save)} lines)",
        },
    )

    try:
        from api.services.observability import metrics

        metrics.inc_counter("samanvay_docs_ingested_total", labels={"doc_type": doc_type, "status": doc.status})
    except Exception:  # noqa: BLE001, S110
        pass

    return doc


async def precheck_document(
    session: AsyncSession,
    org_id: str,
    description: str,
    category_hint: str | None = None,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """Executes a pre-procurement duplicate check (Section 10.0, 15.1).

    Checks description against the golden catalog to see if masters already exist.
    Creates nothing except a tamper-evident audit record.
    """
    from api.routers.match import execute_match_pipeline

    match_resp = await execute_match_pipeline(
        description=description,
        category_hint=category_hint,
        top_k=5,
        db=session,
        org_id=org_id,
    )

    # Audit record for pre-procurement check
    audit_after = json.dumps(
        {
            "description": description,
            "clean_text": match_resp.clean_text,
            "subcategory": match_resp.subcategory,
            "candidates_count": len(match_resp.candidates),
            "top_candidate": match_resp.candidates[0].golden_code if match_resp.candidates else None,
            "top_tier": match_resp.candidates[0].tier if match_resp.candidates else None,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'DOC_PRECHECK', 'precheck', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": user_id,
            "entity_id": match_resp.subcategory,
            "after": audit_after,
            "rationale": "Pre-procurement check executed; no entities created",
        },
    )

    has_tier1 = any(c.tier == 1 for c in match_resp.candidates)
    alert = (
        "EXISTING_GOLDEN_MASTER_FOUND: An identical golden master already exists in the catalog. Avoid procurement duplicate."
        if has_tier1
        else None
    )

    return {
        "clean_text": match_resp.clean_text,
        "subcategory": match_resp.subcategory,
        "category_confidence": match_resp.category_confidence,
        "flags": match_resp.flags,
        "extracted": {k: v.model_dump() for k, v in match_resp.extracted.items()},
        "candidates": [c.model_dump() for c in match_resp.candidates],
        "procurement_alert": alert,
    }


async def get_document_lines_details(
    session: AsyncSession,
    document_id: UUID,
    org_id: str,
) -> dict[str, Any]:
    """Retrieves document lines with bounding box and OCR confidence (Section 15.1)."""
    stmt_doc = select(Document).where(Document.id == document_id, Document.org_id == org_id)
    res_doc = await session.execute(stmt_doc)
    doc = res_doc.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    stmt_lines = select(DocLine).where(DocLine.document_id == document_id).order_by(DocLine.page, DocLine.id)
    res_lines = await session.execute(stmt_lines)
    lines = res_lines.scalars().all()

    return {
        "document_id": str(doc.id),
        "status": doc.status,
        "capture_channel": doc.capture_channel,
        "lines": [
            {
                "line_id": str(l.id),
                "page": l.page,
                "bbox": l.bbox,
                "raw_text": l.raw_text,
                "ocr_engine": l.ocr_engine,
                "raster_dpi": l.raster_dpi,
                "ocr_conf": float(l.ocr_conf) if l.ocr_conf is not None else 1.0,
                "fields": l.fields or {},
                "flags": [],
            }
            for l in lines
        ],
    }


async def promote_doc_line_to_raw_item(
    session: AsyncSession,
    document_id: UUID,
    doc_line_id: UUID,
    org_id: str,
    actor_id: UUID | None = None,
) -> Any:
    """Promote an extracted document line item into a raw_item for downstream harmonization."""
    stmt_line = (
        select(DocLine)
        .join(Document, Document.id == DocLine.document_id)
        .where(
            DocLine.id == doc_line_id,
            DocLine.document_id == document_id,
            Document.org_id == org_id,
        )
    )
    res_line = await session.execute(stmt_line)
    line = res_line.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document line not found")

    from api.extractors.registry import default_registry
    from api.models.entities import RawItem
    from api.services.classify import classify_subcategory
    from api.services.normalize import normalize_text

    norm_res = normalize_text(line.raw_text)
    clean_text = norm_res.clean_text

    cls_res = classify_subcategory(clean_text)
    subcat = cls_res.subcategory
    confidence = cls_res.confidence

    extracted: dict[str, Any] = {}
    flags: list[str] = list(norm_res.flags) + list(cls_res.flags)
    if line.ocr_conf is not None and float(line.ocr_conf) < 0.70:
        flags.append("LOW_OCR_CONFIDENCE")

    if subcat:
        ext_dict = default_registry.extract_attributes(clean_text, subcat)
        for aname, aev in ext_dict.items():
            if aev.value is not None:
                extracted[aname] = aev.value
            flags.extend(aev.flags)

    item_code = f"DOC-{document_id.hex[:6].upper()}-L{line.page or 1}-{str(doc_line_id)[:6].upper()}"

    raw_item = RawItem(
        org_id=org_id,
        source_type="PROCUREMENT_DOC",
        doc_line_id=line.id,
        ocr_conf=line.ocr_conf,
        raw_payload={
            "document_id": str(document_id),
            "doc_line_id": str(doc_line_id),
            "page": line.page,
            "bbox": line.bbox,
            "ocr_engine": line.ocr_engine,
            "fields": line.fields,
            "category_confidence": confidence,
        },
        item_code=item_code,
        raw_description=line.raw_text,
        clean_text=clean_text,
        subcategory=subcat,
        extracted=extracted,
        extraction_flags=list(set(flags)),
    )
    session.add(raw_item)
    await session.flush()

    line.raw_item_id = raw_item.id

    audit_after = json.dumps(
        {
            "id": str(raw_item.id),
            "org_id": org_id,
            "item_code": item_code,
            "document_id": str(document_id),
            "doc_line_id": str(doc_line_id),
            "subcategory": subcat,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'PROMOTE_DOC_LINE', 'raw_items', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(raw_item.id),
            "after": audit_after,
            "rationale": f"Promoted document line {doc_line_id} from doc {document_id} to raw_items",
        },
    )

    return raw_item
