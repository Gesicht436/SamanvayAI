"""Life monitor service and remaining life calculation engine.

Enforces Section 11.0:
- Pure functions with injectable Clock protocol (domain functions NEVER call datetime.now() directly).
- Bases: SHELF_LIFE_DAYS, USAGE_COUNT, USAGE_HOURS; earliest-ending basis wins.
- Risk states: GREEN, AMBER, RED, EXPIRED, UNKNOWN.
- Invariant S6: Expired lot or lot with unknown expiry on expiry_required class is never GREEN,
  never Stream A eligible, never auto-issued.
- Invariant S7: Usage-based lot with no usage events is never GREEN (INSUFFICIENT_DATA or UNKNOWN).
- Invariant S8: Adding usage never increases remaining life; risk never improves as time advances.
- Ordered FEFO disposition ladder.
"""

from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.entities import StockLot, UsageEvent

logger = logging.getLogger(__name__)


class Clock(Protocol):
    """Protocol for abstracting time in domain computations."""

    def now(self) -> datetime.datetime: ...

    def today(self) -> datetime.date: ...


class RealClock:
    """Production clock using real system UTC time."""

    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.UTC)

    def today(self) -> datetime.date:
        return datetime.datetime.now(datetime.UTC).date()


class SimulatedClock:
    """Injectable simulated clock for tests and deterministic simulation."""

    def __init__(self, current_time: datetime.datetime | datetime.date | str):
        if isinstance(current_time, str):
            if "T" in current_time:
                self._dt = datetime.datetime.fromisoformat(current_time)
            else:
                d = datetime.date.fromisoformat(current_time)
                self._dt = datetime.datetime.combine(d, datetime.time.min, tzinfo=datetime.UTC)
        elif isinstance(current_time, datetime.date) and not isinstance(current_time, datetime.datetime):
            self._dt = datetime.datetime.combine(current_time, datetime.time.min, tzinfo=datetime.UTC)
        else:
            self._dt = current_time

    def now(self) -> datetime.datetime:
        return self._dt

    def today(self) -> datetime.date:
        return self._dt.date()

    def advance_days(self, days: int) -> None:
        """Advances simulated time forward by given days."""
        self._dt += datetime.timedelta(days=days)


@dataclass
class BasisRemaining:
    basis: str
    limit_value: float
    consumed_value: float
    remaining_value: float
    remaining_ratio: float  # 0.0 to 1.0


@dataclass
class LifeEvaluationResult:
    lot_id: str
    risk: str  # GREEN, AMBER, RED, EXPIRED, UNKNOWN
    basis: str  # Earliest-ending basis
    remaining_days: int | None
    remaining_ratio: float | None
    stream_a_eligible: bool
    stream_a_reason: str | None
    near_expiry_path: bool
    reasons: list[str]
    disposition_ladder: list[dict[str, str]]


def compute_remaining_life_per_basis(
    mfg_date: datetime.date | None,
    expiry_date: datetime.date | None,
    policies: list[dict[str, Any]],
    usage_events: list[dict[str, Any]],
    clock: Clock,
) -> dict[str, BasisRemaining]:
    """Pure function calculating remaining life across all applicable policy bases."""
    current_date = clock.today()
    results: dict[str, BasisRemaining] = {}

    for pol in policies:
        basis = pol["basis"]
        limit_val = float(pol["limit_value"])

        if basis == "SHELF_LIFE_DAYS":
            target_expiry = expiry_date
            if not target_expiry and mfg_date:
                target_expiry = mfg_date + datetime.timedelta(days=int(limit_val))

            if target_expiry:
                remaining_d = (target_expiry - current_date).days
                total_span = limit_val
                if mfg_date:
                    total_span = max(1.0, float((target_expiry - mfg_date).days))
                ratio = max(0.0, min(1.0, remaining_d / total_span))
                consumed_d = total_span - remaining_d
                results[basis] = BasisRemaining(
                    basis=basis,
                    limit_value=total_span,
                    consumed_value=max(0.0, consumed_d),
                    remaining_value=float(remaining_d),
                    remaining_ratio=ratio,
                )

        elif basis in ("USAGE_COUNT", "USAGE_HOURS"):
            consumed = sum(float(ev["amount"]) for ev in usage_events)
            rem = max(0.0, limit_val - consumed)
            ratio = max(0.0, min(1.0, rem / limit_val)) if limit_val > 0 else 0.0
            results[basis] = BasisRemaining(
                basis=basis,
                limit_value=limit_val,
                consumed_value=consumed,
                remaining_value=rem,
                remaining_ratio=ratio,
            )

    return results


