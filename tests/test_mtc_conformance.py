"""Test suite for MTC Chemistry extraction, derived CE/PREN metrics, and Invariant S15 conformance.

Enforces Section 10.2:
- Extraction of 17 chemical elements with decimal comma handling.
- Out-of-bounds chemistry values (<0, >100, sum>100) become None with CHEM_OUT_OF_RANGE.
- Derived metrics CE_IIW and PREN computed strictly when all required constituents are present;
  missing elements are NEVER treated as zero.
- Worked check from spec: C 0.21, Mn 0.88, Cr 0.08, Mo 0.02, V 0.01, Ni 0.05, Cu 0.12 gives CE_IIW = 0.390.
- Safety Invariant S15: An MTC never yields CONFORMS against an unverified reference row,
  and lot is marked MTC-verified only by CONFORMS plus a heat/batch number match.
- Endpoint: POST /docs/{id}/mtc.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.entities import GradeReference, StockLot
from api.security.jwt_auth import create_access_token
from api.services.mtc import (
    compute_ce_iiw,
    compute_pren,
    evaluate_mtc_conformance,
    sanitize_chemistry,
)

client = TestClient(app)


def test_chemistry_decimal_comma_and_bounds():
    """Verify chemistry parsing handles decimal commas and flags out-of-bounds values."""
    raw = {
        "C": "0,21",
        "Mn": "0,88",
        "Si": "0.25",
        "P": "105.0",  # Out of range > 100
        "S": "-0.01",  # Out of range < 0
    }
    clean, flags = sanitize_chemistry(raw)

    assert clean["C"] == 0.21
    assert clean["Mn"] == 0.88
    assert clean["Si"] == 0.25
    assert clean["P"] is None
    assert clean["S"] is None
    assert "CHEM_OUT_OF_RANGE_P" in flags
    assert "CHEM_OUT_OF_RANGE_S" in flags


def test_derived_ce_iiw_worked_check():
    """Verify CE_IIW formula against the specsheet worked test:

    C 0.21, Mn 0.88, Cr 0.08, Mo 0.02, V 0.01, Ni 0.05, Cu 0.12 gives CE_IIW = 0.390.
    """
    chem = {
        "C": 0.21,
        "Mn": 0.88,
        "Cr": 0.08,
        "Mo": 0.02,
        "V": 0.01,
        "Ni": 0.05,
        "Cu": 0.12,
    }
    ce, flags = compute_ce_iiw(chem)
    assert flags == []
    assert ce == 0.390


def test_derived_ce_iiw_missing_element_incomplete():
    """Strict Rule: Missing element in CE_IIW is NEVER treated as zero; yields CE_INCOMPLETE."""
    # Mo is missing
    chem_missing_mo = {
        "C": 0.21,
        "Mn": 0.88,
        "Cr": 0.08,
        "Mo": None,  # Missing
        "V": 0.01,
        "Ni": 0.05,
        "Cu": 0.12,
    }
    ce, flags = compute_ce_iiw(chem_missing_mo)
    assert ce is None
    assert "CE_INCOMPLETE" in flags


def test_derived_pren_worked_and_incomplete():
    """Verify PREN = Cr + 3.3*Mo + 16*N and strict missing check."""
    # Complete duplex grade F51 chemistry
    chem_duplex = {"Cr": 22.0, "Mo": 3.1, "N": 0.18}
    pren, flags = compute_pren(chem_duplex)
    assert flags == []
    # 22.0 + 3.3*3.1 + 16*0.18 = 22.0 + 10.23 + 2.88 = 35.11 -> 35.1
    assert pren == 35.1

    # Missing Nitrogen
    chem_missing_n = {"Cr": 22.0, "Mo": 3.1, "N": None}
    pren_inc, flags_inc = compute_pren(chem_missing_n)
    assert pren_inc is None
    assert "PREN_INCOMPLETE" in flags_inc


@pytest.mark.asyncio
async def test_invariant_s15_unverified_reference_never_conforms(db_session):
    """Invariant S15: An MTC never yields CONFORMS against an unverified reference row."""
    org_id = "OIL-1"

    # Seed an UNVERIFIED reference row for ASTM A105
    ref_unverified = GradeReference(
        grade="ASTM_A105_TEST",
        product_form="FORGING",
        property="C",
        kind="CHEM",
        min_value=0.0,
        max_value=0.35,
        unit="%",
        verified=False,  # Unverified!
    )
    db_session.add(ref_unverified)
    await db_session.flush()

    res = await evaluate_mtc_conformance(
        session=db_session,
        org_id=org_id,
        grade_claimed="ASTM_A105_TEST",
        product_form="FORGING",
        heat_no="HT-94810-A",
        raw_chemistry={"C": "0.21", "Mn": "0.88", "Cr": "0.08", "Mo": "0.02", "V": "0.01", "Ni": "0.05", "Cu": "0.12"},
    )

    # Invariant S15 Assertions:
    assert res["conformance"] == "UNVERIFIED_REFERENCE"
    assert res["reference_verified"] is False
    assert res["requires_review"] is True
    assert "UNVERIFIED_REFERENCE_USED" in res["flags"]


@pytest.mark.asyncio
async def test_invariant_s15_verified_reference_conforms_and_links_lot(db_session):
    """Invariant S15: Lot marked MTC-verified ONLY by CONFORMS plus heat/batch number match."""
    org_id = "STEEL-1"
    heat_no = "HEAT-BATCH-8821"

    # 1. Create a stock lot with matching batch_no
    lot = StockLot(
        org_id=org_id,
        plant="PLANT-1",
        qty_remaining=50.0,
        batch_no=heat_no,
    )
    db_session.add(lot)

    # 2. Seed VERIFIED reference rows
    ref_c = GradeReference(
        grade="A105_VERIFIED",
        product_form="FORGING",
        property="C",
        kind="CHEM",
        min_value=0.0,
        max_value=0.35,
        unit="%",
        verified=True,  # Verified!
    )
    ref_mn = GradeReference(
        grade="A105_VERIFIED",
        product_form="FORGING",
        property="Mn",
        kind="CHEM",
        min_value=0.60,
        max_value=1.05,
        unit="%",
        verified=True,  # Verified!
    )
    db_session.add_all([ref_c, ref_mn])
    await db_session.flush()

    # 3. Evaluate MTC passing all limits
    res = await evaluate_mtc_conformance(
        session=db_session,
        org_id=org_id,
        grade_claimed="A105_VERIFIED",
        product_form="FORGING",
        heat_no=heat_no,
        raw_chemistry={"C": "0.21", "Mn": "0.88", "Cr": "0.08", "Mo": "0.02", "V": "0.01", "Ni": "0.05", "Cu": "0.12"},
    )

    assert res["conformance"] == "CONFORMS"
    assert res["reference_verified"] is True
    assert res["requires_review"] is False
    assert res["lot_id"] == str(lot.id)
    assert res["lot_mtc_verified"] is True


def test_mtc_api_endpoint():
    """Verify POST /docs/{id}/mtc endpoint integration."""
    token = create_access_token("user-mtc", "POWER-1", "CHECKER")
    headers = {"Authorization": f"Bearer {token}"}

    import uuid

    suffix = uuid.uuid4().hex[:8]
    file_bytes = f"MTC 3.1 CERTIFICATE HEAT NO HT-94810-A GRADE A105 {suffix}".encode()
    doc_resp = client.post(
        "/docs",
        data={"doc_type": "MTC_CERTIFICATE", "capture_channel": "UPLOAD"},
        files={"file": ("cert.txt", file_bytes, "text/plain")},
        headers=headers,
    )
    assert doc_resp.status_code == 200
    doc_id = doc_resp.json()["id"]

    # Evaluate MTC
    mtc_resp = client.post(
        f"/docs/{doc_id}/mtc",
        json={
            "grade_claimed": "A105",
            "product_form": "FORGING",
            "heat_no": "HT-94810-A",
            "chemistry": {
                "C": "0,21",
                "Mn": "0,88",
                "Si": 0.22,
                "P": 0.015,
                "S": 0.012,
                "Cr": 0.08,
                "Ni": 0.05,
                "Mo": 0.02,
                "Cu": 0.12,
                "V": 0.01,
            },
            "mechanical": {
                "yield_mpa": 285,
                "tensile_mpa": 530,
                "elongation_pct": 28.5,
                "hardness": {"scale": "HBW", "value": 156},
            },
            "heat_treatment": "NORMALIZED",
            "ndt": ["UT"],
        },
        headers=headers,
    )
    assert mtc_resp.status_code == 200
    data = mtc_resp.json()
    assert data["document_id"] == doc_id
    assert data["heat_no"] == "HT-94810-A"
    assert data["ce_iiw"] == 0.390
    assert data["ce_label"] == "INDICATIVE"
    assert data["chemistry"]["C"] == 0.21
    assert data["heat_treatment"] == "NORMALIZED"
    assert "UT" in data["ndt"]
