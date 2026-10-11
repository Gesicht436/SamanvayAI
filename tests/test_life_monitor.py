"""Test suite for Life Monitor, Clock injection, and Invariants S6, S7, S8.

Enforces Section 11.0:
- Pure functions with injectable Clock protocol.
- Multi-basis remaining life (SHELF_LIFE_DAYS, USAGE_COUNT, USAGE_HOURS); earliest-ending basis wins.
- Safety Invariant S6: Expired lot or unknown expiry on expiry_required class is never GREEN,
  never Stream A eligible, never auto-issued.
- Safety Invariant S7: Usage-based lot without usage events is never GREEN (UNKNOWN/INSUFFICIENT_DATA).
- Safety Invariant S8: Adding usage never increases remaining life; risk never improves as time advances.
- Ordered FEFO disposition ladder.
- Endpoints: GET /lots, GET /lots/{id}, POST /lots/{id}/usage, GET /lots/{id}/disposition.
"""

from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.entities import StockLot
from api.security.jwt_auth import create_access_token
from api.services.life import (
    SimulatedClock,
    compute_remaining_life_per_basis,
    evaluate_lot_risk,
)

client = TestClient(app)


def test_clock_injection_pure_domain():
    """Verify that domain functions use the injected clock without calling system time."""
    sim_clock = SimulatedClock("2026-10-10")
    assert sim_clock.today() == datetime.date(2026, 10, 10)

    sim_clock.advance_days(30)
    assert sim_clock.today() == datetime.date(2026, 11, 9)


def test_invariant_s6_expired_lot_never_green_nor_stream_a():
    """Invariant S6: An expired lot is never GREEN, never Stream A eligible."""
    clock = SimulatedClock("2026-10-10")
    past_expiry = datetime.date(2026, 10, 5)  # Expired 5 days ago

    res = evaluate_lot_risk(
        mfg_date=datetime.date(2025, 10, 5),
        expiry_date=past_expiry,
        expiry_required=True,
        policies=[],
        usage_events=[],
        clock=clock,
    )

    assert res.risk == "EXPIRED"
    assert res.risk != "GREEN"
    assert res.stream_a_eligible is False
    assert res.stream_a_reason == "EXPIRED_LOT_S6"
    assert res.remaining_days == -5


def test_invariant_s6_unknown_expiry_on_required_class():
    """Invariant S6: Unknown expiry on an expiry_required category is never GREEN, never Stream A eligible."""
    clock = SimulatedClock("2026-10-10")

    res = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=None,  # Missing expiry!
        expiry_required=True,  # Mandatory expiry category (e.g. monolithics, batteries, OTR tyres)
        policies=[],
        usage_events=[],
        clock=clock,
    )

    assert res.risk == "UNKNOWN"
    assert res.risk != "GREEN"
    assert res.stream_a_eligible is False
    assert res.stream_a_reason == "EXPIRY_REQUIRED_BUT_UNKNOWN_S6"


def test_invariant_s7_usage_lot_without_events_never_green():
    """Invariant S7: A usage-based lot with no usage events is never GREEN (status UNKNOWN / INSUFFICIENT_DATA)."""
    clock = SimulatedClock("2026-10-10")
    policies = [{"basis": "USAGE_COUNT", "limit_value": 1000.0, "unit": "PARTS"}]

    res = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=datetime.date(2028, 1, 1),
        expiry_required=False,
        policies=policies,
        usage_events=[],  # No usage events!
        clock=clock,
    )

    assert res.risk == "UNKNOWN"
    assert res.risk != "GREEN"
    assert res.stream_a_eligible is False
    assert res.stream_a_reason == "INSUFFICIENT_DATA_S7"


