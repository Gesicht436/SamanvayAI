"""MTC (Material Test Certificate) evaluation and chemistry/mechanical analysis engine.

Enforces Section 10.2:
- Extraction of up to 17 chemical elements with decimal comma handling.
- Out-of-bounds chemistry values (<0, >100, sum>100) become None with CHEM_OUT_OF_RANGE.
- Derived metrics CE_IIW and PREN computed strictly when all required constituents are present;
  missing elements are NEVER treated as zero (Invariant S15).
- Conformance against grade_reference:
  Invariant S15: An MTC never yields CONFORMS against an unverified reference row.
  Lot is marked MTC-verified only by CONFORMS plus a heat/batch number match.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.entities import CertRecord, GradeReference, MtcResult, StockLot

logger = logging.getLogger(__name__)

CHEM_ELEMENTS = (
    "C",
    "Mn",
    "Si",
    "P",
    "S",
    "Cr",
    "Ni",
    "Mo",
    "Cu",
    "V",
    "Nb",
    "N",
    "Al",
    "W",
    "Co",
    "Ti",
    "B",
)

# Elements required for CE_IIW: C, Mn, Cr, Mo, V, Ni, Cu
CE_IIW_REQUIRED = ("C", "Mn", "Cr", "Mo", "V", "Ni", "Cu")

# Elements required for PREN: Cr, Mo, N
PREN_REQUIRED = ("Cr", "Mo", "N")


def parse_numeric_value(val: Any) -> float | None:
    """Parses a numeric value handling decimal commas and string representations."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", ".")
        # Match float or integer with optional sign
        match = re.search(r"[-+]?\d*\.?\d+", cleaned)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def sanitize_chemistry(raw_chem: dict[str, Any]) -> tuple[dict[str, float | None], list[str]]:
    """Sanitizes raw chemistry mapping for up to 17 elements.

    Rules:
    - Decimal commas handled ('0,21' -> 0.21).
    - Values outside [0, 100] become None with flag 'CHEM_OUT_OF_RANGE'.
    - If total sum of elements > 100, flag 'CHEM_SUM_EXCEEDS_100'.
    """
    clean_chem: dict[str, float | None] = {}
    flags: list[str] = []
    total_sum = 0.0

    for elem in CHEM_ELEMENTS:
        # Match case-insensitively in input dictionary
        val_raw = None
        for k, v in raw_chem.items():
            if k.strip().upper() == elem.upper():
                val_raw = v
                break

        if val_raw is not None:
            parsed = parse_numeric_value(val_raw)
            if parsed is None or parsed < 0.0 or parsed > 100.0:
                clean_chem[elem] = None
                flags.append(f"CHEM_OUT_OF_RANGE_{elem}")
            else:
                clean_chem[elem] = round(parsed, 4)
                total_sum += parsed
        else:
            clean_chem[elem] = None

    if total_sum > 100.0:
        flags.append("CHEM_SUM_EXCEEDS_100")

    return clean_chem, flags


def compute_ce_iiw(chemistry: dict[str, float | None]) -> tuple[float | None, list[str]]:
    """Computes Carbon Equivalent CE_IIW per Section 10.2:

    CE_IIW = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15

    Strict Rule: Computed ONLY when every requisite element is present.
    A missing element is NEVER treated as zero.
    Returns (ce_value, flags).
    """
    missing = [elem for elem in CE_IIW_REQUIRED if chemistry.get(elem) is None]
    if missing:
        return None, ["CE_INCOMPLETE"]

    c = chemistry["C"]  # type: ignore
    mn = chemistry["Mn"]  # type: ignore
    cr = chemistry["Cr"]  # type: ignore
    mo = chemistry["Mo"]  # type: ignore
    v = chemistry["V"]  # type: ignore
    ni = chemistry["Ni"]  # type: ignore
    cu = chemistry["Cu"]  # type: ignore

    ce = c + (mn / 6.0) + ((cr + mo + v) / 5.0) + ((ni + cu) / 15.0)
    return round(ce, 3), []


