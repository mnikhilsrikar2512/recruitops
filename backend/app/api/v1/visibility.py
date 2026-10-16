"""Visibility Rules admin page — which roles can see which commercial
fields, company-wide. See scripts/031_visibility_rules.sql."""
from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.visibility import VisibilityRulesBulkUpdate, VisibilityRulesResponse
from app.services.auth import AuthContext
from app.services.visibility import get_visibility_rules_service, update_visibility_rules_service

router = APIRouter()


@router.get("/", response_model=VisibilityRulesResponse)
def get_visibility_rules_endpoint(
    auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> VisibilityRulesResponse:
    return get_visibility_rules_service(engine)


@router.put("/", response_model=VisibilityRulesResponse)
def update_visibility_rules_endpoint(
    payload: VisibilityRulesBulkUpdate,
    auth: object = Depends(require_permissions("visibility_rules.write")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> VisibilityRulesResponse:
    return update_visibility_rules_service(engine, payload, auth_context.user.id)
