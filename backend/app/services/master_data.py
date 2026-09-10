from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.master_data import (
    create_value,
    find_category_by_code,
    find_value_by_code,
    find_value_by_id,
    list_values_by_category,
    update_value,
)
from app.schemas.master_data import (
    MasterDataCategoryResponse,
    MasterDataValueCreate,
    MasterDataValueListResponse,
    MasterDataValueResponse,
    MasterDataValueUpdate,
)
from app.schemas.pagination import PaginationMeta


def get_category_service(engine: Engine, category_code: str) -> MasterDataCategoryResponse:
    cat = find_category_by_code(engine, category_code)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master data category '{category_code}' was not found",
        )
    return MasterDataCategoryResponse.model_validate(cat)


def list_values_service(
    engine: Engine,
    category_code: str,
    page: int = 1,
    page_size: int = 50,
) -> MasterDataValueListResponse:
    cat = find_category_by_code(engine, category_code)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master data category '{category_code}' was not found",
        )
    items, total = list_values_by_category(engine, cat.id, page, page_size)
    return MasterDataValueListResponse(
        items=[MasterDataValueResponse.model_validate(v) for v in items],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


def create_value_service(
    engine: Engine,
    category_code: str,
    payload: MasterDataValueCreate,
) -> MasterDataValueResponse:
    cat = find_category_by_code(engine, category_code)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master data category '{category_code}' was not found",
        )
    existing = find_value_by_code(engine, cat.id, payload.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Value code '{payload.code}' already exists in category '{category_code}'",
        )
    created = create_value(engine, cat.id, payload)
    return MasterDataValueResponse.model_validate(created)


def update_value_service(
    engine: Engine,
    value_id: int,
    payload: MasterDataValueUpdate,
) -> MasterDataValueResponse:
    existing = find_value_by_id(engine, value_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master data value was not found",
        )
    updated = update_value(engine, value_id, payload)
    return MasterDataValueResponse.model_validate(updated)
