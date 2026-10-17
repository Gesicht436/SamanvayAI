"""Endpoints for Text Normalization, UoM Conversion, and Document Ingestion."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_db
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.ingest import (
    enqueue_ingest_job,
    get_job_status,
    ingest_tabular_document,
    process_next_ingest_job,
)
from api.services.normalize import normalize_text
from api.services.uom import convert_to_canonical

router = APIRouter(prefix="", tags=["Normalization & Ingest"])


# --- Schemas ---


class NormalizeRequest(BaseModel):
    text: str = Field(..., description="Raw material description string.")
    category: str | None = Field(None, description="Optional candidate category/family.")


class NormalizeResponse(BaseModel):
    clean_text: str
    tokens: list[str]
    language: str
    flags: list[str]


class UomConvertRequest(BaseModel):
    qty: float = Field(..., description="Original quantity.")
    raw_uom: str = Field(..., description="Original unit of measure.")
    category: str | None = Field(None, description="Material family/category.")
    attributes: dict[str, Any] | None = Field(default_factory=dict, description="Attributes for physical conversion.")


class UomConvertResponse(BaseModel):
    original_qty: float
    original_uom: str
    standard_uom: str
    canonical_qty: float
    canonical_uom: str
    conversion_factor: float
    flags: list[str]
    conversion_note: str | None


class IngestUploadResponse(BaseModel):
    document_id: UUID
    file_hash: str
    status: str
    is_duplicate: bool
    total_rows: int
    inserted_rows: int
    error_rows: int
    message: str


class IngestJobEnqueueResponse(BaseModel):
    job_id: int
    status: str
    message: str


class IngestJobStatusResponse(BaseModel):
    job_id: int
    kind: str
    state: str
    attempts: int
    last_error: str | None = None
    result: dict[str, Any] | None = None


class IngestJobProcessResponse(BaseModel):
    processed: bool
    job: dict[str, Any] | None = None
    message: str | None = None


# --- Endpoints ---


@router.post("/normalize", response_model=NormalizeResponse)
async def normalize_description(payload: NormalizeRequest):
    """Normalize a material description, transliterating Indic terms and expanding category-gated abbreviations."""
    res = normalize_text(payload.text, category=payload.category)
    return NormalizeResponse(
        clean_text=res.clean_text,
        tokens=res.tokens,
        language=res.language,
        flags=res.flags,
    )


@router.post("/uom/convert", response_model=UomConvertResponse)
async def convert_uom(payload: UomConvertRequest):
    """Standardize and convert a quantity and unit of measure to its canonical base unit."""
    res = convert_to_canonical(
        qty=payload.qty,
        raw_uom=payload.raw_uom,
        category=payload.category,
        attributes=payload.attributes,
    )
    return UomConvertResponse(
        original_qty=res.original_qty,
        original_uom=res.original_uom,
        standard_uom=res.standard_uom,
        canonical_qty=res.canonical_qty,
        canonical_uom=res.canonical_uom,
        conversion_factor=res.conversion_factor,
        flags=res.flags,
        conversion_note=res.conversion_note,
    )


@router.post("/ingest/upload", response_model=IngestUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("LEGACY_MASTER"),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a legacy master CSV or XLSX file.

    Performs:
    1. Idempotency check on SHA-256 file hash.
    2. Column mapping and parsing.
    3. Row-level text normalization and canonical UoM conversion.
    4. Database persistence into documents and raw_items.
    5. Append-only transactional audit log record.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must belong to an organization to ingest documents.",
        )

    file_bytes = await file.read(get_settings().upload_max_mb * 1024 * 1024 + 1)
    if len(file_bytes) > get_settings().upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the configured size limit.")
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    res = await ingest_tabular_document(
        db=db,
        org_id=current_user.org_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload.csv",
        uploaded_by=current_user.user_id,
        doc_type=doc_type,
    )

    return IngestUploadResponse(
        document_id=res.document_id,
        file_hash=res.file_hash,
        status=res.status,
        is_duplicate=res.is_duplicate,
        total_rows=res.total_rows,
        inserted_rows=res.inserted_rows,
        error_rows=res.error_rows,
        message=res.message,
    )


@router.post("/ingest/jobs", response_model=IngestJobEnqueueResponse)
async def enqueue_job(
    file: UploadFile = File(...),
    doc_type: str = Form("LEGACY_MASTER"),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enqueues an asynchronous tabular ingestion job into the jobs table (Section 4.1)."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must belong to an organization to ingest documents.",
        )

    file_bytes = await file.read(get_settings().upload_max_mb * 1024 * 1024 + 1)
    if len(file_bytes) > get_settings().upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the configured size limit.")
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    job_id = await enqueue_ingest_job(
        db=db,
        org_id=current_user.org_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload.csv",
        uploaded_by=current_user.sub,
        doc_type=doc_type,
    )

    return IngestJobEnqueueResponse(
        job_id=job_id,
        status="QUEUED",
        message=f"Ingestion job {job_id} successfully queued for background processing.",
    )


@router.get("/ingest/jobs/{job_id}", response_model=IngestJobStatusResponse)
async def get_job(
    job_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the current state and result of a queued ingest job."""
    job_info = await get_job_status(db, job_id=job_id, org_id=current_user.org_id)
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    return IngestJobStatusResponse(**job_info)


@router.post("/ingest/jobs/process-next", response_model=IngestJobProcessResponse)
async def process_next_job(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dequeues and processes the next pending job using SELECT ... FOR UPDATE SKIP LOCKED (Section 4.1)."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Job processing requires ADMIN role.")
    result = await process_next_ingest_job(db, org_id=current_user.org_id)
    if not result:
        return IngestJobProcessResponse(
            processed=False,
            job=None,
            message="No queued jobs available to process.",
        )
    return IngestJobProcessResponse(
        processed=True,
        job=result,
        message=f"Job {result['job_id']} processed with state {result['state']}.",
    )

