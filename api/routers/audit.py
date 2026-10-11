"""Audit trail endpoints and hash-chain verification."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.hashchain import verify_chain
from api.database import get_db
from api.security.jwt_auth import AuthUser, get_current_user

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditVerifyResponse(BaseModel):
    verified_records: int
    first_broken_seq: int | None
    head_hash: str | None
    anchored_head: str | None
    status: str


@router.get("/verify", response_model=AuditVerifyResponse)
async def verify_audit_log(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Verify cryptographic SHA-256 hash chain of the audit log (Section 9.4, 15.1)."""
    # Fetch all audit log records ordered by seq
    res = await db.execute(
        text(
            "SELECT seq, at, actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash "
            "FROM audit_log ORDER BY seq ASC"
        )
    )
    rows = res.fetchall()

    if not rows:
        return AuditVerifyResponse(
            verified_records=0,
            first_broken_seq=None,
            head_hash=None,
            anchored_head=None,
            status="OK",
        )

    chain_records = []
    head_hash = rows[-1].this_hash
    for r in rows:
        # Reconstruct canonical record dictionary
        record_dict = {
            "at": r.at.isoformat() if r.at else "",
            "actor": str(r.actor) if r.actor else "",
            "action": r.action,
            "entity": r.entity,
            "entity_id": r.entity_id,
            "before": r.before or {},
            "after": r.after or {},
            "rationale": r.rationale or "",
        }
        chain_records.append(
            {
                "seq": r.seq,
                "record": record_dict,
                "prev_hash": r.prev_hash,
                "hash": r.this_hash,
            }
        )

    # Note: In-memory chain verification checks sequential linkage
    ok, broken_seq = verify_chain(chain_records)
    status_str = "OK" if ok else "TAMPERED"

    return AuditVerifyResponse(
        verified_records=len(rows),
        first_broken_seq=broken_seq,
        head_hash=head_hash,
        anchored_head=None,
        status=status_str,
    )
