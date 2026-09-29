from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.pipeline import PipelineStageMove
from app.services.auth import AuthContext
from app.services.pipeline import move_pipeline_stage_service


def _auth_context(user_id: int, location_id: int, role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


@pytest.fixture(autouse=True)
def _stub_branch_settings(monkeypatch):
    """Stage-move tests pass a bare engine object; default the branch-config
    lookup (offer toggle) to enabled so tests exercise stage rules only."""
    monkeypatch.setattr(
        "app.services.pipeline.find_branch_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=1, code="HYD01", offers_enabled=True),
    )


def _application(
    *,
    current_stage: str = "submitted",
    application_status: str = "active",
    location_id: int = 4,
) -> SimpleNamespace:
    return SimpleNamespace(
        application_id=201,
        candidate_id=11,
        candidate_name="Asha Verma",
        requisition_id=55,
        requisition_title="Java Developer",
        location_id=location_id,
        location_name="Pune",
        owner_user_id=91,
        owner_name="Owner User",
        sourced_by_user_id=77,
        sourced_by_name="Recruiter User",
        submitted_by_user_id=92,
        submitted_by_name="Submitter User",
        current_stage=current_stage,
        application_status=application_status,
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


def _stage(stage_code: str, stage_order: int, stage_type: str = "normal") -> SimpleNamespace:
    return SimpleNamespace(
        pipeline_template_id=9,
        stage_code=stage_code,
        stage_order=stage_order,
        stage_type=stage_type,
        allows_rejection=(stage_type == "rejection"),
    )


def test_move_pipeline_stage_rejects_stage_outside_template(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.services.pipeline.find_pipeline_template_stage_for_application",
        lambda engine, application_id, stage_code: _stage("submitted", 1) if stage_code == "submitted" else None,
    )

    with pytest.raises(HTTPException) as exc_info:
        move_pipeline_stage_service(
            object(),
            201,
            PipelineStageMove(to_stage="client-round"),
            _auth_context(91, 4),
        )

    assert exc_info.value.status_code == 422


def test_move_pipeline_stage_blocks_backward_move(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="l2"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)

    def _find_stage(engine, application_id, stage_code):
        if stage_code == "l2":
            return _stage("l2", 3)
        if stage_code == "submitted":
            return _stage("submitted", 1)
        return None

    monkeypatch.setattr("app.services.pipeline.find_pipeline_template_stage_for_application", _find_stage)

    with pytest.raises(HTTPException) as exc_info:
        move_pipeline_stage_service(
            object(),
            201,
            PipelineStageMove(to_stage="submitted"),
            _auth_context(91, 4),
        )

    assert exc_info.value.status_code == 409
    assert "Backward stage movement" in exc_info.value.detail


def test_move_pipeline_stage_requires_rejection_reason(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="client-round"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)

    def _find_stage(engine, application_id, stage_code):
        if stage_code == "client-round":
            return _stage("client-round", 2)
        if stage_code == "client-rejected":
            return _stage("client-rejected", 3, "rejection")
        return None

    monkeypatch.setattr("app.services.pipeline.find_pipeline_template_stage_for_application", _find_stage)

    with pytest.raises(HTTPException) as exc_info:
        move_pipeline_stage_service(
            object(),
            201,
            PipelineStageMove(to_stage="client-rejected"),
            _auth_context(91, 4),
        )

    assert exc_info.value.status_code == 422
    assert "Rejection reason" in exc_info.value.detail


def test_move_pipeline_stage_requires_joining_date(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="offer"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)

    def _find_stage(engine, application_id, stage_code):
        if stage_code == "offer":
            return _stage("offer", 4)
        if stage_code == "joined":
            return _stage("joined", 5, "joining")
        return None

    monkeypatch.setattr("app.services.pipeline.find_pipeline_template_stage_for_application", _find_stage)

    with pytest.raises(HTTPException) as exc_info:
        move_pipeline_stage_service(
            object(),
            201,
            PipelineStageMove(to_stage="joined"),
            _auth_context(91, 4),
        )

    assert exc_info.value.status_code == 422
    assert "Joining date" in exc_info.value.detail


def test_move_pipeline_stage_blocks_post_joined_transition(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="joined", application_status="joined"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)

    def _find_stage(engine, application_id, stage_code):
        if stage_code == "joined":
            return _stage("joined", 5, "joining")
        if stage_code == "client-rejected":
            return _stage("client-rejected", 6, "rejection")
        return None

    monkeypatch.setattr("app.services.pipeline.find_pipeline_template_stage_for_application", _find_stage)

    with pytest.raises(HTTPException) as exc_info:
        move_pipeline_stage_service(
            object(),
            201,
            PipelineStageMove(to_stage="client-rejected", rejection_reason="late rejection"),
            _auth_context(91, 4),
        )

    assert exc_info.value.status_code == 409
    assert "Joined applications cannot move" in exc_info.value.detail


def test_move_pipeline_stage_succeeds_with_valid_transition(monkeypatch) -> None:
    updated = _application(current_stage="client-round", application_status="active")
    updated.stage_updated_at = "2026-08-19T01:00:00Z"

    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="submitted"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)

    def _find_stage(engine, application_id, stage_code):
        if stage_code == "submitted":
            return _stage("submitted", 1)
        if stage_code == "client-round":
            return _stage("client-round", 2)
        return None

    monkeypatch.setattr("app.services.pipeline.find_pipeline_template_stage_for_application", _find_stage)
    monkeypatch.setattr("app.services.pipeline.move_pipeline_stage", lambda *args, **kwargs: ("submitted", updated))

    response = move_pipeline_stage_service(
        object(),
        201,
        PipelineStageMove(to_stage="client-round", notes="screen cleared"),
        _auth_context(91, 4),
    )

    assert response.from_stage == "submitted"
    assert response.to_stage == "client-round"


def test_move_to_offer_stage_rejected_when_branch_disables_offers(monkeypatch) -> None:
    """Offer-phase streamlining: sourcing-only branches reject moves into offer."""
    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="executive-review"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.services.pipeline.find_pipeline_template_stage_for_application",
        lambda engine, application_id, stage_code: _stage(stage_code, 2),
    )
    monkeypatch.setattr(
        "app.services.pipeline.find_branch_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=1, code="HYD01", offers_enabled=False),
    )

    with pytest.raises(HTTPException) as exc_info:
        move_pipeline_stage_service(
            object(),
            201,
            PipelineStageMove(to_stage="offer"),
            _auth_context(91, 4),
        )

    assert exc_info.value.status_code == 409
    assert "hand off" in exc_info.value.detail


