"""Tests for stewardship governance, Maker-Checker rules, domain tags, and feedback capture.

Validates:
- Proposer != Approver invariant (Maker-Checker rule)
- Domain-tag enforcement on safety-critical subcategories
- Task approval and execution of domain actions (LINK, CREATE_MASTER, MERGE)
- Feedback example recording (label=True on approve, label=False on reject)
- Transactional audit log generation on task lifecycle transitions
"""

import random
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.verhoeff import make_code
from api.database import get_async_engine
from api.extractors.registry import default_registry
from api.main import app
from api.models import AuditLog, FeedbackExample, GoldenMaster, RawItem
from api.security.jwt_auth import create_access_token


@pytest.fixture(autouse=True)
def ensure_packs_loaded():
    default_registry.load_packs("packs")


@pytest.fixture
async def async_session():
    engine = get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


def _create_token(
    sub: str,
    org: str = "OIL-1",
    role: str = "MAKER",
    domains: list[str] | None = None,
) -> str:
    return create_access_token(
        sub=sub,
        org_id=org,
        role=role,
        domains=domains or ["COMMON"],
        display_name=f"User {sub}",
    )


@pytest.mark.asyncio
async def test_maker_proposes_link_task_and_lists_tasks(async_session: AsyncSession):
    """Maker creates a LINK task and verifies it appears in OPEN state."""
    client = TestClient(app)

    # Create raw item
    raw = RawItem(
        org_id="OIL-1",
        raw_payload={"item_code": "VALVE-RAW-001"},
        raw_description="GATE VALVE 2 INCH 150# WCB FLANGED",
        subcategory="VALVES.GATE",
        status="PENDING",
    )
    async_session.add(raw)

    # Create master
    master = GoldenMaster(
        code=make_code(random.randint(100_000_000, 999_999_999)),
        descriptor="VALVES.GATE | 50 | ASME_150 | A216_WCB",
        status="ACTIVE",
        major_category="VALVES",
        subcategory="VALVES.GATE",
        block_key="VALVES.GATE:50:ASME_150:A216_WCB",
        canonical_text="GATE VALVE 2 INCH 150# WCB FLANGED RF",
        canonical_uom="EA",
        attributes={"size_nb": 50, "pressure_class": "ASME_150"},
    )
    async_session.add(master)
    await async_session.commit()

    maker_token = _create_token("usr-maker-test-1", role="MAKER", domains=["COMMON"])

    # 1. Propose LINK task
    resp = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {maker_token}"},
        json={
            "kind": "LINK",
            "raw_id": str(raw.id),
            "payload": {
                "golden_id": str(master.id),
                "subcategory": "VALVES.GATE",
                "features": {"attr_agree_ratio": 1.0, "trigram_sim": 0.95},
            },
            "reason_codes": ["STEWARD_MANUAL_LINK"],
        },
    )
    assert resp.status_code == 201, resp.text
    task_data = resp.json()
    task_id = task_data["id"]
    assert task_data["kind"] == "LINK"
    assert task_data["state"] == "OPEN"
    assert task_data["raw_id"] == str(raw.id)

    # 2. List tasks
    list_resp = client.get(
        "/tasks?state=OPEN&kind=LINK",
        headers={"Authorization": f"Bearer {maker_token}"},
    )
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert any(t["id"] == task_id for t in tasks)

    # 3. Get single task
    get_resp = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {maker_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id


@pytest.mark.asyncio
async def test_maker_checker_violation_proposer_cannot_approve(async_session: AsyncSession):
    """Verifies Maker != Checker: Proposer attempting to approve own task is rejected with 403."""
    client = TestClient(app)
    same_user_sub = "usr-proposer-same-1"
    token = _create_token(same_user_sub, role="MAKER", domains=["COMMON"])

    # Propose task
    resp = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "kind": "LINK",
            "payload": {
                "golden_id": str(uuid.uuid4()),
                "subcategory": "VALVES.GATE",
            },
        },
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # Generate token for the same user with CHECKER role
    checker_token_same_user = _create_token(same_user_sub, role="CHECKER", domains=["COMMON"])

    # Attempt to approve
    approve_resp = client.post(
        f"/tasks/{task_id}/approve",
        headers={"Authorization": f"Bearer {checker_token_same_user}"},
        json={"rationale": "Self approval attempt"},
    )
    assert approve_resp.status_code == 403
    err = approve_resp.json()["detail"]
    assert err["code"] == "MAKER_CHECKER_VIOLATION"


