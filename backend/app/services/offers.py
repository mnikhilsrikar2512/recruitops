from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.offers import create_offer, find_offer_by_application_id, list_offers, update_offer_decision
from app.repositories.pipeline import find_pipeline_application_by_id
from app.repositories.users import find_user_by_id
from app.repositories.display_ids import find_branch_by_id
from app.schemas.offer import OfferCreate, OfferDecisionUpdate, OfferListFilters, OfferListResponse, OfferResponse
from app.schemas.pagination import PaginationMeta
from app.services import scope
from app.services.auth import AuthContext
from app.services.pipeline import _assert_pipeline_application_access


def list_offers_service(
    engine: Engine,
    filters: OfferListFilters,
    auth_context: AuthContext | None = None,
) -> OfferListResponse:
    if auth_context and not scope.is_company_wide(auth_context) and filters.location_id is None:
        filters = filters.model_copy(update={"location_id": auth_context.user.location_id})
    items, total = list_offers(engine, filters)
    return OfferListResponse(
        items=[OfferResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_offer_detail_service(
    engine: Engine,
    application_id: int,
    auth_context: AuthContext | None = None,
) -> OfferResponse:
    offer = find_offer_by_application_id(engine, application_id)
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer was not found")
    application = find_pipeline_application_by_id(engine, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if auth_context:
        _assert_pipeline_application_access(application, auth_context, engine)
    return OfferResponse.model_validate(offer)


def create_offer_service(
    engine: Engine,
    payload: OfferCreate,
    auth_context: AuthContext | None = None,
) -> OfferResponse:
    application = find_pipeline_application_by_id(engine, payload.candidate_application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if auth_context:
        _assert_pipeline_application_access(application, auth_context, engine)
    branch = find_branch_by_id(engine, application.location_id)
    if branch is not None and branch.offers_enabled is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer tracking is disabled for this branch; offers are handed off to the client outside the system",
        )
    if payload.assigned_to_user_id and not find_user_by_id(engine, payload.assigned_to_user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned approver was not found")
    actor_user_id = payload.requested_by_user_id
    if actor_user_id is None and auth_context:
        actor_user_id = auth_context.user.id
    if actor_user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Requested by user is required")
    created = create_offer(engine, payload, location_id=application.location_id, actor_user_id=actor_user_id)
    return OfferResponse.model_validate(created)


def update_offer_decision_service(
    engine: Engine,
    application_id: int,
    payload: OfferDecisionUpdate,
    auth_context: AuthContext | None = None,
) -> OfferResponse:
    get_offer_detail_service(engine, application_id, auth_context)
    actor_user_id = auth_context.user.id if auth_context else 0
    updated = update_offer_decision(engine, application_id, payload, actor_user_id=actor_user_id)
    return OfferResponse.model_validate(updated)
