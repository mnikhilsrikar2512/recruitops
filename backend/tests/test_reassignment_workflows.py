from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.candidate import CandidateOwnerReassignment
from app.schemas.requisition import RequisitionOwnerReassignment
from app.services.auth import AuthContext
from app.services.candidates import reassign_candidate_owner_service
from app.services.requisitions import reassign_requisition_owners_service


def _auth_context(user_id: int, location_id: int, role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def test_reassign_candidate_owner_requires_review_when_active_work_exists(monkeypatch) -> None:
    candidate = SimpleNamespace(primary_owner_user_id=12)
    monkeypatch.setattr("app.services.candidates.get_candidate_detail_service", lambda *args, **kwargs: candidate)
    monkeypatch.setattr("app.services.candidates._assert_user_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.count_active_candidate_applications", lambda *args, **kwargs: 2)

    with pytest.raises(HTTPException) as exc_info:
        reassign_candidate_owner_service(
            object(),
            10,
            CandidateOwnerReassignment(new_primary_owner_user_id=15, reason="handover"),
            _auth_context(1, 1),
        )

    assert exc_info.value.status_code == 409


def test_reassign_candidate_owner_succeeds_after_review(monkeypatch) -> None:
    candidate = SimpleNamespace(primary_owner_user_id=12)
    captured = {}
    monkeypatch.setattr("app.services.candidates.get_candidate_detail_service", lambda *args, **kwargs: candidate)
    monkeypatch.setattr("app.services.candidates._assert_user_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.count_active_candidate_applications", lambda *args, **kwargs: 1)
    monkeypatch.setattr(
        "app.services.candidates.update_candidate",
        lambda engine, candidate_id, payload: captured.update({"candidate_id": candidate_id, "owner": payload.primary_owner_user_id}),
    )
    monkeypatch.setattr("app.services.candidates.insert_audit_log", lambda *args, **kwargs: None)

    response = reassign_candidate_owner_service(
        object(),
        10,
        CandidateOwnerReassignment(new_primary_owner_user_id=15, reason="handover", review_confirmed=True),
        _auth_context(1, 1),
    )

    assert captured == {"candidate_id": 10, "owner": 15}
    assert response.review_required is True


def test_reassign_requisition_owners_requires_review_when_active_work_exists(monkeypatch) -> None:
    requisition = SimpleNamespace(
        id=55,
        location_id=4,
        primary_owner_user_id=20,
        delivery_owner_user_id=21,
    )
    monkeypatch.setattr("app.services.requisitions.find_requisition_by_id", lambda *args, **kwargs: requisition)
    monkeypatch.setattr("app.services.requisitions._assert_user_in_location", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.requisitions.count_active_requisition_assignments", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.requisitions.count_active_requisition_applications", lambda *args, **kwargs: 3)

    with pytest.raises(HTTPException) as exc_info:
        reassign_requisition_owners_service(
            object(),
            55,
            RequisitionOwnerReassignment(new_primary_owner_user_id=30, reason="handover"),
        )

    assert exc_info.value.status_code == 409


def test_reassign_requisition_owners_succeeds_after_review(monkeypatch) -> None:
    requisition = SimpleNamespace(
        id=55,
        location_id=4,
        primary_owner_user_id=20,
        delivery_owner_user_id=21,
    )
    captured = {}
    monkeypatch.setattr("app.services.requisitions.find_requisition_by_id", lambda *args, **kwargs: requisition)
    monkeypatch.setattr("app.services.requisitions._assert_user_in_location", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.requisitions.count_active_requisition_assignments", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.requisitions.count_active_requisition_applications", lambda *args, **kwargs: 2)
    monkeypatch.setattr(
        "app.services.requisitions.update_requisition",
        lambda engine, requisition_id, payload: captured.update(
            {
                "requisition_id": requisition_id,
                "primary_owner_user_id": payload.primary_owner_user_id,
                "delivery_owner_user_id": payload.delivery_owner_user_id,
            }
        ),
    )

    response = reassign_requisition_owners_service(
        object(),
        55,
        RequisitionOwnerReassignment(
            new_primary_owner_user_id=30,
            new_delivery_owner_user_id=31,
            reason="handover",
            review_confirmed=True,
        ),
    )

    assert captured == {
        "requisition_id": 55,
        "primary_owner_user_id": 30,
        "delivery_owner_user_id": 31,
    }
    assert response.review_required is True
