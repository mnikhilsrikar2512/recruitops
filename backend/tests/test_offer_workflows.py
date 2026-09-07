from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.offer import OfferCreate, OfferDecisionUpdate, OfferListFilters
from app.services.offers import create_offer_service, get_offer_detail_service, list_offers_service, update_offer_decision_service


def _application(**overrides):
    values = {
        "application_id": 501,
        "candidate_id": 401,
        "candidate_name": "Maya Patel",
        "requisition_id": 301,
        "requisition_title": "Platform Reliability Lead",
        "location_id": 1,
        "location_name": "HQ",
        "owner_user_id": 7,
        "owner_name": "API Tester",
        "sourced_by_user_id": 7,
        "sourced_by_name": "API Tester",
        "submitted_by_user_id": 7,
        "submitted_by_name": "API Tester",
        "current_stage": "offer",
        "application_status": "active",
        "screening_status": "passed",
        "stage_reason": None,
        "rejection_side": "none",
        "rejection_stage": None,
        "rejection_reason": None,
        "client_feedback_status": None,
        "client_feedback_notes": None,
        "stage_updated_at": datetime(2026, 8, 28, 9, 0),
        "last_activity_at": datetime(2026, 8, 28, 9, 30),
        "expected_joining_date": None,
        "applied_at": datetime(2026, 8, 27, 9, 0),
        "updated_at": datetime(2026, 8, 28, 9, 30),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _offer(**overrides):
    values = {
        "application_id": 501,
        "candidate_id": 401,
        "candidate_name": "Maya Patel",
        "candidate_email": "maya.patel@example.com",
        "requisition_id": 301,
        "requisition_title": "Platform Reliability Lead",
        "location_id": 1,
        "location_name": "HQ",
        "owner_user_id": 7,
        "owner_name": "API Tester",
        "current_stage": "offer",
        "application_status": "active",
        "offer_status": "pending-approval",
        "offered_ctc": Decimal("145000"),
        "offer_currency": "USD",
        "signing_bonus": Decimal("10000"),
        "expected_joining_date": date(2026, 9, 15),
        "offer_notes": "Offer ready for approval.",
        "approval_request_id": 3011,
        "approval_status": "pending",
        "requested_by_user_id": 7,
        "assigned_to_user_id": 601,
        "offer_created_at": datetime(2026, 8, 30, 9, 0),
        "offer_sent_at": None,
        "updated_at": datetime(2026, 8, 30, 9, 0),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_list_offers_applies_non_admin_location(monkeypatch) -> None:
    captured = {}

    def fake_list(_engine, filters):
        captured["location_id"] = filters.location_id
        return [_offer()], 1

    auth = SimpleNamespace(user=SimpleNamespace(role_code="recruiter", location_id=4, id=7))
    monkeypatch.setattr("app.services.offers.list_offers", fake_list)

    response = list_offers_service(object(), OfferListFilters(), auth)

    assert captured["location_id"] == 4
    assert response.meta.total == 1


def test_get_offer_detail_raises_for_missing_offer(monkeypatch) -> None:
    monkeypatch.setattr("app.services.offers.find_offer_by_application_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        get_offer_detail_service(object(), 501)

    assert exc.value.status_code == 404


def test_create_offer_rejects_missing_application(monkeypatch) -> None:
    monkeypatch.setattr("app.services.offers.find_pipeline_application_by_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        create_offer_service(object(), OfferCreate(candidate_application_id=501, requested_by_user_id=7))

    assert exc.value.status_code == 404


def test_create_offer_succeeds_and_routes_approval(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr("app.services.offers.find_pipeline_application_by_id", lambda *args, **kwargs: _application())
    monkeypatch.setattr("app.services.offers.find_user_by_id", lambda *args, **kwargs: SimpleNamespace(id=601))

    def fake_create(_engine, payload, *, location_id, actor_user_id):
        captured["location_id"] = location_id
        captured["actor_user_id"] = actor_user_id
        captured["assigned_to_user_id"] = payload.assigned_to_user_id
        return _offer()

    monkeypatch.setattr("app.services.offers.create_offer", fake_create)

    response = create_offer_service(
        object(),
        OfferCreate(candidate_application_id=501, offered_ctc=Decimal("145000"), assigned_to_user_id=601, requested_by_user_id=7),
    )

    assert response.offer_status == "pending-approval"
    assert captured == {"location_id": 1, "actor_user_id": 7, "assigned_to_user_id": 601}


def test_update_offer_decision_accepts_and_sets_joining(monkeypatch) -> None:
    monkeypatch.setattr("app.services.offers.find_offer_by_application_id", lambda *args, **kwargs: _offer())
    monkeypatch.setattr("app.services.offers.find_pipeline_application_by_id", lambda *args, **kwargs: _application())
    monkeypatch.setattr(
        "app.services.offers.update_offer_decision",
        lambda *args, **kwargs: _offer(offer_status="accepted", application_status="joined", expected_joining_date=date(2026, 9, 15)),
    )

    auth = SimpleNamespace(user=SimpleNamespace(role_code="admin", location_id=1, id=7))
    response = update_offer_decision_service(
        object(),
        501,
        OfferDecisionUpdate(status="accepted", expected_joining_date=date(2026, 9, 15)),
        auth,
    )

    assert response.offer_status == "accepted"
    assert response.application_status == "joined"
    assert response.expected_joining_date == date(2026, 9, 15)