def evaluate_lot_risk(
    mfg_date: datetime.date | None,
    expiry_date: datetime.date | None,
    expiry_required: bool,
    policies: list[dict[str, Any]],
    usage_events: list[dict[str, Any]],
    clock: Clock,
    stream_a_ratio_threshold: float = 0.60,
) -> LifeEvaluationResult:
    """Pure domain evaluation of lot risk and Stream A eligibility.

    Enforces:
    - Invariant S6: Expired lot or lot with unknown expiry on an expiry_required class
      is NEVER GREEN, NEVER Stream A eligible, NEVER auto-issued.
    - Invariant S7: Usage-based lot without usage events is NEVER GREEN (INSUFFICIENT_DATA/UNKNOWN).
    - Invariant S8: Adding usage never increases remaining life; risk never improves as time advances.
    """
    current_date = clock.today()

    # Invariant S6 Check: Unknown expiry date on expiry_required category
    if expiry_required and not expiry_date:
        return LifeEvaluationResult(
            lot_id="",
            risk="UNKNOWN",
            basis="SHELF_LIFE_DAYS",
            remaining_days=None,
            remaining_ratio=None,
            stream_a_eligible=False,
            stream_a_reason="EXPIRY_REQUIRED_BUT_UNKNOWN_S6",
            near_expiry_path=False,
            reasons=["S6_VIOLATION_UNKNOWN_EXPIRY: Lot requires expiry date but has none"],
            disposition_ladder=_build_disposition_ladder("UNKNOWN"),
        )

    # Invariant S6 Check: Expired lot by calendar date
    if expiry_date and expiry_date < current_date:
        days_past = (current_date - expiry_date).days
        return LifeEvaluationResult(
            lot_id="",
            risk="EXPIRED",
            basis="SHELF_LIFE_DAYS",
            remaining_days=-days_past,
            remaining_ratio=0.0,
            stream_a_eligible=False,
            stream_a_reason="EXPIRED_LOT_S6",
            near_expiry_path=False,
            reasons=[f"S6_VIOLATION_EXPIRED: Lot expired {days_past} days ago"],
            disposition_ladder=_build_disposition_ladder("EXPIRED"),
        )

    # Check Invariant S7: Usage-based policy with zero usage events
    has_usage_policy = any(p["basis"] in ("USAGE_COUNT", "USAGE_HOURS") for p in policies)
    if has_usage_policy and not usage_events:
        return LifeEvaluationResult(
            lot_id="",
            risk="UNKNOWN",
            basis="USAGE_COUNT",
            remaining_days=None,
            remaining_ratio=None,
            stream_a_eligible=False,
            stream_a_reason="INSUFFICIENT_DATA_S7",
            near_expiry_path=False,
            reasons=["S7_VIOLATION_NO_USAGE_EVENTS: Usage-based lot with zero events cannot be GREEN"],
            disposition_ladder=_build_disposition_ladder("UNKNOWN"),
        )

    # If no policies exist at all:
    if not policies:
        # Default calendar calculation if expiry_date exists
        if expiry_date:
            rem_d = (expiry_date - current_date).days
            if rem_d <= 0:
                risk = "EXPIRED"
            elif rem_d <= 30:
                risk = "RED"
            elif rem_d <= 90:
                risk = "AMBER"
            else:
                risk = "GREEN"

            is_eligible = risk == "GREEN" and rem_d > 180
            return LifeEvaluationResult(
                lot_id="",
                risk=risk,
                basis="SHELF_LIFE_DAYS",
                remaining_days=rem_d,
                remaining_ratio=None,
                stream_a_eligible=is_eligible,
                stream_a_reason=None if is_eligible else "SHELF_LIFE_BELOW_THRESHOLD",
                near_expiry_path=risk in ("AMBER", "RED"),
                reasons=[f"Remaining days: {rem_d}"],
                disposition_ladder=_build_disposition_ladder(risk),
            )

        return LifeEvaluationResult(
            lot_id="",
            risk="UNKNOWN",
            basis="NONE",
            remaining_days=None,
            remaining_ratio=None,
            stream_a_eligible=False,
            stream_a_reason="NO_RESOLVABLE_POLICY",
            near_expiry_path=False,
            reasons=["No resolvable life policy"],
            disposition_ladder=_build_disposition_ladder("UNKNOWN"),
        )

    # Calculate per basis; earliest-ending basis wins
    basis_map = compute_remaining_life_per_basis(mfg_date, expiry_date, policies, usage_events, clock)

    if not basis_map:
        return LifeEvaluationResult(
            lot_id="",
            risk="UNKNOWN",
            basis="NONE",
            remaining_days=None,
            remaining_ratio=None,
            stream_a_eligible=False,
            stream_a_reason="NO_COMPUTED_BASIS",
            near_expiry_path=False,
            reasons=["Could not compute remaining life on configured policies"],
            disposition_ladder=_build_disposition_ladder("UNKNOWN"),
        )

    # Earliest-ending basis (lowest remaining_ratio)
    winning_basis = min(basis_map.values(), key=lambda b: b.remaining_ratio)
    ratio = winning_basis.remaining_ratio
    rem_days = int(basis_map["SHELF_LIFE_DAYS"].remaining_value) if "SHELF_LIFE_DAYS" in basis_map else None

    # Risk state thresholds
    if ratio <= 0.0 or (rem_days is not None and rem_days <= 0):
        risk = "EXPIRED"
    elif ratio <= 0.20 or (rem_days is not None and rem_days <= 30):
        risk = "RED"
    elif ratio <= 0.50 or (rem_days is not None and rem_days <= 90):
        risk = "AMBER"
    else:
        risk = "GREEN"

    # Stream A eligibility check
    near_expiry = False
    if risk == "EXPIRED":
        stream_a_ok = False
        reason_a = "EXPIRED_LOT_S6"
    elif risk in ("RED", "AMBER") or ratio < stream_a_ratio_threshold:
        stream_a_ok = False
        reason_a = "SHELF_LIFE_RATIO_BELOW_THRESHOLD"
        near_expiry = True
    else:
        stream_a_ok = True
        reason_a = None

    return LifeEvaluationResult(
        lot_id="",
        risk=risk,
        basis=winning_basis.basis,
        remaining_days=rem_days,
        remaining_ratio=round(ratio, 4),
        stream_a_eligible=stream_a_ok,
        stream_a_reason=reason_a,
        near_expiry_path=near_expiry,
        reasons=[f"Earliest-ending basis: {winning_basis.basis} with remaining ratio {ratio:.1%}"],
        disposition_ladder=_build_disposition_ladder(risk),
    )


