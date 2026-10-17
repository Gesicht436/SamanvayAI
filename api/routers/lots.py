"""Stock lots, usage events, and life monitor API router.

Enforces Section 11.0, 15.1:
- GET /lots: Lists stock lots with risk and Stream A eligibility filtering.
- GET /lots/{id}: Retrieves lot details and remaining life across all bases.
- POST /lots/{id}/usage: Logs physical usage event with transactional audit logging.
- GET /lots/{id}/disposition: Returns ordered FEFO disposition ladder.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.entities import GoldenMaster, LifePolicy, StockLot, SubcategorySpec, UsageEvent
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.life import (
    Clock,
    RealClock,
    SimulatedClock,
    evaluate_lot_risk,
    record_usage_event,
)

router = APIRouter(prefix="/lots", tags=["Stock Lots & Life Monitor"])


# --- Schemas ---


class LotListItem(BaseModel):
    lot_id: str
    golden_code: str | None
    descriptor: str | None
    plant: str | None
    batch_no: str | None
    mfg_date: str | None
    expiry_date: str | None
    remaining_days: int | None
    risk: str
    basis: str
    qty_remaining: float | None
    uom: str | None
    stream_a_eligible: bool
    reason: str | None = None
    near_expiry_path: bool = False


class LotsListResponse(BaseModel):
    as_of: str
    clock: str
    lots: list[LotListItem]


class LotDetailResponse(BaseModel):
    lot_id: str
    org_id: str
    golden_id: str | None
    golden_code: str | None
    descriptor: str | None
    plant: str | None
    batch_no: str | None
    mfg_date: str | None
    expiry_date: str | None
    qty_remaining: float | None
    risk: str
    basis: str
    remaining_days: int | None
    remaining_ratio: float | None
    stream_a_eligible: bool
    stream_a_reason: str | None
    near_expiry_path: bool
    disposition_ladder: list[dict[str, str]]
    reasons: list[str]


class UsageLogRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount consumed (must be strictly positive).")
    unit: str = Field(..., description="Unit of consumption, e.g. EA, M, HOURS, CYCLES.")


class UsageLogResponse(BaseModel):
    id: int
    lot_id: str
    amount: float
    unit: str
    ts: str
    qty_remaining_after: float | None


class DispositionLadderResponse(BaseModel):
    lot_id: str
    risk: str
    disposition_ladder: list[dict[str, str]]


# --- Helper Function ---


async def _evaluate_db_lot(
    session: AsyncSession,
    lot: StockLot,
    clock: Clock,
) -> dict[str, Any]:
    # 1. Fetch Golden Master & SubcategorySpec if present
    golden_code = None
    descriptor = None
    expiry_required = False
    uom = None

    if lot.golden_id:
        stmt_gm = select(GoldenMaster).where(GoldenMaster.id == lot.golden_id)
        res_gm = await session.execute(stmt_gm)
        gm = res_gm.scalar_one_or_none()
        if gm:
            golden_code = gm.code
            descriptor = gm.descriptor
            uom = gm.canonical_uom

            stmt_sub = select(SubcategorySpec).where(SubcategorySpec.subcategory == gm.subcategory)
            res_sub = await session.execute(stmt_sub)
            sub = res_sub.scalar_one_or_none()
            if sub:
                expiry_required = sub.expiry_required

    # 2. Fetch Policies
    stmt_pol = select(LifePolicy).where((LifePolicy.org_id == lot.org_id) | (LifePolicy.org_id.is_(None)))
    res_pol = await session.execute(stmt_pol)
    policies = [
        {"basis": p.basis, "limit_value": float(p.limit_value), "unit": p.unit} for p in res_pol.scalars().all()
    ]

    # 3. Fetch Usage Events
    stmt_ev = select(UsageEvent).where(UsageEvent.lot_id == lot.id).order_by(UsageEvent.ts.asc())
    res_ev = await session.execute(stmt_ev)
    usage_events = [{"amount": float(e.amount), "unit": e.unit, "ts": e.ts} for e in res_ev.scalars().all()]

    # 4. Evaluate Risk
    eval_res = evaluate_lot_risk(
        mfg_date=lot.mfg_date,
        expiry_date=lot.expiry_date,
        expiry_required=expiry_required,
        policies=policies,
        usage_events=usage_events,
        clock=clock,
    )

    return {
        "golden_code": golden_code,
        "descriptor": descriptor,
        "uom": uom,
        "eval_res": eval_res,
    }


# --- Endpoints ---


@router.get("", response_model=LotsListResponse)
async def list_lots(
    risk: str | None = Query(None, description="Optional risk filter: GREEN, AMBER, RED, EXPIRED, UNKNOWN"),
    plant: str | None = Query(None, description="Plant filter"),
    clock: str = Query("REAL", description="REAL or SIMULATED"),
    simulated_date: str | None = Query(None, description="ISO date for SIMULATED clock, e.g. 2026-10-10"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Lists stock lots with life risk status and Stream A eligibility (Section 11.0, 15.1)."""
    clk: Clock
    if clock.upper() == "SIMULATED" and simulated_date:
        clk = SimulatedClock(simulated_date)
    else:
        clk = RealClock()

    stmt = select(StockLot).where(StockLot.org_id == current_user.org_id)
    if plant:
        stmt = stmt.where(StockLot.plant == plant)

    res = await db.execute(stmt)
    lots = res.scalars().all()

    items: list[LotListItem] = []
    for lot in lots:
        data = await _evaluate_db_lot(db, lot, clk)
        ev = data["eval_res"]

        if risk and ev.risk.upper() != risk.upper():
            continue

        items.append(
            LotListItem(
                lot_id=str(lot.id),
                golden_code=data["golden_code"],
                descriptor=data["descriptor"],
                plant=lot.plant,
                batch_no=lot.batch_no,
                mfg_date=lot.mfg_date.isoformat() if lot.mfg_date else None,
                expiry_date=lot.expiry_date.isoformat() if lot.expiry_date else None,
                remaining_days=ev.remaining_days,
                risk=ev.risk,
                basis=ev.basis,
                qty_remaining=float(lot.qty_remaining) if lot.qty_remaining is not None else None,
                uom=data["uom"],
                stream_a_eligible=ev.stream_a_eligible,
                reason=ev.stream_a_reason,
                near_expiry_path=ev.near_expiry_path,
            )
        )

    return LotsListResponse(
        as_of=clk.today().isoformat(),
        clock="SIMULATED" if clock.upper() == "SIMULATED" else "REAL",
        lots=items,
    )


