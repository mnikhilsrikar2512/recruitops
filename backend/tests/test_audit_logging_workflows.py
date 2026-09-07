from types import SimpleNamespace

from app.schemas.candidate import CandidateDuplicateDecisionPayload, CandidateOwnerReassignment
from app.schemas.requisition import RequisitionOwnerReassignment, RequisitionStatusUpdate
from app.services.auth import AuthContext
from app.services.candidates import (
    create_candidate_duplicate_decision_service,
    reassign_candidate_owner_service,
)
from app.services.requisitions import (
    reassign_requisition_owners_service,
    update_requisition_status_service,
)


def _auth_context(user_id: int, location_id: int | None, role_code: str = "admin") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def test_candidate_duplicate_decision_writes_audit_log(monkeypatch) -> None:
    candidate = SimpleNamespace(id=10, duplicate_state="in-review")
    created_case = SimpleNamespace(decision_status="approved")
    captured = {}
    monkeypatch.setattr(
        "app.services.candidates.get_candidate_detail_service",
        lambda *args, **kwargs: SimpleNamespace(duplicate_state="in-review"),
    )
    monkeypatch.setattr("app.services.candidates.find_candidate_by_id", lambda *args, **kwargs: candidate)
    monkeypatch.setattr("app.services.candidates._assert_user_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.update_candidate_duplicate_state", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.create_duplicate_review_case", lambda *args, **kwargs: created_case)
    monkeypatch.setattr(
        "app.services.candidates.CandidateDuplicateReviewCaseResponse.model_validate",
        lambda case: case,
    )
    monkeypatch.setattr("app.services.candidates.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    response = create_candidate_duplicate_decision_service(
        object(),
        10,
        CandidateDuplicateDecisionPayload(
            decision="link_existing",
            matched_candidate_id=44,
            requested_by_user_id=7,
        ),
        _auth_context(7, 3),
    )

    assert response is created_case
    assert captured["entity_type"] == "candidate"
    assert captured["action_type"] == "duplicate_decision_created"
    assert captured["old_values"] == {"duplicate_state": "in-review"}


def test_candidate_owner_reassignment_writes_audit_log(monkeypatch) -> None:
    candidate = SimpleNamespace(primary_owner_user_id=12)
    captured = {}
    monkeypatch.setattr("app.services.candidates.get_candidate_detail_service", lambda *args, **kwargs: candidate)
    monkeypatch.setattr("app.services.candidates._assert_user_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.count_active_candidate_applications", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.candidates.update_candidate", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    reassign_candidate_owner_service(
        object(),
        10,
        CandidateOwnerReassignment(new_primary_owner_user_id=15, reason="handover"),
        _auth_context(9, 4),
    )

    assert captured["action_type"] == "primary_owner_reassigned"
    assert captured["old_values"] == {"primary_owner_user_id": 12}
    assert captured["new_values"]["primary_owner_user_id"] == 15


def test_requisition_status_update_writes_audit_log(monkeypatch) -> None:
    existing = SimpleNamespace(status="open")
    updated = SimpleNamespace()
    captured = {}
    monkeypatch.setattr("app.services.requisitions.find_requisition_by_id", lambda *args, **kwargs: existing)
    monkeypatch.setattr("app.services.requisitions.update_requisition_status", lambda *args, **kwargs: updated)
    monkeypatch.setattr("app.services.requisitions.RequisitionResponse.model_validate", lambda value: value)
    monkeypatch.setattr("app.services.requisitions.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    response = update_requisition_status_service(
        object(),
        55,
        RequisitionStatusUpdate(status="closed", reason="filled"),
        _auth_context(20, 8),
    )

    assert response is updated
    assert captured["action_type"] == "status_updated"
    assert captured["old_values"] == {"status": "open"}
    assert captured["new_values"] == {"status": "closed", "reason": "filled"}


def test_requisition_owner_reassignment_writes_audit_log(monkeypatch) -> None:
    existing = SimpleNamespace(
        id=55,
        location_id=4,
        primary_owner_user_id=20,
        delivery_owner_user_id=21,
    )
    captured = {}
    monkeypatch.setattr("app.services.requisitions.find_requisition_by_id", lambda *args, **kwargs: existing)
    monkeypatch.setattr("app.services.requisitions._assert_user_in_location", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.requisitions.count_active_requisition_assignments", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.requisitions.count_active_requisition_applications", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.requisitions.update_requisition", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.requisitions.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    reassign_requisition_owners_service(
        object(),
        55,
        RequisitionOwnerReassignment(
            new_primary_owner_user_id=30,
            new_delivery_owner_user_id=31,
            reason="handover",
            review_confirmed=True,
        ),
        _auth_context(8, 4),
    )

    assert captured["action_type"] == "owners_reassigned"
    assert captured["old_values"] == {
        "primary_owner_user_id": 20,
        "delivery_owner_user_id": 21,
    }
    assert captured["new_values"]["primary_owner_user_id"] == 30
