"""Document intake and MTC evaluation API router.

Enforces Section 10.0, 10.1, 10.2, 15.1:
- POST /docs: Ingests documents via UPLOAD, CAMERA, or PASTE.
- GET /docs/{id}: Retrieves document metadata.
- GET /docs/{id}/lines: Returns extracted lines with bounding boxes and OCR confidence.
- POST /docs/precheck: Pre-procurement duplicate check without persisting items.
- POST /docs/{id}/mtc: Evaluates MTC chemistry and mechanical conformance (Invariant S15).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.entities import Document
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.docs import (
    get_document_lines_details,
    ingest_document,
    precheck_document,
)
from api.services.mtc import evaluate_mtc_conformance

router = APIRouter(prefix="/docs", tags=["Document Intake & MTC"])


# --- Schemas ---


class PrecheckRequest(BaseModel):
    description: str = Field(..., description="Draft material specification or requisition line.")
    category_hint: str | None = Field(None, description="Optional subcategory hint.")


class PrecheckResponse(BaseModel):
    clean_text: str
    subcategory: str
    category_confidence: float
    flags: list[str]
    extracted: dict[str, Any]
    candidates: list[dict[str, Any]]
    procurement_alert: str | None = None


class PasteDocRequest(BaseModel):
    pasted_text: str = Field(..., description="Raw pasted invoice or requisition text.")
    doc_type: str = Field("INVOICE", description="PO_GRN, INVOICE, MTC_CERTIFICATE, DATASHEET_LABEL")
    vendor_gstin: str | None = None
    invoice_no: str | None = None
    invoice_date: str | None = None


class DocumentResponse(BaseModel):
    id: str
    org_id: str
    doc_type: str
    capture_channel: str
    file_hash: str
    pages: int | None
    status: str
    vendor_gstin: str | None = None
    invoice_no: str | None = None
    invoice_date: str | None = None
    invoice_key: str | None = None


class DocLineItem(BaseModel):
    line_id: str
    page: int | None
    bbox: list[float] | None
    raw_text: str
    ocr_engine: str | None
    raster_dpi: int | None
    ocr_conf: float | None
    fields: dict[str, Any]
    flags: list[str] = []


class DocumentLinesResponse(BaseModel):
    document_id: str
    status: str
    capture_channel: str
    lines: list[DocLineItem]


class MtcEvaluationRequest(BaseModel):
    grade_claimed: str = Field(..., description="Claimed grade, e.g. A105, A216_WCB, A182_F316.")
    product_form: str = Field("FORGING", description="Product form, e.g. FORGING, CAST, PIPE.")
    heat_no: str | None = Field(None, description="Heat or melt batch number.")
    chemistry: dict[str, Any] = Field(default_factory=dict, description="Elemental chemistry map.")
    mechanical: dict[str, Any] = Field(default_factory=dict, description="Mechanical test results.")
    heat_treatment: str | None = Field(None, description="Heat treatment condition, e.g. NORMALIZED.")
    ndt: list[str] = Field(default_factory=list, description="NDT endorsements, e.g. ['UT', 'MPI'].")


class MtcEvaluationResponse(BaseModel):
    id: str
    document_id: str | None
    heat_no: str | None
    grade_claimed: str
    chemistry: dict[str, Any]
    mechanical: dict[str, Any]
    ce_iiw: float | None
    ce_label: str | None
    pren: float | None
    flags: list[str]
    heat_treatment: str | None
    ndt: list[str]
    conformance: str
    reference_verified: bool
    requires_review: bool
    lot_id: str | None
    lot_mtc_verified: bool
    property_verdicts: list[dict[str, Any]]


# --- Endpoints ---


def _parse_uuid(val: Any) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


@router.post("/precheck", response_model=PrecheckResponse)
async def run_precheck(
    req: PrecheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Pre-procurement duplicate check against golden masters (Section 10.0).

    Prevents duplicates at the start of the procurement cycle. Creates no entities
    except an audit trail entry.
    """
    res = await precheck_document(
        session=db,
        org_id=current_user.org_id,
        description=req.description,
        category_hint=req.category_hint,
        user_id=_parse_uuid(current_user.sub),
    )
    return PrecheckResponse(**res)


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile | None = File(None),
    doc_type: str = Form("INVOICE"),
    capture_channel: str = Form("UPLOAD"),
    vendor_gstin: str | None = Form(None),
    invoice_no: str | None = Form(None),
    invoice_date: str | None = Form(None),
    block_duplicates: bool = Form(True),
    auto_promote: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Uploads and ingests a document via UPLOAD or CAMERA channel.

    Enforces Invariant S10: duplicates warn or block; never silently merge.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File upload payload is required.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    doc = await ingest_document(
        session=db,
        org_id=current_user.org_id,
        file_bytes=file_bytes,
        doc_type=doc_type,
        capture_channel=capture_channel,
        filename=file.filename,
        vendor_gstin=vendor_gstin,
        invoice_no=str(invoice_no) if invoice_no else None,
        invoice_date=invoice_date,
        uploaded_by=_parse_uuid(current_user.sub),
        block_duplicates=block_duplicates,
        auto_promote=auto_promote,
    )

    return DocumentResponse(
        id=str(doc.id),
        org_id=doc.org_id,
        doc_type=doc.doc_type,
        capture_channel=doc.capture_channel,
        file_hash=doc.file_hash,
        pages=doc.pages,
        status=doc.status,
        vendor_gstin=doc.vendor_gstin,
        invoice_no=doc.invoice_no,
        invoice_date=doc.invoice_date.isoformat() if doc.invoice_date else None,
        invoice_key=doc.invoice_key,
    )