@router.get("/{lot_id}", response_model=LotDetailResponse)
async def get_lot(
    lot_id: UUID,
    clock: str = Query("REAL", description="REAL or SIMULATED"),
    simulated_date: str | None = Query(None, description="ISO date for SIMULATED clock"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieves single stock lot details with remaining life across bases."""
    stmt = select(StockLot).where(StockLot.id == lot_id, StockLot.org_id == current_user.org_id)
    res = await db.execute(stmt)
    lot = res.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found.")

    clk: Clock
    if clock.upper() == "SIMULATED" and simulated_date:
        clk = SimulatedClock(simulated_date)
    else:
        clk = RealClock()

    data = await _evaluate_db_lot(db, lot, clk)
    ev = data["eval_res"]

    return LotDetailResponse(
        lot_id=str(lot.id),
        org_id=lot.org_id,
        golden_id=str(lot.golden_id) if lot.golden_id else None,
        golden_code=data["golden_code"],
        descriptor=data["descriptor"],
        plant=lot.plant,
        batch_no=lot.batch_no,
        mfg_date=lot.mfg_date.isoformat() if lot.mfg_date else None,
        expiry_date=lot.expiry_date.isoformat() if lot.expiry_date else None,
        qty_remaining=float(lot.qty_remaining) if lot.qty_remaining is not None else None,
        risk=ev.risk,
        basis=ev.basis,
        remaining_days=ev.remaining_days,
        remaining_ratio=ev.remaining_ratio,
        stream_a_eligible=ev.stream_a_eligible,
        stream_a_reason=ev.stream_a_reason,
        near_expiry_path=ev.near_expiry_path,
        disposition_ladder=ev.disposition_ladder,
        reasons=ev.reasons,
    )


def _parse_uuid(val: Any) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


@router.post("/{lot_id}/usage", response_model=UsageLogResponse)
async def log_usage(
    lot_id: UUID,
    req: UsageLogRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Logs physical usage event on a lot, reducing quantity and remaining life (Section 11.0).

    Enforces Invariant S8: Adding usage never increases remaining life.
    """
    stmt = select(StockLot).where(StockLot.id == lot_id, StockLot.org_id == current_user.org_id)
    res = await db.execute(stmt)
    lot = res.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found.")

    event = await record_usage_event(
        session=db,
        lot_id=lot.id,
        amount=req.amount,
        unit=req.unit,
        clock=RealClock(),
        actor_id=_parse_uuid(current_user.sub),
    )

    return UsageLogResponse(
        id=event.id,
        lot_id=str(lot.id),
        amount=float(event.amount),
        unit=event.unit,
        ts=event.ts.isoformat(),
        qty_remaining_after=float(lot.qty_remaining) if lot.qty_remaining is not None else None,
    )


@router.get("/{lot_id}/disposition", response_model=DispositionLadderResponse)
async def get_lot_disposition(
    lot_id: UUID,
    clock: str = Query("REAL", description="REAL or SIMULATED"),
    simulated_date: str | None = Query(None, description="ISO date for SIMULATED clock"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Returns the ordered FEFO disposition ladder for a lot."""
    stmt = select(StockLot).where(StockLot.id == lot_id, StockLot.org_id == current_user.org_id)
    res = await db.execute(stmt)
    lot = res.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found.")

    clk: Clock
    if clock.upper() == "SIMULATED" and simulated_date:
        clk = SimulatedClock(simulated_date)
    else:
        clk = RealClock()

    data = await _evaluate_db_lot(db, lot, clk)
    ev = data["eval_res"]

    return DispositionLadderResponse(
        lot_id=str(lot.id),
        risk=ev.risk,
        disposition_ladder=ev.disposition_ladder,
    )


@router.get("/{lot_id}/depletion")
async def get_lot_depletion(
    lot_id: UUID,
    window_days: int = Query(90, ge=1, le=365),
    min_events: int = Query(3, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Returns consumption velocity and projected depletion date (Section 11.0)."""
    stmt = select(StockLot).where(StockLot.id == lot_id, StockLot.org_id == current_user.org_id)
    res = await db.execute(stmt)
    lot = res.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found.")

    stmt_ev = select(UsageEvent).where(UsageEvent.lot_id == lot.id).order_by(UsageEvent.ts.desc())
    res_ev = await db.execute(stmt_ev)
    events = res_ev.scalars().all()

    from api.services.life import projected_depletion

    qty = float(lot.qty_remaining) if lot.qty_remaining is not None else 0.0
    return projected_depletion(events, remaining_qty=qty, window_days=window_days, min_events=min_events)


@router.get("/{lot_id}/disposal-request")
async def get_lot_disposal_request(
    lot_id: UUID,
    scrap_rate_pct: float = Query(0.05, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Produces formatted condemnation board disposal request export per Step 4 of Section 11.0 ladder."""
    stmt = select(StockLot).where(StockLot.id == lot_id, StockLot.org_id == current_user.org_id)
    res = await db.execute(stmt)
    lot = res.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found.")

    data = await _evaluate_db_lot(db, lot, RealClock())
    ev = data["eval_res"]

    from api.services.life import generate_disposal_request

    return generate_disposal_request(lot, ev, scrap_rate_pct=scrap_rate_pct)


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Acknowledges a life alert, updating state to ACKED (Section 11.0)."""
    import datetime

    from api.models.entities import LifeAlert

    stmt = (
        select(LifeAlert)
        .join(StockLot, StockLot.id == LifeAlert.lot_id)
        .where(LifeAlert.id == alert_id, StockLot.org_id == current_user.org_id)
    )
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Life alert not found.")

    now_ts = datetime.datetime.now(datetime.UTC)
    alert.state = "ACKED"
    alert.acked_at = now_ts
    await db.flush()

    return {"alert_id": alert.id, "state": alert.state, "acked_at": alert.acked_at.isoformat()}


@router.post("/{lot_id}/alerts/ack")
async def acknowledge_lot_alerts(
    lot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Acknowledges all alerts for a specific stock lot (Section 11.0)."""
    import datetime

    from api.models.entities import LifeAlert

    stmt = (
        select(LifeAlert)
        .join(StockLot, StockLot.id == LifeAlert.lot_id)
        .where(LifeAlert.lot_id == lot_id, StockLot.org_id == current_user.org_id)
    )
    res = await db.execute(stmt)
    alerts = res.scalars().all()

    now_ts = datetime.datetime.now(datetime.UTC)
    acked_count = 0
    for a in alerts:
        a.state = "ACKED"
        a.acked_at = now_ts
        acked_count += 1
    await db.flush()

    return {"lot_id": str(lot_id), "acked_count": acked_count, "state": "ACKED", "acked_at": now_ts.isoformat()}


