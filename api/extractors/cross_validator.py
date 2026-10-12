"""Stage 2 Three-Layer Attribute Cross-Validator per Section 4.3 and Invariant S12.

Three layers in order:
1. YAML-lexicon and Python rule extractors (Section 7).
2. Optional LLM extractor and optional NER token classifier (Section 8.1b).
3. Cross-validator:
   - Per HARD attribute:
     * Both agree: confidence 0.95+ (e.g. 0.98), source 'rule+ner'.
     * Disagree: null + EXTRACTION_CONFLICT (and ATTRIBUTE_EXTRACTION_CONFLICT).
     * One source (rule only): confidence 0.70-0.90.
     * One source (NER/LLM only): Invariant S12 blocks unbacked statutory/HARD attributes (null + UNVERIFIED_ML_EXTRACTION).
     * Physically invalid: null + flag.
   - Every extracted value carries an evidence span (start, end).
"""

from __future__ import annotations

from typing import Any

from api.extractors.base import ExtractedValue, none_with


def _normalize_cmp_val(val: Any) -> str:
    """Normalize extracted value representation for cross-comparison."""
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, dict):
        # Comparison on canonical code/tag if present
        return str(val.get("canonical", val.get("value", val))).strip().upper()
    return str(val).strip().upper()


def values_agree(v1: Any, v2: Any) -> bool:
    """Check semantic equivalence between rule and auxiliary extractions."""
    s1 = _normalize_cmp_val(v1)
    s2 = _normalize_cmp_val(v2)
    if not s1 or not s2:
        return False
    if s1 == s2:
        return True

    # Numeric equivalence (e.g. 150 vs 150.0)
    try:
        f1 = float(s1)
        f2 = float(s2)
        return abs(f1 - f2) < 1e-5
    except (ValueError, TypeError):
        pass

    # Substring / token containment (e.g., ASME_150 vs CL150 or 150)
    tokens1 = set(s1.replace("_", " ").replace("-", " ").split())
    tokens2 = set(s2.replace("_", " ").replace("-", " ").split())
    return bool(tokens1 and tokens2 and (tokens1.issubset(tokens2) or tokens2.issubset(tokens1)))


