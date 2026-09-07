from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.repositories.candidates import CandidateApplicationSummaryRecord
from app.schemas.candidate import CandidateListFilters
from app.services.auth import AuthContext
from app.services.candidates import get_candidate_detail_service, list_candidates_service


def _auth_context(user_id: int, location_id: int, role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _candidate_record() -> SimpleNamespace:
    return SimpleNamespace(
        id=11,
        candidate_code="C-11",
        full_name="Asha Verma",
        email="asha@example.com",
        phone="9999999999",
        current_company="Acme",
        current_designation="Engineer",
        source_type="linkedin",
        source_detail=None,
        total_experience_years=5.0,
        notice_period_days=30,
        sourced_by_user_id=41,
        sourced_by_name="Source Owner",
        primary_owner_user_id=42,
        primary_owner_name="Primary Owner",
        created_by_user_id=43,
        duplicate_state="cleared",
        profile_status="active",
        intake_stage="ready-to-save",
        resume_file_name=None,
        resume_file_path=None,
        resume_uploaded_at=None,
        finalized_at=None,
        created_at="2026-08-19T00:00:00Z",
        updated_at="2026-08-19T00:00:00Z",
    )


def test_candidate_detail_allows_same_location_linked_application(monkeypatch) -> None:
    monkeypatch.setattr("app.services.candidates.find_candidate_by_id", lambda engine, candidate_id: _candidate_record())
    monkeypatch.setattr(
        "app.services.candidates.list_candidate_applications",
        lambda engine, candidate_id: [
            CandidateApplicationSummaryRecord(
                id=101,
                requisition_id=55,
                requisition_title="Java Developer",
                location_id=7,
                owner_user_id=99,
                owner_name="Other Owner",
                submitted_by_user_id=98,
                current_stage="submitted",
                application_status="active",
                stage_updated_at="2026-08-19T00:00:00Z",
                expected_joining_date=None,
            )
        ],
    )
    monkeypatch.setattr("app.services.candidates.social_profiles_for_candidate", lambda candidate: [])

    response = get_candidate_detail_service(object(), 11, _auth_context(user_id=5, location_id=7))

    assert response.id == 11


def test_candidate_detail_blocks_unrelated_user(monkeypatch) -> None:
    monkeypatch.setattr("app.services.candidates.find_candidate_by_id", lambda engine, candidate_id: _candidate_record())
    monkeypatch.setattr(
        "app.services.candidates.list_candidate_applications",
        lambda engine, candidate_id: [
            CandidateApplicationSummaryRecord(
                id=101,
                requisition_id=55,
                requisition_title="Java Developer",
                location_id=8,
                owner_user_id=99,
                owner_name="Other Owner",
                submitted_by_user_id=98,
                current_stage="submitted",
                application_status="active",
                stage_updated_at="2026-08-19T00:00:00Z",
                expected_joining_date=None,
            )
        ],
    )
    monkeypatch.setattr("app.services.candidates.social_profiles_for_candidate", lambda candidate: [])

    with pytest.raises(HTTPException) as exc_info:
        get_candidate_detail_service(object(), 11, _auth_context(user_id=5, location_id=7))

    assert exc_info.value.status_code == 403


def test_list_candidates_defaults_owner_scope_for_non_admin(monkeypatch) -> None:
    captured = {}

    def fake_list_candidates(engine, filters):
        captured["owner_user_id"] = filters.owner_user_id
        return [], 0

    monkeypatch.setattr("app.services.candidates.list_candidates", fake_list_candidates)

    response = list_candidates_service(
        object(),
        CandidateListFilters(),
        _auth_context(user_id=77, location_id=2),
    )

    assert captured["owner_user_id"] == 77
    assert response.meta.total == 0
