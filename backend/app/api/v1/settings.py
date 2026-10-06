"""Company settings API — letterhead source of truth for reports."""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import Engine

from app.api.deps import caller_tenant_id, get_engine, require_permissions
from app.schemas.settings import (
    CompanyLogoResponse,
    CompanyLogoUpdate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)
from app.services.settings import (
    clear_company_logo_service,
    get_company_logo_for_primary,
    get_company_profile_service,
    update_company_logo_service,
    update_company_profile_service,
)

router = APIRouter()


@router.get("/profile", response_model=CompanyProfileResponse)
def get_company_profile_endpoint(
    auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> CompanyProfileResponse:
    return get_company_profile_service(engine, caller_tenant_id(auth))


@router.patch("/profile", response_model=CompanyProfileResponse)
def update_company_profile_endpoint(
    payload: CompanyProfileUpdate,
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> CompanyProfileResponse:
    return update_company_profile_service(engine, payload, caller_tenant_id(auth))


@router.put("/logo", response_model=CompanyLogoResponse)
def update_company_logo_endpoint(
    payload: CompanyLogoUpdate,
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> CompanyLogoResponse:
    return update_company_logo_service(engine, payload, caller_tenant_id(auth))


@router.delete("/logo", response_model=CompanyLogoResponse)
def clear_company_logo_endpoint(
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> CompanyLogoResponse:
    return clear_company_logo_service(engine, caller_tenant_id(auth))


@router.get("/logo")
def get_company_logo_endpoint(
    v: int | None = Query(default=None, ge=1, description="company profile id (from logo_url)"),
    engine: Engine = Depends(get_engine),
) -> Response:
    """Public binary logo endpoint — the logo itself is not sensitive and this
    keeps <img src> simple for report letterheads. ``v`` is the company
    profile id carried in the profile's logo_url."""
    image_bytes, media_type = get_company_logo_for_primary(engine, v)
    return Response(content=image_bytes, media_type=media_type)
