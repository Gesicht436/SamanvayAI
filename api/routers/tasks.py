"""FastAPI router for stewardship governance tasks (Section 4.7, 8.0, 9.4)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.stewardship import (
    approve_steward_task,
    create_steward_task,
    get_steward_task,
    list_steward_tasks,
    reject_steward_task,
)

router = APIRouter(prefix="/tasks", tags=["stewardship"])


class TaskCreateRequest(BaseModel):
    """Payload to propose a new stewardship task."""

    kind: str = Field(..., description="LINK, CREATE_MASTER, MERGE, SPLIT, CORRECT_ATTR, DOC_REVIEW")
    payload: dict[str, Any] = Field(..., description="Action parameters and attributes")
    raw_id: UUID | None = Field(default=None, description="Linked raw item ID if applicable")
    reason_codes: list[str] = Field(default_factory=list, description="Associated heuristic codes")


class TaskDecisionRequest(BaseModel):
    """Payload for approving or rejecting a task."""

    rationale: str = Field(default="Steward reviewed decision", description="Audit rationale")


class TaskResponse(BaseModel):
    """Serialized representation of a stewardship task."""

    id: int
    raw_id: UUID | None
    kind: str
    payload: dict[str, Any]
    reason_codes: list[str]
    maker: UUID | None
    checker: UUID | None
    state: str
    created_at: datetime | None
    decided_at: datetime | None


def _serialize_task(task: Any) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        raw_id=task.raw_id,
        kind=task.kind,
        payload=task.payload,
        reason_codes=task.reason_codes or [],
        maker=task.maker,
        checker=task.checker,
        state=task.state,
        created_at=task.created_at,
        decided_at=task.decided_at,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(
    req: TaskCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new stewardship proposal. Must be initiated by a Maker or Admin."""
    if current_user.role not in ("MAKER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INSUFFICIENT_ROLE",
                "message": f"Only Makers or Admins can propose tasks (current: {current_user.role}).",
            },
        )

    task = await create_steward_task(
        session=db,
        kind=req.kind,
        payload=req.payload,
        maker_sub=current_user.sub,
        raw_id=req.raw_id,
        reason_codes=req.reason_codes,
        org_id=current_user.org_id,
    )
    await db.commit()
    return _serialize_task(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks_endpoint(
    state: str | None = Query(default=None, description="Filter by state (OPEN, APPROVED, REJECTED)"),
    kind: str | None = Query(default=None, description="Filter by kind"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists stewardship tasks with optional state and kind filters."""
    tasks = await list_steward_tasks(
        session=db,
        state=state,
        kind=kind,
        limit=limit,
        offset=offset,
    )
    return [_serialize_task(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_endpoint(
    task_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a single stewardship task by ID."""
    task = await get_steward_task(db, task_id)
    return _serialize_task(task)


@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_task_endpoint(
    task_id: int,
    req: TaskDecisionRequest = TaskDecisionRequest(),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approves a stewardship task. Requires Checker or Admin role, different from the proposer."""
    if current_user.role not in ("CHECKER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INSUFFICIENT_ROLE",
                "message": f"Only Checkers or Admins can approve tasks (current: {current_user.role}).",
            },
        )

    task = await approve_steward_task(
        session=db,
        task_id=task_id,
        checker_sub=current_user.sub,
        checker_role=current_user.role,
        checker_domains=current_user.domains,
        rationale=req.rationale,
    )
    await db.commit()
    return _serialize_task(task)


@router.post("/{task_id}/reject", response_model=TaskResponse)
async def reject_task_endpoint(
    task_id: int,
    req: TaskDecisionRequest = TaskDecisionRequest(),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rejects a stewardship task. Requires Checker or Admin role, different from the proposer."""
    if current_user.role not in ("CHECKER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INSUFFICIENT_ROLE",
                "message": f"Only Checkers or Admins can reject tasks (current: {current_user.role}).",
            },
        )

    task = await reject_steward_task(
        session=db,
        task_id=task_id,
        checker_sub=current_user.sub,
        checker_role=current_user.role,
        checker_domains=current_user.domains,
        rationale=req.rationale,
    )
    await db.commit()
    return _serialize_task(task)
