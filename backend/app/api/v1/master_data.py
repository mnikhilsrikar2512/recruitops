from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.master_data import (
    MasterDataCategoryResponse,
    MasterDataValueCreate,
    MasterDataValueListResponse,
    MasterDataValueResponse,
    MasterDataValueUpdate,
)
from app.services.master_data import (
    create_value_service,
    get_category_service,
    list_values_service,
    update_value_service,
)

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get(
    "/categories/{category_code}",
    response_model=MasterDataCategoryResponse,
)
def get_category_endpoint(
    _auth: object = Depends(require_permissions("settings.read")),
    category_code: str = Path(..., min_length=1, max_length=100),
    engine: Engine = Depends(get_engine),
) -> MasterDataCategoryResponse:
    return get_category_service(engine, category_code)


@router.get(
    "/categories/{category_code}/values",
    response_model=MasterDataValueListResponse,
)
def list_values_endpoint(
    _auth: object = Depends(require_permissions("settings.read")),
    category_code: str = Path(..., min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> MasterDataValueListResponse:
    return list_values_service(engine, category_code, page, page_size)


@router.post(
    "/categories/{category_code}/values",
    response_model=MasterDataValueResponse,
    status_code=201,
)
def create_value_endpoint(
    payload: MasterDataValueCreate,
    _auth: object = Depends(require_permissions("settings.create")),
    category_code: str = Path(..., min_length=1, max_length=100),
    engine: Engine = Depends(get_engine),
) -> MasterDataValueResponse:
    return create_value_service(engine, category_code, payload)


@router.patch(
    "/values/{value_id}",
    response_model=MasterDataValueResponse,
)
def update_value_endpoint(
    payload: MasterDataValueUpdate,
    _auth: object = Depends(require_permissions("settings.update")),
    value_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> MasterDataValueResponse:
    return update_value_service(engine, value_id, payload)
