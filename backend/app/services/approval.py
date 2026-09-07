from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.approval import (
    create_approval,
    decide_approval,
    find_approval_by_id,
    list_approvals,
)
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalListFilters,
    ApprovalListResponse,
    ApprovalResponse,
)
from app.schemas.pagination import PaginationMeta


def list_approvals_service(engine: Engine, filters: ApprovalListFilters) -> ApprovalListResponse:
    items, total = list_approvals(engine, filters)
    return ApprovalListResponse(
        items=[ApprovalResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_approval_detail_service(engine: Engine, approval_id: int) -> ApprovalResponse:
    approval = find_approval_by_id(engine, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return ApprovalResponse.model_validate(approval)


def create_approval_service(engine: Engine, payload: ApprovalCreate) -> ApprovalResponse:
    created = create_approval(engine, payload)
    return ApprovalResponse.model_validate(created)


def decide_approval_service(engine: Engine, approval_id: int, payload: ApprovalDecision) -> ApprovalResponse:
    existing = find_approval_by_id(engine, approval_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if existing.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval already {existing.status}",
        )
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Decision must be 'approved' or 'rejected'",
        )
    updated = decide_approval(engine, approval_id, payload)
    return ApprovalResponse.model_validate(updated)