def _build_disposition_ladder(risk: str) -> list[dict[str, str]]:
    """Generates the ordered FEFO disposition ladder per Section 11.0."""
    return [
        {
            "step": "1",
            "action": "ISSUE_OLDEST_FIRST_FEFO",
            "description": "Issue oldest stock first per First-Expired-First-Out rule.",
            "status": "RECOMMENDED" if risk in ("GREEN", "AMBER") else "INELIGIBLE",
        },
        {
            "step": "2",
            "action": "REDEPLOY_NEAR_EXPIRY",
            "description": "Redeploy to another plant or CPSE capable of immediate consumption before expiry.",
            "status": "RECOMMENDED" if risk in ("AMBER", "RED") else "STANDBY",
        },
        {
            "step": "3",
            "action": "VENDOR_RETEST_RETURN",
            "description": "Engage vendor for recertification, shelf-life extension testing, or buy-back.",
            "status": "RECOMMENDED" if risk == "RED" else "STANDBY",
        },
        {
            "step": "4",
            "action": "DISPOSAL_REQUEST_EXPORT",
            "description": "Generate official CPSE disposal request file for condemnation board and auction.",
            "status": "ACTION_REQUIRED" if risk == "EXPIRED" else "STANDBY",
        },
    ]


async def record_usage_event(
    session: AsyncSession,
    lot_id: UUID,
    amount: float,
    unit: str,
    clock: Clock | None = None,
    actor_id: UUID | None = None,
) -> UsageEvent:
    """Records a physical usage event on a lot, reducing remaining qty.

    Enforces:
    - Invariant S8: Adding usage never increases remaining life.
    - Transactional audit log recording (LOT_USAGE_RECORD).
    """
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usage amount must be strictly positive.",
        )

    stmt_lot = select(StockLot).where(StockLot.id == lot_id)
    res_lot = await session.execute(stmt_lot)
    lot = res_lot.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found.")

    clk = clock or RealClock()
    event_ts = clk.now()

    # Create usage event
    event = UsageEvent(
        lot_id=lot.id,
        ts=event_ts,
        amount=amount,
        unit=unit,
    )
    session.add(event)

    # Decrement remaining quantity if tracked
    before_qty = float(lot.qty_remaining) if lot.qty_remaining is not None else None
    if before_qty is not None:
        lot.qty_remaining = max(0.0, before_qty - amount)

    await session.flush()

    # Record transactional audit log
    audit_after = json.dumps(
        {
            "lot_id": str(lot.id),
            "amount": amount,
            "unit": unit,
            "qty_before": before_qty,
            "qty_after": float(lot.qty_remaining) if lot.qty_remaining is not None else None,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'LOT_USAGE_RECORD', 'usage_events', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(event.id),
            "after": audit_after,
            "rationale": f"Usage of {amount} {unit} logged for lot {lot.id}",
        },
    )

    return event
