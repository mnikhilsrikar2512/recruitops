from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Engine

from app.api.deps import (
    reject_unknown_query_params,
    caller_tenant_id,
    get_current_auth_context,
    get_engine,
    invalidate_permission_cache,
    require_permissions,
)
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

from app.services import scope
from app.services.auth import AuthContext

router = APIRouter(dependencies=[Depends(require_permissions("role.read"))])


def _scope_role(
    role_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> None:
    """A company sees its own roles and the shared system roles only."""
    scope.assert_role_usable(engine, auth_context, role_id)


def _editable_role(
    role_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> None:
    """Shared system roles (tenant_id NULL) are read-only to companies."""
    scope.assert_role_usable(engine, auth_context, role_id)
    if caller_tenant_id(auth_context) is not None and scope.role_is_system(engine, role_id):
        raise HTTPException(status_code=403, detail="System roles are read-only")


@router.get("/", response_model=RoleListResponse, dependencies=[Depends(reject_unknown_query_params)])
def list_roles_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> RoleListResponse:
    filters = RoleListFilters(status=status, search=search, page=page, page_size=page_size)
    filters.tenant_id = caller_tenant_id(auth_context)
    return list_roles_service(engine, filters)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role_detail_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    _role_scope: object = Depends(_scope_role),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RoleResponse:
    return get_role_detail_service(engine, role_id)


@router.get("/{role_id}/permissions", response_model=RolePermissionsResponse)
def get_role_permissions_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    _role_scope: object = Depends(_scope_role),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RolePermissionsResponse:
    return get_role_permissions_service(engine, role_id)


@router.post("/", response_model=RoleResponse, status_code=201)
def create_role_endpoint(
    payload: RoleCreate,
    _auth: object = Depends(require_permissions("role.create")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> RoleResponse:
    return create_role_service(engine, payload, caller_tenant_id(auth_context))


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role_endpoint(
    payload: RoleUpdate,
    _auth: object = Depends(require_permissions("role.update")),
    _role_scope: object = Depends(_editable_role),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RoleResponse:
    return update_role_service(engine, role_id, payload)


@router.put("/{role_id}/permissions", response_model=RolePermissionsResponse)
def assign_role_permissions_endpoint(
    payload: RolePermissionsUpdate,
    _auth: object = Depends(require_permissions("role.permissions.assign")),
    _role_scope: object = Depends(_editable_role),
    role_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> RolePermissionsResponse:
    response = assign_role_permissions_service(engine, role_id, payload)
    invalidate_permission_cache()  # permission grants changed — drop stale cached sets
    return response
