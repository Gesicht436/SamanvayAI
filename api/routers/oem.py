"""OEM catalogue onboarding router.

Exposes REST endpoints for bulk OEM catalogue onboarding per Section 20.2:
  - POST /oem/onboard
  - GET /oem/batches/{id}/proposals
  - POST /oem/proposals/{id}/review
  - POST /oem/batches/{id}/approve
  - POST /oem/supersessions
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.database import tenant_sync_session
from api.models.entities import OemCatalogueBatch, OemPartSupersession, OemProposal
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.audit import append_audit_entry
from api.services.oem import (
    approve_catalogue_batch,
    ingest_oem_catalogue_rows,
    normalize_oem_name,
    normalize_oem_part_number,
    review_proposal,
)

router = APIRouter(prefix="/oem", tags=["oem"])


def _parse_uuid(val: Any) -> uuid.UUID | None:
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


class OemOnboardRequest(BaseModel):
    oem_name: str
    filename: str = "catalogue.json"
    rows: list[dict[str, Any]]


class ProposalReviewRequest(BaseModel):
    action: str = Field(..., description="ACCEPT, REJECT, or EDIT")
    edited_part_number: str | None = None
    edited_description: str | None = None


class BatchApproveRequest(BaseModel):
    rationale: str = Field(..., min_length=5, description="Engineering rationale for catalogue publication")


class SupersessionCreateRequest(BaseModel):
    manufacturer: str
    old_pn: str
    new_pn: str
    note: str | None = None


@router.post("/onboard")
def onboard_oem_catalogue(
    req: OemOnboardRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload and process OEM catalogue rows to generate draft proposals."""
    if current_user.role not in ("MAKER", "ADMIN"):
        raise HTTPException(status_code=403, detail="OEM onboarding requires MAKER or ADMIN role.")
    org_id = current_user.org_id
    user_id = _parse_uuid(current_user.sub)
    with tenant_sync_session(current_user.org_id) as db:
        return ingest_oem_catalogue_rows(
            db=db,
            org_id=org_id,
            oem_name=req.oem_name,
            filename=req.filename,
            rows=req.rows,
            user_id=user_id,
        )


@router.get("/batches/{batch_id}/proposals")
def get_batch_proposals(
    batch_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve all draft proposals for an OEM catalogue batch."""
    with tenant_sync_session(current_user.org_id) as db:
        batch = db.get(OemCatalogueBatch, batch_id)
        if not batch or batch.org_id != current_user.org_id:
            raise HTTPException(status_code=404, detail="Batch not found")

        proposals = (
            db.execute(select(OemProposal).where(OemProposal.batch_id == batch_id).order_by(OemProposal.id))
            .scalars()
            .all()
        )

        return {
            "batch_id": str(batch.id),
            "oem_name": batch.oem_name,
            "filename": batch.filename,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "summary": batch.summary,
            "proposals": [
                {
                    "id": p.id,
                    "raw_part_number": p.raw_part_number,
                    "norm_part_number": p.norm_part_number,
                    "effective_part_number": p.effective_part_number,
                    "superseded_from": p.superseded_from,
                    "drawing_no": p.drawing_no,
                    "parent_equipment_model": p.parent_equipment_model,
                    "raw_description": p.raw_description,
                    "subcategory": p.subcategory,
                    "evidence_spans": p.evidence_spans,
                    "status": p.status,
                    "golden_id": str(p.golden_id) if p.golden_id else None,
                }
                for p in proposals
            ],
        }


@router.post("/proposals/{proposal_id}/review")
def review_single_proposal(
    proposal_id: int,
    req: ProposalReviewRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Maker review of a single catalogue proposal."""
    user_id = _parse_uuid(current_user.sub)
    if current_user.role not in ("MAKER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Proposal review requires MAKER or ADMIN role.")
    with tenant_sync_session(current_user.org_id) as db:
        proposal = db.get(OemProposal, proposal_id)
        batch = db.get(OemCatalogueBatch, proposal.batch_id) if proposal else None
        if not batch or batch.org_id != current_user.org_id:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return review_proposal(
            db=db,
            proposal_id=proposal_id,
            action=req.action,
            edited_part_number=req.edited_part_number,
            edited_description=req.edited_description,
            user_id=user_id,
        )


@router.post("/batches/{batch_id}/approve")
def approve_batch(
    batch_id: uuid.UUID,
    req: BatchApproveRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Checker approves the catalogue batch and publishes active golden masters."""
    user_id = _parse_uuid(current_user.sub)
    if current_user.role not in ("CHECKER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Batch approval requires CHECKER or ADMIN role.")
    if not user_id:
        raise HTTPException(status_code=403, detail="A UUID subject is required for approval.")
    roles = [current_user.role]
    domain_tags = current_user.domains

    with tenant_sync_session(current_user.org_id) as db:
        batch = db.get(OemCatalogueBatch, batch_id)
        if not batch or batch.org_id != current_user.org_id:
            raise HTTPException(status_code=404, detail="Batch not found")
        return approve_catalogue_batch(
            db=db,
            batch_id=batch_id,
            checker_id=user_id,
            user_roles=roles,
            user_domain_tags=domain_tags,
            rationale=req.rationale,
        )


@router.post("/supersessions")
def create_supersession_rule(
    req: SupersessionCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Register an OEM part supersession mapping row."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Supersession management requires ADMIN role.")
    mfr_norm = normalize_oem_name(req.manufacturer)
    old_norm = normalize_oem_part_number(req.old_pn)
    new_norm = normalize_oem_part_number(req.new_pn)
    user_id = _parse_uuid(current_user.sub)

    with tenant_sync_session(current_user.org_id) as db:
        existing = db.execute(
            select(OemPartSupersession).where(
                OemPartSupersession.manufacturer == mfr_norm,
                OemPartSupersession.old_pn == old_norm,
            )
        ).scalar_one_or_none()

        if existing:
            old_data = {
                "manufacturer": existing.manufacturer,
                "old_pn": existing.old_pn,
                "new_pn": existing.new_pn,
                "note": existing.note,
            }
            existing.new_pn = new_norm
            existing.note = req.note
            row = existing
            append_audit_entry(
                db=db,
                actor=user_id,
                action="OEM_SUPERSESSION_UPDATE",
                entity_type="oem_part_supersessions",
                entity_id=str(row.id),
                old_val=old_data,
                new_val={"manufacturer": mfr_norm, "old_pn": old_norm, "new_pn": new_norm, "note": req.note},
            )
        else:
            row = OemPartSupersession(
                manufacturer=mfr_norm,
                old_pn=old_norm,
                new_pn=new_norm,
                note=req.note,
            )
            db.add(row)
            db.flush()
            append_audit_entry(
                db=db,
                actor=user_id,
                action="OEM_SUPERSESSION_CREATE",
                entity_type="oem_part_supersessions",
                entity_id=str(row.id),
                old_val=None,
                new_val={"manufacturer": mfr_norm, "old_pn": old_norm, "new_pn": new_norm, "note": req.note},
            )
        db.commit()

        return {
            "id": row.id,
            "manufacturer": row.manufacturer,
            "old_pn": row.old_pn,
            "new_pn": row.new_pn,
            "note": row.note,
        }
