"""Company settings API — letterhead source of truth for reports."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import Engine

from app.api.deps import get_engine, require_permissions
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
    _auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> CompanyProfileResponse:
    return get_company_profile_service(engine)


@router.patch("/profile", response_model=CompanyProfileResponse)
def update_company_profile_endpoint(
    payload: CompanyProfileUpdate,
    _auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> CompanyProfileResponse:
    return update_company_profile_service(engine, payload)


@router.put("/logo", response_model=CompanyLogoResponse)
def update_company_logo_endpoint(
    payload: CompanyLogoUpdate,
    _auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> CompanyLogoResponse:
    return update_company_logo_service(engine, payload)


@router.delete("/logo", response_model=CompanyLogoResponse)
def clear_company_logo_endpoint(
    _auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> CompanyLogoResponse:
    return clear_company_logo_service(engine)


@router.get("/logo")
def get_company_logo_endpoint(
    engine: Engine = Depends(get_engine),
) -> Response:
    """Public binary logo endpoint — the logo itself is not sensitive and this
    keeps <img src> simple for report letterheads."""
    image_bytes, media_type = get_company_logo_for_primary(engine)
    return Response(content=image_bytes, media_type=media_type)
