"""Evaluation and release gate tests (Section 14.0, 21 Phase 8).

Validates:
1. Mathematical correctness of exact Clopper-Pearson binomial confidence intervals.
2. Hard release gates enforcement via gate_check.
3. Three-baseline comparison: Cosine vs Trigram vs Samanvay safety path.
4. Sector and Organisation parity guarantees.
"""

import math

from scripts.clopper_pearson import (
    clopper_pearson,
    trials_needed_for_zero_failures,
    upper_bound_zero_failures,
)
from scripts.eval_harness import evaluate_harness
from scripts.gate_check import check, run_gate_check


def test_clopper_pearson_exact_intervals_known_vectors():
    """Validates Clopper-Pearson exact confidence intervals against standard mathematical benchmarks."""
    # Vector 1: 0 failures in 150 trials (95% confidence)
    lo, hi = clopper_pearson(0, 150, confidence=0.95, two_sided=True)
    assert lo == 0.0
    # For two-sided 95%, alpha/2 = 0.025; 1 - 0.025^(1/150) ~= 0.02429 (2.43%)
    assert math.isclose(hi, 0.02429, rel_tol=1e-2)

    # Vector 2: 100 successes in 100 trials
    lo_perf, hi_perf = clopper_pearson(100, 100, confidence=0.95, two_sided=True)
    assert hi_perf == 1.0
    assert lo_perf > 0.95

    # Vector 3: 50 successes out of 100 trials (p = 0.5)
    lo_mid, hi_mid = clopper_pearson(50, 100, confidence=0.95, two_sided=True)
    assert lo_mid < 0.5 < hi_mid
    # Symmetrical around 0.5
    assert math.isclose(0.5 - lo_mid, hi_mid - 0.5, rel_tol=1e-3)


def test_clopper_pearson_zero_failures_closed_form():
    """Validates upper_bound_zero_failures and trials_needed_for_zero_failures."""
    # For n=300, one-sided 95% upper bound should be approx 3/300 = 1%
    hi_one_sided = upper_bound_zero_failures(300, confidence=0.95, two_sided=False)
    assert math.isclose(hi_one_sided, 0.00994, rel_tol=1e-2)

    # Trials needed for target upper bound of 1% (0.01) at 95% confidence
    needed = trials_needed_for_zero_failures(0.01, confidence=0.95, two_sided=False)
    assert 295 <= needed <= 305


def test_clopper_pearson_interval_containment_and_monotonicity():
    """Property test: lower <= p_hat <= upper, and bounds are monotonic in k."""
    n = 80
    prev_hi = 0.0
    for k in range(n + 1):
        lo, hi = clopper_pearson(k, n, confidence=0.95)
        p_hat = k / n
        assert lo <= p_hat <= hi, f"Violated containment at k={k}: lo={lo}, p={p_hat}, hi={hi}"
        assert hi >= prev_hi, f"Violated monotonicity at k={k}: prev={prev_hi}, cur={hi}"
        prev_hi = hi


def test_gate_check_hard_release_gates():
    """Verifies gate_check blocks any release breaking safety thresholds."""
    # 1. Compliant metrics -> ALL PASS
    good_metrics = {
        "hard_negative_pairs": 170,
        "hard_negative_false_merges": 0,
        "missing_attr_cases": 76,
        "missing_attr_routed_ok": 76,
        "low_ocr_in_tier1": 0,
        "mtc_conforms_unverified": 0,
        "auto_tier_tp": 600,
        "auto_tier_fp": 0,
        "precision_target": 0.995,
    }
    results = check(good_metrics)
    assert all(ok for _, ok, _ in results)
    assert run_gate_check(good_metrics) == 0

    # 2. Hard-negative false merge leak (1 false merge) -> FAILS GATE
    bad_merge = dict(good_metrics, hard_negative_false_merges=1)
    results = check(bad_merge)
    assert any(name == "Hard-negative false merges" and not ok for name, ok, _ in results)
    assert run_gate_check(bad_merge) == 1

    # 3. Missing-attribute routing failure -> FAILS GATE
    bad_missing = dict(good_metrics, missing_attr_routed_ok=74)
    results = check(bad_missing)
    assert any(name == "Missing-attribute routing" and not ok for name, ok, _ in results)
    assert run_gate_check(bad_missing) == 1

    # 4. Low-confidence OCR in Tier 1 -> FAILS GATE
    bad_ocr = dict(good_metrics, low_ocr_in_tier1=1)
    results = check(bad_ocr)
    assert any(name == "Low-confidence OCR in Tier 1" and not ok for name, ok, _ in results)

    # 5. MTC conforms against unverified reference -> FAILS GATE
    bad_mtc = dict(good_metrics, mtc_conforms_unverified=1)
    results = check(bad_mtc)
    assert any(name == "MTC conforms against unverified reference" and not ok for name, ok, _ in results)

    # 6. Auto-tier precision below target (target=0.995, actual=0.98) -> FAILS GATE
    bad_prec = dict(good_metrics, auto_tier_tp=490, auto_tier_fp=10)
    results = check(bad_prec)
    assert any(name == "Auto-tier precision (dev)" and not ok for name, ok, _ in results)


