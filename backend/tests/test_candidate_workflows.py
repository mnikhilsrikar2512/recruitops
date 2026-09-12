from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from tests.stubs import make_user_record
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDocumentCreate,
    CandidateDuplicateDecisionPayload,
    CandidateFinalizePayload,
)
from app.services.auth import AuthContext
from app.services.candidates import (
    create_candidate_document_service,
    create_candidate_duplicate_decision_service,
    create_candidate_service,
    finalize_candidate_service,
)


def _auth_context(user_id: int, location_id: int, role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _candidate_payload() -> CandidateCreate:
    return CandidateCreate(
        full_name="Asha Verma",
        email="asha@example.com",
        phone="9999999999",
        source_type="linkedin",
        source_detail="direct search",
        current_company="Acme",
        current_designation="Engineer",
        primary_owner_user_id=22,
        sourced_by_user_id=21,
        created_by_user_id=20,
    )


def _candidate_response(duplicate_state: str = "cleared") -> SimpleNamespace:
    return SimpleNamespace(
        id=11,
        candidate_code="C-11",
        full_name="Asha Verma",
        email="asha@example.com",
        phone="9999999999",
        current_company="Acme",
        current_designation="Engineer",
        source_type="linkedin",
        source_detail="direct search",
        total_experience_years=5.0,
        notice_period_days=30,
        social_profiles=[],
        sourced_by_user_id=21,
        sourced_by_name="Source Owner",
        primary_owner_user_id=22,
        primary_owner_name="Primary Owner",
        created_by_user_id=20,
        duplicate_state=duplicate_state,
        profile_status="active",
        intake_stage="ready-to-save",
        resume_file_name="resume.pdf",
        resume_file_path="/files/resume.pdf",
        resume_uploaded_at="2026-08-19T00:00:00Z",
        finalized_at=None,
        applications=[],
        created_at="2026-08-19T00:00:00Z",
        updated_at="2026-08-19T00:00:00Z",
    )


def test_create_candidate_validates_user_references(monkeypatch) -> None:
    seen = []

    def _assert_user_exists(engine, user_id, label):
        seen.append((user_id, label))

    created = SimpleNamespace(id=11)
    monkeypatch.setattr("app.services.candidates._assert_user_exists", _assert_user_exists)
    monkeypatch.setattr("app.services.candidates.create_candidate", lambda *args, **kwargs: created)
    monkeypatch.setattr(
        "app.services.candidates.get_candidate_detail_service",
        lambda *args, **kwargs: _candidate_response(),
    )

    response = create_candidate_service(object(), _candidate_payload())

    assert response.id == 11
    assert seen == [
        (22, "Primary owner user"),
        (21, "Sourced by user"),
        (20, "Created by user"),
    ]


def test_create_candidate_document_requires_uploaded_by_user_id(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.candidates.get_candidate_detail_service",
        lambda *args, **kwargs: _candidate_response(),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_candidate_document_service(
            object(),
            11,
            CandidateDocumentCreate(file_name="resume.pdf", file_path="/files/resume.pdf"),
            _auth_context(1, 4),
        )

    assert exc_info.value.status_code == 400
    assert "uploaded_by_user_id is required" == exc_info.value.detail


def test_duplicate_decision_creates_audit(monkeypatch) -> None:
    candidate = _candidate_response(duplicate_state="in-review")
    created_case = SimpleNamespace(
        id=500,
        candidate_id=11,
        matched_candidate_id=12,
        decision_status="override-requested",
        decision_notes="possible duplicate",
        requested_by_user_id=21,
        assigned_reviewer_user_id=30,
        created_at="2026-08-19T00:00:00Z",
        updated_at="2026-08-19T00:00:00Z",
    )
    captured = {}

    monkeypatch.setattr("app.services.candidates.find_candidate_by_id", lambda *args, **kwargs: candidate)
    monkeypatch.setattr("app.services.candidates.get_candidate_detail_service", lambda *args, **kwargs: candidate)
    monkeypatch.setattr("app.services.candidates._assert_user_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.services.candidates.create_duplicate_review_case",
        lambda *args, **kwargs: created_case,
    )
    monkeypatch.setattr("app.services.candidates.update_candidate_duplicate_state", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.candidates.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    response = create_candidate_duplicate_decision_service(
        object(),
        11,
        CandidateDuplicateDecisionPayload(
            decision="request_override",
            matched_candidate_id=12,
            decision_notes="possible duplicate",
            requested_by_user_id=21,
            assigned_reviewer_user_id=30,
        ),
        _auth_context(21, 4),
    )

    assert response.id == 500
    assert captured["action_type"] == "duplicate_decision_created"
    assert captured["new_values"]["decision"] == "request_override"


def test_finalize_candidate_requires_duplicate_clearance(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.candidates.get_candidate_detail_service",
        lambda *args, **kwargs: _candidate_response(duplicate_state="not-started"),
    )

    with pytest.raises(HTTPException) as exc_info:
        finalize_candidate_service(
            object(),
            11,
            CandidateFinalizePayload(
                requisition_id=55,
                initial_stage="submitted",
                owner_user_id=22,
                submitted_by_user_id=21,
                finalized_by_user_id=20,
            ),
            _auth_context(20, 4),
        )

    assert exc_info.value.status_code == 409
    assert "duplicate check must be cleared" in exc_info.value.detail


def test_finalize_candidate_blocks_duplicate_requisition_link(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.candidates.get_candidate_detail_service",
        lambda *args, **kwargs: _candidate_response(duplicate_state="cleared"),
    )
    monkeypatch.setattr(
        "app.services.candidates.find_requisition_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=55, location_id=4),
    )
    monkeypatch.setattr(
        "app.services.candidates.count_candidate_applications_for_requisition",
        lambda *args, **kwargs: 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        finalize_candidate_service(
            object(),
            11,
            CandidateFinalizePayload(
                requisition_id=55,
                initial_stage="submitted",
                owner_user_id=22,
                submitted_by_user_id=21,
                finalized_by_user_id=20,
            ),
            _auth_context(20, 4),
        )

    assert exc_info.value.status_code == 409
    assert "already linked" in exc_info.value.detail


def test_finalize_candidate_succeeds_with_valid_context(monkeypatch) -> None:
    finalized = SimpleNamespace(
        candidate_id=11,
        requisition_id=55,
        application_id=900,
        current_stage="submitted",
        application_status="active",
        finalized_at="2026-08-19T00:00:00Z",
    )
    monkeypatch.setattr(
        "app.services.candidates.get_candidate_detail_service",
        lambda *args, **kwargs: _candidate_response(duplicate_state="cleared"),
    )
    monkeypatch.setattr(
        "app.services.candidates.find_requisition_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=55, location_id=4),
    )
    monkeypatch.setattr(
        "app.services.candidates.count_candidate_applications_for_requisition",
        lambda *args, **kwargs: 0,
    )
    monkeypatch.setattr(
        "app.services.candidates.find_user_by_id",
        lambda *args, **kwargs: make_user_record(user_id=22, primary_location_id=4),
    )
    monkeypatch.setattr("app.services.candidates._assert_user_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.services.candidates.finalize_candidate_into_requisition",
        lambda *args, **kwargs: finalized,
    )

    response = finalize_candidate_service(
        object(),
        11,
        CandidateFinalizePayload(
            requisition_id=55,
            initial_stage="submitted",
            owner_user_id=22,
            submitted_by_user_id=21,
            finalized_by_user_id=20,
        ),
        _auth_context(20, 4),
    )

    assert response.application_id == 900
    assert response.application_status == "active"
