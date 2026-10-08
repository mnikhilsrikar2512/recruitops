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
from decimal import Decimal

from fastapi import HTTPException

from app.repositories.audit import insert_audit_log
from app.repositories.offer_settings import (
    get_company_bonus_switches,
    get_offer_approval_threshold,
    set_company_bonus_switches,
    set_offer_approval_threshold,
)
from app.schemas.settings import OfferApprovalSettings
from app.schemas.stage_lists import StageListOverview, StageListResponse, StageListUpdate
from app.services.stage_lists import get_client_list_service, get_overview_service, save_list_service
from app.schemas.stage_buckets import StageBucketMapResponse, StageBucketResponse, StageBucketUpdate
from app.services.stage_buckets import (
    get_stage_bucket_map_service,
    reset_stage_bucket_service,
    set_stage_bucket_service,
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


# ---- Stage Bucket Map (Phase 4.5) -------------------------------------
@router.get("/stage-buckets", response_model=StageBucketMapResponse)
def get_stage_bucket_map_endpoint(
    auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> StageBucketMapResponse:
    """How every stage label this company uses is counted in reports."""
    return get_stage_bucket_map_service(engine, auth)


@router.put("/stage-buckets/{stage}", response_model=StageBucketResponse)
def set_stage_bucket_endpoint(
    stage: str,
    payload: StageBucketUpdate,
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> StageBucketResponse:
    return set_stage_bucket_service(engine, stage, payload, auth)


@router.delete("/stage-buckets/{stage}", response_model=StageBucketResponse)
def reset_stage_bucket_endpoint(
    stage: str,
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> StageBucketResponse:
    """Drop the company's own mapping; the platform default applies again."""
    return reset_stage_bucket_service(engine, stage, auth)


# ---- Offer approval threshold (Phase 4.8, D-06) ------------------------
@router.get("/offer-approval", response_model=OfferApprovalSettings)
def get_offer_approval_endpoint(
    auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> OfferApprovalSettings:
    return _offer_settings(engine, caller_tenant_id(auth))


def _offer_settings(engine: Engine, tenant_id: int | None) -> OfferApprovalSettings:
    offers_bonus, counts = get_company_bonus_switches(engine, tenant_id)
    return OfferApprovalSettings(
        threshold=float(get_offer_approval_threshold(engine, tenant_id)),
        offers_signing_bonus=offers_bonus,
        bonus_counts_against_budget=counts,
    )


@router.put("/offer-approval", response_model=OfferApprovalSettings)
def set_offer_approval_endpoint(
    payload: OfferApprovalSettings,
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> OfferApprovalSettings:
    tenant_id = caller_tenant_id(auth)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="The offer threshold belongs to a company; sign in as a company user")
    before = _offer_settings(engine, tenant_id)
    set_offer_approval_threshold(engine, tenant_id, Decimal(str(payload.threshold)))
    set_company_bonus_switches(
        engine,
        tenant_id,
        before.offers_signing_bonus if payload.offers_signing_bonus is None else payload.offers_signing_bonus,
        before.bonus_counts_against_budget if payload.bonus_counts_against_budget is None else payload.bonus_counts_against_budget,
    )
    after = _offer_settings(engine, tenant_id)
    insert_audit_log(
        engine,
        actor_user_id=auth.user.id,
        location_id=auth.user.location_id,
        entity_type="tenant",
        entity_id=int(tenant_id),
        action_type="settings.offer_threshold.set",
        old_values=before.model_dump(),
        new_values=after.model_dump(),
    )
    return after


# ---- Stage lists (Phase 4.10, D-4.10): company default + one per client --
@router.get("/stage-lists", response_model=StageListOverview)
def get_stage_lists_endpoint(
    auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> StageListOverview:
    return get_overview_service(engine, auth)


@router.get("/stage-lists/company", response_model=StageListResponse)
def get_company_stage_list_endpoint(
    auth: object = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> StageListResponse:
    return get_overview_service(engine, auth).company


@router.put("/stage-lists/company", response_model=StageListResponse)
def save_company_stage_list_endpoint(
    payload: StageListUpdate,
    auth: object = Depends(require_permissions("settings.update")),
    engine: Engine = Depends(get_engine),
) -> StageListResponse:
    """Used for internal hiring and for clients without their own list."""
    return save_list_service(engine, auth, payload, None)


@router.get("/stage-lists/clients/{client_id}", response_model=StageListResponse)
def get_client_stage_list_endpoint(
    client_id: int,
    auth: object = Depends(require_permissions("client.read")),
    engine: Engine = Depends(get_engine),
) -> StageListResponse:
    return get_client_list_service(engine, auth, client_id)


@router.put("/stage-lists/clients/{client_id}", response_model=StageListResponse)
def save_client_stage_list_endpoint(
    client_id: int,
    payload: StageListUpdate,
    auth: object = Depends(require_permissions("client.update")),
    engine: Engine = Depends(get_engine),
) -> StageListResponse:
    """Every requisition for this client uses this list."""
    return save_list_service(engine, auth, payload, client_id)
