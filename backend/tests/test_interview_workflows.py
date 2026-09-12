from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from tests.stubs import make_user_record
from app.schemas.interview import InterviewCreate, InterviewFeedbackUpdate, InterviewListFilters
from app.services.interviews import create_interview_service, get_interview_detail_service, list_interviews_service, update_interview_feedback_service


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
        "current_stage": "Screening",
        "application_status": "active",
        "screening_status": "pending",
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


def _interview(**overrides):
    values = {
        "id": 901,
        "candidate_application_id": 501,
        "candidate_id": 401,
        "candidate_name": "Maya Patel",
        "requisition_id": 301,
        "requisition_title": "Platform Reliability Lead",
        "location_id": 1,
        "location_name": "HQ",
        "round_type": "manager",
        "round_name": "L1 Manager Review",
        "scheduled_at": datetime(2026, 8, 31, 9, 30),
        "interviewer_name": "Devon Harper",
        "interviewer_user_id": 601,
        "status": "scheduled",
        "feedback_status": "pending",
        "decision": None,
        "feedback_notes": None,
        "created_by_user_id": 7,
        "created_by_name": "API Tester",
        "created_at": datetime(2026, 8, 30, 9, 0),
        "updated_at": datetime(2026, 8, 30, 9, 0),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_list_interviews_applies_non_admin_location(monkeypatch) -> None:
    captured = {}

    def fake_list(_engine, filters):
        captured["location_id"] = filters.location_id
        return [_interview()], 1

    auth = SimpleNamespace(user=SimpleNamespace(role_code="recruiter", location_id=4, id=7))
    monkeypatch.setattr("app.services.interviews.list_interviews", fake_list)

    response = list_interviews_service(object(), InterviewListFilters(), auth)

    assert captured["location_id"] == 4
    assert response.meta.total == 1


def test_get_interview_detail_raises_for_missing_interview(monkeypatch) -> None:
    monkeypatch.setattr("app.services.interviews.find_interview_by_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        get_interview_detail_service(object(), 999)

    assert exc.value.status_code == 404


def test_create_interview_rejects_missing_application(monkeypatch) -> None:
    monkeypatch.setattr("app.services.interviews.find_pipeline_application_by_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        create_interview_service(
            object(),
            InterviewCreate(candidate_application_id=501, round_type="manager", round_name="L1", created_by_user_id=7),
        )

    assert exc.value.status_code == 404


def test_create_interview_succeeds_with_valid_refs(monkeypatch) -> None:
    monkeypatch.setattr("app.services.interviews.find_pipeline_application_by_id", lambda *args, **kwargs: _application())
    monkeypatch.setattr("app.services.interviews.find_user_by_id", lambda *args, **kwargs: make_user_record(user_id=601))
    monkeypatch.setattr("app.services.interviews.create_interview", lambda *args, **kwargs: _interview())

    response = create_interview_service(
        object(),
        InterviewCreate(
            candidate_application_id=501,
            round_type="manager",
            round_name="L1 Manager Review",
            interviewer_user_id=601,
            created_by_user_id=7,
        ),
    )

    assert response.id == 901
    assert response.candidate_name == "Maya Patel"


def test_update_interview_feedback_records_decision(monkeypatch) -> None:
    monkeypatch.setattr("app.services.interviews.find_interview_by_id", lambda *args, **kwargs: _interview())
    monkeypatch.setattr("app.services.interviews.find_pipeline_application_by_id", lambda *args, **kwargs: _application())
    monkeypatch.setattr(
        "app.services.interviews.update_interview_feedback",
        lambda *args, **kwargs: _interview(status="completed", feedback_status="received", decision="strong-yes"),
    )

    response = update_interview_feedback_service(
        object(),
        901,
        InterviewFeedbackUpdate(decision="strong-yes", feedback_notes="Advance to final round."),
    )

    assert response.status == "completed"
    assert response.feedback_status == "received"
    assert response.decision == "strong-yes"