def test_move_to_joining_stage_allowed_when_branch_disables_offers(monkeypatch) -> None:
    """Joins/rejections stay reachable on offer-disabled branches (no tracked offer)."""
    updated = _application(current_stage="joined", application_status="active")
    updated.stage_updated_at = "2026-08-19T01:00:00Z"

    monkeypatch.setattr(
        "app.services.pipeline.get_pipeline_application_detail_service",
        lambda *args, **kwargs: _application(current_stage="executive-review"),
    )
    monkeypatch.setattr("app.services.pipeline.application_has_pipeline_template", lambda *args, **kwargs: True)

    def _find_stage(engine, application_id, stage_code):
        if stage_code == "executive-review":
            return _stage("executive-review", 2)
        if stage_code == "joined":
            return _stage("joined", 5, stage_type="joining")
        return None

    monkeypatch.setattr("app.services.pipeline.find_pipeline_template_stage_for_application", _find_stage)
    monkeypatch.setattr("app.services.pipeline.move_pipeline_stage", lambda *args, **kwargs: ("executive-review", updated))
    monkeypatch.setattr(
        "app.services.pipeline.find_branch_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=1, code="HYD01", offers_enabled=False),
    )
    monkeypatch.setattr("app.services.pipeline.create_notification_service", lambda *args, **kwargs: None)

    response = move_pipeline_stage_service(
        object(),
        201,
        PipelineStageMove(to_stage="joined", joining_date=__import__("datetime").date(2026, 10, 1)),
        _auth_context(91, 4),
    )

    assert response.to_stage == "joined"
