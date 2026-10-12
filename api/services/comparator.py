"""Safety attribute comparator and directional lattice engine.

Implements deterministic attribute-by-attribute comparison, directional substitution
lattices (IEC 60079 gas groups, temperature classes, motor efficiencies), and verdict matrices.
Conforms to specsheet.md Sections 4.6, 5.1, 5.2, 5.4, and Safety Invariants S1 to S15.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from api.extractors.registry import (
    AttributeRole,
    SubcategorySpecDef,
    default_registry,
)


class Verdict(str, Enum):
    """Verdict of comparing a single attribute between requirement and candidate."""

    EXACT = "EXACT"  # Values are present and identically equal
    MISSING = "MISSING"  # Value is absent or None on either side
    MISMATCH = "MISMATCH"  # Values are both present, differ, and candidate is NOT an allowed upgrade
    UPGRADE = "UPGRADE"  # Candidate value is an allowed directional substitution upgrade


# --- Directional Substitution Lattices ---

# Gas Groups: IIC >= IIB >= IIA (IEC 60079, within Group II only)
GAS_GROUP_RANKS: dict[str, int] = {
    "IIA": 1,
    "IIB": 2,
    "IIC": 3,
}

# Temperature Classes: T6 >= T5 >= T4 >= T3 >= T2 >= T1 (IEC 60079)
TEMP_CLASS_RANKS: dict[str, int] = {
    "T1": 1,
    "T2": 2,
    "T3": 3,
    "T4": 4,
    "T5": 5,
    "T6": 6,
}

# Motor Efficiency Classes: IE4 > IE3 > IE2 > IE1 > EFF3 (IEC 60034-30-1 / IS 12615)
EFFICIENCY_RANKS: dict[str, int] = {
    "EFF3": 0,
    "IE1": 1,
    "IE2": 2,
    "IE3": 3,
    "IE4": 4,
}


@dataclass
class AttributeVerdictResult:
    """Detailed verdict of comparing one attribute."""

    attr: str
    role: AttributeRole
    raw_val: Any  # Requirement value
    candidate_val: Any
    verdict: Verdict
    notes: str | None = None


@dataclass
class ItemComparisonResult:
    """Full attribute comparison report between requirement item and candidate item."""

    subcategory: str
    verdicts: dict[str, AttributeVerdictResult]
    has_hard_mismatch: bool
    has_required_mismatch: bool
    has_missing_hard: bool
    has_missing_required: bool
    has_upgrade: bool
    missing_hard_attributes: list[str]
    missing_required_attributes: list[str]
    attribute_gap_alert: str | None = None


def _compare_scalars(a: Any, b: Any) -> bool:
    """Safe equality check for strings, integers, floats, and booleans."""
    if a is None or b is None:
        return False

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-5, abs_tol=1e-5)

    if isinstance(a, str) and isinstance(b, str):
        return a.strip().upper() == b.strip().upper()

    return a == b


def evaluate_directional_gas_group(req_val: str, cand_val: str) -> Verdict:
    """Evaluates gas group directional lattice within Group II.

    Invariant S11: Group I (mines) and Group II (surface) never equal, never substitutes.
    """
    req = str(req_val).strip().upper()
    cand = str(cand_val).strip().upper()

    if req == cand:
        return Verdict.EXACT

    # Check for Group I vs Group II contamination
    if ("GROUP_I" in (req, cand) or "GROUP_1" in (req, cand) or "I" in (req, cand)) and req != cand:
        return Verdict.MISMATCH

    req_rank = GAS_GROUP_RANKS.get(req)
    cand_rank = GAS_GROUP_RANKS.get(cand)

    if req_rank is not None and cand_rank is not None:
        if cand_rank > req_rank:
            return Verdict.UPGRADE
        if cand_rank == req_rank:
            return Verdict.EXACT
        return Verdict.MISMATCH

    return Verdict.MISMATCH


def evaluate_directional_temp_class(req_val: str, cand_val: str) -> Verdict:
    """Evaluates temperature class directional lattice: T6 >= T5 >= T4 >= T3 >= T2 >= T1."""
    req = str(req_val).strip().upper()
    cand = str(cand_val).strip().upper()

    if req == cand:
        return Verdict.EXACT

    req_rank = TEMP_CLASS_RANKS.get(req)
    cand_rank = TEMP_CLASS_RANKS.get(cand)

    if req_rank is not None and cand_rank is not None:
        if cand_rank > req_rank:
            return Verdict.UPGRADE
        if cand_rank == req_rank:
            return Verdict.EXACT
        return Verdict.MISMATCH

    return Verdict.MISMATCH


def evaluate_directional_efficiency(req_val: str, cand_val: str) -> Verdict:
    """Evaluates motor efficiency lattice: IE4 > IE3 > IE2 > IE1 > EFF3."""
    req = str(req_val).strip().upper()
    cand = str(cand_val).strip().upper()

    if req == cand:
        return Verdict.EXACT

    req_rank = EFFICIENCY_RANKS.get(req)
    cand_rank = EFFICIENCY_RANKS.get(cand)

    if req_rank is not None and cand_rank is not None:
        if cand_rank > req_rank:
            return Verdict.UPGRADE
        if cand_rank == req_rank:
            return Verdict.EXACT
        return Verdict.MISMATCH

    return Verdict.MISMATCH


def evaluate_attribute_verdict(
    attr_name: str,
    role: AttributeRole,
    req_val: Any,
    cand_val: Any,
    subcategory: str = "",
) -> AttributeVerdictResult:
    """Compares a single attribute value between requirement and candidate."""

    # Unwrap dict or ExtractedValue objects
    if isinstance(req_val, dict) and "value" in req_val:
        req_val = req_val.get("value")
    elif hasattr(req_val, "value"):
        req_val = req_val.value

    if isinstance(cand_val, dict) and "value" in cand_val:
        cand_val = cand_val.get("value")
    elif hasattr(cand_val, "value"):
        cand_val = cand_val.value

    # 1. Missing data handling
    if req_val is None or cand_val is None or req_val == "" or cand_val == "":
        return AttributeVerdictResult(
            attr=attr_name,
            role=role,
            raw_val=req_val,
            candidate_val=cand_val,
            verdict=Verdict.MISSING,
        )

    # 2. Invariant S11: Ex Group I and Group II regime separation
    if attr_name in ("ex_group", "equipment_group"):
        r_grp = str(req_val).strip().upper()
        c_grp = str(cand_val).strip().upper()
        if (r_grp in ("I", "GROUP_I") and c_grp not in ("I", "GROUP_I")) or (
            c_grp in ("I", "GROUP_I") and r_grp not in ("I", "GROUP_I")
        ):
            return AttributeVerdictResult(
                attr=attr_name,
                role=role,
                raw_val=req_val,
                candidate_val=cand_val,
                verdict=Verdict.MISMATCH,
                notes="Regime violation: Ex Group I (mines) and Group II (surface) never equal or substitute (Invariant S11)",
            )

    # 3. Directional Lattices
    if attr_name in ("gas_group", "explosion_group"):
        verdict = evaluate_directional_gas_group(req_val, cand_val)
        return AttributeVerdictResult(
            attr=attr_name,
            role=role,
            raw_val=req_val,
            candidate_val=cand_val,
            verdict=verdict,
        )

    if attr_name in ("temp_class", "temperature_class", "t_class"):
        verdict = evaluate_directional_temp_class(req_val, cand_val)
        return AttributeVerdictResult(
            attr=attr_name,
            role=role,
            raw_val=req_val,
            candidate_val=cand_val,
            verdict=verdict,
        )

    if attr_name in ("efficiency_class", "motor_efficiency"):
        verdict = evaluate_directional_efficiency(req_val, cand_val)
        return AttributeVerdictResult(
            attr=attr_name,
            role=role,
            raw_val=req_val,
            candidate_val=cand_val,
            verdict=verdict,
        )

    # Transformer kVA higher is UPGRADE (substitution only)
    if attr_name in ("rating_kva", "base_kva"):
        try:
            r_num = float(req_val)
            c_num = float(cand_val)
            if math.isclose(r_num, c_num, rel_tol=1e-5):
                verdict = Verdict.EXACT
            elif c_num > r_num:
                verdict = Verdict.UPGRADE
            else:
                verdict = Verdict.MISMATCH
            return AttributeVerdictResult(
                attr=attr_name,
                role=role,
                raw_val=req_val,
                candidate_val=cand_val,
                verdict=verdict,
            )
        except (ValueError, TypeError):
            pass

    # Breaker breaking kA higher is UPGRADE (substitution only)
    if attr_name in ("breaking_ka", "rated_breaking_current_ka"):
        try:
            r_num = float(req_val)
            c_num = float(cand_val)
            if math.isclose(r_num, c_num, rel_tol=1e-5):
                verdict = Verdict.EXACT
            elif c_num > r_num:
                verdict = Verdict.UPGRADE
            else:
                verdict = Verdict.MISMATCH
            return AttributeVerdictResult(
                attr=attr_name,
                role=role,
                raw_val=req_val,
                candidate_val=cand_val,
                verdict=verdict,
            )
        except (ValueError, TypeError):
            pass

    # Pressure class: higher class does NOT fit by default due to PCD / bolt count differences
    if attr_name == "pressure_class":
        if _compare_scalars(req_val, cand_val):
            return AttributeVerdictResult(
                attr=attr_name,
                role=role,
                raw_val=req_val,
                candidate_val=cand_val,
                verdict=Verdict.EXACT,
            )
        return AttributeVerdictResult(
            attr=attr_name,
            role=role,
            raw_val=req_val,
            candidate_val=cand_val,
            verdict=Verdict.MISMATCH,
            notes="Pressure class mismatch: higher class requires explicit dimensional bolt circle check",
        )

    # 4. Standard Scalar Equality
    if _compare_scalars(req_val, cand_val):
        return AttributeVerdictResult(
            attr=attr_name,
            role=role,
            raw_val=req_val,
            candidate_val=cand_val,
            verdict=Verdict.EXACT,
        )

    return AttributeVerdictResult(
        attr=attr_name,
        role=role,
        raw_val=req_val,
        candidate_val=cand_val,
        verdict=Verdict.MISMATCH,
    )


def _check_when_condition(condition: str | None, extracted: dict[str, Any]) -> bool:
    """Evaluate simple when-condition string against extracted attribute values."""
    if not condition:
        return True
    try:
        if "has" in condition:
            parts = condition.split("has")
            key = parts[0].strip()
            val = extracted.get(key)
            if isinstance(val, dict):
                val = val.get("value")
            return bool(val)

        if " in " in condition:
            left, right = condition.split(" in ", 1)
            left_val = extracted.get(left.strip())
            if isinstance(left_val, dict):
                left_val = left_val.get("value")
            right_clean = right.strip().strip("[]").replace("'", "").replace('"', "")
            allowed = [item.strip() for item in right_clean.split(",")]
            return str(left_val).upper() in allowed

        if "==" in condition:
            left, right = condition.split("==", 1)
            left_val = extracted.get(left.strip())
            if isinstance(left_val, dict):
                left_val = left_val.get("value")
            right_val = right.strip().strip("'\"")
            return str(left_val).upper() == right_val.upper()

        if "!=" in condition:
            left, right = condition.split("!=", 1)
            left_val = extracted.get(left.strip())
            if isinstance(left_val, dict):
                left_val = left_val.get("value")
            right_val = right.strip().strip("'\"")
            return str(left_val).upper() != right_val.upper()

        return True
    except (AttributeError, ValueError, KeyError):
        return True


def compare_items(
    req_attrs: dict[str, Any],
    cand_attrs: dict[str, Any],
    subcategory: str,
    spec: SubcategorySpecDef | None = None,
) -> ItemComparisonResult:
    """Compares requirement attributes against candidate attributes under the subcategory specification.

    Returns:
        ItemComparisonResult with per-attribute verdicts, mismatch/missing flags, and gap alert.
    """
    resolved_spec = spec or default_registry.get_spec(subcategory)

    verdicts: dict[str, AttributeVerdictResult] = {}
    missing_hard: list[str] = []
    missing_required: list[str] = []
    has_hard_mismatch = False
    has_required_mismatch = False
    has_upgrade = False

    # Determine attribute roles from spec if available
    attr_defs = resolved_spec.attributes if resolved_spec else []

    if attr_defs:
        for a_def in attr_defs:
            name = a_def.name
            role = a_def.role
            r_val = req_attrs.get(name)
            c_val = cand_attrs.get(name)

            # Special exemption for Group I Ex equipment (Invariant S11)
            # For Group I, absent gas_group and t_class are not considered missing
            is_group_1 = str(req_attrs.get("ex_group", "")).upper() in ("I", "GROUP_I") or str(
                cand_attrs.get("ex_group", "")
            ).upper() in ("I", "GROUP_I")
            if is_group_1 and name in ("gas_group", "temp_class", "t_class") and r_val is None and c_val is None:
                verdicts[name] = AttributeVerdictResult(
                    attr=name,
                    role=role,
                    raw_val=r_val,
                    candidate_val=c_val,
                    verdict=Verdict.EXACT,
                    notes="Ex Group I exemption: gas_group/t_class absent by design (Invariant S11)",
                )
                continue

            # When-condition gating: inapplicable attributes should not be marked MISSING
            if getattr(a_def, "when", None):
                req_applies = _check_when_condition(a_def.when, req_attrs)
                cand_applies = _check_when_condition(a_def.when, cand_attrs)
                if not req_applies and not cand_applies and r_val is None and c_val is None:
                    verdicts[name] = AttributeVerdictResult(
                        attr=name,
                        role=role,
                        raw_val=r_val,
                        candidate_val=c_val,
                        verdict=Verdict.EXACT,
                        notes=f"Inapplicable due to when condition ({a_def.when})",
                    )
                    continue

            v_res = evaluate_attribute_verdict(name, role, r_val, c_val, subcategory)
            verdicts[name] = v_res

            if v_res.verdict == Verdict.MISMATCH:
                if role == AttributeRole.HARD:
                    has_hard_mismatch = True
                elif role == AttributeRole.REQUIRED:
                    has_required_mismatch = True
            elif v_res.verdict == Verdict.MISSING:
                if role == AttributeRole.HARD:
                    missing_hard.append(name)
                elif role == AttributeRole.REQUIRED:
                    missing_required.append(name)
            elif v_res.verdict == Verdict.UPGRADE:
                has_upgrade = True
    else:
        # Fallback if subcategory spec is not loaded: compare all union keys as HARD
        all_keys = sorted(set(req_attrs.keys()) | set(cand_attrs.keys()))
        for k in all_keys:
            r_val = req_attrs.get(k)
            c_val = cand_attrs.get(k)
            v_res = evaluate_attribute_verdict(k, AttributeRole.HARD, r_val, c_val, subcategory)
            verdicts[k] = v_res
            if v_res.verdict == Verdict.MISMATCH:
                has_hard_mismatch = True
            elif v_res.verdict == Verdict.MISSING:
                missing_hard.append(k)
            elif v_res.verdict == Verdict.UPGRADE:
                has_upgrade = True

    # Build attribute gap alert string if required attributes are missing
    gap_alert = None
    all_missing = missing_hard + missing_required
    if all_missing:
        gap_alert = f"Missing: {', '.join(all_missing)}"

    return ItemComparisonResult(
        subcategory=subcategory,
        verdicts=verdicts,
        has_hard_mismatch=has_hard_mismatch,
        has_required_mismatch=has_required_mismatch,
        has_missing_hard=len(missing_hard) > 0,
        has_missing_required=len(missing_required) > 0,
        has_upgrade=has_upgrade,
        missing_hard_attributes=missing_hard,
        missing_required_attributes=missing_required,
        attribute_gap_alert=gap_alert,
    )
