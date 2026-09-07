from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.pipeline import PipelineBoardFilters
from app.services.auth import AuthContext
from app.services.pipeline import get_pipeline_application_detail_service, list_pipeline_board_service


def _auth_context(user_id: int, location_id: int, role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _application_record() -> SimpleNamespace:
    return SimpleNamespace(
        application_id=201,
        candidate_id=11,
        candidate_name="Asha Verma",
        requisition_id=55,
        requisition_title="Java Developer",
        location_id=8,
        location_name="Pune",
        owner_user_id=91,
        owner_name="Owner User",
        sourced_by_user_id=77,
        sourced_by_name="Recruiter User",
        submitted_by_user_id=92,
        submitted_by_name="Submitter User",
        current_stage="submitted",
        application_status="active",
        screening_status="pending",
        stage_reason=None,
        rejection_side="none",
        rejection_stage=None,
        rejection_reason=None,
        client_feedback_status=None,
        client_feedback_notes=None,
        stage_updated_at="2026-08-19T00:00:00Z",
        last_activity_at="2026-08-19T00:00:00Z",
        expected_joining_date=None,
        applied_at="2026-08-19T00:00:00Z",
        updated_at="2026-08-19T00:00:00Z",
    )


def test_pipeline_detail_allows_sourced_by_user(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.find_pipeline_application_by_id",
        lambda engine, application_id: _application_record(),
    )

    response = get_pipeline_application_detail_service(object(), 201, _auth_context(user_id=77, location_id=3))

    assert response.application_id == 201


def test_pipeline_detail_blocks_unrelated_user(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.find_pipeline_application_by_id",
        lambda engine, application_id: _application_record(),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_pipeline_application_detail_service(object(), 201, _auth_context(user_id=5, location_id=3))

    assert exc_info.value.status_code == 403


def test_pipeline_board_defaults_location_scope_for_non_admin(monkeypatch) -> None:
    captured = {}

    def fake_list_pipeline_board(engine, filters):
        captured["location_id"] = filters.location_id
        return []

    monkeypatch.setattr("app.services.pipeline.list_pipeline_board", fake_list_pipeline_board)

    response = list_pipeline_board_service(
        object(),
        PipelineBoardFilters(),
        _auth_context(user_id=22, location_id=6),
    )

    assert captured["location_id"] == 6
    assert response == []
