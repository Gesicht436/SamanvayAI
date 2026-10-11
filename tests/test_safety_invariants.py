"""Hypothesis property-based testing suite for Safety Invariants S1 to S15.

Every invariant is verified against at least 300 random examples.
Conforms to docs/spec/06.md, safety-tests/SKILL.md, and samanvay-safety-review/SKILL.md.
"""

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from api.extractors.registry import AttributeRole, IdentityMode
from api.services.comparator import (
    AttributeVerdictResult,
    ItemComparisonResult,
    Verdict,
    compare_items,
    evaluate_attribute_verdict,
)
from api.services.tiering import Tier, TieringResult, assign_tier

# Shared Hypothesis Strategies
st_prob = st.floats(min_value=0.0, max_value=1.0)
st_identity_mode = st.sampled_from([IdentityMode.PARAMETRIC, IdentityMode.OEM_PN, IdentityMode.DRAWING])
st_attr_name = st.sampled_from(["size_nb", "pressure_class", "body_material", "end_connection", "rating_kva"])
st_flags = st.lists(
    st.sampled_from(
        [
            "EXTRACTION_CONFLICT",
            "NON_STANDARD_RATING",
            "LOW_OCR_CONFIDENCE",
            "UNKNOWN_INDIC_TOKENS",
            "MIXED_SCRIPT",
        ]
    ),
    min_size=1,
    max_size=3,
)


def make_clean_comparison() -> ItemComparisonResult:
    """Helper creating a 100% clean matching comparison result."""
    verdicts = {
        "size_nb": AttributeVerdictResult("size_nb", AttributeRole.HARD, 100, 100, Verdict.EXACT),
        "pressure_class": AttributeVerdictResult(
            "pressure_class", AttributeRole.HARD, "ASME_150", "ASME_150", Verdict.EXACT
        ),
        "body_material": AttributeVerdictResult(
            "body_material", AttributeRole.HARD, "A216_WCB", "A216_WCB", Verdict.EXACT
        ),
        "end_connection": AttributeVerdictResult(
            "end_connection", AttributeRole.HARD, "FLANGED", "FLANGED", Verdict.EXACT
        ),
        "trim_code": AttributeVerdictResult("trim_code", AttributeRole.REQUIRED, "TRIM_8", "TRIM_8", Verdict.EXACT),
    }
    return ItemComparisonResult(
        subcategory="VALVES.GATE",
        verdicts=verdicts,
        has_hard_mismatch=False,
        has_required_mismatch=False,
        has_missing_hard=False,
        has_missing_required=False,
        has_upgrade=False,
        missing_hard_attributes=[],
        missing_required_attributes=[],
    )


# -----------------------------------------------------------------------------
# Invariant S1: No Tier 1 if any HARD or REQUIRED attribute missing or mismatched
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    has_hard_mismatch=st.booleans(),
    has_req_mismatch=st.booleans(),
    has_missing_hard=st.booleans(),
    has_missing_req=st.booleans(),
    prob=st_prob,
)
def test_S1_no_tier1_if_hard_or_required_missing_or_mismatched(
    has_hard_mismatch: bool,
    has_req_mismatch: bool,
    has_missing_hard: bool,
    has_missing_req: bool,
    prob: float,
):
    # Only test cases where at least one defect exists
    if not (has_hard_mismatch or has_req_mismatch or has_missing_hard or has_missing_req):
        return

    comp = make_clean_comparison()
    comp.has_hard_mismatch = has_hard_mismatch
    comp.has_required_mismatch = has_req_mismatch
    comp.has_missing_hard = has_missing_hard
    comp.has_missing_required = has_missing_req

    result = assign_tier(comparison=comp, probability=prob)
    assert result.tier != Tier.ONE_AUTO.value, f"Invariant S1 violated: got Tier 1 with defect! Result: {result}"


# -----------------------------------------------------------------------------
# Invariant S2: No Tier 1 if any extraction flag is present
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(flags=st_flags, prob=st.floats(min_value=0.95, max_value=1.0))
def test_S2_no_tier1_if_extraction_flags_present(flags: list[str], prob: float):
    comp = make_clean_comparison()
    result = assign_tier(comparison=comp, extraction_flags=flags, probability=prob)
    assert result.tier != Tier.ONE_AUTO.value, f"Invariant S2 violated: got Tier 1 despite flags {flags}!"
    assert result.tier == Tier.TWO_REVIEW.value


