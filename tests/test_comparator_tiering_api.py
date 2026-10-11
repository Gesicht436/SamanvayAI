"""Integration tests for /compare and /tier REST API endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.extractors.registry import default_registry
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_packs_loaded():
    default_registry.load_packs("packs")


def test_compare_endpoint_exact_match():
    """Verify POST /compare returns EXACT verdicts on identical valve attributes."""
    req_attrs = {
        "size_nb": 100,
        "pressure_class": "ASME_150",
        "body_material": "A216_WCB",
        "end_connection": "FLANGED",
        "facing": "RF",
        "design_standard": "API_600",
    }
    cand_attrs = dict(req_attrs)

    payload = {
        "subcategory": "VALVES.GATE",
        "requirement_attributes": req_attrs,
        "candidate_attributes": cand_attrs,
    }
    res = client.post("/compare", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["has_hard_mismatch"] is False
    assert data["has_missing_hard"] is False
    assert data["verdicts"]["size_nb"]["verdict"] == "EXACT"
    assert data["verdicts"]["pressure_class"]["verdict"] == "EXACT"
    assert data["verdicts"]["design_standard"]["verdict"] == "EXACT"


def test_compare_endpoint_missing_and_mismatch():
    """Verify POST /compare detects missing attributes and alerts."""
    req_attrs = {"size_nb": 100, "pressure_class": "ASME_150"}
    cand_attrs = {"size_nb": 150}  # size mismatch, pressure class missing

    payload = {
        "subcategory": "VALVES.GATE",
        "requirement_attributes": req_attrs,
        "candidate_attributes": cand_attrs,
    }
    res = client.post("/compare", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["has_hard_mismatch"] is True
    assert data["has_missing_hard"] is True
    assert "Missing:" in data["attribute_gap_alert"]


def test_compare_endpoint_directional_upgrade():
    """Verify POST /compare identifies directional substitution upgrades."""
    req_attrs = {"gas_group": "IIA", "temp_class": "T4"}
    cand_attrs = {"gas_group": "IIC", "temp_class": "T6"}  # Both are upgrades

    payload = {
        "subcategory": "MOTORS.EX",
        "requirement_attributes": req_attrs,
        "candidate_attributes": cand_attrs,
    }
    res = client.post("/compare", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["has_upgrade"] is True
    assert data["verdicts"]["gas_group"]["verdict"] == "UPGRADE"
    assert data["verdicts"]["temp_class"]["verdict"] == "UPGRADE"


def test_tier_endpoint_tier_1_auto():
    """Verify POST /tier returns Tier 1 for fully matching attributes and high probability."""
    attrs = {
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
        "sour_service": "NO",
    }
    payload = {
        "subcategory": "VALVES.GATE",
        "requirement_attributes": attrs,
        "candidate_attributes": attrs,
        "probability": 0.98,
    }
    res = client.post("/tier", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tier"] == 1
    assert data["stream_a_eligible"] is True
    assert data["requires_review"] is False


def test_tier_endpoint_tier_2_on_missing_or_flags():
    """Verify POST /tier routes to Tier 2 on missing attributes or extraction flags."""
    attrs = {"size_nb": 100, "pressure_class": "ASME_150"}
    payload = {
        "subcategory": "VALVES.GATE",
        "requirement_attributes": attrs,
        "candidate_attributes": attrs,
        "extraction_flags": ["EXTRACTION_CONFLICT"],
        "probability": 0.99,
    }
    res = client.post("/tier", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tier"] == 2
    assert data["requires_review"] is True
    assert "EXTRACTION_CONFLICT" in data["reason_codes"]


def test_tier_endpoint_tier_3_on_hard_mismatch():
    """Verify POST /tier routes to Tier 3 on HARD attribute mismatch."""
    req_attrs = {"size_nb": 100, "pressure_class": "ASME_150"}
    cand_attrs = {"size_nb": 150, "pressure_class": "ASME_150"}  # size 100 vs 150

    payload = {
        "subcategory": "VALVES.GATE",
        "requirement_attributes": req_attrs,
        "candidate_attributes": cand_attrs,
        "probability": 0.99,
    }
    res = client.post("/tier", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tier"] == 3
    assert data["stream_a_eligible"] is False
    assert "HARD_ATTRIBUTE_MISMATCH" in data["reason_codes"]
