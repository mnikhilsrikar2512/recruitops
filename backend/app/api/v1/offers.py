from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import caller_tenant_id, get_current_auth_context, get_engine, require_location_scope, require_permissions, reject_unknown_query_params
from app.schemas.offer import OfferCreate, OfferDecisionUpdate, OfferListFilters, OfferListResponse, OfferPolicyResponse, OfferResponse
from app.services.auth import AuthContext
from app.services.offers import create_offer_service, get_offer_detail_service, get_offer_policy_service, list_offers_service, update_offer_decision_service
from app.services import scope

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=OfferListResponse, dependencies=[Depends(reject_unknown_query_params)])
def list_offers_endpoint(
    _auth: object = Depends(require_permissions("offer.read")),
    _scope: object = Depends(require_location_scope("location_id")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    location_id: int | None = Query(default=None, ge=1),
    requisition_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> OfferListResponse:
    filters = OfferListFilters(location_id=location_id, requisition_id=requisition_id, status=status, page=page, page_size=page_size)
    filters.tenant_id = caller_tenant_id(auth_context)
    return list_offers_service(engine, filters, auth_context)


@router.post("/", response_model=OfferResponse, status_code=201)
def create_offer_endpoint(
    payload: OfferCreate,
    _auth: object = Depends(require_permissions("offer.create")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> OfferResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return create_offer_service(engine, payload, auth_context)


@router.get("/policy/{application_id}", response_model=OfferPolicyResponse)
def get_offer_policy_endpoint(
    _auth: object = Depends(require_permissions("offer.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    application_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> OfferPolicyResponse:
    """Phase 4.13: is a signing bonus allowed, and does it count against the budget?"""
    return OfferPolicyResponse(**get_offer_policy_service(engine, application_id, auth_context))


@router.get("/{application_id}", response_model=OfferResponse)
def get_offer_detail_endpoint(
    _auth: object = Depends(require_permissions("offer.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    application_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> OfferResponse:
    return get_offer_detail_service(engine, application_id, auth_context)


@router.patch("/{application_id}/decision", response_model=OfferResponse)
def update_offer_decision_endpoint(
    payload: OfferDecisionUpdate,
    _auth: object = Depends(require_permissions("offer.decide")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    application_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> OfferResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return update_offer_decision_service(engine, application_id, payload, auth_context)