@pytest.mark.asyncio
async def test_domain_tag_enforcement_on_safety_critical(async_session: AsyncSession):
    """Verifies Checker without matching domain tag cannot approve safety-critical task."""
    client = TestClient(app)

    maker_token = _create_token("usr-maker-dom-1", role="MAKER", domains=["COMMON"])

    # Propose task for POWER.TRANSFORMER (safety-critical, segment: [POWER])
    resp = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {maker_token}"},
        json={
            "kind": "CREATE_MASTER",
            "payload": {
                "subcategory": "POWER.TRANSFORMER",
                "attributes": {"rating_kva": 25000, "hv_kv": 33.0, "lv_kv": 11.0},
            },
        },
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # Checker without "POWER" domain tag (only "STEEL", "MINING")
    checker_no_domain = _create_token("usr-checker-nodom-1", role="CHECKER", domains=["STEEL", "MINING"])

    bad_approve = client.post(
        f"/tasks/{task_id}/approve",
        headers={"Authorization": f"Bearer {checker_no_domain}"},
        json={"rationale": "Attempting approval without POWER domain"},
    )
    assert bad_approve.status_code == 403
    err = bad_approve.json()["detail"]
    assert err["code"] == "DOMAIN_TAG_REQUIRED"
    assert "POWER" in err["required"]

    # Checker WITH "POWER" domain tag
    checker_with_domain = _create_token("usr-checker-hasdom-1", role="CHECKER", domains=["POWER", "COMMON"])

    good_approve = client.post(
        f"/tasks/{task_id}/approve",
        headers={"Authorization": f"Bearer {checker_with_domain}"},
        json={"rationale": "Authorized power engineer approved"},
    )
    assert good_approve.status_code == 200
    assert good_approve.json()["state"] == "APPROVED"


@pytest.mark.asyncio
async def test_checker_approves_task_records_feedback_and_audit(async_session: AsyncSession):
    """Verifies approval executes action, records FeedbackExample (label=True), and writes AuditLog."""
    client = TestClient(app)

    # Create raw item
    raw = RawItem(
        org_id="OIL-1",
        raw_payload={"item_code": "PUMP-RAW-001"},
        raw_description="CENTRIFUGAL PROCESS PUMP 150 M3/HR",
        subcategory="HEAVY.PUMP_CENTRIFUGAL",
        status="PENDING",
    )
    async_session.add(raw)
    await async_session.commit()

    maker_token = _create_token("usr-maker-pumps-1", role="MAKER", domains=["HEAVY_ENG"])

    # Propose CREATE_MASTER task
    create_resp = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {maker_token}"},
        json={
            "kind": "CREATE_MASTER",
            "raw_id": str(raw.id),
            "payload": {
                "subcategory": "HEAVY.PUMP_CENTRIFUGAL",
                "attributes": {
                    "flow_m3h": 150.0,
                    "head_m": 80.0,
                    "pump_type": "CENTRIFUGAL",
                    "design_standard": "API_610",
                },
                "features": {"attr_agree_ratio": 1.0},
            },
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    checker_token = _create_token("usr-checker-pumps-1", role="CHECKER", domains=["HEAVY_ENG"])

    approve_resp = client.post(
        f"/tasks/{task_id}/approve",
        headers={"Authorization": f"Bearer {checker_token}"},
        json={"rationale": "Approved centrifugal pump master creation"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["state"] == "APPROVED"

    # Verify FeedbackExample row exists with label=True
    async with AsyncSession(get_async_engine()) as session:
        feedback_stmt = select(FeedbackExample).where(FeedbackExample.raw_id == raw.id)
        feedback_rows = list((await session.execute(feedback_stmt)).scalars().all())
        assert len(feedback_rows) >= 1
        assert feedback_rows[0].label is True

        # Verify raw item is linked
        refreshed_raw = await session.get(RawItem, raw.id)
        assert refreshed_raw.status == "LINKED"
        assert refreshed_raw.golden_id is not None

        # Verify AuditLog recorded task approval
        audit_stmt = select(AuditLog).where(
            AuditLog.entity == "steward_tasks",
            AuditLog.entity_id == str(task_id),
            AuditLog.action == "STEWARD_TASK_APPROVE",
        )
        audit_rows = list((await session.execute(audit_stmt)).scalars().all())
        assert len(audit_rows) >= 1


@pytest.mark.asyncio
async def test_checker_rejects_task_records_negative_feedback(async_session: AsyncSession):
    """Verifies rejection records FeedbackExample (label=False) and updates state to REJECTED."""
    client = TestClient(app)

    maker_token = _create_token("usr-maker-rej-1", role="MAKER", domains=["COMMON"])
    checker_token = _create_token("usr-checker-rej-1", role="CHECKER", domains=["COMMON"])

    # Create real raw item
    raw = RawItem(
        org_id="OIL-1",
        raw_payload={"item_code": "REJ-ITEM-001"},
        raw_description="GATE VALVE 4 INCH 300# WCB FLANGED",
        subcategory="VALVES.GATE",
        status="PENDING",
    )
    async_session.add(raw)
    await async_session.commit()

    dummy_golden_id = uuid.uuid4()

    resp = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {maker_token}"},
        json={
            "kind": "LINK",
            "raw_id": str(raw.id),
            "payload": {
                "golden_id": str(dummy_golden_id),
                "subcategory": "VALVES.GATE",
                "features": {"attr_agree_ratio": 0.5},
            },
        },
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    reject_resp = client.post(
        f"/tasks/{task_id}/reject",
        headers={"Authorization": f"Bearer {checker_token}"},
        json={"rationale": "Mismatched rating; rejecting proposal"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["state"] == "REJECTED"

    # Verify FeedbackExample row exists with label=False
    async with AsyncSession(get_async_engine()) as session:
        feedback_stmt = select(FeedbackExample).where(FeedbackExample.raw_id == raw.id)
        feedback_rows = list((await session.execute(feedback_stmt)).scalars().all())
        assert len(feedback_rows) >= 1
        assert feedback_rows[0].label is False
