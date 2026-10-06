"""Company settings service — profile retrieval, updates, and logo handling."""
from __future__ import annotations

from fastapi import HTTPException, Response, status
from sqlalchemy import Engine

from app.repositories import settings as settings_repo
from app.schemas.settings import (
    CompanyLogoResponse,
    CompanyLogoUpdate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)

_UPDATABLE_FIELDS = {
    "display_name",
    "legal_name",
    "company_type_code",
    "hq_city",
    "hq_state",
    "country_name",
    "support_email",
    "support_phone",
    "website_url",
    "registered_address",
}


def _require_profile(engine: Engine, tenant_id: int | None = None):
    """The caller's company profile; a company without one gets it created
    from its name on first use (migration 012)."""
    record = settings_repo.get_primary_company_profile(engine, tenant_id)
    if record is None and tenant_id is not None:
        settings_repo.create_company_profile_for_tenant(engine, tenant_id)
        record = settings_repo.get_primary_company_profile(engine, tenant_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active primary company entity is configured",
        )
    return record


def get_company_profile_service(engine: Engine, tenant_id: int | None = None) -> CompanyProfileResponse:
    return CompanyProfileResponse.model_validate(_require_profile(engine, tenant_id))


def update_company_profile_service(
    engine: Engine, payload: CompanyProfileUpdate, tenant_id: int | None = None
) -> CompanyProfileResponse:
    profile = _require_profile(engine, tenant_id)
    fields = {
        name: value
        for name, value in payload.model_dump(exclude_unset=True).items()
        if name in _UPDATABLE_FIELDS
    }
    updated = settings_repo.update_company_profile(engine, profile.id, fields)
    return CompanyProfileResponse.model_validate(updated)


def update_company_logo_service(
    engine: Engine, payload: CompanyLogoUpdate, tenant_id: int | None = None
) -> CompanyLogoResponse:
    profile = _require_profile(engine, tenant_id)
    settings_repo.set_company_logo(engine, profile.id, payload.data_url)
    return CompanyLogoResponse(logo_url=f"/api/v1/settings/logo?v={profile.id}")


def get_company_logo_raw(engine: Engine, company_id: int) -> tuple[bytes, str]:
    """Return (image_bytes, media_type) for the <img> tag; 404 when unset."""
    data_url = settings_repo.get_company_logo(engine, company_id)
    if not data_url or "," not in data_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No logo configured"
        )
    header, encoded = data_url.split(",", 1)
    media_type = header[5:].split(";", 1)[0] or "image/png"
    import base64

    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stored logo is invalid"
        ) from exc
    return image_bytes, media_type


def get_company_logo_for_primary(engine: Engine, company_id: int | None = None) -> tuple[bytes, str]:
    """Logo by profile id (``?v=`` from the profile's logo_url). Without an id
    there is no single "primary" company any more (migration 012)."""
    if company_id is not None:
        return get_company_logo_raw(engine, company_id)
    company_id = settings_repo.get_primary_company_id(engine) if settings_repo.count_primary_profiles(engine) == 1 else None
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active primary company entity is configured",
        )
    return get_company_logo_raw(engine, company_id)


def clear_company_logo_service(engine: Engine, tenant_id: int | None = None) -> CompanyLogoResponse:
    profile = _require_profile(engine, tenant_id)
    settings_repo.set_company_logo(engine, profile.id, None)
    return CompanyLogoResponse(logo_url=None)