@router.post("/paste", response_model=DocumentResponse)
async def paste_document(
    req: PasteDocRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Ingests raw text via PASTE channel, skipping OCR (Section 10.1)."""
    file_bytes = req.pasted_text.encode("utf-8")
    doc = await ingest_document(
        session=db,
        org_id=current_user.org_id,
        file_bytes=file_bytes,
        doc_type=req.doc_type,
        capture_channel="PASTE",
        vendor_gstin=req.vendor_gstin,
        invoice_no=req.invoice_no,
        invoice_date=req.invoice_date,
        uploaded_by=_parse_uuid(current_user.sub),
        block_duplicates=True,
    )
    return DocumentResponse(
        id=str(doc.id),
        org_id=doc.org_id,
        doc_type=doc.doc_type,
        capture_channel=doc.capture_channel,
        file_hash=doc.file_hash,
        pages=doc.pages,
        status=doc.status,
        vendor_gstin=doc.vendor_gstin,
        invoice_no=doc.invoice_no,
        invoice_date=doc.invoice_date.isoformat() if doc.invoice_date else None,
        invoice_key=doc.invoice_key,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieves document metadata."""
    stmt = select(Document).where(Document.id == document_id, Document.org_id == current_user.org_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentResponse(
        id=str(doc.id),
        org_id=doc.org_id,
        doc_type=doc.doc_type,
        capture_channel=doc.capture_channel,
        file_hash=doc.file_hash,
        pages=doc.pages,
        status=doc.status,
        vendor_gstin=doc.vendor_gstin,
        invoice_no=doc.invoice_no,
        invoice_date=doc.invoice_date.isoformat() if doc.invoice_date else None,
        invoice_key=doc.invoice_key,
    )


@router.get("/{document_id}/lines", response_model=DocumentLinesResponse)
async def get_document_lines(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Returns extracted lines with bounding box and OCR confidence (Section 15.1)."""
    res = await get_document_lines_details(session=db, document_id=document_id, org_id=current_user.org_id)
    return DocumentLinesResponse(**res)


@router.post("/mtc/evaluate", response_model=MtcEvaluationResponse)
async def evaluate_standalone_mtc(
    req: MtcEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Parses and evaluates MTC chemistry without requiring an existing document ID (Section 10.2).

    Enforces Invariant S15:
    - Never yields CONFORMS against an unverified reference row.
    """
    eval_result = await evaluate_mtc_conformance(
        session=db,
        org_id=current_user.org_id,
        grade_claimed=req.grade_claimed,
        product_form=req.product_form,
        heat_no=req.heat_no,
        raw_chemistry=req.chemistry,
        raw_mechanical=req.mechanical,
        heat_treatment=req.heat_treatment,
        ndt=req.ndt,
        document_id=None,
        actor_id=_parse_uuid(current_user.sub),
    )
    return MtcEvaluationResponse(**eval_result)


@router.post("/{document_id}/mtc", response_model=MtcEvaluationResponse)
async def evaluate_mtc(
    document_id: UUID,
    req: MtcEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Parses MTC chemistry, mechanical properties, and evaluates conformance (Section 10.2).

    Enforces Invariant S15:
    - Never yields CONFORMS against an unverified reference row.
    - Lot marked MTC-verified only by CONFORMS plus a heat/batch number match.
    """
    stmt = select(Document).where(Document.id == document_id, Document.org_id == current_user.org_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chemistry = dict(req.chemistry) if req.chemistry else {}
    mechanical = dict(req.mechanical) if req.mechanical else {}
    grade_claimed = req.grade_claimed
    heat_no = req.heat_no

    # Automated OCR parser extraction if chemistry not provided directly
    if not chemistry:
        from api.models.entities import DocLine
        from api.services.mtc import parse_mtc_text_to_chemistry

        stmt_lines = select(DocLine).where(DocLine.document_id == document_id).order_by(DocLine.page, DocLine.id)
        res_lines = await db.execute(stmt_lines)
        doc_lines = res_lines.scalars().all()
        if doc_lines:
            combined_text = "\n".join(l.raw_text for l in doc_lines if l.raw_text)
            parsed_chem, parsed_mech, parsed_meta, _ = parse_mtc_text_to_chemistry(combined_text)
            if parsed_chem:
                chemistry = parsed_chem
            if parsed_mech and not mechanical:
                mechanical = parsed_mech
            if parsed_meta.get("heat_no") and not heat_no:
                heat_no = parsed_meta["heat_no"]
            if parsed_meta.get("grade") and not grade_claimed:
                grade_claimed = parsed_meta["grade"]

    eval_result = await evaluate_mtc_conformance(
        session=db,
        org_id=current_user.org_id,
        grade_claimed=grade_claimed,
        product_form=req.product_form,
        heat_no=heat_no,
        raw_chemistry=chemistry,
        raw_mechanical=mechanical,
        heat_treatment=req.heat_treatment,
        ndt=req.ndt,
        document_id=doc.id,
        actor_id=_parse_uuid(current_user.sub),
    )

    return MtcEvaluationResponse(**eval_result)


class PromoteLineResponse(BaseModel):
    raw_item_id: str
    item_code: str
    subcategory: str | None
    clean_text: str | None
    status: str = "PROMOTED"


class PromoteDocResponse(BaseModel):
    document_id: str
    promoted_count: int
    items: list[PromoteLineResponse]


@router.post("/{document_id}/lines/{line_id}/promote", response_model=PromoteLineResponse)
async def promote_document_line(
    document_id: UUID,
    line_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Promote an extracted document line item into a raw_item for matching."""
    from api.services.docs import promote_doc_line_to_raw_item

    raw_item = await promote_doc_line_to_raw_item(
        session=db,
        document_id=document_id,
        doc_line_id=line_id,
        org_id=current_user.org_id,
        actor_id=_parse_uuid(current_user.sub),
    )
    return PromoteLineResponse(
        raw_item_id=str(raw_item.id),
        item_code=raw_item.item_code or "",
        subcategory=raw_item.subcategory,
        clean_text=raw_item.clean_text,
        status="PROMOTED",
    )


@router.post("/{document_id}/promote", response_model=PromoteDocResponse)
async def promote_all_document_lines(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Promote all extracted lines of a document into raw_items."""
    from api.models.entities import DocLine
    from api.services.docs import promote_doc_line_to_raw_item

    stmt = select(DocLine).where(DocLine.document_id == document_id, DocLine.raw_item_id.is_(None))
    res = await db.execute(stmt)
    lines = res.scalars().all()

    promoted_items = []
    actor_id = _parse_uuid(current_user.sub)
    for l in lines:
        raw_item = await promote_doc_line_to_raw_item(
            session=db,
            document_id=document_id,
            doc_line_id=l.id,
            org_id=current_user.org_id,
            actor_id=actor_id,
        )
        promoted_items.append(
            PromoteLineResponse(
                raw_item_id=str(raw_item.id),
                item_code=raw_item.item_code or "",
                subcategory=raw_item.subcategory,
                clean_text=raw_item.clean_text,
                status="PROMOTED",
            )
        )

    return PromoteDocResponse(
        document_id=str(document_id),
        promoted_count=len(promoted_items),
        items=promoted_items,
    )

