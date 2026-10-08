from fastapi import HTTPException, status
from sqlalchemy import Engine

from decimal import Decimal

from app.repositories.offer_settings import OfferPolicy, get_offer_approval_threshold, get_offer_policy
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


def _assert_offer_can_change(application, action: str) -> None:
    """4.11: no offer work for a candidate who withdrew or was rejected;
    4.12: none while the requisition is on hold (declining stays allowed)."""
    closed = getattr(application, "application_status", None)
    if closed in ("withdrawn", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The candidate's application is {closed}; reopen it before you {action}",
        )
    if getattr(application, "offer_status", None) == "withdrawn" and action != "create an offer":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This offer was withdrawn; create a new offer instead")
    if getattr(application, "requisition_status", None) == "on-hold":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The requisition is on hold; resume it before you {action}",
        )


def offer_total_for_budget(policy: OfferPolicy, payload: OfferCreate) -> Decimal:
    """CTC, plus the signing bonus only where it counts against the budget (4.13)."""
    total = Decimal(payload.offered_ctc or 0)
    if policy.signing_bonus_allowed and policy.bonus_counts_against_budget:
        total += Decimal(payload.signing_bonus or 0)
    return total


def approval_needed(policy: OfferPolicy, payload: OfferCreate) -> bool:
    """Phase 4.8 (D-06, revised) + 4.13 (D-4.13): which offers need approval.

    The amount compared is CTC, plus the signing bonus when the company (or,
    for client hiring, the client) counts the bonus against the budget.
    1. No amount yet -> approval (nothing to compare).
    2. The requisition has a max budget -> the budget decides: at or under
       it the offer is approved now, over it needs approval. An offer in a
       different currency from the budget needs approval (it can't be
       compared safely).
    3. No budget on the requisition -> the company threshold decides
       (default 0 = every paid offer needs approval).
    """
    if payload.offered_ctc is None:
        return True
    total = offer_total_for_budget(policy, payload)
    if policy.budget_max is not None and policy.budget_max > 0:
        if policy.currency_code and payload.offer_currency and policy.currency_code.strip().upper() != payload.offer_currency.upper():
            return True
        return total > policy.budget_max
    return total > policy.threshold


def _policy_for(engine: Engine, location_id: int, payload: OfferCreate) -> OfferPolicy:
    policy = get_offer_policy(engine, payload.candidate_application_id)
    if policy is None:
        policy = OfferPolicy(threshold=get_offer_approval_threshold(engine, scope.tenant_of_office(engine, location_id)))
    return policy


def offer_requires_approval(engine: Engine, location_id: int, payload: OfferCreate) -> bool:
    return approval_needed(_policy_for(engine, location_id, payload), payload)


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
    _assert_offer_can_change(application, "create an offer")
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
    policy = _policy_for(engine, application.location_id, payload) if isinstance(engine, Engine) else OfferPolicy()
    if not policy.signing_bonus_allowed and payload.signing_bonus:
        who = "This client" if policy.source == "client" else "Your company"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{who} does not pay signing bonuses; remove the bonus or turn it on in settings",
        )
    if not policy.signing_bonus_allowed:
        payload = payload.model_copy(update={"signing_bonus": None})
    created = create_offer(
        engine,
        payload,
        location_id=application.location_id,
        actor_user_id=actor_user_id,
        requires_approval=offer_requires_approval(engine, application.location_id, payload),
    )
    return OfferResponse.model_validate(created)


def update_offer_decision_service(
    engine: Engine,
    application_id: int,
    payload: OfferDecisionUpdate,
    auth_context: AuthContext | None = None,
) -> OfferResponse:
    get_offer_detail_service(engine, application_id, auth_context)
    if payload.status not in ("declined", "cancelled"):
        application = find_pipeline_application_by_id(engine, application_id)
        if application is not None:
            _assert_offer_can_change(application, "move this offer forward")
    actor_user_id = auth_context.user.id if auth_context else 0
    updated = update_offer_decision(engine, application_id, payload, actor_user_id=actor_user_id)
    return OfferResponse.model_validate(updated)


def get_offer_policy_service(engine: Engine, application_id: int, auth_context: AuthContext | None = None) -> dict:
    """What the offer form needs before it is filled in (4.13)."""
    application = find_pipeline_application_by_id(engine, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if auth_context:
        _assert_pipeline_application_access(application, auth_context, engine)
    policy = get_offer_policy(engine, application_id) or OfferPolicy()
    return {
        "application_id": application_id,
        "signing_bonus_allowed": policy.signing_bonus_allowed,
        "bonus_counts_against_budget": policy.bonus_counts_against_budget,
        "source": policy.source,
        "client_company_id": policy.client_company_id,
        "budget_max": float(policy.budget_max) if policy.budget_max is not None else None,
        "currency_code": policy.currency_code,
    }
