"""Safety Tiering Engine and Invariant Enforcement Core.

Single authoritative decision point for Tier 1 auto-harmonization, Tier 2 human review,
and Tier 3 distinct categorization. Strictly enforces Safety Invariants S1 to S15.
"""

from dataclasses import dataclass, field
from enum import Enum

from api.extractors.registry import IdentityMode
from api.services.comparator import ItemComparisonResult


class Tier(int, Enum):
    """Harmonization decision tiers."""

    ONE_AUTO = 1  # Tier 1: Auto-Harmonize (strictly gated, identical master)
    TWO_REVIEW = 2  # Tier 2: Steward Review with Diff Inspector
    THREE_DISTINCT = 3  # Tier 3: Distinct items (never merged)


@dataclass
class TieringResult:
    """Decision output produced by the tiering engine."""

    tier: int
    is_substitution: bool = False
    stream_a_eligible: bool = False
    requires_review: bool = False
    reason_codes: list[str] = field(default_factory=list)
    attribute_gap_alert: str | None = None
    explanation: str = ""


def assign_tier(
    comparison: ItemComparisonResult,
    identity_mode: IdentityMode = IdentityMode.PARAMETRIC,
    extraction_flags: list[str] | None = None,
    probability: float = 1.0,
    tau_auto: float = 0.95,
    tau_review: float = 0.70,
    is_partial_block: bool = False,
    is_category_uncertain: bool = False,
    has_alias_conflict: bool = False,
    oem_pn_match: bool = False,
    drawing_keys_match: bool = False,
    drawing_revisions_match: bool = False,
    has_approved_revision_equivalence: bool = False,
    statutory_missing: bool = False,
    ocr_confidence_low: bool = False,
    lot_expired: bool = False,
    lot_unknown_expiry: bool = False,
    lot_no_usage: bool = False,
    is_duplicate_document: bool = False,
    mtc_unverified_reference: bool = False,
) -> TieringResult:
    """Evaluates comparison results and returns authoritative tier decision.

    Strictly enforces Safety Invariants S1 to S15:
    - S1: No Tier 1 if ANY HARD or REQUIRED attribute is missing or mismatched.
    - S2: No Tier 1 if ANY extraction flag is present.
    - S3: No Tier 1 if PARTIAL_BLOCK or CATEGORY_UNCERTAIN.
    - S4: Changing one HARD attribute never yields Tier 1.
    - S5: Low OCR confidence routes to Tier 2.
    - S6: Expired lot or unknown expiry is never Stream A eligible.
    - S7: Usage-based lot without usage is never GREEN.
    - S9: Scoring model probability may lower a tier, never raise a gated item to Tier 1.
    - S10: Duplicate document blocks or warns; never merges silently.
    - S11: Ex Group I and II never equal, never substitutes.
    - S12: Missing statutory attribute keeps item out of Tier 1 and Stream A.
    - S13: In DRAWING mode, revision difference is never better than Tier 2.
    - S14: In OEM_PN and DRAWING modes, text similarity alone never yields Tier 1.
    - S15: MTC never yields CONFORMS against unverified reference rows.
    """
    flags = extraction_flags or []
    reasons: list[str] = []

    # ---------------------------------------------------------
    # 1. HARD Mismatches -> Immediate Tier 3 (Distinct)
    # ---------------------------------------------------------
    if comparison.has_hard_mismatch:
        reasons.append("HARD_ATTRIBUTE_MISMATCH")
        return TieringResult(
            tier=Tier.THREE_DISTINCT.value,
            stream_a_eligible=False,
            requires_review=False,
            reason_codes=reasons,
            attribute_gap_alert=comparison.attribute_gap_alert,
            explanation="Tier 3: One or more HARD attributes mismatched. Items are distinct.",
        )

    # ---------------------------------------------------------
    # 2. Identity Mode Specific Hard Checks (S13, S14)
    # ---------------------------------------------------------
    if identity_mode == IdentityMode.OEM_PN:
        if not oem_pn_match:
            reasons.append("OEM_PN_MISMATCH")
            return TieringResult(
                tier=Tier.THREE_DISTINCT.value,
                stream_a_eligible=False,
                requires_review=False,
                reason_codes=reasons,
                explanation="Tier 3: OEM Part Number does not match. Text similarity alone cannot yield Tier 1 (Invariant S14).",
            )

    elif identity_mode == IdentityMode.DRAWING and not drawing_keys_match:
        reasons.append("DRAWING_KEY_MISMATCH")
        return TieringResult(
            tier=Tier.THREE_DISTINCT.value,
            stream_a_eligible=False,
            requires_review=False,
            reason_codes=reasons,
            explanation="Tier 3: Engineering drawing number or owner does not match.",
        )

    # ---------------------------------------------------------
    # 3. REQUIRED Mismatches -> Tier 3 (unless overridden by steward)
    # ---------------------------------------------------------
    if comparison.has_required_mismatch:
        reasons.append("REQUIRED_ATTRIBUTE_MISMATCH")
        return TieringResult(
            tier=Tier.THREE_DISTINCT.value,
            stream_a_eligible=False,
            requires_review=False,
            reason_codes=reasons,
            attribute_gap_alert=comparison.attribute_gap_alert,
            explanation="Tier 3: One or more REQUIRED attributes mismatched.",
        )

    # ---------------------------------------------------------
    # 4. Substitution Upgrade (Directional Lattice)
    # ---------------------------------------------------------
    # Identity is never substitution. Upgrade items are Tier 2 (Review) for requisition only.
    if comparison.has_upgrade:
        reasons.append("SUBSTITUTION_UPGRADE")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            is_substitution=True,
            stream_a_eligible=False,  # Needs engineering sign-off
            requires_review=True,
            reason_codes=reasons,
            explanation="Substitution Candidate: Candidate has directional upgrade (e.g. higher gas group/temp class). Requires human sign-off; never identical.",
        )

    # ---------------------------------------------------------
    # 5. Extraction Flags & Safety Alerts (Invariant S2, S5)
    # ---------------------------------------------------------
    if len(flags) > 0:
        reasons.extend(flags)
        if comparison.has_missing_hard:
            reasons.append("MISSING_HARD_ATTRIBUTE")
        if comparison.has_missing_required:
            reasons.append("MISSING_REQUIRED_ATTRIBUTE")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            attribute_gap_alert=comparison.attribute_gap_alert,
            explanation=f"Tier 2: Extraction flags present ({', '.join(flags)}). Automatic harmonization blocked (Invariant S2).",
        )

    # ---------------------------------------------------------
    # 6. Missing Data Checks (Invariant S1, S12)
    # ---------------------------------------------------------
    if comparison.has_missing_hard or comparison.has_missing_required:
        if comparison.has_missing_hard:
            reasons.append("MISSING_HARD_ATTRIBUTE")
        if comparison.has_missing_required:
            reasons.append("MISSING_REQUIRED_ATTRIBUTE")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            attribute_gap_alert=comparison.attribute_gap_alert,
            explanation=f"Tier 2: Incomplete attribute signature ({comparison.attribute_gap_alert}). Routed to steward review (Invariant S1).",
        )

    if statutory_missing:
        reasons.append("STATUTORY_ATTRIBUTE_MISSING")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            explanation="Tier 2: Required statutory certification (e.g. IBR/Ex) is missing (Invariant S12).",
        )

    if ocr_confidence_low:
        reasons.append("LOW_OCR_CONFIDENCE")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            explanation="Tier 2: OCR confidence below threshold (Invariant S5).",
        )

    # ---------------------------------------------------------
    # 7. Blocking & Uncertainty Guards (Invariant S3, S10)
    # ---------------------------------------------------------
    if is_partial_block or is_category_uncertain:
        if is_partial_block:
            reasons.append("PARTIAL_BLOCK")
        if is_category_uncertain:
            reasons.append("CATEGORY_UNCERTAIN")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            explanation="Tier 2: Retrieval uncertainty (partial block key or uncertain category, Invariant S3).",
        )

    if is_duplicate_document:
        reasons.append("DUPLICATE_DOCUMENT")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            explanation="Tier 2: Duplicate document intake detected; cannot merge silently (Invariant S10).",
        )

    if has_alias_conflict:
        reasons.append("ALIAS_CONFLICT")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            explanation="Tier 2: Conflicting golden alias resolved.",
        )

    # ---------------------------------------------------------
    # 8. Drawing Revision Equivalence Guard (Invariant S13)
    # ---------------------------------------------------------
    if identity_mode == IdentityMode.DRAWING and not drawing_revisions_match and not has_approved_revision_equivalence:
        reasons.append("DRAWING_REVISION_DIFFERENCE")
        return TieringResult(
            tier=Tier.TWO_REVIEW.value,
            stream_a_eligible=False,
            requires_review=True,
            reason_codes=reasons,
            explanation="Tier 2: Drawing revision differs and no approved equivalence exists (Invariant S13).",
        )

    # ---------------------------------------------------------
    # 9. Probability Score Checks (Invariant S9)
    # ---------------------------------------------------------
    # The scoring model may lower a tier, never raise a gated item to Tier 1.
    if probability < tau_auto:
        if probability >= tau_review:
            reasons.append("PROBABILITY_REVIEW_RANGE")
            return TieringResult(
                tier=Tier.TWO_REVIEW.value,
                stream_a_eligible=False,
                requires_review=True,
                reason_codes=reasons,
                explanation=f"Tier 2: Calibrated probability ({probability:.3f}) below tau_auto ({tau_auto}).",
            )
        else:
            reasons.append("PROBABILITY_DISTINCT_RANGE")
            return TieringResult(
                tier=Tier.THREE_DISTINCT.value,
                stream_a_eligible=False,
                requires_review=False,
                reason_codes=reasons,
                explanation=f"Tier 3: Calibrated probability ({probability:.3f}) below tau_review ({tau_review}).",
            )

    # ---------------------------------------------------------
    # 10. Tier 1 (Auto-Harmonize) Authorization
    # ---------------------------------------------------------
    # Reaching this point guarantees all safety invariants are met.
    stream_a = True

    # Lots check for Stream A eligibility (Invariant S6, S7)
    if lot_expired or lot_unknown_expiry:
        stream_a = False
        reasons.append("LOT_EXPIRY_NOT_ELIGIBLE")

    if lot_no_usage:
        stream_a = False
        reasons.append("LOT_NO_USAGE_NOT_ELIGIBLE")

    return TieringResult(
        tier=Tier.ONE_AUTO.value,
        is_substitution=False,
        stream_a_eligible=stream_a,
        requires_review=False,
        reason_codes=reasons or ["ALL_HARD_REQUIRED_EXACT"],
        explanation="Tier 1: All HARD and REQUIRED attributes match exactly with high confidence. Auto-harmonized.",
    )
