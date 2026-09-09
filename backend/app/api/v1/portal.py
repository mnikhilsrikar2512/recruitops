from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_engine, require_permissions
from app.schemas.portal import (
    PortalAccountCreate,
    PortalAccountListFilters,
    PortalAccountListResponse,
    PortalAccountResponse,
    PortalAccountUpdate,
    PortalAvailabilityResponse,
    PortalSlotCreate,
    PortalSlotListFilters,
    PortalSlotListResponse,
    PortalSlotResponse,
    PortalSlotUpdate,
    PortalWeeklyUsageResponse,
)
from app.services.portal import (
    create_portal_account_service,
    create_portal_slot_service,
    delete_portal_slot_service,
    get_portal_account_service,
    list_portal_accounts_service,
    list_portal_slots_service,
    portal_availability_service,
    portal_usage_summary_service,
    update_portal_account_service,
    update_portal_slot_service,
)

router = APIRouter()


@router.get("/", response_model=PortalAccountListResponse)
def list_portal_accounts_endpoint(
    _auth: object = Depends(require_permissions("portal.read")),
    status: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    ownership_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> PortalAccountListResponse:
    filters = PortalAccountListFilters(
        status=status,
        platform=platform,
        ownership_type=ownership_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    return list_portal_accounts_service(engine, filters)


@router.get("/availability", response_model=PortalAvailabilityResponse)
def portal_availability_endpoint(
    _auth: object = Depends(require_permissions("portal.read")),
    platform: str | None = Query(default=None),
    branch_id: int | None = Query(default=None, ge=1),
    usage_date: str | None = Query(default=None),
    engine: Engine = Depends(get_engine),
) -> PortalAvailabilityResponse:
    return portal_availability_service(engine, platform, branch_id, usage_date)


@router.get("/usage-summary", response_model=PortalWeeklyUsageResponse)
def portal_usage_summary_endpoint(
    _auth: object = Depends(require_permissions("portal.read")),
    weeks_back: int = Query(default=6, ge=1, le=52),
    engine: Engine = Depends(get_engine),
) -> PortalWeeklyUsageResponse:
    return portal_usage_summary_service(engine, weeks_back)


@router.get("/{portal_account_id}", response_model=PortalAccountResponse)
def get_portal_account_endpoint(
    _auth: object = Depends(require_permissions("portal.read")),
    portal_account_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> PortalAccountResponse:
    return get_portal_account_service(engine, portal_account_id)


@router.post("/", response_model=PortalAccountResponse, status_code=201)
def create_portal_account_endpoint(
    payload: PortalAccountCreate,
    auth: object = Depends(require_permissions("portal.create")),
    engine: Engine = Depends(get_engine),
) -> PortalAccountResponse:
    # Personal accounts default to the authenticated user as owner
    if payload.ownership_type == "personal" and payload.owned_by_user_id is None:
        payload.owned_by_user_id = auth.user.id
    return create_portal_account_service(engine, payload, actor_user_id=auth.user.id)


@router.patch("/{portal_account_id}", response_model=PortalAccountResponse)
def update_portal_account_endpoint(
    payload: PortalAccountUpdate,
    _auth: object = Depends(require_permissions("portal.update")),
    portal_account_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> PortalAccountResponse:
    return update_portal_account_service(engine, portal_account_id, payload)


@router.get("/{portal_account_id}/slots", response_model=PortalSlotListResponse)
def list_portal_slots_endpoint(
    portal_account_id: int = Path(..., ge=1),
    _auth: object = Depends(require_permissions("portal.read")),
    status: str | None = Query(default=None),
    usage_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    engine: Engine = Depends(get_engine),
) -> PortalSlotListResponse:
    filters = PortalSlotListFilters(
        status=status,
        usage_date=usage_date,
        page=page,
        page_size=page_size,
    )
    return list_portal_slots_service(engine, portal_account_id, filters)


@router.post("/{portal_account_id}/slots", response_model=PortalSlotResponse, status_code=201)
def create_portal_slot_endpoint(
    payload: PortalSlotCreate,
    _auth: object = Depends(require_permissions("portal.assign_slot")),
    portal_account_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> PortalSlotResponse:
    return create_portal_slot_service(engine, portal_account_id, payload)


@router.patch("/{portal_account_id}/slots/{slot_id}", response_model=PortalSlotResponse)
def update_portal_slot_endpoint(
    payload: PortalSlotUpdate,
    _auth: object = Depends(require_permissions("portal.assign_slot")),
    portal_account_id: int = Path(..., ge=1),
    slot_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> PortalSlotResponse:
    return update_portal_slot_service(engine, portal_account_id, slot_id, payload)


@router.delete("/{portal_account_id}/slots/{slot_id}", status_code=204)
def delete_portal_slot_endpoint(
    _auth: object = Depends(require_permissions("portal.assign_slot")),
    portal_account_id: int = Path(..., ge=1),
    slot_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> None:
    delete_portal_slot_service(engine, portal_account_id, slot_id)
