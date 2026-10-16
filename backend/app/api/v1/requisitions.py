from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import (
    sort_clause,
    reject_unknown_query_params,
    caller_tenant_id,
    get_current_auth_context,
    get_engine,
    pinned_location_id,
    require_location_scope,
    require_permissions,
    require_record_in_location,
)
from app.schemas.requisition import (
    RequisitionAssignmentCreate,
    RequisitionAssignmentResponse,
    RequisitionCreate,
    RequisitionListFilters,
    RequisitionListResponse,
    RequisitionResponse,
    RequisitionOwnerReassignment,
    RequisitionOwnerReassignmentResponse,
    RequisitionHoldCreate,
    RequisitionHoldResponse,
    RequisitionResume,
    RequisitionStatusUpdate,
    RequisitionUpdate,
)
from app.services.requisitions import (
    create_requisition_assignment_service,
    create_requisition_service,
    get_requisition_detail_service,
    hold_requisition_service,
    list_requisition_holds_service,
    resume_requisition_service,
    list_requisition_assignments_service,
    list_requisitions_service,
    remove_requisition_assignment_service,
    reassign_requisition_owners_service,
    update_requisition_service,
    update_requisition_status_service,
)
from app.services.auth import AuthContext
from app.services import scope
from app.services.visibility import mask_list, mask_single

router = APIRouter(dependencies=[Depends(get_current_auth_context)])

# Phase 4.9: fields the list can be sorted by (?sort=field or -field).
_REQUISITIONS_SORT = {"title": "title", "status": "status", "priority": "priority", "target_closure_date": "target_close_date", "openings_count": "open_positions", "created_at": "created_at", "updated_at": "updated_at"}

_scope_requisition = require_record_in_location(
    "requisition_id",
    lambda engine, requisition_id: get_requisition_detail_service(engine, requisition_id).location_id,
    "Requisition was not found",
)


