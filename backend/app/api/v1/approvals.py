from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalListFilters,
    ApprovalListResponse,
    ApprovalResponse,
)
from app.services.approval import (
    create_approval_service,
    decide_approval_service,
    get_approval_detail_service,
    list_approvals_service,
)

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=ApprovalListResponse)
def list_approvals_endpoint(
    _auth: object = Depends(require_permissions("approval.read")),
    location_id: int | None = Query(default=None, ge=1),
    approval_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    requester_user_id: int | None = Query(default=None, ge=1),
    assigned_reviewer_user_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> ApprovalListResponse:
    filters = ApprovalListFilters(
        location_id=location_id,
        approval_type=approval_type,
        status=status,
        priority=priority,
        requester_user_id=requester_user_id,
        assigned_reviewer_user_id=assigned_reviewer_user_id,
        page=page,
        page_size=page_size,
    )
    return list_approvals_service(engine, filters)


@router.post("/", response_model=ApprovalResponse, status_code=201)
def create_approval_endpoint(
    payload: ApprovalCreate,
    _auth: object = Depends(require_permissions("approval.create")),
    engine: Engine = Depends(get_engine),
) -> ApprovalResponse:
    return create_approval_service(engine, payload)


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval_detail_endpoint(
    _auth: object = Depends(require_permissions("approval.read")),
    approval_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> ApprovalResponse:
    return get_approval_detail_service(engine, approval_id)


@router.patch("/{approval_id}/decide", response_model=ApprovalResponse)
def decide_approval_endpoint(
    approval_id: int = Path(..., ge=1),
    payload: ApprovalDecision = ...,
    _auth: object = Depends(require_permissions("approval.decide")),
    engine: Engine = Depends(get_engine),
) -> ApprovalResponse:
    return decide_approval_service(engine, approval_id, payload)
