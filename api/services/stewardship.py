"""Stewardship governance and maker-checker task management service for Samanvay.

Enforces Section 4.7, 8.0, 9.4:
- Maker proposes tasks (LINK, CREATE_MASTER, MERGE, SPLIT, CORRECT_ATTR, DOC_REVIEW)
- Checker approves or rejects
- Invariant: Maker != Checker (proposer cannot approve own task)
- Invariant: Safety-critical subcategories require matching domain tag (users.domains)
- Transactional audit logging for all state changes
- Feedback example capture for downstream fine-tuning
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.extractors.registry import default_registry
from api.models import (
    FeedbackExample,
    GoldenMaster,
    RawItem,
    StewardTask,
    SubcategorySpec,
    User,
)
from api.services.lifecycle import (
    correct_master_attributes,
    create_golden_master,
    merge_golden_masters,
    split_golden_master,
)

VALID_TASK_KINDS = (
    "LINK",
    "CREATE_MASTER",
    "MERGE",
    "SPLIT",
    "CORRECT_ATTR",
    "DOC_REVIEW",
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


async def _resolve_user(session: AsyncSession, sub_or_id: str | None) -> User | None:
    """Finds user by subject or UUID."""
    if not sub_or_id:
        return None
    uuid_val = _parse_uuid(sub_or_id)
    if uuid_val:
        stmt = select(User).where(or_(User.id == uuid_val, User.subject == sub_or_id))
    else:
        stmt = select(User).where(User.subject == sub_or_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_steward_task(
    session: AsyncSession,
    kind: str,
    payload: dict[str, Any],
    maker_sub: str,
    raw_id: UUID | None = None,
    reason_codes: list[str] | None = None,
    org_id: str | None = None,
) -> StewardTask:
    """Creates a new stewardship task proposed by a Maker.

    Records the task in OPEN state and emits a transactional audit record.
    """
    if kind not in VALID_TASK_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TASK_KIND",
                "message": f"Task kind '{kind}' is not supported. Allowed: {list(VALID_TASK_KINDS)}",
            },
        )

    maker_user = await _resolve_user(session, maker_sub)
    maker_id = maker_user.id if maker_user else _parse_uuid(maker_sub)

    # Store maker_sub inside payload to guarantee Maker != Checker check across sessions
    task_payload = dict(payload)
    task_payload["_maker_sub"] = maker_sub
    if org_id:
        task_payload["_org_id"] = org_id

    task = StewardTask(
        raw_id=raw_id,
        kind=kind,
        payload=task_payload,
        reason_codes=reason_codes or [],
        maker=maker_id,
        state="OPEN",
    )
    session.add(task)
    await session.flush()

    # Transactional audit log entry
    after_data = json.dumps(
        {
            "id": task.id,
            "kind": kind,
            "raw_id": str(raw_id) if raw_id else None,
            "maker_sub": maker_sub,
            "state": "OPEN",
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'STEWARD_TASK_CREATE', 'steward_tasks', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": maker_id,
            "entity_id": str(task.id),
            "after": after_data,
            "rationale": f"Maker proposed {kind} stewardship task",
        },
    )

    return task


async def list_steward_tasks(
    session: AsyncSession,
    state: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[StewardTask]:
    """Lists steward tasks with optional filtering by state and kind."""
    query = select(StewardTask)
    if state:
        query = query.where(StewardTask.state == state.upper())
    if kind:
        query = query.where(StewardTask.kind == kind.upper())
    query = query.order_by(StewardTask.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_steward_task(session: AsyncSession, task_id: int) -> StewardTask:
    """Retrieves a steward task by ID or raises 404."""
    task = await session.get(StewardTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Steward task #{task_id} not found."},
        )
    return task


async def _check_governance_rules(
    session: AsyncSession,
    task: StewardTask,
    checker_sub: str,
    checker_domains: list[str],
) -> User | None:
    """Verifies Maker != Checker and Domain Tag requirements."""
    checker_user = await _resolve_user(session, checker_sub)
    checker_id = checker_user.id if checker_user else _parse_uuid(checker_sub)

    # 1. Maker != Checker constraint (Section 4.7, 9.4)
    maker_sub_in_payload = task.payload.get("_maker_sub")
    if maker_sub_in_payload and (
        maker_sub_in_payload == checker_sub or (checker_user and maker_sub_in_payload == checker_user.subject)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MAKER_CHECKER_VIOLATION",
                "message": "The approver must differ from the proposer.",
            },
        )

    if task.maker is not None and checker_id is not None and task.maker == checker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MAKER_CHECKER_VIOLATION",
                "message": "The approver must differ from the proposer.",
            },
        )

    # 2. Safety-Critical Domain Tag check (Section 4.7)
    subcategory: str | None = task.payload.get("subcategory")
    if not subcategory and task.raw_id:
        raw_item = await session.get(RawItem, task.raw_id)
        if raw_item and raw_item.subcategory:
            subcategory = raw_item.subcategory

    if not subcategory and task.kind in ("MERGE", "SPLIT"):
        source_id = _parse_uuid(task.payload.get("source_id"))
        if source_id:
            src_m = await session.get(GoldenMaster, source_id)
            if src_m:
                subcategory = src_m.subcategory

    if subcategory:
        spec = default_registry.get_spec(subcategory)
        db_spec = await session.get(SubcategorySpec, subcategory)

        is_safety_critical = (spec and getattr(spec, "safety_critical", False)) or (
            db_spec and getattr(db_spec, "safety_critical", False)
        )
        spec_segments: list[str] = []
        if spec and getattr(spec, "segment", None):
            spec_segments = list(spec.segment)
        elif db_spec and getattr(db_spec, "segment", None):
            spec_segments = list(db_spec.segment)

        if is_safety_critical and spec_segments:
            effective_domains = set(checker_domains or [])
            if checker_user and checker_user.domains:
                effective_domains.update(checker_user.domains)

            # Check if checker possesses at least one segment domain tag
            has_matching_domain = any(seg in effective_domains for seg in spec_segments)
            if not has_matching_domain:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "DOMAIN_TAG_REQUIRED",
                        "required": spec_segments,
                        "user_domains": list(effective_domains),
                        "message": f"Approval of safety-critical '{subcategory}' requires domain tag(s): {spec_segments}.",
                    },
                )

    return checker_user


async def approve_steward_task(
    session: AsyncSession,
    task_id: int,
    checker_sub: str,
    checker_role: str,
    checker_domains: list[str],
    rationale: str = "Steward approved proposal",
) -> StewardTask:
    """Approves a steward task, executes its domain action, logs audit record, and captures feedback."""
    task = await get_steward_task(session, task_id)
    if task.state != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TASK_NOT_OPEN",
                "message": f"Task #{task_id} has already been decided ({task.state}).",
            },
        )

    checker_user = await _check_governance_rules(session, task, checker_sub, checker_domains)
    checker_id = checker_user.id if checker_user else _parse_uuid(checker_sub)

    # Execute the domain action based on task kind
    payload = task.payload
    target_golden_id: UUID | None = None

    if task.kind == "LINK":
        gid = _parse_uuid(payload.get("golden_id"))
        target_golden_id = gid
        if task.raw_id and gid:
            raw_item = await session.get(RawItem, task.raw_id)
            if raw_item:
                raw_item.golden_id = gid
                raw_item.status = "LINKED"

    elif task.kind == "CREATE_MASTER":
        subcat = payload.get("subcategory", "UNKNOWN")
        attrs = payload.get("attributes", {})
        uom = payload.get("canonical_uom", "EA")
        is_prop = payload.get("is_proprietary", False)
        oem_n = payload.get("oem_name")
        oem_p = payload.get("oem_part_number")
        master = await create_golden_master(
            session=session,
            subcategory=subcat,
            attributes=attrs,
            canonical_uom=uom,
            status="ACTIVE",
            actor_id=checker_id,
            is_proprietary=is_prop,
            oem_name=oem_n,
            oem_part_number=oem_p,
            rationale=f"Approved task #{task.id}: {rationale}",
        )
        target_golden_id = master.id
        if task.raw_id:
            raw_item = await session.get(RawItem, task.raw_id)
            if raw_item:
                raw_item.golden_id = master.id
                raw_item.status = "LINKED"

    elif task.kind == "MERGE":
        src_id = _parse_uuid(payload.get("source_id"))
        tgt_id = _parse_uuid(payload.get("target_id"))
        if src_id and tgt_id:
            target_golden_id = tgt_id
            await merge_golden_masters(
                session=session,
                source_id=src_id,
                target_id=tgt_id,
                actor_id=checker_id,
                rationale=f"Approved task #{task.id}: {rationale}",
            )

    elif task.kind == "SPLIT":
        src_id = _parse_uuid(payload.get("source_id"))
        targets_data = payload.get("targets", [])
        if src_id and targets_data:
            await split_golden_master(
                session=session,
                source_id=src_id,
                target_specs=targets_data,
                actor_id=checker_id,
                rationale=f"Approved task #{task.id}: {rationale}",
            )

    elif task.kind == "CORRECT_ATTR":
        master_id = _parse_uuid(payload.get("master_id"))
        new_attrs = payload.get("attributes", {})
        if master_id and new_attrs:
            target_golden_id = master_id
            await correct_master_attributes(
                session=session,
                master_id=master_id,
                corrected_attributes=new_attrs,
                actor_id=checker_id,
                rationale=f"Approved task #{task.id}: {rationale}",
            )

    # Update Task State
    task.state = "APPROVED"
    task.checker = checker_id
    task.decided_at = datetime.now(UTC)

    # Capture Feedback Example (label=True for approved match/link)
    features = payload.get("features")
    feedback = FeedbackExample(
        raw_id=task.raw_id,
        golden_id=target_golden_id or _parse_uuid(payload.get("golden_id")),
        label=True,
        features=features,
        steward=checker_id,
    )
    session.add(feedback)

    # Record Audit Log
    after_data = json.dumps(
        {
            "id": task.id,
            "kind": task.kind,
            "checker_sub": checker_sub,
            "state": "APPROVED",
            "target_golden_id": str(target_golden_id) if target_golden_id else None,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'STEWARD_TASK_APPROVE', 'steward_tasks', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": checker_id,
            "entity_id": str(task.id),
            "after": after_data,
            "rationale": rationale,
        },
    )

    return task


async def reject_steward_task(
    session: AsyncSession,
    task_id: int,
    checker_sub: str,
    checker_role: str,
    checker_domains: list[str],
    rationale: str = "Steward rejected proposal",
) -> StewardTask:
    """Rejects a steward task, updates state to REJECTED, logs audit record, and captures negative feedback."""
    task = await get_steward_task(session, task_id)
    if task.state != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TASK_NOT_OPEN",
                "message": f"Task #{task_id} has already been decided ({task.state}).",
            },
        )

    checker_user = await _check_governance_rules(session, task, checker_sub, checker_domains)
    checker_id = checker_user.id if checker_user else _parse_uuid(checker_sub)

    task.state = "REJECTED"
    task.checker = checker_id
    task.decided_at = datetime.now(UTC)

    # Capture Feedback Example (label=False for rejected link)
    features = task.payload.get("features")
    feedback = FeedbackExample(
        raw_id=task.raw_id,
        golden_id=_parse_uuid(task.payload.get("golden_id")),
        label=False,
        features=features,
        steward=checker_id,
    )
    session.add(feedback)

    # Record Audit Log
    after_data = json.dumps(
        {
            "id": task.id,
            "kind": task.kind,
            "checker_sub": checker_sub,
            "state": "REJECTED",
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'STEWARD_TASK_REJECT', 'steward_tasks', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": checker_id,
            "entity_id": str(task.id),
            "after": after_data,
            "rationale": rationale,
        },
    )

    return task