@router.get("/", response_model=RequisitionListResponse, dependencies=[Depends(reject_unknown_query_params)])
def list_requisitions_endpoint(
    _auth: object = Depends(require_permissions("requisition.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    _scope: object = Depends(require_location_scope("location_id")),
    location_id: int | None = Query(default=None, ge=1),
    client_id: int | None = Query(default=None, ge=1),
    primary_owner_user_id: int | None = Query(default=None, ge=1),
    delivery_owner_user_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    due_date_from: str | None = Query(default=None),
    due_date_to: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str | None = Query(default=None, description="field or -field; comma-separated"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> RequisitionListResponse:
    filters = RequisitionListFilters(
        location_id=pinned_location_id(auth_context, location_id),
        client_id=client_id,
        primary_owner_user_id=primary_owner_user_id,
        delivery_owner_user_id=delivery_owner_user_id,
        status=status,
        priority=priority,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        page=page,
        page_size=page_size,
    )
    filters.order_by = sort_clause(sort, _REQUISITIONS_SORT, "updated_at DESC, id DESC") + (", id DESC" if sort else "")
    filters.tenant_id = caller_tenant_id(auth_context)
    response = list_requisitions_service(engine, filters)
    return mask_list("requisition", response, auth_context.user.role_code, engine, caller_tenant_id(auth_context))


@router.post("/", response_model=RequisitionResponse, status_code=201)
def create_requisition_endpoint(
    payload: RequisitionCreate,
    _auth: object = Depends(require_permissions("requisition.create")),
    _scope: object = Depends(require_location_scope("location_id")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> RequisitionResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return create_requisition_service(engine, payload)


@router.get("/{requisition_id}", response_model=RequisitionResponse)
def get_requisition_detail_endpoint(
    _auth: object = Depends(require_permissions("requisition.read")),
    _in_scope: object = Depends(_scope_requisition),
    auth_context: AuthContext = Depends(get_current_auth_context),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RequisitionResponse:
    response = get_requisition_detail_service(engine, requisition_id)
    return mask_single("requisition", response, auth_context.user.role_code, engine, caller_tenant_id(auth_context))


@router.patch("/{requisition_id}", response_model=RequisitionResponse)
def update_requisition_endpoint(
    payload: RequisitionUpdate,
    _auth: object = Depends(require_permissions("requisition.update")),
    _in_scope: object = Depends(_scope_requisition),
    requisition_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> RequisitionResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return update_requisition_service(engine, requisition_id, payload)


@router.patch("/{requisition_id}/status", response_model=RequisitionResponse)
def update_requisition_status_endpoint(
    payload: RequisitionStatusUpdate,
    _auth: object = Depends(require_permissions("requisition.status.update")),
    _in_scope: object = Depends(_scope_requisition),
    auth_context: AuthContext = Depends(get_current_auth_context),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RequisitionResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return update_requisition_status_service(engine, requisition_id, payload, auth_context)


@router.post("/{requisition_id}/hold", response_model=RequisitionResponse)
def hold_requisition_endpoint(
    payload: RequisitionHoldCreate,
    _auth: object = Depends(require_permissions("requisition.status.update")),
    _in_scope: object = Depends(_scope_requisition),
    auth_context: AuthContext = Depends(get_current_auth_context),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RequisitionResponse:
    """Phase 4.12: put on hold with a reason; candidates freeze, clocks pause."""
    return hold_requisition_service(engine, requisition_id, payload, auth_context)


@router.post("/{requisition_id}/resume", response_model=RequisitionResponse)
def resume_requisition_endpoint(
    payload: RequisitionResume,
    _auth: object = Depends(require_permissions("requisition.status.update")),
    _in_scope: object = Depends(_scope_requisition),
    auth_context: AuthContext = Depends(get_current_auth_context),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RequisitionResponse:
    """Phase 4.12: back to the status it had; the target date moves out by the hold days."""
    return resume_requisition_service(engine, requisition_id, payload, auth_context)


@router.get("/{requisition_id}/holds", response_model=list[RequisitionHoldResponse])
def list_requisition_holds_endpoint(
    _auth: object = Depends(require_permissions("requisition.read")),
    _in_scope: object = Depends(_scope_requisition),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> list[RequisitionHoldResponse]:
    return list_requisition_holds_service(engine, requisition_id)


@router.get("/{requisition_id}/assignments", response_model=list[RequisitionAssignmentResponse])
def list_requisition_assignments_endpoint(
    _auth: object = Depends(require_permissions("assignment.read")),
    _in_scope: object = Depends(_scope_requisition),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> list[RequisitionAssignmentResponse]:
    return list_requisition_assignments_service(engine, requisition_id)


@router.post("/{requisition_id}/assignments", response_model=RequisitionAssignmentResponse, status_code=201)
def create_requisition_assignment_endpoint(
    payload: RequisitionAssignmentCreate,
    _auth: object = Depends(require_permissions("assignment.create")),
    _in_scope: object = Depends(_scope_requisition),
    requisition_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> RequisitionAssignmentResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return create_requisition_assignment_service(engine, requisition_id, payload)


@router.delete("/assignments/{assignment_id}")
def remove_requisition_assignment_endpoint(
    _auth: object = Depends(require_permissions("assignment.update")),
    assignment_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> dict[str, object]:
    return remove_requisition_assignment_service(engine, assignment_id)


@router.post("/{requisition_id}/reassign-owners", response_model=RequisitionOwnerReassignmentResponse)
def reassign_requisition_owners_endpoint(
    payload: RequisitionOwnerReassignment,
    _auth: object = Depends(require_permissions("requisition.update")),
    _in_scope: object = Depends(_scope_requisition),
    auth_context: AuthContext = Depends(get_current_auth_context),
    requisition_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RequisitionOwnerReassignmentResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return reassign_requisition_owners_service(engine, requisition_id, payload, auth_context)
