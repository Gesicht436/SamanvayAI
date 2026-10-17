"""Stream B forward demand pooling and tender pack router per Section 8.1 & 13.0.

Exposes REST endpoints for joint procurement pooling and tender pack generation:
  - POST /indents
  - GET /indents
  - POST /pools
  - GET /pools
  - GET /pools/{id}/tender-pack
  - POST /pools/{id}/export
"""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.database import tenant_sync_session
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.pool import (
    create_forward_indent,
    create_tender_pool,
    generate_tender_pack,
    list_forward_indents,
    list_tender_pools,
)

router = APIRouter(tags=["pools"])


class ForwardIndentCreateRequest(BaseModel):
    golden_id: uuid.UUID
    qty: float = Field(..., gt=0.0, description="Indent quantity required")
    uom: str = Field("EA", description="Unit of measure")
    need_by: date = Field(..., description="Target delivery date")
    delivery_site: str | None = None
    plant: str | None = None
    budget_unit_cost: float | None = None


class TenderPoolCreateRequest(BaseModel):
    indent_ids: list[uuid.UUID] = Field(..., min_length=1, description="List of open forward indent UUIDs")
    mou_ref: str | None = Field(None, description="Inter-CPSE MoU or Joint Committee reference")


@router.post("/indents")
def post_forward_indent(
    req: ForwardIndentCreateRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new forward demand indent for the current CPSE."""
    with tenant_sync_session(user.org_id) as db:
        indent = create_forward_indent(
            db=db,
            org_id=user.org_id,
            user_id=user.user_id,
            golden_id=req.golden_id,
            qty=req.qty,
            uom=req.uom,
            need_by=req.need_by,
            delivery_site=req.delivery_site,
            plant=req.plant,
            budget_unit_cost=req.budget_unit_cost,
        )
        return {
            "indent_id": str(indent.id),
            "org_id": indent.org_id,
            "golden_id": str(indent.golden_id),
            "qty": float(indent.qty),
            "uom": indent.uom,
            "need_by": str(indent.need_by),
            "status": indent.status,
            "created_at": indent.created_at.isoformat() if indent.created_at else None,
        }


@router.get("/indents")
def get_forward_indents(
    golden_id: uuid.UUID | None = Query(None, description="Filter by Golden Master UUID"),
    status: str | None = Query(None, description="Filter by status (OPEN, POOLED, etc.)"),
    cross_org: bool = Query(False, description="Whether to include indents from other partner CPSEs for pooling"),
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List forward indents."""
    with tenant_sync_session(user.org_id) as db:
        if cross_org and user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Cross-organization indent listing requires ADMIN.")
        org_filter = None if cross_org else user.org_id
        return list_forward_indents(
            db=db,
            current_org_id=org_filter,
            golden_id=golden_id,
            status=status,
        )


@router.post("/pools")
def post_tender_pool(
    req: TenderPoolCreateRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregate selected forward indents into a joint procurement Tender Pool."""
    with tenant_sync_session(user.org_id) as db:
        pool = create_tender_pool(
            db=db,
            lead_org_id=user.org_id,
            user_id=user.user_id,
            indent_ids=req.indent_ids,
            mou_ref=req.mou_ref,
            allow_cross_org=user.role == "ADMIN",
        )
        return {
            "pool_id": str(pool.id),
            "lead_org": pool.lead_org,
            "golden_id": str(pool.golden_id),
            "status": pool.status,
            "mou_ref": pool.mou_ref,
            "total_qty": float(pool.total_qty),
            "canonical_uom": pool.canonical_uom,
            "estimated_baseline_cost": float(pool.estimated_baseline_cost),
            "estimated_pooled_cost": float(pool.estimated_pooled_cost),
            "estimated_savings": float(pool.estimated_savings),
            "created_at": pool.created_at.isoformat() if pool.created_at else None,
        }


@router.get("/pools")
def get_tender_pools(
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all joint procurement tender pools."""
    with tenant_sync_session(user.org_id) as db:
        return list_tender_pools(db=db, current_org_id=user.org_id)


@router.get("/pools/{id}/tender-pack")
def get_tender_pack(
    id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate structured Tender Pack data and CSV export."""
    with tenant_sync_session(user.org_id) as db:
        return generate_tender_pack(db=db, pool_id=id, current_org_id=user.org_id)


@router.post("/pools/{id}/export")
def post_tender_pack_export(
    id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Export tender pack (Section 15.0 endpoint compatibility)."""
    with tenant_sync_session(user.org_id) as db:
        return generate_tender_pack(db=db, pool_id=id, current_org_id=user.org_id)