def compute_pren(chemistry: dict[str, float | None]) -> tuple[float | None, list[str]]:
    """Computes Pitting Resistance Equivalent Number (PREN) per Section 10.2:

    PREN = Cr + 3.3*Mo + 16*N

    Strict Rule: Computed ONLY when every requisite element is present.
    A missing element is NEVER treated as zero.
    Returns (pren_value, flags).
    """
    missing = [elem for elem in PREN_REQUIRED if chemistry.get(elem) is None]
    if missing:
        return None, ["PREN_INCOMPLETE"]

    cr = chemistry["Cr"]  # type: ignore
    mo = chemistry["Mo"]  # type: ignore
    n = chemistry["N"]  # type: ignore

    pren = cr + (3.3 * mo) + (16.0 * n)
    return round(pren, 1), []


async def evaluate_mtc_conformance(
    session: AsyncSession,
    org_id: str,
    grade_claimed: str,
    product_form: str = "FORGING",
    heat_no: str | None = None,
    raw_chemistry: dict[str, Any] | None = None,
    raw_mechanical: dict[str, Any] | None = None,
    heat_treatment: str | None = None,
    ndt: list[str] | None = None,
    document_id: UUID | None = None,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    """Evaluates MTC chemistry, mechanical properties, and conformance against grade_reference.

    Enforces Invariant S15:
    - An MTC never yields CONFORMS against an unverified reference row.
    - Lot is marked MTC-verified only by CONFORMS plus a heat/batch number match.
    """
    flags: list[str] = []

    # 1. Clean chemistry
    chemistry, chem_flags = sanitize_chemistry(raw_chemistry or {})
    flags.extend(chem_flags)

    # 2. Compute derived metrics
    ce_val, ce_flags = compute_ce_iiw(chemistry)
    flags.extend(ce_flags)

    pren_val, pren_flags = compute_pren(chemistry)
    flags.extend(pren_flags)

    # 3. Clean mechanical properties
    mechanical: dict[str, Any] = {}
    if raw_mechanical:
        for k, v in raw_mechanical.items():
            if isinstance(v, dict):
                sub_dict = {}
                for sk, sv in v.items():
                    sub_dict[sk] = parse_numeric_value(sv) if parse_numeric_value(sv) is not None else sv
                mechanical[k] = sub_dict
            else:
                parsed = parse_numeric_value(v)
                mechanical[k] = parsed if parsed is not None else v

    # 4. Fetch grade reference specifications
    stmt = select(GradeReference).where(GradeReference.grade.ilike(grade_claimed.strip()))
    res = await session.execute(stmt)
    ref_rows = res.scalars().all()

    property_verdicts: list[dict[str, Any]] = []
    has_unverified_ref = False
    all_passed = True
    any_failed = False
    has_required_checks = len(ref_rows) > 0

    if not ref_rows:
        conformance = "REQUIRES_REVIEW"
        reference_verified = False
        flags.append("NO_REFERENCE_SPECIFICATION")
    else:
        for ref in ref_rows:
            if not ref.verified:
                has_unverified_ref = True

            # Determine actual value from chemistry or mechanical
            actual_val = None
            prop_key = ref.property.upper()

            if ref.kind == "CHEM":
                for ck, cv in chemistry.items():
                    if ck.upper() == prop_key:
                        actual_val = cv
                        break
            elif ref.kind == "MECH":
                for mk, mv in mechanical.items():
                    if mk.upper() == prop_key:
                        actual_val = mv if not isinstance(mv, dict) else mv.get("value")
                        break

            # Verdict evaluation
            if actual_val is None:
                p_verdict = "NOT_REPORTED"
                all_passed = False
            else:
                passes_min = ref.min_value is None or actual_val >= float(ref.min_value)
                passes_max = ref.max_value is None or actual_val <= float(ref.max_value)
                if passes_min and passes_max:
                    p_verdict = "PASS"
                else:
                    p_verdict = "FAIL"
                    any_failed = True
                    all_passed = False

            property_verdicts.append(
                {
                    "property": ref.property,
                    "kind": ref.kind,
                    "reference_min": float(ref.min_value) if ref.min_value is not None else None,
                    "reference_max": float(ref.max_value) if ref.max_value is not None else None,
                    "actual": actual_val,
                    "unit": ref.unit,
                    "verified_reference": ref.verified,
                    "verdict": p_verdict,
                }
            )

        reference_verified = not has_unverified_ref

        # Invariant S15: An MTC never yields CONFORMS against an unverified reference row
        if has_unverified_ref:
            conformance = "UNVERIFIED_REFERENCE"
            flags.append("UNVERIFIED_REFERENCE_USED")
        elif any_failed:
            conformance = "FAILS"
        elif all_passed and has_required_checks:
            conformance = "CONFORMS"
        else:
            conformance = "INCOMPLETE"

    # 5. Check heat/batch number match against stock lots
    matched_lot_id: UUID | None = None
    lot_mtc_verified = False
    if heat_no and heat_no.strip():
        clean_heat = heat_no.strip()
        stmt_lot = select(StockLot).where(
            StockLot.org_id == org_id,
            StockLot.batch_no.ilike(clean_heat),
        )
        res_lot = await session.execute(stmt_lot)
        matched_lot = res_lot.scalar_one_or_none()
        if matched_lot:
            matched_lot_id = matched_lot.id
            # Invariant S15: lot is marked MTC-verified ONLY by CONFORMS plus a heat/batch number match
            if conformance == "CONFORMS":
                lot_mtc_verified = True

    # 6. Create cert_records row
    cert = CertRecord(
        org_id=org_id,
        lot_id=matched_lot_id,
        cert_type="MTC_3_1",
        cert_no=heat_no,
        issuer="MTC_ISSUER",
        verified=(conformance == "CONFORMS"),
    )
    session.add(cert)
    await session.flush()

    # 7. Create mtc_results row
    mtc_record = MtcResult(
        org_id=org_id,
        document_id=document_id,
        cert_id=cert.id,
        lot_id=matched_lot_id,
        heat_no=heat_no,
        grade_claimed=grade_claimed,
        chemistry=chemistry,
        mechanical=mechanical,
        ce_iiw=ce_val,
        pren=pren_val,
        heat_treatment=heat_treatment,
        ndt=ndt or [],
        flags=flags,
        conformance=conformance,
        reference_verified=reference_verified,
    )
    session.add(mtc_record)
    await session.flush()

    # 8. Record audit log
    audit_after = json.dumps(
        {
            "id": str(mtc_record.id),
            "grade_claimed": grade_claimed,
            "heat_no": heat_no,
            "conformance": conformance,
            "reference_verified": reference_verified,
            "lot_id": str(matched_lot_id) if matched_lot_id else None,
            "lot_mtc_verified": lot_mtc_verified,
            "ce_iiw": ce_val,
            "pren": pren_val,
            "flags": flags,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'MTC_EVALUATE', 'mtc_results', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(mtc_record.id),
            "after": audit_after,
            "rationale": f"MTC evaluated: conformance={conformance}, reference_verified={reference_verified} (S15)",
        },
    )

    return {
        "id": str(mtc_record.id),
        "document_id": str(document_id) if document_id else None,
        "heat_no": heat_no,
        "grade_claimed": grade_claimed,
        "chemistry": chemistry,
        "mechanical": mechanical,
        "ce_iiw": ce_val,
        "ce_label": "INDICATIVE" if ce_val is not None else None,
        "pren": pren_val,
        "flags": flags,
        "heat_treatment": heat_treatment,
        "ndt": ndt or [],
        "conformance": conformance,
        "reference_verified": reference_verified,
        "requires_review": conformance != "CONFORMS",
        "lot_id": str(matched_lot_id) if matched_lot_id else None,
        "lot_mtc_verified": lot_mtc_verified,
        "property_verdicts": property_verdicts,
    }
