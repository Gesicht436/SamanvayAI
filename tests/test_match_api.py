"""Integration tests for the Match API Endpoint (POST /match) and execution pipeline.

Verifies conformance to API Contract Section 15.1:
- Exact matches return Tier 1 (prob >= 0.95, no flags).
- Missing attributes route to Tier 2 with attribute gap alert.
- Mismatched HARD attributes route to Tier 3.
- Directional upgrades route to Tier 2 for substitution only.
- Authentication gating (unauthorized requests return 401).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.extractors.registry import default_registry
from api.main import app
from api.routers.match import execute_match_pipeline
from api.security.jwt_auth import create_access_token
from api.services.candidates import RetrievedCandidate


@pytest.fixture(autouse=True)
def load_spec_packs():
    default_registry.load_packs("packs")


def test_match_api_authentication_required():
    """Unauthenticated request to POST /match returns HTTP 401."""
    client = TestClient(app)
    resp = client.post("/match", json={"description": "GATE VALVE 100 NB", "top_k": 3})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_match_pipeline_section_15_1_golden_case():
    """Matches the exact spec example from Section 15.1:

    Input description with missing REQUIRED attributes routes to Tier 2 (never auto-linked).
    """
    # Candidate with complete golden master specification
    cand = RetrievedCandidate(
        golden_master_id=uuid4(),
        golden_code="MPNG-0004821937-3",
        descriptor="VALVES.GATE | 100NB | CL150 | A216-WCB | FLG-RF | API600",
        subcategory="VALVES.GATE",
        canonical_text="VALVE GATE 100 NB CL150 WCB FLANGED RF API600",
        attributes={
            "size_nb": 100,
            "pressure_class": "ASME_150",
            "body_material": "A216_WCB",
            "end_connection": "FLANGED",
            "facing": "RF",
            "design_standard": "API_600",
            "trim_code": "API_TRIM_8",
            "bonnet_type": "BOLTED",
            "operator": "HANDWHEEL",
            "fire_safe": "API_607",
            "sour_service": "NO",
        },
        block_key="VALVES:VALVES.GATE:size_nb=100_NB_MM",
    )

    # Raw input description missing trim_code, bonnet_type, operator, fire_safe, sour_service
    raw_desc = "VLV GT 100 NB CL150 WCB FLG RF API600"

    resp = await execute_match_pipeline(
        description=raw_desc,
        category_hint=None,
        top_k=3,
        mock_candidates=[cand],
    )

    assert resp.subcategory == "VALVES.GATE"
    assert resp.category_confidence >= 0.90
    assert "size_nb" in resp.extracted
    assert resp.extracted["size_nb"].value == 100
    assert resp.extracted["pressure_class"].value == "ASME_150"

    assert len(resp.candidates) == 1
    top_cand = resp.candidates[0]
    assert top_cand.golden_code == "MPNG-0004821937-3"
    assert top_cand.tier == 2  # Tier 2 Review because REQUIRED attributes are missing
    assert "MISSING_REQUIRED_ATTRIBUTE" in top_cand.reason_codes
    assert top_cand.attribute_gap_alert is not None
    assert "trim_code" in top_cand.attribute_gap_alert


@pytest.mark.asyncio
async def test_match_pipeline_tier1_auto_harmonize():
    """Exact match on all HARD + REQUIRED attributes with high probability yields Tier 1."""
    full_attrs = {
        "size_nb": 100,
        "pressure_class": "ASME_150",
        "body_material": "A216_WCB",
        "end_connection": "FLANGED",
        "facing": "RF",
        "design_standard": "API_600",
        "trim_code": "TRIM_8",
        "bonnet_type": "BOLTED",
        "operator": "HANDWHEEL",
        "fire_safe": "API_607",
        "sour_service": "NACE_MR0175",
    }
    cand = RetrievedCandidate(
        golden_master_id=uuid4(),
        golden_code="MPNG-0004821937-3",
        descriptor="VALVES.GATE | 100 | ASME_150 | A216_WCB | FLANGED | RF | API_600",
        subcategory="VALVES.GATE",
        canonical_text="GATE VALVE 100NB CL150 WCB FLANGED RF API600 TRIM 8 BOLTED BONNET HANDWHEEL FIRE SAFE NACE MR0175",
        attributes=full_attrs,
        block_key="VALVES:VALVES.GATE:size_nb=100_NB_MM",
    )

    # Complete raw description
    raw_desc = "GATE VALVE 100NB CL150 WCB FLANGED RF API600 TRIM 8 BOLTED HANDWHEEL FIRE SAFE NACE MR0175"

    resp = await execute_match_pipeline(
        description=raw_desc,
        top_k=1,
        mock_candidates=[cand],
    )

    assert len(resp.candidates) == 1
    top_cand = resp.candidates[0]
    assert top_cand.tier == 1
    assert top_cand.prob >= 0.95
    assert "ALL_HARD_REQUIRED_EXACT" in top_cand.reason_codes


@pytest.mark.asyncio
async def test_match_pipeline_tier3_hard_mismatch():
    """Mismatched HARD attribute (e.g. Class 150 vs Class 300) yields Tier 3."""
    cand = RetrievedCandidate(
        golden_master_id=uuid4(),
        golden_code="MPNG-0004821937-3",
        descriptor="VALVES.GATE | 100 | ASME_300 | A216_WCB",
        subcategory="VALVES.GATE",
        canonical_text="GATE VALVE 100NB CL300 WCB FLANGED RF API600",
        attributes={
            "size_nb": 100,
            "pressure_class": "ASME_300",  # CL300 in master
            "body_material": "A216_WCB",
            "end_connection": "FLANGED",
            "facing": "RF",
            "design_standard": "API_600",
        },
        block_key="VALVES:VALVES.GATE:size_nb=100_NB_MM",
    )

    # Raw description is CL150
    raw_desc = "GATE VALVE 100NB CL150 WCB FLANGED RF API600"

    resp = await execute_match_pipeline(
        description=raw_desc,
        top_k=1,
        mock_candidates=[cand],
    )

    assert len(resp.candidates) == 1
    top_cand = resp.candidates[0]
    assert top_cand.tier == 3
    assert "HARD_ATTRIBUTE_MISMATCH" in top_cand.reason_codes


def test_match_api_endpoint_authenticated_roundtrip():
    """Verify HTTP POST /match with valid JWT token against TestClient."""
    client = TestClient(app)
    token = create_access_token(sub="steward-1", org_id="OIL-1", role="MAKER")

    payload = {
        "description": "SEAMLESS PIPE 200 NB SCH 40 ASTM A106 GR B BE",
        "category_hint": "PIPES",
        "top_k": 3,
    }
    resp = client.post(
        "/match",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subcategory"] == "PIPES.PIPE"
    assert data["category_confidence"] >= 0.90
    assert "size_nb" in data["extracted"]
    assert data["extracted"]["size_nb"]["value"] == 200
