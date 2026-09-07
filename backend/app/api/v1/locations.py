from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.location import (
    LocationCreate,
    LocationListFilters,
    LocationListResponse,
    LocationResponse,
    LocationUpdate,
)
from app.services.locations import (
    create_location_service,
    get_location_detail_service,
    list_locations_service,
    update_location_service,
)

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=LocationListResponse)
def list_locations_endpoint(
    _auth: object = Depends(require_permissions("location.read")),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> LocationListResponse:
    filters = LocationListFilters(
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return list_locations_service(engine, filters)


@router.get("/{location_id}", response_model=LocationResponse)
def get_location_detail_endpoint(
    _auth: object = Depends(require_permissions("location.read")),
    location_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> LocationResponse:
    return get_location_detail_service(engine, location_id)


@router.post("/", response_model=LocationResponse, status_code=201)
def create_location_endpoint(
    payload: LocationCreate,
    _auth: object = Depends(require_permissions("location.create")),
    engine: Engine = Depends(get_engine),
) -> LocationResponse:
    return create_location_service(engine, payload)


@router.patch("/{location_id}", response_model=LocationResponse)
def update_location_endpoint(
    payload: LocationUpdate,
    _auth: object = Depends(require_permissions("location.update")),
    location_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> LocationResponse:
    return update_location_service(engine, location_id, payload)
