from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import (
    caller_tenant_id,
    get_current_auth_context,
    get_engine,
    pinned_location_id,
    require_location_scope,
    require_permissions,
    require_record_in_location,
)
from app.schemas.daily_update import (
    DailyUpdateCreate,
    DailyUpdateListFilters,
    DailyUpdateListResponse,
    DailyUpdateResponse,
)
from app.services.daily_updates import (
    create_daily_update_service,
    get_daily_update_detail_service,
    list_daily_updates_service,
)
from app.services.auth import AuthContext
from app.services import scope

router = APIRouter(dependencies=[Depends(get_current_auth_context)])

_scope_daily_update = require_record_in_location(
    "daily_update_id",
    lambda engine, daily_update_id: get_daily_update_detail_service(engine, daily_update_id).location_id,
    "Daily update was not found",
)


@router.get("/", response_model=DailyUpdateListResponse)
def list_daily_updates_endpoint(
    _auth: object = Depends(require_permissions("daily_update.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    _scope: object = Depends(require_location_scope("location_id")),
    location_id: int | None = Query(default=None, ge=1),
    user_id: int | None = Query(default=None, ge=1),
    requisition_id: int | None = Query(default=None, ge=1),
    update_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> DailyUpdateListResponse:
    filters = DailyUpdateListFilters(
        location_id=pinned_location_id(auth_context, location_id),
        user_id=user_id,
        requisition_id=requisition_id,
        update_date=update_date,
        page=page,
        page_size=page_size,
    )
    filters.tenant_id = caller_tenant_id(auth_context)
    return list_daily_updates_service(engine, filters)


@router.post("/", response_model=DailyUpdateResponse, status_code=201)
def create_daily_update_endpoint(
    payload: DailyUpdateCreate,
    auth: object = Depends(require_permissions("daily_update.create_main")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> DailyUpdateResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    # The submitter is always the authenticated user — never trust a client-supplied id
    payload.submitted_by_user_id = auth.user.id
    return create_daily_update_service(engine, payload)


@router.get("/{daily_update_id}", response_model=DailyUpdateResponse)
def get_daily_update_detail_endpoint(
    _auth: object = Depends(require_permissions("daily_update.read")),
    _in_scope: object = Depends(_scope_daily_update),
    daily_update_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> DailyUpdateResponse:
    return get_daily_update_detail_service(engine, daily_update_id)
