"""FastAPI router for attribute extraction, specification catalog, and database sync."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.extractors.registry import SubcategorySpecDef, default_registry
from api.security.jwt_auth import AuthUser, require_role

router = APIRouter(prefix="/extract", tags=["extractors"])


class ExtractRequest(BaseModel):
    """Request payload for attribute extraction."""

    text: str
    subcategory: str


class ExtractedAttributeItem(BaseModel):
    """Serialized representation of an extracted attribute."""

    value: Any = None
    confidence: float = 0.0
    source: str = "rule"
    evidence_span: list[int] | None = None
    flags: list[str] = []
    is_valid: bool = False


class ExtractResponse(BaseModel):
    """Extraction response containing all subcategory attributes."""

    subcategory: str
    identity_mode: str
    attributes: dict[str, ExtractedAttributeItem]


class SpecSummaryItem(BaseModel):
    """Summary of a registered subcategory specification."""

    subcategory: str
    segment: list[str]
    identity_mode: str
    safety_critical: bool
    depth: str | None
    attribute_count: int


@router.post("", response_model=ExtractResponse)
async def extract_item_attributes(payload: ExtractRequest) -> ExtractResponse:
    """Extracts typed attributes from description text according to subcategory spec."""
    spec = default_registry.get_spec(payload.subcategory)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcategory '{payload.subcategory}' not found in registry.",
        )

    extractions = default_registry.extract_attributes(payload.text, payload.subcategory)
    serialized_attrs: dict[str, ExtractedAttributeItem] = {}

    for name, item in extractions.items():
        span_list = list(item.evidence_span) if item.evidence_span else None
        serialized_attrs[name] = ExtractedAttributeItem(
            value=item.value,
            confidence=item.confidence,
            source=item.source,
            evidence_span=span_list,
            flags=item.flags,
            is_valid=item.is_valid(),
        )

    return ExtractResponse(
        subcategory=payload.subcategory,
        identity_mode=spec.identity_mode.value,
        attributes=serialized_attrs,
    )


@router.get("/specs", response_model=list[SpecSummaryItem])
async def list_specifications() -> list[SpecSummaryItem]:
    """Lists all registered subcategory specifications across loaded sector packs."""
    items: list[SpecSummaryItem] = []
    for subcat in default_registry.list_subcategories():
        spec = default_registry.get_spec(subcat)
        if spec:
            items.append(
                SpecSummaryItem(
                    subcategory=spec.subcategory,
                    segment=spec.segment,
                    identity_mode=spec.identity_mode.value,
                    safety_critical=spec.safety_critical,
                    depth=spec.depth,
                    attribute_count=len(spec.attributes),
                )
            )
    return items


@router.get("/specs/{subcategory}", response_model=SubcategorySpecDef)
async def get_specification_detail(subcategory: str) -> SubcategorySpecDef:
    """Returns the complete attribute specification definition for a subcategory."""
    spec = default_registry.get_spec(subcategory)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcategory '{subcategory}' not found in registry.",
        )
    return spec


@router.post("/sync")
async def sync_specifications_to_db(
    current_user: AuthUser = Depends(require_role("MAKER")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Syncs in-memory sector pack specifications into PostgreSQL database tables.

    Requires authenticated steward/admin maker privileges.
    """
    sub_count, attr_count = await default_registry.sync_to_db(db)
    return {
        "status": "synchronized",
        "subcategories_synced": sub_count,
        "attributes_synced": attr_count,
        "synced_by": current_user.sub,
    }
