"""Evaluation and acceptance gate test suite for the 6 Deep Flagship Families.

Validates:
1. Extraction accuracy across 40+ fixtures per family.
2. Hard-negative false merge rate = 0 (zero adversarial pairs reach Tier 1).
3. Missing-attribute routing is 100% Tier 2.
Conforms to implementation_plan.md Module 4 and add-family/SKILL.md.
"""

import csv
import math
from pathlib import Path

import pytest

from api.extractors.registry import default_registry
from api.services.comparator import compare_items
from api.services.tiering import Tier, assign_tier

DEEP_FAMILIES = [
    ("packs/common/fixtures/valves_gate.csv", "VALVES.GATE"),
    ("packs/common/fixtures/motors_ex.csv", "MOTORS.EX"),
    ("packs/power/fixtures/transformers.csv", "POWER.TRANSFORMER"),
    ("packs/steel/fixtures/refractory.csv", "STEEL.REFRACTORY"),
    ("packs/mining/fixtures/otr_tyres.csv", "MINING.OTR_TYRE"),
    ("packs/heavy_eng/fixtures/pumps_centrifugal.csv", "HEAVY.PUMP_CENTRIFUGAL"),
]

HARD_NEGATIVE_FILES = [
    ("packs/common/eval/pairs_valves_gate.csv", "VALVES.GATE"),
    ("packs/common/eval/pairs_motors_ex.csv", "MOTORS.EX"),
    ("packs/power/eval/pairs_transformers.csv", "POWER.TRANSFORMER"),
    ("packs/steel/eval/pairs_refractory.csv", "STEEL.REFRACTORY"),
    ("packs/mining/eval/pairs_otr_tyres.csv", "MINING.OTR_TYRE"),
    ("packs/heavy_eng/eval/pairs_pumps_centrifugal.csv", "HEAVY.PUMP_CENTRIFUGAL"),
]


@pytest.fixture(autouse=True, scope="module")
def setup_packs():
    default_registry.load_packs("packs")


def _is_close(val1, val2) -> bool:
    """Safe equality check for string and numeric ground truth values."""
    if val1 is None and val2 is None:
        return True
    if val1 is None or val2 is None:
        return False
    try:
        f1 = float(val1)
        f2 = float(val2)
        return math.isclose(f1, f2, rel_tol=1e-3, abs_tol=1e-3)
    except (ValueError, TypeError):
        return str(val1).strip().upper() == str(val2).strip().upper()


def test_deep_families_fixtures_count():
    """Verify every deep family has >= 40 test fixtures."""
    for csv_rel, subcat in DEEP_FAMILIES:
        p = Path(csv_rel)
        assert p.exists(), f"Fixtures file missing: {csv_rel}"
        with open(p, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 40, f"{subcat} has only {len(rows)} fixtures; expected >= 40"


def test_deep_families_hard_negatives_count():
    """Verify every deep family has >= 15 adversarial hard-negative pairs."""
    for csv_rel, subcat in HARD_NEGATIVE_FILES:
        p = Path(csv_rel)
        assert p.exists(), f"Hard negatives file missing: {csv_rel}"
        with open(p, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 15, f"{subcat} has only {len(rows)} pairs; expected >= 15"


def test_deep_families_extraction_accuracy():
    """Evaluate extraction accuracy per attribute across all 6 deep families."""
    print("\n--- Deep Families Extraction Accuracy Report ---")
    total_evaluated = 0
    total_correct = 0

    for csv_rel, subcat in DEEP_FAMILIES:
        p = Path(csv_rel)
        with open(p, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        family_evaluated = 0
        family_correct = 0

        for r in rows:
            desc = r["description"]
            extracted = default_registry.extract_attributes(desc, subcat)

            for col, expected_val in r.items():
                if col == "description" or not expected_val.strip():
                    continue

                family_evaluated += 1
                actual_val = extracted.get(col).value if col in extracted else None

                if _is_close(actual_val, expected_val):
                    family_correct += 1

        accuracy = family_correct / family_evaluated if family_evaluated > 0 else 1.0
        print(f"{subcat:25s}: {accuracy:.1%} ({family_correct}/{family_evaluated} correct)")

        total_evaluated += family_evaluated
        total_correct += family_correct

        assert accuracy >= 0.90, f"{subcat} accuracy was {accuracy:.1%}; expected >= 90%"

    overall_accuracy = total_correct / total_evaluated
    print(f"Overall Deep Family Accuracy: {overall_accuracy:.1%} ({total_correct}/{total_evaluated})")
    assert overall_accuracy >= 0.95


def test_zero_hard_negatives_reach_tier1():
    """Gate Check: ZERO hard-negative pairs must reach Tier 1 (fail closed)."""
    leaks = []

    for csv_rel, subcat in HARD_NEGATIVE_FILES:
        p = Path(csv_rel)
        with open(p, "r", encoding="utf-8") as f:
            pairs = list(csv.DictReader(f))

        for idx, row in enumerate(pairs, 1):
            req_text = row["req_text"]
            cand_text = row["cand_text"]

            req_attrs = {
                k: v.value
                for k, v in default_registry.extract_attributes(req_text, subcat).items()
                if v.value is not None
            }
            cand_attrs = {
                k: v.value
                for k, v in default_registry.extract_attributes(cand_text, subcat).items()
                if v.value is not None
            }

            comp = compare_items(req_attrs, cand_attrs, subcat)
            decision = assign_tier(comp, probability=0.99)

            if decision.tier == Tier.ONE_AUTO.value:
                leaks.append(f"{subcat} Pair #{idx}: req='{req_text}' vs cand='{cand_text}' leaked to Tier 1!")

    assert len(leaks) == 0, f"False merge leak detected! {len(leaks)} pairs reached Tier 1: {leaks}"


def test_missing_attribute_cases_land_in_tier2():
    """Gate Check: 100% of missing-attribute cases must land in Tier 2 (Review)."""
    for csv_rel, subcat in HARD_NEGATIVE_FILES:
        p = Path(csv_rel)
        with open(p, "r", encoding="utf-8") as f:
            pairs = list(csv.DictReader(f))

        for row in pairs:
            if row.get("expected_verdict") == "MISSING" or row.get("expected_tier") == "2":
                req_text = row["req_text"]
                cand_text = row["cand_text"]

                req_attrs = {
                    k: v.value
                    for k, v in default_registry.extract_attributes(req_text, subcat).items()
                    if v.value is not None
                }
                cand_attrs = {
                    k: v.value
                    for k, v in default_registry.extract_attributes(cand_text, subcat).items()
                    if v.value is not None
                }

                comp = compare_items(req_attrs, cand_attrs, subcat)
                decision = assign_tier(comp, probability=0.99)

                # Must not be Tier 1
                assert decision.tier != Tier.ONE_AUTO.value
                assert decision.tier == Tier.TWO_REVIEW.value, (
                    f"Missing/upgrade case in {subcat} got Tier {decision.tier} instead of Tier 2!"
                )
