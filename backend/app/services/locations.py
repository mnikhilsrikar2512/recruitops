from fastapi import HTTPException, status
from sqlalchemy import Engine, text

from app.repositories.locations import (
    create_location,
    find_location_by_code,
    find_location_by_id,
    list_locations,
    update_location,
    user_exists,
)
from app.schemas.location import (
    LocationCreate,
    LocationListFilters,
    LocationListResponse,
    LocationResponse,
    LocationUpdate,
)
from app.schemas.pagination import PaginationMeta


def get_location_detail_service(engine: Engine, location_id: int) -> LocationResponse:
    existing_location = find_location_by_id(engine, location_id)
    if not existing_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location was not found",
        )
    return LocationResponse.model_validate(existing_location)


def list_locations_service(engine: Engine, filters: LocationListFilters) -> LocationListResponse:
    items, total = list_locations(engine, filters)
    return LocationListResponse(
        items=[LocationResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def _head_in_company(engine: Engine, user_id: int, tenant_id: int | None) -> bool:
    if not user_exists(engine, user_id):
        return False
    if tenant_id is None:
        return True
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT 1 FROM dbo.users WHERE id = :user_id AND tenant_id = :tenant_id"),
            {"user_id": user_id, "tenant_id": tenant_id},
        ).first() is not None


def create_location_service(engine: Engine, payload: LocationCreate, tenant_id: int | None = None) -> LocationResponse:
    existing_location = find_location_by_code(engine, payload.location_code, tenant_id)
    if existing_location:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location code already exists",
        )

    if payload.location_head_user_id and not _head_in_company(engine, payload.location_head_user_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location head user was not found",
        )

    created = create_location(engine, payload, tenant_id)
    return LocationResponse.model_validate(created)


def update_location_service(
    engine: Engine, location_id: int, payload: LocationUpdate, tenant_id: int | None = None
) -> LocationResponse:
    existing_location = find_location_by_id(engine, location_id)
    if not existing_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location was not found",
        )

    if payload.location_head_user_id is not None and not _head_in_company(engine, payload.location_head_user_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location head user was not found",
        )

    updated = update_location(engine, location_id, payload)
    return LocationResponse.model_validate(updated)

