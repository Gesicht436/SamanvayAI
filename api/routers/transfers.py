"""Stream A surplus stock transfer requisition router per Section 8.1 & 13.0.

Exposes REST endpoints for inter-CPSE surplus transfer orders:
  - POST /transfers
  - GET /transfers
  - PATCH /transfers/{id}/gate
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.database import SyncSessionLocal
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.transfer import list_transfers, request_transfer, review_transfer_gate

router = APIRouter(prefix="/transfers", tags=["transfers"])


class TransferCreateRequest(BaseModel):
    lot_id: uuid.UUID
    requested_qty: float = Field(..., gt=0.0, description="Quantity requested for transfer")
    to_plant: str | None = Field(None, description="Destination plant code of receiving CPSE")
    basis: str = Field("BOOK_VALUE", description="BOOK_VALUE, LAST_PURCHASE_PRICE, or AGREED")
    agreed_price: float | None = Field(None, description="Agreed unit transfer price in INR")
    recipient_market_price: float | None = Field(None, description="Current market replacement cost in INR")


class TransferGateReviewRequest(BaseModel):
    action: str = Field(..., description="TECHNICAL_REVIEW, COMMERCIAL_REVIEW, APPROVED, REJECTED, DISPATCHED, COMPLETED")
    rationale: str = Field(..., min_length=3, description="Justification for workflow progression or rejection")
    mtc_uploaded: bool | None = None
    pmi_done: bool | None = None


@router.post("")
def create_transfer_requisition(
    req: TransferCreateRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Initiate a Stream A inter-CPSE surplus transfer requisition."""
    with SyncSessionLocal() as db:
        order = request_transfer(
            db=db,
            to_org_id=user.org_id,
            user_id=user.user_id,
            lot_id=req.lot_id,
            requested_qty=req.requested_qty,
            to_plant=req.to_plant,
            basis=req.basis,
            agreed_price=req.agreed_price,
            recipient_market_price=req.recipient_market_price,
        )

        return {
            "transfer_id": str(order.id),
            "from_org": order.from_org,
            "to_org": order.to_org,
            "lot_id": str(order.lot_id),
            "golden_id": str(order.golden_id),
            "qty": float(order.qty),
            "basis": order.basis,
            "unit_price": float(order.unit_price or 0.0),
            "avoided_purchase_cost": float(order.avoided_purchase_cost or 0.0),
            "transfer_cost": float(order.transfer_cost or 0.0),
            "net_benefit": float(order.net_benefit or 0.0),
            "state": order.state,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }


@router.get("")
def get_transfers(
    direction: str = "ALL",  # INCOMING, OUTGOING, ALL
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List transfers involving the current organization."""
    with SyncSessionLocal() as db:
        return list_transfers(db=db, current_org_id=user.org_id, direction=direction)


@router.patch("/{id}/gate")
def update_transfer_gate(
    id: uuid.UUID,
    req: TransferGateReviewRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Advance or reject a transfer requisition through Maker-Checker workflow."""
    with SyncSessionLocal() as db:
        order = review_transfer_gate(
            db=db,
            transfer_id=id,
            user_id=user.user_id,
            action=req.action,
            rationale=req.rationale,
            mtc_uploaded=req.mtc_uploaded,
            pmi_done=req.pmi_done,
        )
        return {
            "transfer_id": str(order.id),
            "state": order.state,
            "mtc_uploaded": order.mtc_uploaded,
            "pmi_done": order.pmi_done,
            "reviewed_by": str(order.reviewed_by) if order.reviewed_by else None,
            "rejection_reason": order.rejection_reason,
        }
