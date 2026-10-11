"""Unit and integration tests for catalog health scoring and dashboard (Section 20.1 & 15.2).

Verifies:
  - Multi-factor item completeness: HARD=2, REQUIRED=1, SOFT=0.
  - When-condition evaluation in attribute specs.
  - Non-blended indicators: classified share, uncertain items, flag rates, duplicate rate.
  - Top missing attributes per subcategory.
  - GET /dashboard/summary and GET /metrics/catalog-health endpoints.
  - GET /audit/verify endpoint.
"""

from starlette.testclient import TestClient

from api.main import app
from api.security.jwt_auth import create_access_token
from api.services.health import (
    _check_when_condition,
    compute_catalog_health,
    compute_item_completeness,
)


def test_when_condition_evaluation() -> None:
    """Verify conditional attribute applicability rules."""
    assert _check_when_condition("form in [BRICK, PRECAST_SHAPE]", {"form": "BRICK"}) is True
    assert _check_when_condition("form in [BRICK, PRECAST_SHAPE]", {"form": "CASTABLE"}) is False
    assert _check_when_condition("form == CASTABLE", {"form": "CASTABLE"}) is True
    assert _check_when_condition("form == CASTABLE", {"form": "RAMMING_MASS"}) is False
    assert _check_when_condition(None, {}) is True


def test_item_completeness_weighting() -> None:
    """Verify HARD=2, REQUIRED=1, SOFT=0 weighting in item completeness calculation."""
    # Valves Gate: HARD: size_nb (2), pressure_class (2), body_material (2), end_connection (2), facing (2), design_standard (2)
    # REQUIRED: trim_code (1), bonnet_type (1), operator (1), fire_safe (1), sour_service (1)
    # Total applicable weight = 12 (HARD) + 5 (REQUIRED) = 17
    extracted = {
        "size_nb": 100,
        "pressure_class": "ASME_150",
        "body_material": "A216_WCB",
        "end_connection": "FLANGED",
        "facing": "RF",
        "design_standard": "API_600",
        # Missing all 5 required attributes
    }
    res = compute_item_completeness("VALVES.GATE", extracted, extraction_flags=[])
    assert res["applicable_weight"] == 17
    assert res["populated_weight"] == 12
    # 12 / 17 = 0.7059
    assert res["completeness"] == 0.7059
    assert len(res["missing_attributes"]) == 5

    # If an attribute is flagged (e.g. EXTRACTION_CONFLICT on size_nb), it does NOT count towards populated
    res_flagged = compute_item_completeness("VALVES.GATE", extracted, extraction_flags=["SIZE_NB_CONFLICT"])
    assert res_flagged["populated_weight"] == 10  # 12 - 2
    assert res_flagged["completeness"] == round(10 / 17, 4)


def test_compute_catalog_health_multi_factor() -> None:
    """Verify catalog health aggregation returns non-blended distinct indicators."""
    items = [
        {
            "item_code": "V-001",
            "raw_description": "Gate valve 100 NB 150# A216 WCB RF API 600",
            "subcategory": "VALVES.GATE",
            "category_confidence": 0.95,
            "extracted": {
                "size_nb": 100,
                "pressure_class": "ASME_150",
                "body_material": "A216_WCB",
                "end_connection": "FLANGED",
                "facing": "RF",
                "design_standard": "API_600",
            },
            "extraction_flags": [],
            "golden_id": "00000000-0000-0000-0000-000000000001",
        },
        {
            "item_code": "V-002",
            "raw_description": "Gate valve 150 NB 300# WCB RF",
            "subcategory": "VALVES.GATE",
            "category_confidence": 0.92,
            "extracted": {
                "size_nb": 150,
                "pressure_class": "ASME_300",
                "body_material": "A216_WCB",
            },
            "extraction_flags": ["MISSING_STANDARD"],
            "golden_id": "00000000-0000-0000-0000-000000000001",  # Same golden master -> duplicate
        },
        {
            "item_code": "M-001",
            "raw_description": "General unknown electrical hardware",
            "subcategory": None,  # Unclassified item
            "category_confidence": 0.30,
            "extracted": {},
            "extraction_flags": ["CATEGORY_UNCERTAIN"],
            "golden_id": None,
        },
    ]

    report = compute_catalog_health(items, confidence_floor=0.60)
    assert report["total_items"] == 3
    assert report["classified_count"] == 2
    assert report["unclassified_count"] == 1
    assert report["classified_share"] == round(2 / 3, 4)
    assert report["category_uncertain_count"] == 1
    assert "MISSING_STANDARD" in report["extraction_flag_rate"]
    assert report["duplicate_rate"] == 3.0  # 3 items / 1 distinct golden master
    assert "VALVES.GATE" in report["top_missing_attributes"]
    assert len(report["unclassified_items"]) == 1


def test_dashboard_and_audit_endpoints() -> None:
    """Verify GET /dashboard/summary and GET /audit/verify return 200 with valid schema."""
    client = TestClient(app)

    # 1. Dashboard summary
    resp_dash = client.get("/dashboard/summary")
    assert resp_dash.status_code == 200
    dash_data = resp_dash.json()
    assert "queue_by_domain" in dash_data
    assert "tier_distribution" in dash_data
    assert "harmonization" in dash_data
    assert "catalog_health" in dash_data
    assert "ocr_readiness" in dash_data
    assert "audit_integrity" in dash_data

    # 2. Catalog health endpoint
    resp_health = client.get("/metrics/catalog-health")
    assert resp_health.status_code == 200
    health_data = resp_health.json()
    assert "catalog_completeness" in health_data
    assert "classified_share" in health_data

    # 3. Audit verify endpoint
    token = create_access_token(sub="admin-1", org_id="OIL-1", role="ADMIN")
    resp_audit = client.get("/audit/verify", headers={"Authorization": f"Bearer {token}"})
    assert resp_audit.status_code == 200
    audit_data = resp_audit.json()
    assert "verified_records" in audit_data
    assert "status" in audit_data
    assert audit_data["status"] == "OK"
