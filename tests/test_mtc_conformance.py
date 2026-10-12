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

import json
import re
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.entities import GradeReference, StockLot
from api.security.jwt_auth import create_access_token
from api.services.mtc import (
    _clean_chem_header,
    compute_ce_iiw,
    compute_pren,
    evaluate_mtc_conformance,
    get_grade_limits,
    parse_mtc_text_to_chemistry,
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


def test_mtc_verified_lot_and_grade_seeds_present():
    """Verify grade_reference starter rows are present and stock_lots.mtc_verified is boolean."""
    from sqlalchemy import select

    from api.database import SyncSessionLocal
    from api.models.entities import GradeReference, StockLot

    with SyncSessionLocal() as session:
        # 1. Verify starter grades seeded in DB
        grades = session.scalars(select(GradeReference.grade).distinct()).all()
        assert "ASTM A105" in grades
        assert "ASTM A216 WCB" in grades
        assert "ASTM A182 F51" in grades
        assert "API 5L X52" in grades

        # Invariant S15: seeded rows MUST have verified = False until checked
        unverified_count = session.scalars(
            select(GradeReference).where(GradeReference.verified.is_(False))
        ).all()
        assert len(unverified_count) >= 60

        # 2. Verify StockLot entity has mtc_verified column
        lot = StockLot(
            org_id="OIL-1",
            batch_no="HEAT-TEST-VERIFY-1",
            mtc_verified=False,
        )
        assert lot.mtc_verified is False


def test_mtc_sample_pdf_fixtures_extraction_both_modes():
    """Verify that all sample MTC/Challan PDFs extract chemistry and mechanical values matching ground truth

    using both plain text extraction and layout/sorted-block extraction.
    """
    fixtures_dir = Path(__file__).parent / "fixtures" / "mtc"
    gt_file = fixtures_dir / "sample_mtc_ground_truth.json"
    assert gt_file.exists(), "sample_mtc_ground_truth.json must exist"

    ground_truth = json.loads(gt_file.read_text(encoding="utf-8"))

    for item in ground_truth:
        fname = item["filename"]
        pdf_path = fixtures_dir / fname
        assert pdf_path.exists(), f"Sample PDF {fname} must exist"

        doc = pymupdf.open(pdf_path)

        # Mode 1: Plain text extraction
        plain_text = "".join(page.get_text("text") for page in doc)
        chem_plain, mech_plain, _meta_plain, _flags_plain = parse_mtc_text_to_chemistry(plain_text)

        # Mode 2: Layout/sorted blocks extraction
        layout_lines: list[str] = []
        for page in doc:
            blocks = page.get_text("blocks")
            sorted_blocks = sorted(blocks, key=lambda b: (round(b[1] / 10) * 10, b[0]))
            for b in sorted_blocks:
                layout_lines.append(b[4])
        layout_text = "\n".join(layout_lines)
        chem_layout, mech_layout, _meta_layout, _flags_layout = parse_mtc_text_to_chemistry(layout_text)

        # Verify chemistry against ground truth
        expected_chem_headers = [_clean_chem_header(h) for h in item["chemical"][0]]
        expected_chem_vals = [float(re.sub(r"(?<=\d),(?=\d)", ".", v)) for v in item["chemical"][1]]
        for h, v in zip(expected_chem_headers, expected_chem_vals, strict=False):
            assert h is not None, f"Could not clean header {h}"
            assert chem_plain.get(h) == v, f"{fname} plain text mismatch for element {h}: {chem_plain.get(h)} != {v}"
            assert chem_layout.get(h) == v, f"{fname} layout text mismatch for element {h}: {chem_layout.get(h)} != {v}"

        # Verify mechanical properties against ground truth
        mech_headers = item["mechanical"][0]
        mech_vals = item["mechanical"][1]

        if "Yield (MPa)" in mech_headers:
            y_val = float(mech_vals[mech_headers.index("Yield (MPa)")])
            assert mech_plain.get("yield_mpa") == y_val
            assert mech_layout.get("yield_mpa") == y_val

        if "Tensile (MPa)" in mech_headers:
            t_val = float(mech_vals[mech_headers.index("Tensile (MPa)")])
            assert mech_plain.get("tensile_mpa") == t_val
            assert mech_layout.get("tensile_mpa") == t_val

        if "Elongation (%)" in mech_headers:
            e_val = float(mech_vals[mech_headers.index("Elongation (%)")])
            assert mech_plain.get("elongation_pct") == e_val
            assert mech_layout.get("elongation_pct") == e_val

        if "Hardness (HBW)" in mech_headers:
            h_val = float(mech_vals[mech_headers.index("Hardness (HBW)")])
            assert mech_plain.get("hardness") == {"scale": "HBW", "value": h_val}
            assert mech_layout.get("hardness") == {"scale": "HBW", "value": h_val}

        if "Hardness (HRC)" in mech_headers:
            h_val = float(mech_vals[mech_headers.index("Hardness (HRC)")])
            assert mech_plain.get("hardness") == {"scale": "HRC", "value": h_val}
            assert mech_layout.get("hardness") == {"scale": "HRC", "value": h_val}

        if "Hydro Shell (bar)" in mech_headers:
            hs_val = float(mech_vals[mech_headers.index("Hydro Shell (bar)")])
            assert mech_plain.get("hydro_shell_bar") == hs_val
            assert mech_layout.get("hydro_shell_bar") == hs_val

        if "Visual Inspection" in mech_headers:
            vis_val = mech_vals[mech_headers.index("Visual Inspection")].upper()
            assert mech_plain.get("visual") == vis_val
            assert mech_layout.get("visual") == vis_val


def test_mtc_decimal_comma_table_without_splitting():
    """Regression test: decimal commas like '0,21 1,15' must not be split on comma into 'C=0, Mn=21'."""
    text_content = (
        "MILL TEST CERTIFICATE EN 10204 3.1\n"
        "CHEMICAL COMPOSITION (%)\n"
        "C% Mn% Si% P% S%\n"
        "0,21 1,15 0,35 0,018 0,012\n"
        "MECHANICAL PROPERTIES\n"
        "Yield (MPa) Tensile (MPa) Elongation (%)\n"
        "310 520 28,5\n"
    )
    chem, mech, _meta, _flags = parse_mtc_text_to_chemistry(text_content)
    assert chem["C"] == 0.21, f"Expected C=0.21, got {chem.get('C')}"
    assert chem["Mn"] == 1.15, f"Expected Mn=1.15, got {chem.get('Mn')}"
    assert chem["Si"] == 0.35, f"Expected Si=0.35, got {chem.get('Si')}"
    assert chem["P"] == 0.018, f"Expected P=0.018, got {chem.get('P')}"
    assert chem["S"] == 0.012, f"Expected S=0.012, got {chem.get('S')}"
    assert mech["elongation_pct"] == 28.5


def test_mtc_b16_5_is_not_misread_as_boron():
    """Regression test: 'B16.5' standard citation must never be extracted as Boron (B=16.5)."""
    text_content = (
        "MATERIAL TEST REPORT\n"
        "STANDARD: ASME B16.5 / ASTM A105\n"
        "DESCRIPTION: FLANGE WELD NECK 4 INCH CLASS 300\n"
        "HEAT NO: HT-99881\n"
        "CHEMICAL ANALYSIS:\n"
        "C: 0.20%\n"
        "Mn: 0.90%\n"
        "Si: 0.25%\n"
        "P: 0.015%\n"
        "S: 0.010%\n"
    )
    chem, _mech, _meta, _flags = parse_mtc_text_to_chemistry(text_content)
    assert chem.get("B") is None, f"Boron was erroneously extracted from B16.5: {chem.get('B')}"
    assert chem["C"] == 0.20
    assert chem["Mn"] == 0.90


def test_mtc_grade_limits_f316_vs_f316l_carbon_distinction():
    """Verify that grade specifications strictly distinguish ASTM A182 F316 (C max 0.080%)

    from ASTM A182 F316L (C max 0.030% per ASTM A182 Table 2).
    """
    limits_f316 = get_grade_limits("ASTM A182 F316")
    limits_f316l = get_grade_limits("ASTM A182 F316L")

    assert limits_f316 is not None
    assert limits_f316l is not None

    c_limit_316 = next(item for item in limits_f316 if item["property"] == "C")
    c_limit_316l = next(item for item in limits_f316l if item["property"] == "C")

    assert c_limit_316["max_value"] == 0.080
    assert c_limit_316l["max_value"] == 0.030

    # A chemistry with C = 0.035%:
    # Conforms to F316 (0.035 <= 0.080)
    # Fails for F316L (0.035 > 0.030)
    assert 0.035 <= c_limit_316["max_value"]
    assert 0.035 > c_limit_316l["max_value"]


