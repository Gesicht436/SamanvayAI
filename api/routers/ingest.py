"""Endpoints for Text Normalization, UoM Conversion, and Document Ingestion."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.ingest import ingest_tabular_document
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

    file_bytes = await file.read()
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
