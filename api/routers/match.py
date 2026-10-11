"""Match API Router.

Implements the end-to-end matching endpoint POST /match conforming to Section 15.1:
1. Normalizes raw description.
2. Classifies subcategory with confidence and flags.
3. Extracts physical attributes using the specification registry.
4. Generates candidates via CandidateRetrievalPipeline (alias, MPN, block key, fuzzy recall).
5. Compares candidates using the deterministic safety comparator.
6. Scores candidate pairs and computes calibrated probabilities.
7. Assigns authoritative tiers enforcing Invariants S1 to S15.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.extractors.registry import default_registry
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.candidates import RetrievedCandidate, retrieve_candidates_db
from api.services.classify import classify_subcategory
from api.services.comparator import compare_items
from api.services.normalize import normalize_text
from api.services.scoring import extract_match_features, score_candidate
from api.services.tiering import assign_tier

router = APIRouter(prefix="", tags=["Match Engine"])


# --- Schemas ---


class MatchRequest(BaseModel):
    description: str = Field(..., description="Raw material description string.")
    category_hint: str | None = Field(None, description="Optional category or subcategory hint.")
    top_k: int = Field(3, ge=1, le=200, description="Maximum candidate matches to return.")


class AttributeEvidence(BaseModel):
    value: Any
    confidence: float
    evidence: list[int] | None = None


class VerdictItem(BaseModel):
    attr: str
    role: str
    raw: Any
    golden: Any
    verdict: str


class CandidateMatch(BaseModel):
    golden_code: str
    descriptor: str
    tier: int
    prob: float
    reason_codes: list[str]
    verdicts: list[VerdictItem]
    attribute_gap_alert: str | None = None


class MatchResponse(BaseModel):
    clean_text: str
    subcategory: str
    category_confidence: float
    flags: list[str]
    extracted: dict[str, AttributeEvidence]
    candidates: list[CandidateMatch]


# --- Service Core Helper for Match Execution ---


async def execute_match_pipeline(
    description: str,
    category_hint: str | None = None,
    top_k: int = 3,
    db: AsyncSession | None = None,
    org_id: str | None = None,
    mock_candidates: list[RetrievedCandidate] | None = None,
) -> MatchResponse:
    """Executes the complete matching pipeline.

    Supports both database-backed candidate retrieval and in-memory mock candidates.
    """
    # 1. Normalize description
    norm_res = normalize_text(description, category=category_hint)
    clean_text = norm_res.clean_text
    flags = list(norm_res.flags)

    # 2. Classify subcategory
    class_res = classify_subcategory(clean_text, category_hint=category_hint)
    sub = class_res.subcategory or "COMMON.UNKNOWN"
    cat_conf = class_res.confidence
    if class_res.flags:
        flags.extend(class_res.flags)

    # 3. Extract physical attributes
    extracted_map = default_registry.extract_attributes(clean_text, sub)
    extracted_response: dict[str, AttributeEvidence] = {}
    extracted_flat: dict[str, Any] = {}
    min_conf = 1.0

    for attr_name, ev in extracted_map.items():
        if ev.value is not None:
            extracted_flat[attr_name] = ev.value
            ev_span = [ev.evidence_span[0], ev.evidence_span[1]] if ev.evidence_span else None
            extracted_response[attr_name] = AttributeEvidence(
                value=ev.value,
                confidence=round(ev.confidence, 3),
                evidence=ev_span,
            )
            min_conf = min(min_conf, ev.confidence)
        if ev.flags:
            flags.extend(ev.flags)

    # Remove flag duplicates
    flags = list(dict.fromkeys(flags))

    # 4. Retrieve candidates
    candidates: list[RetrievedCandidate] = []
    if mock_candidates is not None:
        candidates = mock_candidates[:top_k]
    elif db is not None:
        candidates = await retrieve_candidates_db(
            session=db,
            clean_text=clean_text,
            subcategory=sub,
            extracted_attrs=extracted_flat,
            top_k=top_k,
            org_id=org_id,
        )

    # 5, 6, 7. Compare, Score, and Tier each candidate
    candidate_matches: list[CandidateMatch] = []
    for cand in candidates:
        # Deterministic attribute comparison
        comparison = compare_items(
            req_attrs=extracted_flat,
            cand_attrs=cand.attributes,
            subcategory=sub,
        )

        # Extract features and calculate calibrated probability
        features = extract_match_features(
            raw_text=clean_text,
            candidate_text=cand.canonical_text,
            comparison=comparison,
            extraction_conf_min=min_conf,
            mpn_exact=cand.mpn_exact,
            alias_exact=cand.alias_exact,
        )
        scoring = score_candidate(features)

        # Authoritative tier decision enforcing Invariants S1 to S15
        spec = default_registry.get_spec(sub)
        identity_mode = spec.identity_mode if spec else cand.identity_mode

        tier_res = assign_tier(
            comparison=comparison,
            identity_mode=identity_mode,
            extraction_flags=flags,
            probability=scoring.prob,
            tau_auto=0.95,
            tau_review=0.70,
            is_partial_block=cand.is_partial_block,
            is_category_uncertain=("CATEGORY_UNCERTAIN" in flags),
            oem_pn_match=cand.mpn_exact,
        )

        # Build verdict items
        verdict_items = [
            VerdictItem(
                attr=v.attr,
                role=v.role.value if hasattr(v.role, "value") else str(v.role),
                raw=v.raw_val,
                golden=v.candidate_val,
                verdict=v.verdict.value,
            )
            for v in comparison.verdicts.values()
        ]

        candidate_matches.append(
            CandidateMatch(
                golden_code=cand.golden_code,
                descriptor=cand.descriptor,
                tier=tier_res.tier,
                prob=scoring.prob,
                reason_codes=tier_res.reason_codes,
                verdicts=verdict_items,
                attribute_gap_alert=tier_res.attribute_gap_alert,
            )
        )

    return MatchResponse(
        clean_text=clean_text,
        subcategory=sub,
        category_confidence=round(cat_conf, 3),
        flags=flags,
        extracted=extracted_response,
        candidates=candidate_matches,
    )


# --- API Endpoint ---


@router.post("/match", response_model=MatchResponse, summary="Match and harmonize material description")
async def match_material(
    payload: MatchRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """Matches a material description against golden masters.

    Authenticated endpoint extracting organisation identity from JWT.
    Enforces Safety Invariants S1 to S15:
    - Tier 1: Auto-harmonize (exact match on all HARD+REQUIRED, prob >= 0.95, no flags).
    - Tier 2: Review (missing attributes, low confidence, partial block).
    - Tier 3: Distinct (hard or required mismatch).
    """
    return await execute_match_pipeline(
        description=payload.description,
        category_hint=payload.category_hint,
        top_k=payload.top_k,
        db=db,
        org_id=current_user.org_id,
    )