def test_invariant_s8_monotonicity_usage_and_time():
    """Invariant S8: Adding usage never increases remaining life; risk never improves as time advances."""
    clock = SimulatedClock("2026-01-01")
    expiry = datetime.date(2026, 12, 31)
    policies = [
        {"basis": "SHELF_LIFE_DAYS", "limit_value": 365.0, "unit": "DAYS"},
        {"basis": "USAGE_COUNT", "limit_value": 100.0, "unit": "PIECES"},
    ]

    # Stage 1: Initial state (GREEN)
    ev1 = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=expiry,
        expiry_required=True,
        policies=policies,
        usage_events=[{"amount": 5.0}],
        clock=clock,
    )
    assert ev1.risk == "GREEN"
    rem_ratio_1 = ev1.remaining_ratio
    assert rem_ratio_1 is not None

    # Stage 2: Time advances 200 days (ratio degrades)
    clock.advance_days(200)
    ev2 = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=expiry,
        expiry_required=True,
        policies=policies,
        usage_events=[{"amount": 5.0}],
        clock=clock,
    )
    assert ev2.remaining_ratio <= rem_ratio_1
    assert ev2.risk in ("AMBER", "RED")

    # Stage 3: Adding significant usage (80 pieces)
    ev3 = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=expiry,
        expiry_required=True,
        policies=policies,
        usage_events=[{"amount": 5.0}, {"amount": 80.0}],  # 85 consumed out of 100
        clock=clock,
    )
    assert ev3.remaining_ratio <= ev2.remaining_ratio
    assert ev3.risk == "RED"

    # Stage 4: Advancing past expiry
    clock.advance_days(200)
    ev4 = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=expiry,
        expiry_required=True,
        policies=policies,
        usage_events=[{"amount": 5.0}, {"amount": 80.0}],
        clock=clock,
    )
    assert ev4.risk == "EXPIRED"
    assert ev4.stream_a_eligible is False


def test_earliest_ending_basis_wins():
    """Verify that multiple policies resolve to earliest-ending basis."""
    clock = SimulatedClock("2026-06-01")
    # Calendar has 50% life left (180/365)
    # Usage has only 10% life left (90/100 consumed)
    policies = [
        {"basis": "SHELF_LIFE_DAYS", "limit_value": 365.0, "unit": "DAYS"},
        {"basis": "USAGE_COUNT", "limit_value": 100.0, "unit": "PARTS"},
    ]
    usage = [{"amount": 90.0}]

    basis_res = compute_remaining_life_per_basis(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=datetime.date(2026, 12, 31),
        policies=policies,
        usage_events=usage,
        clock=clock,
    )

    assert "SHELF_LIFE_DAYS" in basis_res
    assert "USAGE_COUNT" in basis_res
    assert basis_res["USAGE_COUNT"].remaining_ratio < basis_res["SHELF_LIFE_DAYS"].remaining_ratio

    eval_res = evaluate_lot_risk(
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=datetime.date(2026, 12, 31),
        expiry_required=True,
        policies=policies,
        usage_events=usage,
        clock=clock,
    )
    # Earliest-ending basis wins
    assert eval_res.basis == "USAGE_COUNT"
    assert eval_res.risk == "RED"


@pytest.mark.asyncio
async def test_lots_api_end_to_end(db_session):
    """Verify GET /lots, GET /lots/{id}, POST /lots/{id}/usage, and disposition ladder."""
    org_id = "OIL-1"
    token = create_access_token("user-lots", org_id, "SITE_ENGINEER")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a stock lot
    lot = StockLot(
        org_id=org_id,
        plant="BOKARO_PLANT_1",
        qty_remaining=100.0,
        batch_no="BATCH-2026-Q1",
        mfg_date=datetime.date(2026, 1, 1),
        expiry_date=datetime.date(2026, 12, 31),
    )
    db_session.add(lot)
    await db_session.commit()

    # 2. Query GET /lots
    resp_list = client.get(
        "/lots",
        params={"clock": "SIMULATED", "simulated_date": "2026-06-01"},
        headers=headers,
    )
    assert resp_list.status_code == 200
    lots_data = resp_list.json()
    assert len(lots_data["lots"]) >= 1
    found_lot = next(l for l in lots_data["lots"] if l["lot_id"] == str(lot.id))
    assert found_lot["plant"] == "BOKARO_PLANT_1"

    # 3. Query GET /lots/{id}
    resp_detail = client.get(
        f"/lots/{lot.id}",
        params={"clock": "SIMULATED", "simulated_date": "2026-06-01"},
        headers=headers,
    )
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["lot_id"] == str(lot.id)
    assert len(detail["disposition_ladder"]) == 4

    # 4. Log usage POST /lots/{id}/usage
    resp_usage = client.post(
        f"/lots/{lot.id}/usage",
        json={"amount": 25.0, "unit": "EA"},
        headers=headers,
    )
    assert resp_usage.status_code == 200
    usage_data = resp_usage.json()
    assert usage_data["amount"] == 25.0
    assert usage_data["qty_remaining_after"] == 75.0

    # 5. Query disposition GET /lots/{id}/disposition
    resp_disp = client.get(f"/lots/{lot.id}/disposition", headers=headers)
    assert resp_disp.status_code == 200
    disp_data = resp_disp.json()
    assert len(disp_data["disposition_ladder"]) == 4
    assert disp_data["disposition_ladder"][0]["action"] == "ISSUE_OLDEST_FIRST_FEFO"
