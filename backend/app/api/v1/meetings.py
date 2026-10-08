from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import (
    reject_unknown_query_params,
    caller_tenant_id,
    get_current_auth_context,
    get_engine,
    pinned_location_id,
    require_location_scope,
    require_permissions,
    require_record_in_location,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingListFilters,
    MeetingListResponse,
    MeetingResponse,
    MeetingUpdate,
)
from app.services.meetings import (
    create_meeting_service,
    get_meeting_detail_service,
    list_meetings_service,
    update_meeting_service,
)
from app.services.auth import AuthContext
from app.services import scope

router = APIRouter(dependencies=[Depends(get_current_auth_context)])

_scope_meeting = require_record_in_location(
    "meeting_id",
    lambda engine, meeting_id: get_meeting_detail_service(engine, meeting_id).location_id,
    "Meeting was not found",
)


@router.get("/", response_model=MeetingListResponse, dependencies=[Depends(reject_unknown_query_params)])
def list_meetings_endpoint(
    _auth: object = Depends(require_permissions("meeting.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    _scope: object = Depends(require_location_scope("location_id")),
    location_id: int | None = Query(default=None, ge=1),
    client_id: int | None = Query(default=None, ge=1),
    meeting_owner_user_id: int | None = Query(default=None, ge=1),
    attendance_status: str | None = Query(default=None),
    outcome_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> MeetingListResponse:
    filters = MeetingListFilters(
        location_id=pinned_location_id(auth_context, location_id),
        client_id=client_id,
        meeting_owner_user_id=meeting_owner_user_id,
        attendance_status=attendance_status,
        outcome_status=outcome_status,
        page=page,
        page_size=page_size,
    )
    filters.tenant_id = caller_tenant_id(auth_context)
    return list_meetings_service(engine, filters)


@router.post("/", response_model=MeetingResponse, status_code=201)
def create_meeting_endpoint(
    payload: MeetingCreate,
    _auth: object = Depends(require_permissions("meeting.create")),
    _scope: object = Depends(require_location_scope("location_id")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> MeetingResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return create_meeting_service(engine, payload)


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting_detail_endpoint(
    _auth: object = Depends(require_permissions("meeting.read")),
    _in_scope: object = Depends(_scope_meeting),
    meeting_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> MeetingResponse:
    return get_meeting_detail_service(engine, meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
def update_meeting_endpoint(
    payload: MeetingUpdate,
    _auth: object = Depends(require_permissions("meeting.update")),
    _in_scope: object = Depends(_scope_meeting),
    meeting_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> MeetingResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return update_meeting_service(engine, meeting_id, payload)