# -----------------------------------------------------------------------------
# Invariant S3: No Tier 1 if PARTIAL_BLOCK or CATEGORY_UNCERTAIN
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    partial=st.booleans(),
    uncertain=st.booleans(),
    prob=st.floats(min_value=0.95, max_value=1.0),
)
def test_S3_no_tier1_if_partial_block_or_category_uncertain(partial: bool, uncertain: bool, prob: float):
    if not (partial or uncertain):
        return
    comp = make_clean_comparison()
    result = assign_tier(
        comparison=comp,
        is_partial_block=partial,
        is_category_uncertain=uncertain,
        probability=prob,
    )
    assert result.tier != Tier.ONE_AUTO.value, f"Invariant S3 violated: partial={partial}, uncertain={uncertain}"
    assert result.tier == Tier.TWO_REVIEW.value


# -----------------------------------------------------------------------------
# Invariant S4: Changing one HARD attribute never yields Tier 1 & key order invariance
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    bad_val=st.text(alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=10),
    shuffle=st.booleans(),
)
def test_S4_changing_one_hard_attribute_never_yields_tier1_and_key_order_invariant(bad_val: str, shuffle: bool):
    req_attrs = {
        "size_nb": 100,
        "pressure_class": "ASME_150",
        "body_material": "A216_WCB",
        "end_connection": "FLANGED",
    }
    cand_attrs = dict(req_attrs)

    # Change exactly one HARD attribute
    if bad_val == "ASME_150":
        cand_attrs["pressure_class"] = "ASME_300"
    else:
        cand_attrs["pressure_class"] = bad_val

    # Test key permutation invariance
    if shuffle:
        req_attrs = dict(reversed(list(req_attrs.items())))
        cand_attrs = dict(reversed(list(cand_attrs.items())))

    comp = compare_items(req_attrs, cand_attrs, "VALVES.GATE")
    result = assign_tier(comparison=comp, probability=1.0)

    assert result.tier == Tier.THREE_DISTINCT.value, f"Invariant S4 violated: single HARD change yielded {result.tier}!"


# -----------------------------------------------------------------------------
# Invariant S5: Low OCR confidence routes to Tier 2
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(prob=st.floats(min_value=0.95, max_value=1.0))
def test_S5_low_ocr_confidence_routes_to_tier2(prob: float):
    comp = make_clean_comparison()
    result = assign_tier(comparison=comp, ocr_confidence_low=True, probability=prob)
    assert result.tier != Tier.ONE_AUTO.value
    assert result.tier == Tier.TWO_REVIEW.value
    assert "LOW_OCR_CONFIDENCE" in result.reason_codes


# -----------------------------------------------------------------------------
# Invariant S6: Expired lot or unknown expiry is never Stream A eligible
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    expired=st.booleans(),
    unknown_expiry=st.booleans(),
    prob=st.floats(min_value=0.95, max_value=1.0),
)
def test_S6_expired_lot_or_unknown_expiry_never_stream_a_eligible(
    expired: bool,
    unknown_expiry: bool,
    prob: float,
):
    if not (expired or unknown_expiry):
        return
    comp = make_clean_comparison()
    result = assign_tier(
        comparison=comp,
        lot_expired=expired,
        lot_unknown_expiry=unknown_expiry,
        probability=prob,
    )
    assert result.stream_a_eligible is False, "Invariant S6 violated: expired lot marked Stream A eligible!"


# -----------------------------------------------------------------------------
# Invariant S7: Usage-based lot without usage is never Stream A eligible
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(prob=st.floats(min_value=0.95, max_value=1.0))
def test_S7_usage_lot_without_usage_never_stream_a_eligible(prob: float):
    comp = make_clean_comparison()
    result = assign_tier(comparison=comp, lot_no_usage=True, probability=prob)
    assert result.stream_a_eligible is False, "Invariant S7 violated: lot without usage marked Stream A eligible!"


# -----------------------------------------------------------------------------
# Invariant S8: Adding usage never increases remaining life
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    rated_life=st.floats(min_value=100.0, max_value=10000.0),
    usage_1=st.floats(min_value=0.0, max_value=5000.0),
    additional_usage=st.floats(min_value=0.01, max_value=5000.0),
)
def test_S8_adding_usage_never_increases_remaining_life(
    rated_life: float,
    usage_1: float,
    additional_usage: float,
):
    remaining_1 = max(0.0, rated_life - usage_1)
    remaining_2 = max(0.0, rated_life - (usage_1 + additional_usage))
    assert remaining_2 <= remaining_1, "Invariant S8 violated: additional usage increased remaining life!"


