from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import (
    get_current_auth_context,
    get_engine,
    pinned_location_id,
    require_permissions,
    require_record_in_location,
)
from app.schemas.user import (
    UserCreate,
    UserDeactivateRequest,
    UserDeactivationResponse,
    UserListFilters,
    UserListResponse,
    UserMoveRequest,
    UserMoveResponse,
    UserResetCredentials,
    UserResetCredentialsResponse,
    UserResponse,
    UserUpdate,
)
from app.services.users import (
    create_user_service,
    deactivate_user_service,
    get_user_detail_service,
    list_users_service,
    move_user_service,
    reset_user_credentials_service,
    update_user_service,
)
from app.services.auth import AuthContext

router = APIRouter(dependencies=[Depends(get_current_auth_context)])

_scope_user = require_record_in_location(
    "user_id",
    lambda engine, user_id: get_user_detail_service(engine, user_id).primary_location_id,
    "User was not found",
)


@router.get("/", response_model=UserListResponse)
def list_users_endpoint(
    _auth: object = Depends(require_permissions("user.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    location_id: int | None = Query(default=None, ge=1),
    role_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> UserListResponse:
    filters = UserListFilters(
        location_id=pinned_location_id(auth_context, location_id),
        role_id=role_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return list_users_service(engine, filters)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user_endpoint(
    payload: UserCreate,
    _auth: object = Depends(require_permissions("user.create")),
    engine: Engine = Depends(get_engine),
) -> UserResponse:
    return create_user_service(engine, payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_detail_endpoint(
    _auth: object = Depends(require_permissions("user.read")),
    _in_scope: object = Depends(_scope_user),
    user_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> UserResponse:
    return get_user_detail_service(engine, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    payload: UserUpdate,
    _auth: object = Depends(require_permissions("user.update")),
    _in_scope: object = Depends(_scope_user),
    user_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> UserResponse:
    return update_user_service(engine, user_id, payload)


@router.post("/{user_id}/credentials/reset", response_model=UserResetCredentialsResponse)
def reset_user_credentials_endpoint(
    payload: UserResetCredentials,
    _auth: object = Depends(require_permissions("user.credentials.manage")),
    _in_scope: object = Depends(_scope_user),
    user_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> UserResetCredentialsResponse:
    return reset_user_credentials_service(engine, user_id, payload)


@router.post("/{user_id}/deactivate", response_model=UserDeactivationResponse)
def deactivate_user_endpoint(
    payload: UserDeactivateRequest,
    _auth: object = Depends(require_permissions("user.update")),
    _in_scope: object = Depends(_scope_user),
    auth_context: AuthContext = Depends(get_current_auth_context),
    user_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> UserDeactivationResponse:
    return deactivate_user_service(engine, user_id, payload, auth_context)


@router.post("/{user_id}/move", response_model=UserMoveResponse)
def move_user_endpoint(
    payload: UserMoveRequest,
    _auth: object = Depends(require_permissions("user.update")),
    _in_scope: object = Depends(_scope_user),
    auth_context: AuthContext = Depends(get_current_auth_context),
    user_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> UserMoveResponse:
    return move_user_service(engine, user_id, payload, auth_context)
