"""FastAPI router for deterministic attribute comparison and safety tiering."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.extractors.registry import IdentityMode, default_registry
from api.services.comparator import (
    ItemComparisonResult,
    Verdict,
    compare_items,
)
from api.services.drawing import is_drawing_revision_equivalent, normalize_drawing_key
from api.services.tiering import TieringResult, assign_tier

router = APIRouter(prefix="", tags=["Comparator & Tiering"])


class CompareRequest(BaseModel):
    """Payload to compare requirement attributes with candidate attributes."""

    subcategory: str
    requirement_attributes: dict[str, Any]
    candidate_attributes: dict[str, Any]


class AttributeVerdictResponse(BaseModel):
    """Verdict result for a single attribute."""

    attr: str
    role: str
    raw_val: Any
    candidate_val: Any
    verdict: Verdict
    notes: str | None = None


class CompareResponse(BaseModel):
    """Item comparison response."""

    subcategory: str
    verdicts: dict[str, AttributeVerdictResponse]
    has_hard_mismatch: bool
    has_required_mismatch: bool
    has_missing_hard: bool
    has_missing_required: bool
    has_upgrade: bool
    missing_hard_attributes: list[str]
    missing_required_attributes: list[str]
    attribute_gap_alert: str | None = None


class TierRequest(BaseModel):
    """Payload to evaluate tiering decision."""

    subcategory: str
    requirement_attributes: dict[str, Any]
    candidate_attributes: dict[str, Any]
    identity_mode: IdentityMode | None = None
    extraction_flags: list[str] = Field(default_factory=list)
    probability: float = 1.0
    tau_auto: float = 0.95
    tau_review: float = 0.70
    is_partial_block: bool = False
    is_category_uncertain: bool = False
    has_alias_conflict: bool = False
    oem_pn_match: bool = False
    drawing_keys_match: bool = False
    drawing_revisions_match: bool = False
    has_approved_revision_equivalence: bool = False
    statutory_missing: bool = False
    ocr_confidence_low: bool = False
    lot_expired: bool = False
    lot_unknown_expiry: bool = False
    lot_no_usage: bool = False
    is_duplicate_document: bool = False


@router.post("/compare", response_model=CompareResponse)
async def compare_materials_endpoint(payload: CompareRequest) -> CompareResponse:
    """Evaluates deterministic attribute-by-attribute comparison under subcategory spec."""
    spec = default_registry.get_spec(payload.subcategory)

    comp_res: ItemComparisonResult = compare_items(
        req_attrs=payload.requirement_attributes,
        cand_attrs=payload.candidate_attributes,
        subcategory=payload.subcategory,
        spec=spec,
    )

    serialized_verdicts: dict[str, AttributeVerdictResponse] = {}
    for k, v in comp_res.verdicts.items():
        serialized_verdicts[k] = AttributeVerdictResponse(
            attr=v.attr,
            role=v.role.value,
            raw_val=v.raw_val,
            candidate_val=v.candidate_val,
            verdict=v.verdict,
            notes=v.notes,
        )

    return CompareResponse(
        subcategory=comp_res.subcategory,
        verdicts=serialized_verdicts,
        has_hard_mismatch=comp_res.has_hard_mismatch,
        has_required_mismatch=comp_res.has_required_mismatch,
        has_missing_hard=comp_res.has_missing_hard,
        has_missing_required=comp_res.has_missing_required,
        has_upgrade=comp_res.has_upgrade,
        missing_hard_attributes=comp_res.missing_hard_attributes,
        missing_required_attributes=comp_res.missing_required_attributes,
        attribute_gap_alert=comp_res.attribute_gap_alert,
    )


@router.post("/tier", response_model=TieringResult)
async def evaluate_tier_endpoint(
    payload: TierRequest,
    db: AsyncSession = Depends(get_db),
) -> TieringResult:
    """Evaluates safety invariants and assigns harmonization tier (Tier 1, 2, or 3)."""
    spec = default_registry.get_spec(payload.subcategory)
    identity_mode = payload.identity_mode or (spec.identity_mode if spec else IdentityMode.PARAMETRIC)

    drawing_keys_match = payload.drawing_keys_match
    drawing_revisions_match = payload.drawing_revisions_match
    has_approved_revision_equivalence = payload.has_approved_revision_equivalence

    if identity_mode == IdentityMode.DRAWING:
        req_owner = payload.requirement_attributes.get("drawing_owner")
        cand_owner = payload.candidate_attributes.get("drawing_owner")
        req_dwg = payload.requirement_attributes.get("drawing_number") or payload.requirement_attributes.get("drawing_no")
        cand_dwg = payload.candidate_attributes.get("drawing_number") or payload.candidate_attributes.get("drawing_no")

        if req_owner and cand_owner and req_dwg and cand_dwg:
            k1 = normalize_drawing_key(req_owner, req_dwg)
            k2 = normalize_drawing_key(cand_owner, cand_dwg)
            drawing_keys_match = (k1 == k2)

            req_rev = payload.requirement_attributes.get("drawing_revision") or payload.requirement_attributes.get("revision")
            cand_rev = payload.candidate_attributes.get("drawing_revision") or payload.candidate_attributes.get("revision")
            if req_rev is not None and cand_rev is not None:
                drawing_revisions_match = (str(req_rev).strip().upper() == str(cand_rev).strip().upper())
                if drawing_keys_match and not drawing_revisions_match and not has_approved_revision_equivalence:
                    has_approved_revision_equivalence = await is_drawing_revision_equivalent(
                        db, k1[0], k1[1], str(req_rev), str(cand_rev)
                    )

    comp_res = compare_items(
        req_attrs=payload.requirement_attributes,
        cand_attrs=payload.candidate_attributes,
        subcategory=payload.subcategory,
        spec=spec,
    )

    decision = assign_tier(
        comparison=comp_res,
        identity_mode=identity_mode,
        extraction_flags=payload.extraction_flags,
        probability=payload.probability,
        tau_auto=payload.tau_auto,
        tau_review=payload.tau_review,
        is_partial_block=payload.is_partial_block,
        is_category_uncertain=payload.is_category_uncertain,
        has_alias_conflict=payload.has_alias_conflict,
        oem_pn_match=payload.oem_pn_match,
        drawing_keys_match=drawing_keys_match,
        drawing_revisions_match=drawing_revisions_match,
        has_approved_revision_equivalence=has_approved_revision_equivalence,
        statutory_missing=payload.statutory_missing,
        ocr_confidence_low=payload.ocr_confidence_low,
        lot_expired=payload.lot_expired,
        lot_unknown_expiry=payload.lot_unknown_expiry,
        lot_no_usage=payload.lot_no_usage,
        is_duplicate_document=payload.is_duplicate_document,
    )

    return decision