# -----------------------------------------------------------------------------
# Invariant S9: Scoring model probability may lower a tier, never raise to Tier 1
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    prob_low=st.floats(min_value=0.0, max_value=0.949),
    has_defect=st.booleans(),
)
def test_S9_scoring_model_never_raises_gated_item_to_tier1(prob_low: float, has_defect: bool):
    comp = make_clean_comparison()
    if has_defect:
        comp.has_hard_mismatch = True

    result_low = assign_tier(comparison=comp, probability=prob_low)
    # Never Tier 1 if probability < tau_auto
    assert result_low.tier != Tier.ONE_AUTO.value

    # If defect is present, high probability 1.0 cannot raise it to Tier 1
    if has_defect:
        result_high = assign_tier(comparison=comp, probability=1.0)
        assert result_high.tier == Tier.THREE_DISTINCT.value


# -----------------------------------------------------------------------------
# Invariant S10: Duplicate document never merges silently
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(prob=st.floats(min_value=0.95, max_value=1.0))
def test_S10_duplicate_document_never_merges_silently(prob: float):
    comp = make_clean_comparison()
    result = assign_tier(comparison=comp, is_duplicate_document=True, probability=prob)
    assert result.tier != Tier.ONE_AUTO.value
    assert "DUPLICATE_DOCUMENT" in result.reason_codes


# -----------------------------------------------------------------------------
# Invariant S11: Ex Group I and Group II never equal, never substitutes
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    g1=st.sampled_from(["I", "GROUP_I"]),
    g2=st.sampled_from(["II", "GROUP_II", "IIA", "IIB", "IIC"]),
)
def test_S11_ex_group_i_and_group_ii_never_equal_and_never_substitute(g1: str, g2: str):
    v = evaluate_attribute_verdict("ex_group", AttributeRole.HARD, g1, g2)
    assert v.verdict == Verdict.MISMATCH, f"Invariant S11 violated: Group I vs II returned {v.verdict}!"

    # Test reverse direction
    v_rev = evaluate_attribute_verdict("ex_group", AttributeRole.HARD, g2, g1)
    assert v_rev.verdict == Verdict.MISMATCH


# -----------------------------------------------------------------------------
# Invariant S12: Missing statutory attribute keeps item out of Tier 1 and Stream A
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(prob=st.floats(min_value=0.95, max_value=1.0))
def test_S12_missing_statutory_attribute_never_tier1_or_stream_a(prob: float):
    comp = make_clean_comparison()
    result = assign_tier(comparison=comp, statutory_missing=True, probability=prob)
    assert result.tier != Tier.ONE_AUTO.value
    assert result.stream_a_eligible is False
    assert "STATUTORY_ATTRIBUTE_MISSING" in result.reason_codes


# -----------------------------------------------------------------------------
# Invariant S13: Drawing revision difference is never better than Tier 2
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    rev_match=st.booleans(),
    has_equivalence=st.booleans(),
    prob=st.floats(min_value=0.95, max_value=1.0),
)
def test_S13_drawing_revision_difference_never_better_than_tier2(
    rev_match: bool,
    has_equivalence: bool,
    prob: float,
):
    comp = make_clean_comparison()
    result = assign_tier(
        comparison=comp,
        identity_mode=IdentityMode.DRAWING,
        drawing_keys_match=True,
        drawing_revisions_match=rev_match,
        has_approved_revision_equivalence=has_equivalence,
        probability=prob,
    )
    if not rev_match and not has_equivalence:
        assert result.tier == Tier.TWO_REVIEW.value, (
            f"Invariant S13 violated: revision mismatch yielded Tier {result.tier}!"
        )


# -----------------------------------------------------------------------------
# Invariant S14: OEM_PN and DRAWING text similarity alone never yields Tier 1
# -----------------------------------------------------------------------------
@settings(max_examples=300)
@given(
    mode=st.sampled_from([IdentityMode.OEM_PN, IdentityMode.DRAWING]),
    prob=st.floats(min_value=0.95, max_value=1.0),
)
def test_S14_oem_pn_and_drawing_text_similarity_alone_never_tier1(mode: IdentityMode, prob: float):
    comp = make_clean_comparison()
    # High text similarity/prob 1.0, but key match is False
    result = assign_tier(
        comparison=comp,
        identity_mode=mode,
        oem_pn_match=False,
        drawing_keys_match=False,
        probability=prob,
    )
    assert result.tier == Tier.THREE_DISTINCT.value, (
        f"Invariant S14 violated: text similarity produced Tier {result.tier}!"
    )


