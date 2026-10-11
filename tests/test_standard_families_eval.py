"""Evaluation and acceptance gate test suite for the 15 Standard Families across 5 Packs.

Validates:
1. Extraction accuracy across >= 20 fixtures per family.
2. Hard-negative false merge rate = 0 (zero adversarial pairs reach Tier 1).
3. Missing-attribute routing is 100% Tier 2.
Conforms to implementation_plan.md Module 5 and specsheet.md Section 7.5, 18.2, 18.4.2-3, 18.5.2-3, 18.6.2, 18.7.2-3.
"""

import csv
import math
from pathlib import Path

import pytest

from api.extractors.registry import default_registry
from api.services.comparator import compare_items
from api.services.tiering import Tier, assign_tier

STANDARD_FAMILIES = [
    ("packs/common/fixtures/pipes.csv", "PIPES.PIPE"),
    ("packs/common/fixtures/flanges.csv", "FLANGES.FLANGE"),
    ("packs/common/fixtures/cables.csv", "CABLES.POWER"),
    ("packs/common/fixtures/structural.csv", "STEEL.STRUCTURAL"),
    ("packs/common/fixtures/rebar.csv", "STEEL.REBAR"),
    ("packs/common/fixtures/bearings.csv", "BEARINGS.BEARING"),
    ("packs/common/fixtures/fasteners.csv", "FASTENERS.STUD_BOLT"),
    ("packs/common/fixtures/instrumentation.csv", "INSTRUMENTS.TRANSMITTER"),
    ("packs/power/fixtures/breakers.csv", "POWER.BREAKER"),
    ("packs/power/fixtures/boiler_tubes.csv", "POWER.BOILER_TUBE"),
    ("packs/steel/fixtures/conveyor_belts.csv", "STEEL.CONVEYOR_BELT"),
    ("packs/steel/fixtures/mill_rolls.csv", "STEEL.MILL_ROLL"),
    ("packs/mining/fixtures/wire_ropes.csv", "MINING.WIRE_ROPE"),
    ("packs/heavy_eng/fixtures/hydraulic_hoses.csv", "HEAVY.HYDRAULIC_HOSE"),
    ("packs/heavy_eng/fixtures/made_to_drawing.csv", "HEAVY.MADE_TO_DRAWING"),
]

HARD_NEGATIVE_FILES = [
    ("packs/common/eval/pairs_pipes.csv", "PIPES.PIPE"),
    ("packs/common/eval/pairs_flanges.csv", "FLANGES.FLANGE"),
    ("packs/common/eval/pairs_cables.csv", "CABLES.POWER"),
    ("packs/common/eval/pairs_structural.csv", "STEEL.STRUCTURAL"),
    ("packs/common/eval/pairs_rebar.csv", "STEEL.REBAR"),
    ("packs/common/eval/pairs_bearings.csv", "BEARINGS.BEARING"),
    ("packs/common/eval/pairs_fasteners.csv", "FASTENERS.STUD_BOLT"),
    ("packs/common/eval/pairs_instrumentation.csv", "INSTRUMENTS.TRANSMITTER"),
    ("packs/power/eval/pairs_breakers.csv", "POWER.BREAKER"),
    ("packs/power/eval/pairs_boiler_tubes.csv", "POWER.BOILER_TUBE"),
    ("packs/steel/eval/pairs_conveyor_belts.csv", "STEEL.CONVEYOR_BELT"),
    ("packs/steel/eval/pairs_mill_rolls.csv", "STEEL.MILL_ROLL"),
    ("packs/mining/eval/pairs_wire_ropes.csv", "MINING.WIRE_ROPE"),
    ("packs/heavy_eng/eval/pairs_hydraulic_hoses.csv", "HEAVY.HYDRAULIC_HOSE"),
    ("packs/heavy_eng/eval/pairs_made_to_drawing.csv", "HEAVY.MADE_TO_DRAWING"),
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


def test_standard_families_fixtures_count():
    """Verify every standard family has >= 20 test fixtures."""
    for csv_rel, subcat in STANDARD_FAMILIES:
        p = Path(csv_rel)
        assert p.exists(), f"Fixtures file missing: {csv_rel}"
        with open(p, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 20, f"{subcat} has only {len(rows)} fixtures; expected >= 20"


def test_standard_families_hard_negatives_count():
    """Verify every standard family has >= 8 adversarial hard-negative pairs."""
    for csv_rel, subcat in HARD_NEGATIVE_FILES:
        p = Path(csv_rel)
        assert p.exists(), f"Hard negatives file missing: {csv_rel}"
        with open(p, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 8, f"{subcat} has only {len(rows)} pairs; expected >= 8"


def test_standard_families_extraction_accuracy():
    """Evaluate extraction accuracy per attribute across all 15 standard families."""
    print("\n--- Standard Families Extraction Accuracy Report ---")
    total_evaluated = 0
    total_correct = 0

    for csv_rel, subcat in STANDARD_FAMILIES:
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
    print(f"Overall Standard Families Accuracy: {overall_accuracy:.1%} ({total_correct}/{total_evaluated})")
    assert overall_accuracy >= 0.95


def test_standard_zero_hard_negatives_reach_tier1():
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


def test_standard_missing_attribute_cases_land_in_tier2():
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