def test_eval_harness_end_to_end_baselines_and_parity():
    """Runs complete evaluation harness across 21 families and verifies all invariants."""
    metrics = evaluate_harness()

    # 1. Total adversarial pairs
    assert metrics["hard_negative_pairs"] == 170

    # 2. Samanvay Safety Path: ZERO false merges
    assert metrics["hard_negative_false_merges"] == 0

    # 3. Baselines: Cosine and Trigram fail closed on adversarial pairs
    b = metrics["baselines_comparison"]
    assert b["cosine_false_merges"] >= 50, f"Expected cosine failures on hard negatives, got {b['cosine_false_merges']}"
    assert b["trigram_false_merges"] >= 40, (
        f"Expected trigram failures on hard negatives, got {b['trigram_false_merges']}"
    )

    # 4. Missing attribute cases: 100% routed to Tier 2
    assert metrics["missing_attr_cases"] == 76
    assert metrics["missing_attr_routed_ok"] == 76

    # 5. Auto-tier precision >= 99.5%
    assert metrics["auto_tier_precision"] >= 0.995

    # 6. Sector Parity check
    sec_parity = metrics["sector_parity"]
    assert len(sec_parity) == 5  # COMMON, POWER, STEEL, MINING, HEAVY_ENG
    for sec, stats in sec_parity.items():
        assert stats["false_merges"] == 0, f"Sector {sec} had false merges: {stats}"
        assert stats["missing_route_rate"] == 1.0, f"Sector {sec} did not route 100% missing to Tier 2"

    # 7. CPSE Organisation Parity check
    org_parity = metrics["org_parity"]
    assert len(org_parity) == 4  # OIL-1, POWER-1, STEEL-1, MINE-1
    for org, stats in org_parity.items():
        assert stats["false_merges"] == 0, f"Organization {org} had false merges: {stats}"

    # 8. Real developer fixtures execution metrics
    assert metrics["total_fixtures_evaluated"] == 600
    assert metrics["auto_tier_tp"] == 62
    assert metrics["auto_tier_tier2"] == 538
    assert metrics["tier_1_recall"] > 0.10

    # 9. Holdout evaluation set verification
    h = metrics.get("holdout_evaluation", {})
    assert h.get("total_pairs") == 120
    assert h.get("hard_negative_pairs") == 60
    assert h.get("hard_negative_false_merges") == 0
    assert h.get("hard_negative_false_merge_rate") == 0.0


def test_flange_raised_face_lands_in_tier1():
    """Validates that regular raised-face flanges land in Tier 1 and rtj_groove is conditional."""
    from api.extractors.registry import default_registry
    from api.services.comparator import compare_items
    from api.services.tiering import Tier, assign_tier

    default_registry.load_packs("packs")
    desc = "FLANGE WNRF 4 IN 150# A105 SCH 40"
    ext = default_registry.extract_attributes(desc, "FLANGES.FLANGE")
    attrs = {k: ev.value for k, ev in ext.items() if ev.value is not None}

    comp = compare_items(attrs, attrs, "FLANGES.FLANGE")
    tier_res = assign_tier(comp, probability=0.99)

    assert tier_res.tier == Tier.ONE_AUTO.value
    assert "ALL_HARD_REQUIRED_EXACT" in tier_res.reason_codes
    # rtj_groove should be inapplicable, not missing
    assert "MISSING_REQUIRED_ATTRIBUTE" not in tier_res.reason_codes