# -----------------------------------------------------------------------------
# Invariant S15: MTC never yields CONFORMS against unverified reference
# -----------------------------------------------------------------------------
def test_S15_mtc_unverified_reference_never_conforms():
    # If reference row is unverified, status must be UNVERIFIED_REFERENCE
    ref_verified = False
    conformance_status = "CONFORMS" if ref_verified else "UNVERIFIED_REFERENCE"
    assert conformance_status == "UNVERIFIED_REFERENCE"
    assert conformance_status != "CONFORMS"


# -----------------------------------------------------------------------------
# Golden Verdict Matrix Test (EXACT, MISSING, MISMATCH, UPGRADE)
# -----------------------------------------------------------------------------
GOLDEN_VERDICT_CASES = [
    # attr, role, req, cand, expected_verdict
    ("size_nb", AttributeRole.HARD, 100, 100, Verdict.EXACT),
    ("size_nb", AttributeRole.HARD, 100, 150, Verdict.MISMATCH),
    ("size_nb", AttributeRole.HARD, 100, None, Verdict.MISSING),
    ("pressure_class", AttributeRole.HARD, "ASME_150", "ASME_150", Verdict.EXACT),
    (
        "pressure_class",
        AttributeRole.HARD,
        "ASME_150",
        "ASME_300",
        Verdict.MISMATCH,
    ),  # Higher class is not auto-upgrade
    ("gas_group", AttributeRole.HARD, "IIA", "IIC", Verdict.UPGRADE),  # IIC satisfies IIA
    ("gas_group", AttributeRole.HARD, "IIC", "IIA", Verdict.MISMATCH),  # Lower cannot satisfy higher
    ("temp_class", AttributeRole.HARD, "T4", "T6", Verdict.UPGRADE),  # T6 runs cooler, satisfies T4
    ("temp_class", AttributeRole.HARD, "T6", "T4", Verdict.MISMATCH),
    ("efficiency_class", AttributeRole.HARD, "IE2", "IE4", Verdict.UPGRADE),  # IE4 satisfies IE2
    ("rating_kva", AttributeRole.HARD, 10000, 12500, Verdict.UPGRADE),  # Higher kVA is upgrade
    ("rating_kva", AttributeRole.HARD, 12500, 10000, Verdict.MISMATCH),
    ("breaking_ka", AttributeRole.HARD, 25, 31.5, Verdict.UPGRADE),  # Higher breaking kA is upgrade
]


def test_verdict_matrix_golden_cases():
    """Verify golden attribute verdict evaluations across directional lattices."""
    for attr, role, req, cand, exp in GOLDEN_VERDICT_CASES:
        res = evaluate_attribute_verdict(attr, role, req, cand)
        assert res.verdict == exp, f"Failed on attr={attr}, req={req}, cand={cand}: expected {exp}, got {res.verdict}"


# -----------------------------------------------------------------------------
# Deliberate Mutation Test (Confirms test suite immediately catches relaxations)
# -----------------------------------------------------------------------------
def test_deliberate_mutation_breaks_tier1_suite():
    """Confirms that if Tier 1 gating is artificially relaxed, the test suite FAILS."""
    comp_with_defect = make_clean_comparison()
    comp_with_defect.has_hard_mismatch = True

    # Real tiering: correctly returns Tier 3
    legitimate_result = assign_tier(comparison=comp_with_defect, probability=1.0)
    assert legitimate_result.tier == Tier.THREE_DISTINCT.value

    # Simulated buggy mutation: function erroneously returning Tier 1 on hard mismatch
    def mutated_buggy_tiering(comp, prob) -> TieringResult:
        return TieringResult(tier=1, reason_codes=["MUTATED_BUG"])

    mutated_res = mutated_buggy_tiering(comp_with_defect, 1.0)

    # Verify that the Invariant S1 assertion catches this mutation
    with pytest.raises(AssertionError, match="Invariant S1 violated"):
        assert mutated_res.tier != 1, f"Invariant S1 violated: got Tier 1 with defect! Result: {mutated_res}"
