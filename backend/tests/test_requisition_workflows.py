from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from tests.stubs import make_user_record
from app.schemas.requisition import (
    RequisitionAssignmentCreate,
    RequisitionCreate,
    RequisitionStatusUpdate,
)
from app.services.auth import AuthContext
from app.services.requisitions import (
    create_requisition_assignment_service,
    create_requisition_service,
    update_requisition_status_service,
)


def _auth_context(user_id: int, location_id: int, role_code: str = "manager") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _requisition_payload() -> RequisitionCreate:
    return RequisitionCreate(
        client_id=12,
        primary_contact_id=101,
        secondary_contact_id=102,
        location_id=4,
        title="Backend Engineer",
        primary_owner_user_id=21,
        delivery_owner_user_id=22,
        openings_count=2,
        target_closure_date="2026-09-30",
        job_description="Build recruitment platform APIs",
        must_have_skills=["Python"],
        good_to_have_skills=["FastAPI"],
    )


def test_create_requisition_rejects_inactive_client(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.requisitions.find_client_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=12, location_id=4, status="inactive"),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_requisition_service(object(), _requisition_payload())

    assert exc_info.value.status_code == 409
    assert "Only active clients" in exc_info.value.detail


def test_create_requisition_rejects_wrong_contact_mapping(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.requisitions.find_client_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=12, location_id=4, status="active"),
    )
    monkeypatch.setattr(
        "app.services.requisitions.list_client_contacts",
        lambda *args, **kwargs: [SimpleNamespace(id=999)],
    )

    with pytest.raises(HTTPException) as exc_info:
        create_requisition_service(object(), _requisition_payload())

    assert exc_info.value.status_code == 400
    assert "Primary contact" in exc_info.value.detail


def test_create_requisition_rejects_owner_from_other_location(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.requisitions.find_client_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=12, location_id=4, status="active"),
    )
    monkeypatch.setattr(
        "app.services.requisitions.list_client_contacts",
        lambda *args, **kwargs: [SimpleNamespace(id=101), SimpleNamespace(id=102)],
    )

    def _find_user(engine, user_id):
        if user_id == 21:
            return make_user_record(user_id=21, primary_location_id=5)
        if user_id == 22:
            return make_user_record(user_id=22, primary_location_id=4)
        return None

    monkeypatch.setattr("app.services.requisitions.find_user_by_id", _find_user)

    with pytest.raises(HTTPException) as exc_info:
        create_requisition_service(object(), _requisition_payload())

    assert exc_info.value.status_code == 400
    assert "same location" in exc_info.value.detail


def test_create_requisition_succeeds_with_valid_mappings(monkeypatch) -> None:
    created = SimpleNamespace(
        id=55,
        location_id=4,
        requisition_code="REQ-55",
        client_id=12,
        client_name="Acme",
        primary_contact_id=101,
        primary_contact_name="Priya",
        secondary_contact_id=102,
        secondary_contact_name="Rahul",
        title="Backend Engineer",
        primary_owner_user_id=21,
        primary_owner_name="Owner One",
        delivery_owner_user_id=22,
        delivery_owner_name="Owner Two",
        priority="medium",
        status="open",
        openings_count=2,
        target_closure_date="2026-09-30T00:00:00",
        employment_type=None,
        work_mode=None,
        acceptable_career_gap_months=None,
        profile_update_window_text=None,
        client_round_required=False,
        job_description="Build recruitment platform APIs",
        stage_template_id=None,
        must_have_skills=["Python"],
        good_to_have_skills=["FastAPI"],
        created_at="2026-08-19T00:00:00",
        updated_at="2026-08-19T00:00:00",
    )
    monkeypatch.setattr(
        "app.services.requisitions.find_client_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=12, location_id=4, status="active"),
    )
    monkeypatch.setattr(
        "app.services.requisitions.list_client_contacts",
        lambda *args, **kwargs: [SimpleNamespace(id=101), SimpleNamespace(id=102)],
    )
    monkeypatch.setattr(
        "app.services.requisitions.find_user_by_id",
        lambda *args, **kwargs: make_user_record(primary_location_id=4),
    )
    monkeypatch.setattr("app.services.requisitions.create_requisition", lambda *args, **kwargs: created)

    response = create_requisition_service(object(), _requisition_payload())

    assert response.id == 55
    assert response.status == "open"


def test_update_requisition_status_writes_audit(monkeypatch) -> None:
    existing = SimpleNamespace(status="draft")
    updated = SimpleNamespace(
        id=55,
        location_id=4,
        requisition_code="REQ-55",
        client_id=12,
        client_name="Acme",
        primary_contact_id=101,
        primary_contact_name="Priya",
        secondary_contact_id=102,
        secondary_contact_name="Rahul",
        title="Backend Engineer",
        primary_owner_user_id=21,
        primary_owner_name="Owner One",
        delivery_owner_user_id=22,
        delivery_owner_name="Owner Two",
        priority="medium",
        status="open",
        openings_count=2,
        target_closure_date="2026-09-30T00:00:00",
        employment_type=None,
        work_mode=None,
        acceptable_career_gap_months=None,
        profile_update_window_text=None,
        client_round_required=False,
        job_description="Build recruitment platform APIs",
        stage_template_id=None,
        must_have_skills=["Python"],
        good_to_have_skills=["FastAPI"],
        created_at="2026-08-19T00:00:00",
        updated_at="2026-08-19T00:00:00",
    )
    captured = {}

    monkeypatch.setattr("app.services.requisitions.find_requisition_by_id", lambda *args, **kwargs: existing)
    monkeypatch.setattr("app.services.requisitions.update_requisition_status", lambda *args, **kwargs: updated)
    monkeypatch.setattr("app.services.requisitions.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    response = update_requisition_status_service(
        object(),
        55,
        RequisitionStatusUpdate(status="open", reason="client confirmed"),
        _auth_context(8, 4),
    )

    assert response.status == "open"
    assert captured["action_type"] == "status_updated"
    assert captured["old_values"]["status"] == "draft"
    assert captured["new_values"]["status"] == "open"


def test_create_requisition_assignment_rejects_user_from_other_location(monkeypatch) -> None:
    requisition = SimpleNamespace(id=55, location_id=4)
    monkeypatch.setattr("app.services.requisitions.find_requisition_by_id", lambda *args, **kwargs: requisition)
    monkeypatch.setattr(
        "app.services.requisitions.find_user_by_id",
        lambda *args, **kwargs: make_user_record(user_id=77, primary_location_id=9),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_requisition_assignment_service(
            object(),
            55,
            RequisitionAssignmentCreate(assigned_user_id=77, assignment_type="support"),
        )

    assert exc_info.value.status_code == 400
    assert "same location" in exc_info.value.detail
