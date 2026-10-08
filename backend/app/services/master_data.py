from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.master_data import (
    copy_templates_for_tenant,
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
    tenant_id: int | None = None,
) -> MasterDataValueListResponse:
    cat = find_category_by_code(engine, category_code)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master data category '{category_code}' was not found",
        )
    if tenant_id is not None:
        copy_templates_for_tenant(engine, cat.id, tenant_id)
    items, total = list_values_by_category(engine, cat.id, page, page_size, tenant_id)
    return MasterDataValueListResponse(
        items=[MasterDataValueResponse.model_validate(v) for v in items],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


def create_value_service(
    engine: Engine,
    category_code: str,
    payload: MasterDataValueCreate,
    tenant_id: int | None = None,
) -> MasterDataValueResponse:
    cat = find_category_by_code(engine, category_code)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master data category '{category_code}' was not found",
        )
    if tenant_id is not None:
        copy_templates_for_tenant(engine, cat.id, tenant_id)
    existing = find_value_by_code(engine, cat.id, payload.code, tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Value code '{payload.code}' already exists in category '{category_code}'",
        )
    created = create_value(engine, cat.id, payload, tenant_id)
    return MasterDataValueResponse.model_validate(created)


def update_value_service(
    engine: Engine,
    value_id: int,
    payload: MasterDataValueUpdate,
    tenant_id: int | None = None,
) -> MasterDataValueResponse:
    existing = find_value_by_id(engine, value_id)
    # A company edits only its own values; templates and other companies'
    # values are "not found".
    if existing and tenant_id is not None and getattr(existing, "tenant_id", None) != tenant_id:
        existing = None
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master data value was not found",
        )
    updated = update_value(engine, value_id, payload)
    return MasterDataValueResponse.model_validate(updated)
