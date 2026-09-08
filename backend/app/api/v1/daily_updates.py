from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_location_scope, require_permissions
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

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=DailyUpdateListResponse)
def list_daily_updates_endpoint(
    _auth: object = Depends(require_permissions("daily_update.read")),
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
        location_id=location_id,
        user_id=user_id,
        requisition_id=requisition_id,
        update_date=update_date,
        page=page,
        page_size=page_size,
    )
    return list_daily_updates_service(engine, filters)


@router.post("/", response_model=DailyUpdateResponse, status_code=201)
def create_daily_update_endpoint(
    payload: DailyUpdateCreate,
    auth: object = Depends(require_permissions("daily_update.create_main")),
    engine: Engine = Depends(get_engine),
) -> DailyUpdateResponse:
    # The submitter is always the authenticated user — never trust a client-supplied id
    payload.submitted_by_user_id = auth.user.id
    return create_daily_update_service(engine, payload)


@router.get("/{daily_update_id}", response_model=DailyUpdateResponse)
def get_daily_update_detail_endpoint(
    _auth: object = Depends(require_permissions("daily_update.read")),
    daily_update_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> DailyUpdateResponse:
    return get_daily_update_detail_service(engine, daily_update_id)
