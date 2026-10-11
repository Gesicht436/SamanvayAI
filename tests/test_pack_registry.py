"""Tests for Sector Pack Registry, identity modes, and extraction API endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.extractors.registry import (
    IdentityMode,
    SpecRegistry,
    default_registry,
)
from api.main import app
from api.security.jwt_auth import create_access_token


def test_load_all_packs_without_errors():
    """Verify registry loads all sector pack specifications without schema errors."""
    registry = SpecRegistry()
    count = registry.load_packs("packs")
    assert count >= 12

    subcats = registry.list_subcategories()
    expected_subcats = [
        "FASTENERS.BOLT",
        "FLANGES.FLANGE",
        "HEAVY.DRAWING_PART",
        "HEAVY.PUMP_CENTRIFUGAL",
        "MINING.OTR_TYRE",
        "PIPES.PIPE",
        "POWER.BOILER_TUBE",
        "POWER.BREAKER",
        "POWER.TRANSFORMER",
        "STEEL.MILL_ROLL",
        "STEEL.REFRACTORY",
        "VALVES.GATE",
    ]
    for subcat in expected_subcats:
        assert subcat in subcats, f"Missing expected subcategory: {subcat}"


def test_identity_modes_and_safety_flags():
    """Verify identity modes (PARAMETRIC, DRAWING) and safety properties."""
    registry = SpecRegistry()
    registry.load_packs("packs")

    # Parametric mode
    assert registry.get_identity_mode("VALVES.GATE") == IdentityMode.PARAMETRIC
    valves_spec = registry.get_spec("VALVES.GATE")
    assert valves_spec is not None
    assert valves_spec.safety_critical is True

    # Drawing mode
    assert registry.get_identity_mode("STEEL.MILL_ROLL") == IdentityMode.DRAWING
    assert registry.get_identity_mode("HEAVY.DRAWING_PART") == IdentityMode.DRAWING

    # Mandatory expiry tracking
    refractory_spec = registry.get_spec("STEEL.REFRACTORY")
    assert refractory_spec is not None
    assert refractory_spec.expiry_required is True

    tyre_spec = registry.get_spec("MINING.OTR_TYRE")
    assert tyre_spec is not None
    assert tyre_spec.expiry_required is True

    # Statutory attributes
    boiler_spec = registry.get_spec("POWER.BOILER_TUBE")
    assert boiler_spec is not None
    statutory_attrs = [a.name for a in boiler_spec.attributes if a.statutory]
    assert "ibr_cert" in statutory_attrs


def test_multi_attribute_extraction_pipeline():
    """Verify coordinated extraction of physical parsers and lexicons."""
    registry = SpecRegistry()
    registry.load_packs("packs")

    description = 'GATE VALVE 4" CL150 WCB FLG RF'
    extracted = registry.extract_attributes(description, "VALVES.GATE")

    assert extracted["size_nb"].value == 100
    assert extracted["size_nb"].confidence == 0.95
    assert extracted["size_nb"].evidence_span == (11, 12)

    assert extracted["pressure_class"].value == "ASME_150"
    assert extracted["pressure_class"].confidence == 0.95

    assert extracted["body_material"].value == "A216_WCB"
    assert extracted["body_material"].confidence == 0.95

    assert extracted["end_connection"].value == "FLANGED"
    assert extracted["end_connection"].confidence == 0.95

    assert extracted["facing"].value == "RF"
    assert extracted["facing"].confidence == 0.95


def test_pack_unmounting_resilience():
    """Verify principle 1.3.7: removing or isolating any pack leaves other packs fully functional."""
    # Isolated common pack registry
    common_registry = SpecRegistry()
    common_registry.load_packs("packs/common")
    subcats = common_registry.list_subcategories()
    assert "VALVES.GATE" in subcats
    assert "POWER.TRANSFORMER" not in subcats

    # Common extraction works seamlessly in isolation
    res = common_registry.extract_attributes("GATE VALVE 2 INCH CL300 WCB RF", "VALVES.GATE")
    assert res["size_nb"].value == 50
    assert res["pressure_class"].value == "ASME_300"
    assert res["body_material"].value == "A216_WCB"


def test_extract_api_endpoints():
    """Verify FastAPI /extract endpoints."""
    # Ensure default_registry is initialized
    default_registry.load_packs("packs")
    client = TestClient(app)

    # 1. GET /extract/specs
    res_specs = client.get("/extract/specs")
    assert res_specs.status_code == 200
    specs_list = res_specs.json()
    assert len(specs_list) >= 12
    subcat_names = [s["subcategory"] for s in specs_list]
    assert "VALVES.GATE" in subcat_names

    # 2. GET /extract/specs/VALVES.GATE
    res_detail = client.get("/extract/specs/VALVES.GATE")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["subcategory"] == "VALVES.GATE"
    assert detail["identity_mode"] == "PARAMETRIC"
    assert detail["safety_critical"] is True

    # 3. POST /extract
    payload = {"text": 'GATE VALVE 4" CL150 WCB FLG RF', "subcategory": "VALVES.GATE"}
    res_extract = client.post("/extract", json=payload)
    assert res_extract.status_code == 200
    data = res_extract.json()
    assert data["subcategory"] == "VALVES.GATE"
    assert data["identity_mode"] == "PARAMETRIC"
    attrs = data["attributes"]
    assert attrs["size_nb"]["value"] == 100
    assert attrs["pressure_class"]["value"] == "ASME_150"
    assert attrs["body_material"]["value"] == "A216_WCB"
    assert attrs["end_connection"]["value"] == "FLANGED"
    assert attrs["facing"]["value"] == "RF"


@pytest.mark.asyncio
async def test_extract_sync_endpoint_with_auth():
    """Verify POST /extract/sync requires maker token and syncs to database."""
    default_registry.load_packs("packs")
    client = TestClient(app)

    # Without token: 401
    res_unauth = client.post("/extract/sync")
    assert res_unauth.status_code == 401

    # With maker token: 200
    maker_token = create_access_token(
        sub="maker_user",
        org_id="OIL-1",
        role="MAKER",
        domains=["COMMON"],
    )
    headers = {"Authorization": f"Bearer {maker_token}"}

    res_sync = client.post("/extract/sync", headers=headers)
    assert res_sync.status_code == 200
    data = res_sync.json()
    assert data["status"] == "synchronized"
    assert data["subcategories_synced"] >= 12
    assert data["attributes_synced"] >= 50
