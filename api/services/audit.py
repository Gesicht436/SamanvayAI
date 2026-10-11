"""Transactional audit logging service for Samanvay.

Guarantees transactional consistency by recording state changes into the
tamper-evident audit_log in the exact same database transaction.
The PostgreSQL append-only trigger automatically links the SHA-256 hash chain.
"""

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class AuditEntryResult:
    seq: int
    hash: str


def append_audit_entry(
    db: Session,
    actor: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    old_val: dict[str, Any] | None,
    new_val: dict[str, Any] | None,
    rationale: str = "",
) -> AuditEntryResult:
    """Insert a transactional audit record and return the generated sequence and hash."""
    before_json = json.dumps(old_val) if old_val is not None else None
    after_json = json.dumps(new_val) if new_val is not None else "{}"

    res = db.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, :action, :entity, :entity_id, CAST(:before AS jsonb), CAST(:after AS jsonb), :rationale, '', '') "
            "RETURNING seq, this_hash"
        ),
        {
            "actor": actor,
            "action": action,
            "entity": entity_type,
            "entity_id": str(entity_id),
            "before": before_json,
            "after": after_json,
            "rationale": rationale or f"Audit event for {action} on {entity_type}",
        },
    )
    row = res.fetchone()
    seq = row[0] if row else 0
    thash = row[1] if row else ""
    return AuditEntryResult(seq=seq, hash=thash)
