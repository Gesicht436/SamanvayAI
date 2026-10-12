"""Drawing Revision Equivalence Service per Section 5.0, 9.2, 18.7.3 and Invariant S13.

Normalizes drawing numbers and evaluates approved engineering revision equivalences.
Safety Invariant S13: In DRAWING mode, revision difference is never better than Tier 2
unless an approved drawing_revision_equivalence row exists with maker-checker verification.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.entities import DrawingRevisionEquivalence

# Suffix pattern to keep sheet and item suffixes: e.g. -1, -2, -SH1, -ITEM3
_SUFFIX_RE = re.compile(r"(-(?:\d{1,2}|SH\d+|SHT\d+|ITEM\d+|PT\d+))$", re.IGNORECASE)


def normalize_drawing_number(drawing_no: str | None) -> str:
    """Normalizes an engineering drawing number per Section 18.7.3.

    Uppercase, collapse spaces and internal hyphens inside the number,
    keep sheet and item suffixes ('D-44120' and 'D44120' are the same;
    'D44120-1' and 'D44120-2' are not).
    """
    if not drawing_no:
        return ""

    raw = str(drawing_no).strip().upper()

    # Check for preserved item/sheet suffix
    suffix = ""
    match = _SUFFIX_RE.search(raw)
    if match:
        prefix = raw[: match.start()]
        # Suffix only applies if the base prefix already contains drawing digits
        if re.search(r"\d", prefix):
            suffix = match.group(1).upper()
            raw = prefix

    # Collapse internal whitespace and hyphens in the base code
    base = re.sub(r"[\s\-_]+", "", raw)
    return f"{base}{suffix}"



def normalize_drawing_key(owner: str | None, drawing_no: str | None) -> tuple[str, str]:
    """Returns normalized (drawing_owner, drawing_norm) tuple."""
    owner_norm = str(owner or "").strip().upper()
    dwg_norm = normalize_drawing_number(drawing_no)
    return owner_norm, dwg_norm


async def is_drawing_revision_equivalent(
    db: AsyncSession,
    drawing_owner: str,
    drawing_no: str,
    rev_a: str,
    rev_b: str,
) -> bool:
    """Checks whether rev_a and rev_b are equivalent for a given drawing key.

    Returns True if revisions are identical, or if an approved maker-checker
    drawing_revision_equivalence row exists in the database (Invariant S13).
    """
    ra = str(rev_a).strip().upper()
    rb = str(rev_b).strip().upper()

    if ra == rb:
        return True

    owner_norm, dwg_norm = normalize_drawing_key(drawing_owner, drawing_no)
    if not owner_norm or not dwg_norm:
        return False

    stmt = (
        select(DrawingRevisionEquivalence)
        .where(
            DrawingRevisionEquivalence.drawing_owner == owner_norm,
            DrawingRevisionEquivalence.drawing_norm == dwg_norm,
            DrawingRevisionEquivalence.approved_by.isnot(None),
            or_(
                (DrawingRevisionEquivalence.rev_a == ra) & (DrawingRevisionEquivalence.rev_b == rb),
                (DrawingRevisionEquivalence.rev_a == rb) & (DrawingRevisionEquivalence.rev_b == ra),
            ),
        )
        .limit(1)
    )

    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def propose_revision_equivalence(
    db: AsyncSession,
    drawing_owner: str,
    drawing_no: str,
    rev_a: str,
    rev_b: str,
    rationale: str,
    proposed_by: UUID | None = None,
) -> DrawingRevisionEquivalence:
    """Proposes a drawing revision equivalence pair requiring maker-checker approval."""
    owner_norm, dwg_norm = normalize_drawing_key(drawing_owner, drawing_no)
    ra = str(rev_a).strip().upper()
    rb = str(rev_b).strip().upper()

    record = DrawingRevisionEquivalence(
        drawing_owner=owner_norm,
        drawing_norm=dwg_norm,
        rev_a=ra,
        rev_b=rb,
        rationale=rationale,
        proposed_by=proposed_by,
        approved_by=None,
        approved_at=None,
    )
    db.add(record)
    await db.flush()

    # Append-only transactional audit log (Invariant S6)
    audit_payload = json.dumps(
        {
            "drawing_owner": owner_norm,
            "drawing_norm": dwg_norm,
            "rev_a": ra,
            "rev_b": rb,
            "rationale": rationale,
        }
    )
    await db.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'PROPOSE_DRAWING_EQUIVALENCE', 'drawing_revision_equivalence', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": proposed_by,
            "entity_id": str(record.id),
            "after": audit_payload,
            "rationale": f"Steward proposal for drawing {owner_norm}/{dwg_norm} rev {ra} == rev {rb}",
        },
    )

    return record


async def approve_revision_equivalence(
    db: AsyncSession,
    equivalence_id: int,
    approved_by: UUID,
) -> DrawingRevisionEquivalence:
    """Approves an engineering revision equivalence with strict Maker-Checker enforcement (Constraint rev_maker_ne_checker)."""
    stmt = select(DrawingRevisionEquivalence).where(DrawingRevisionEquivalence.id == equivalence_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()
    if not record:
        raise ValueError(f"Drawing revision equivalence with id {equivalence_id} not found.")

    if record.proposed_by and record.proposed_by == approved_by:
        raise ValueError(
            "Maker cannot approve own drawing revision proposal (Violation of Maker-Checker constraint rev_maker_ne_checker)."
        )

    record.approved_by = approved_by
    record.approved_at = datetime.now(UTC)
    await db.flush()

    audit_payload = json.dumps(
        {
            "approved_by": str(approved_by),
            "approved_at": record.approved_at.isoformat(),
            "drawing_owner": record.drawing_owner,
            "drawing_norm": record.drawing_norm,
            "rev_a": record.rev_a,
            "rev_b": record.rev_b,
        }
    )
    await db.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'APPROVE_DRAWING_EQUIVALENCE', 'drawing_revision_equivalence', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": approved_by,
            "entity_id": str(record.id),
            "after": audit_payload,
            "rationale": f"Checker approved drawing revision equivalence for {record.drawing_owner}/{record.drawing_norm}",
        },
    )

    return record
