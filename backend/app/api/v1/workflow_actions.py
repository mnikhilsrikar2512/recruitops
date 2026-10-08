from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import caller_tenant_id, get_current_auth_context, get_engine, require_permissions
from app.schemas.workflow_action import (
    OverlaySubmissionCreate,
    WorkflowActionEventCreate,
    WorkflowActionEventResponse,
    WorkflowActionNudgeRequest,
    WorkflowActionQueueFilters,
    WorkflowActionQueueResponse,
    WorkflowActionResolveRequest,
    WorkflowActionStatus,
)
from app.services.auth import AuthContext
from app.services import scope
from app.services.workflow_actions import (
    list_workflow_actions_service,
    nudge_workflow_action_service,
    resolve_workflow_action_service,
    run_workflow_action_service,
    submit_overlay_service,
)

router = APIRouter()


@router.get("/queue", response_model=WorkflowActionQueueResponse)
def list_workflow_actions_endpoint(
    _auth: object = Depends(require_permissions("workflow_action.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    status: WorkflowActionStatus | None = Query(default="open"),
    source: str | None = Query(default=None),
    location_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> WorkflowActionQueueResponse:
    filters = WorkflowActionQueueFilters(
        status=status,
        source=source,
        location_id=location_id,
        page=page,
        page_size=page_size,
    )
    filters.tenant_id = caller_tenant_id(auth_context)
    return list_workflow_actions_service(engine, auth_context, filters)


@router.post("/overlay-submissions", response_model=WorkflowActionEventResponse, status_code=201)
def submit_overlay_endpoint(
    payload: OverlaySubmissionCreate,
    _auth: object = Depends(require_permissions("workflow_overlay.submit")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> WorkflowActionEventResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return submit_overlay_service(engine, auth_context, payload)


@router.post("/{action_item_id}/run", response_model=WorkflowActionEventResponse, status_code=201)
def run_workflow_action_endpoint(
    payload: WorkflowActionEventCreate,
    _auth: object = Depends(require_permissions("workflow_action.run")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    action_item_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> WorkflowActionEventResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return run_workflow_action_service(engine, auth_context, action_item_id, payload)


@router.post("/{action_item_id}/resolve", response_model=WorkflowActionEventResponse, status_code=201)
def resolve_workflow_action_endpoint(
    payload: WorkflowActionResolveRequest,
    _auth: object = Depends(require_permissions("workflow_action.resolve")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    action_item_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> WorkflowActionEventResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return resolve_workflow_action_service(engine, auth_context, action_item_id, payload)


@router.post("/{action_item_id}/nudge", response_model=WorkflowActionEventResponse, status_code=201)
def nudge_workflow_action_endpoint(
    payload: WorkflowActionNudgeRequest,
    _auth: object = Depends(require_permissions("workflow_action.nudge")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    action_item_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> WorkflowActionEventResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return nudge_workflow_action_service(engine, auth_context, action_item_id, payload)