def cross_validate_attributes(
    rule_attrs: dict[str, ExtractedValue],
    aux_attrs: dict[str, ExtractedValue] | None = None,
    hard_attributes: set[str] | list[str] | None = None,
    statutory_attributes: set[str] | list[str] | None = None,
) -> dict[str, ExtractedValue]:
    """Cross-validates Layer 1 (rule) and Layer 2 (aux/NER/LLM) extractions.

    Parameters:
        rule_attrs: Attribute mapping from Layer 1 rule/lexicon extractors.
        aux_attrs: Attribute mapping from Layer 2 NER classifier or LLM.
        hard_attributes: Set of HARD attribute names for the subcategory.
        statutory_attributes: Set of statutory attribute names (Invariant S12).

    Returns:
        dict[str, ExtractedValue] with calibrated confidence, reconciled sources,
        and EXTRACTION_CONFLICT flags where disagreement occurs.
    """
    hard_set = set(hard_attributes or [])
    stat_set = set(statutory_attributes or [])
    aux = aux_attrs or {}

    validated: dict[str, ExtractedValue] = {}
    all_keys = set(rule_attrs.keys()) | set(aux.keys())

    for key in all_keys:
        rule_val = rule_attrs.get(key)
        aux_val = aux.get(key)
        is_hard = key in hard_set
        is_statutory = key in stat_set

        # Case 1: Both Layer 1 and Layer 2 produced values
        if rule_val and rule_val.value is not None and aux_val and aux_val.value is not None:
            # Check physical validity first
            if any("INVALID" in f or "NON_STANDARD" in f for f in rule_val.flags):
                validated[key] = none_with(
                    flag=rule_val.flags[0] if rule_val.flags else "INVALID_RATING",
                    evidence_span=rule_val.evidence_span,
                )
                continue

            if values_agree(rule_val.value, aux_val.value):
                # Agreement on HARD / general attribute: boost confidence to 0.95+
                merged_flags = list(dict.fromkeys(rule_val.flags + aux_val.flags))
                validated[key] = ExtractedValue(
                    value=rule_val.value,
                    confidence=0.98 if is_hard else max(rule_val.confidence, 0.95),
                    source=f"{rule_val.source}+{aux_val.source}",
                    evidence_span=rule_val.evidence_span or aux_val.evidence_span,
                    flags=merged_flags,
                )
            else:
                # Disagreement!
                if is_hard:
                    # Per Section 4.3: Per HARD attribute disagree: null + EXTRACTION_CONFLICT
                    flags = list(dict.fromkeys(rule_val.flags + ["EXTRACTION_CONFLICT", "ATTRIBUTE_EXTRACTION_CONFLICT"]))
                    validated[key] = ExtractedValue(
                        value=None,
                        confidence=0.0,
                        source="cross_validator",
                        evidence_span=rule_val.evidence_span or aux_val.evidence_span,
                        flags=flags,
                    )
                else:
                    # Non-hard: rule extractor takes precedence but flagged with discrepancy
                    validated[key] = ExtractedValue(
                        value=rule_val.value,
                        confidence=min(rule_val.confidence, 0.75),
                        source=rule_val.source,
                        evidence_span=rule_val.evidence_span,
                        flags=list(dict.fromkeys(rule_val.flags + ["AUX_DISCREPANCY"])),
                    )

        # Case 2: Only Layer 1 (rule) produced value
        elif rule_val and rule_val.value is not None:
            if any("INVALID" in f or "NON_STANDARD" in f for f in rule_val.flags):
                validated[key] = none_with(
                    flag=rule_val.flags[0] if rule_val.flags else "INVALID_RATING",
                    evidence_span=rule_val.evidence_span,
                )
            else:
                # Single source (rule): confidence 0.70-0.90 per Section 4.3
                conf = rule_val.confidence if rule_val.confidence > 0 else 0.70
                validated[key] = ExtractedValue(
                    value=rule_val.value,
                    confidence=conf,
                    source=rule_val.source,
                    evidence_span=rule_val.evidence_span,
                    flags=list(rule_val.flags),
                )

        # Case 3: Only Layer 2 (aux/NER/LLM) produced value
        elif aux_val and aux_val.value is not None:
            # Enforce Invariant S12: Statutory/HARD attribute cannot be inferred
            # from ML/LLM alone without rule backing.
            if is_statutory or is_hard:
                validated[key] = ExtractedValue(
                    value=None,
                    confidence=0.0,
                    source=aux_val.source,
                    evidence_span=aux_val.evidence_span,
                    flags=list(dict.fromkeys(aux_val.flags + ["UNVERIFIED_ML_EXTRACTION", "S12_STATUTORY_RULE_REQUIRED"])),
                )
            else:
                # Non-hard/non-statutory: confidence capped at 0.70 per Section 4.3
                validated[key] = ExtractedValue(
                    value=aux_val.value,
                    confidence=min(aux_val.confidence, 0.70),
                    source=aux_val.source,
                    evidence_span=aux_val.evidence_span,
                    flags=list(aux_val.flags),
                )

        # Case 4: Neither produced a non-null value
        else:
            merged_flags = []
            if rule_val:
                merged_flags.extend(rule_val.flags)
            if aux_val:
                merged_flags.extend(aux_val.flags)
            span = (rule_val.evidence_span if rule_val else None) or (aux_val.evidence_span if aux_val else None)
            validated[key] = ExtractedValue(
                value=None,
                confidence=0.0,
                source="rule" if rule_val else "none",
                evidence_span=span,
                flags=list(dict.fromkeys(merged_flags)),
            )

    return validated
