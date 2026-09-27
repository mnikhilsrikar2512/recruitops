from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.permission import ResolvedPermissionsResponse
from app.schemas.permission_catalog import PermissionCatalogResponse
from app.services.auth import AuthContext, get_resolved_permissions_service
from app.services.roles import list_permission_catalog_service

router = APIRouter()


@router.get("/", response_model=PermissionCatalogResponse)
def list_permission_catalog_endpoint(
    _auth: object = Depends(require_permissions("role.read")),
    engine: Engine = Depends(get_engine),
) -> PermissionCatalogResponse:
    """Full permission catalog for the role editor matrix (grouped by module client-side)."""
    return list_permission_catalog_service(engine)


@router.get("/me", response_model=ResolvedPermissionsResponse)
def permissions_me_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ResolvedPermissionsResponse:
    return get_resolved_permissions_service(engine, auth_context)
