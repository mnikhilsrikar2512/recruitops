from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.role import (
    RoleCreate,
    RoleListFilters,
    RoleListResponse,
    RolePermissionsResponse,
    RolePermissionsUpdate,
    RoleResponse,
    RoleUpdate,
)
from app.services.roles import (
    assign_role_permissions_service,
    create_role_service,
    get_role_detail_service,
    get_role_permissions_service,
    list_roles_service,
    update_role_service,
)

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=RoleListResponse)
def list_roles_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> RoleListResponse:
    filters = RoleListFilters(status=status, search=search, page=page, page_size=page_size)
    return list_roles_service(engine, filters)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role_detail_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RoleResponse:
    return get_role_detail_service(engine, role_id)


@router.get("/{role_id}/permissions", response_model=RolePermissionsResponse)
def get_role_permissions_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RolePermissionsResponse:
    return get_role_permissions_service(engine, role_id)


@router.post("/", response_model=RoleResponse, status_code=201)
def create_role_endpoint(
    payload: RoleCreate,
    _auth: object = Depends(require_permissions("role.create")),
    engine: Engine = Depends(get_engine),
) -> RoleResponse:
    return create_role_service(engine, payload)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role_endpoint(
    payload: RoleUpdate,
    _auth: object = Depends(require_permissions("role.update")),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RoleResponse:
    return update_role_service(engine, role_id, payload)


@router.put("/{role_id}/permissions", response_model=RolePermissionsResponse)
def assign_role_permissions_endpoint(
    payload: RolePermissionsUpdate,
    _auth: object = Depends(require_permissions("role.permissions.assign")),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RolePermissionsResponse:
    return assign_role_permissions_service(engine, role_id, payload)
