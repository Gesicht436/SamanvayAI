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


def test_comparator_when_condition_inapplicable_not_missing():
    """Verify conditional attributes with unsatisfied when-clauses are not marked MISSING."""
    from api.services.comparator import Verdict, compare_items

    # Refractory bricks: form=BRICK -> cement_class (when: 'form == CASTABLE') does not apply
    req = {
        "form": "BRICK",
        "material_class": "ALUMINA",
        "key_chemistry": "AL2O3_70",
        "shape_code": "STANDARD_9IN",
        "dimensions_mm": "230X115X75",
    }
    cand = {
        "form": "BRICK",
        "material_class": "ALUMINA",
        "key_chemistry": "AL2O3_70",
        "shape_code": "STANDARD_9IN",
        "dimensions_mm": "230X115X75",
    }
    result = compare_items(req, cand, subcategory="STEEL.REFRACTORY")
    assert "cement_class" in result.verdicts
    assert result.verdicts["cement_class"].verdict == Verdict.EXACT
    assert "Inapplicable due to when condition" in (result.verdicts["cement_class"].notes or "")
    assert "cement_class" not in result.missing_hard_attributes


def test_normalize_drawing_number_contract():
    """Verify Section 18.7.3: collapse internal spaces/hyphens, keep sheet and item suffixes."""
    from api.services.drawing import normalize_drawing_key, normalize_drawing_number

    # D-44120 and D44120 are the same
    assert normalize_drawing_number("D-44120") == "D44120"
    assert normalize_drawing_number("D 44120") == "D44120"
    assert normalize_drawing_number("d-44120") == "D44120"

    # Suffixes are preserved and distinct
    assert normalize_drawing_number("D-44120-1") == "D44120-1"
    assert normalize_drawing_number("D44120-1") == "D44120-1"
    assert normalize_drawing_number("D44120-2") == "D44120-2"
    assert normalize_drawing_number("D-44120-1") != normalize_drawing_number("D-44120-2")

    # Sheet suffix
    assert normalize_drawing_number("DRG-8890-SH1") == "DRG8890-SH1"

    # Normalized key includes owner
    k1 = normalize_drawing_key("bhel", "D-44120")
    k2 = normalize_drawing_key("BHEL", "D44120")
    assert k1 == ("BHEL", "D44120")
    assert k1 == k2


@pytest.mark.asyncio
async def test_drawing_revision_equivalence_flow_and_invariant_s13():
    """Verify Invariant S13, maker-checker constraint, and approved equivalence yielding Tier 1."""
    import uuid

    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.database import get_async_engine
    from api.main import app
    from api.models.entities import User
    from api.services.drawing import (
        approve_revision_equivalence,
        is_drawing_revision_equivalent,
        propose_revision_equivalence,
    )

    engine = get_async_engine()
    maker_id = uuid.uuid4()
    checker_id = uuid.uuid4()
    drg_no = f"DRG-{uuid.uuid4().hex[:6]}"

    async with AsyncSession(engine) as session:
        # Create maker and checker users to satisfy FK constraint
        maker = User(id=maker_id, subject=f"maker-{maker_id.hex[:6]}", role="MAKER", org_id="OIL-1")
        checker = User(id=checker_id, subject=f"checker-{checker_id.hex[:6]}", role="CHECKER", org_id="OIL-1")
        session.add_all([maker, checker])
        await session.commit()

        # 1. Initially rev A and rev B are not equivalent
        eq_initial = await is_drawing_revision_equivalent(session, "BHEL", drg_no, "A", "B")
        assert eq_initial is False

        # 2. Propose equivalence
        prop = await propose_revision_equivalence(
            db=session,
            drawing_owner="BHEL",
            drawing_no=drg_no,
            rev_a="A",
            rev_b="B",
            rationale="Drawing rev B only updated title block; geometry and metallurgy identical.",
            proposed_by=maker_id,
        )
        prop_id = prop.id
        await session.commit()
        assert prop_id is not None

        # 3. Maker cannot approve own proposal (rev_maker_ne_checker)
        with pytest.raises(ValueError, match="Maker cannot approve own"):
            await approve_revision_equivalence(session, prop_id, approved_by=maker_id)

        # 4. Checker approves
        appr = await approve_revision_equivalence(session, prop_id, approved_by=checker_id)
        appr_approved_by = appr.approved_by
        await session.commit()
        assert appr_approved_by == checker_id

        # 5. Now rev A and rev B are equivalent (bidirectional)
        assert await is_drawing_revision_equivalent(session, "BHEL", drg_no, "A", "B") is True
        assert await is_drawing_revision_equivalent(session, "BHEL", drg_no, "B", "A") is True

    # 6. Test via HTTP Tier endpoint
    client = TestClient(app)
    req_body = {
        "subcategory": "HEAVY.MADE_TO_DRAWING",
        "identity_mode": "DRAWING",
        "requirement_attributes": {
            "drawing_owner": "BHEL",
            "drawing_number": drg_no,
            "drawing_revision": "A",
            "material_grade": "IS_2062_E250",
            "item_name": "ROTOR SHAFT",
        },
        "candidate_attributes": {
            "drawing_owner": "BHEL",
            "drawing_number": drg_no,
            "drawing_revision": "B",
            "material_grade": "IS_2062_E250",
            "item_name": "ROTOR SHAFT",
        },
    }
    resp = client.post("/tier", json=req_body)
    assert resp.status_code == 200, resp.text
    tier_data = resp.json()
    # With approved equivalence in DB, Tier 1 is granted
    assert tier_data["tier"] == 1
    assert tier_data["stream_a_eligible"] is True


