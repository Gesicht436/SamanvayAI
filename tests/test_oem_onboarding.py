"""Unit and integration tests for OEM catalogue onboarding wizard (Section 20.2).

Verifies:
  - OEM part number normalization and supersession lookup.
  - Bulk catalogue ingestion proposing DRAFT masters with OEM_PN identity mode.
  - Evidence spans generated for OEM and part numbers.
  - Maker review of draft proposals.
  - Checker approval with Maker != Checker and domain tag enforcement.
  - Publishing of golden masters and aliases with transactional audit logging.
"""

from starlette.testclient import TestClient

from api.database import SyncSessionLocal
from api.main import app
from api.models.entities import User
from api.security.jwt_auth import create_access_token
from api.services.oem import (
    extract_evidence_span,
    normalize_oem_name,
    normalize_oem_part_number,
)


def test_oem_normalization_and_evidence_spans() -> None:
    """Verify part number normalization and character offset evidence spans."""
    assert normalize_oem_part_number(" ABC-123/A ") == "ABC123A"
    assert normalize_oem_part_number("P-44012.01") == "P4401201"
    assert normalize_oem_name("  kirloskar   brothers ltd ") == "KIRLOSKAR BROTHERS LTD"

    text = "IMPELLER FOR PUMP MODEL OH2 PN ABC-123/A DRAWING D-44120"
    span_pn = extract_evidence_span(text, "ABC-123/A")
    assert span_pn != [0, 0]
    assert text[span_pn[0] : span_pn[1]] == "ABC-123/A"

    span_dwg = extract_evidence_span(text, "D-44120")
    assert span_dwg != [0, 0]
    assert text[span_dwg[0] : span_dwg[1]] == "D-44120"


