"""Audit trail endpoints and hash-chain verification."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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

    expected_prev = "0" * 64
    first_broken_seq = None
    import hashlib
    import json

    head_hash = rows[-1].this_hash

    for r in rows:
        if r.prev_hash != expected_prev:
            first_broken_seq = r.seq
            break

        at_str = r.at.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if r.at else ""
        actor_str = str(r.actor) if r.actor else ""
        before_str = json.dumps(r.before) if r.before is not None else ""
        after_str = json.dumps(r.after) if r.after is not None else ""
        rationale_str = r.rationale or ""

        payload = (
            r.prev_hash
            + f"{at_str}|{actor_str}|{r.action}|{r.entity}|{r.entity_id}|{before_str}|{after_str}|{rationale_str}"
        )
        computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if computed_hash != r.this_hash:
            first_broken_seq = r.seq
            break

        expected_prev = r.this_hash

    status_str = "OK" if first_broken_seq is None else "TAMPERED"

    return AuditVerifyResponse(
        verified_records=len(rows),
        first_broken_seq=first_broken_seq,
        head_hash=head_hash,
        anchored_head=None,
        status=status_str,
    )
