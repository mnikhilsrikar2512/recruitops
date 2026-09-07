from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine
from app.schemas.permission import ResolvedPermissionsResponse
from app.services.auth import AuthContext, get_resolved_permissions_service

router = APIRouter()


@router.get("/me", response_model=ResolvedPermissionsResponse)
def permissions_me_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ResolvedPermissionsResponse:
    return get_resolved_permissions_service(engine, auth_context)