def test_oem_onboarding_wizard_full_lifecycle() -> None:
    """End-to-end integration test of OEM onboarding wizard with Maker-Checker governance."""
    client = TestClient(app)

    with SyncSessionLocal() as db:
        maker = db.query(User).filter(User.role == "MAKER", User.org_id == "OIL-1").first()
        checker = db.query(User).filter(User.role == "CHECKER", User.org_id == "OIL-1").first()
        other_checker = db.query(User).filter(User.role == "CHECKER", User.org_id == "STEEL-1").first()
        maker_id = str(maker.id) if maker else "1f8f7307-7d59-4243-b190-337e62b20e7a"
        checker_id = str(checker.id) if checker else "c471e479-b9ac-425b-ac3e-0b8ebac7dba8"
        other_checker_id = str(other_checker.id) if other_checker else "794e95d6-afae-4402-85f9-2dc2eaaf5c7d"

    # 1. Setup Maker and Checker JWT tokens
    maker_token = create_access_token(
        sub=maker_id,
        org_id="OIL-1",
        role="MAKER",
        domains=["COMMON", "HEAVY_ENG"],
    )
    checker_token = create_access_token(
        sub=checker_id,
        org_id="OIL-1",
        role="CHECKER",
        domains=["COMMON", "HEAVY_ENG"],
    )
    maker_headers = {"Authorization": f"Bearer {maker_token}"}
    checker_headers = {"Authorization": f"Bearer {checker_token}"}

    # 2. Register a supersession rule: OLD-PUMP-01 is superseded by NEW-PUMP-02
    resp_super = client.post(
        "/oem/supersessions",
        headers=maker_headers,
        json={
            "manufacturer": "SULZER",
            "old_pn": "OLD-PUMP-01",
            "new_pn": "NEW-PUMP-02",
            "note": "Superseded per vendor bulletin 2026-B",
        },
    )
    assert resp_super.status_code == 200
    super_data = resp_super.json()
    assert super_data["manufacturer"] == "SULZER"
    assert super_data["old_pn"] == "OLDPUMP01"
    assert super_data["new_pn"] == "NEWPUMP02"

    # 3. Maker uploads OEM catalogue batch
    catalogue_rows = [
        {
            "part_number": "OLD-PUMP-01",
            "description": "IMPELLER FOR SULZER PUMP MODEL OH2 PN OLD-PUMP-01",
            "drawing_no": "D-99881",
            "parent_equipment_model": "SULZER OH2",
            "subcategory": "HEAVY.PUMP_SPARE",
        },
        {
            "part_number": "BEARING-RING-44",
            "description": "WEAR RING FOR SULZER PUMP PN BEARING-RING-44",
            "drawing_no": "D-99882",
            "parent_equipment_model": "SULZER OH2",
            "subcategory": "HEAVY.PUMP_SPARE",
        },
    ]

    resp_upload = client.post(
        "/oem/onboard",
        headers=maker_headers,
        json={
            "oem_name": "SULZER",
            "filename": "sulzer_spares_2026.json",
            "rows": catalogue_rows,
        },
    )
    assert resp_upload.status_code == 200
    batch_res = resp_upload.json()
    batch_id = batch_res["batch_id"]
    assert batch_res["total_rows"] == 2
    assert batch_res["superseded_count"] == 1  # OLD-PUMP-01 detected as superseded!

    # 4. Fetch proposals for the batch
    resp_props = client.get(f"/oem/batches/{batch_id}/proposals", headers=maker_headers)
    assert resp_props.status_code == 200
    proposals_data = resp_props.json()["proposals"]
    assert len(proposals_data) == 2

    # Check supersession applied on proposal 1
    p1 = next(p for p in proposals_data if p["raw_part_number"] == "OLD-PUMP-01")
    assert p1["effective_part_number"] == "NEWPUMP02"
    assert p1["superseded_from"] == "OLDPUMP01"
    assert "oem" in p1["evidence_spans"]

    # 5. Maker reviews proposal 2
    p2 = next(p for p in proposals_data if p["raw_part_number"] == "BEARING-RING-44")
    resp_review = client.post(
        f"/oem/proposals/{p2['id']}/review",
        headers=maker_headers,
        json={"action": "ACCEPT"},
    )
    assert resp_review.status_code == 200
    assert resp_review.json()["status"] == "ACCEPTED"

    # 6. Maker attempts to approve own batch -> HTTP 403 MAKER_CHECKER_VIOLATION
    resp_maker_approve = client.post(
        f"/oem/batches/{batch_id}/approve",
        headers=maker_headers,
        json={"rationale": "I am approving my own catalogue upload"},
    )
    assert resp_maker_approve.status_code == 403
    assert resp_maker_approve.json()["detail"]["code"] == "MAKER_CHECKER_VIOLATION"

    # 7. Checker without required domain tag -> HTTP 403 DOMAIN_TAG_REQUIRED
    checker_bad_domain_token = create_access_token(
        sub=other_checker_id,
        org_id="OIL-1",
        role="CHECKER",
        domains=["STEEL"],  # Lacks COMMON or HEAVY_ENG
    )
    resp_bad_domain = client.post(
        f"/oem/batches/{batch_id}/approve",
        headers={"Authorization": f"Bearer {checker_bad_domain_token}"},
        json={"rationale": "Attempting check without domain tag"},
    )
    assert resp_bad_domain.status_code == 403
    assert resp_bad_domain.json()["detail"]["code"] == "DOMAIN_TAG_REQUIRED"

    # 8. Authorized Checker approves batch
    resp_checker_approve = client.post(
        f"/oem/batches/{batch_id}/approve",
        headers=checker_headers,
        json={"rationale": "Datasheet and OEM catalogue verified against Sulzer pump manual"},
    )
    assert resp_checker_approve.status_code == 200
    approve_data = resp_checker_approve.json()
    assert approve_data["status"] == "COMPLETED"
    assert approve_data["published_masters_count"] == 2
    assert "audit_seq" in approve_data
    assert "audit_hash" in approve_data
