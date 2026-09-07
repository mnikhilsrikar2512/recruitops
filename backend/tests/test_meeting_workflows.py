from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.meeting import MeetingCreate, MeetingUpdate
from app.services.meetings import create_meeting_service, get_meeting_detail_service, update_meeting_service


def _meeting(**overrides):
    values = {
        "id": 901,
        "location_id": 4,
        "location_name": "Hyderabad",
        "client_id": 12,
        "client_name": "Acme",
        "end_client_id": None,
        "end_client_name": None,
        "meeting_owner_user_id": 21,
        "meeting_owner_name": "Owner One",
        "title": "Requirement Sync",
        "meeting_type": "requirement_discussion",
        "scheduled_at": "2026-08-31T10:00:00",
        "attendance_status": "pending",
        "outcome_status": "pending",
        "agenda": "Discuss shortlist quality.",
        "minutes_of_meeting": None,
        "decision_summary": None,
        "next_steps": None,
        "follow_up_owner_user_id": None,
        "follow_up_owner_name": None,
        "follow_up_due_date": None,
        "attendees": [],
        "created_at": "2026-08-31T09:00:00",
        "updated_at": "2026-08-31T09:00:00",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _create_payload() -> MeetingCreate:
    return MeetingCreate(
        location_id=4,
        client_id=12,
        meeting_owner_user_id=21,
        title="Requirement Sync",
        meeting_type="requirement_discussion",
        agenda="Discuss shortlist quality.",
    )


def test_get_meeting_detail_returns_404_for_missing_meeting(monkeypatch) -> None:
    monkeypatch.setattr("app.services.meetings.find_meeting_by_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        get_meeting_detail_service(object(), 901)

    assert exc_info.value.status_code == 404


def test_create_meeting_rejects_unknown_client(monkeypatch) -> None:
    monkeypatch.setattr("app.services.meetings.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.meetings.meeting_client_exists", lambda *args, **kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        create_meeting_service(object(), _create_payload())

    assert exc_info.value.status_code == 404
    assert "Client" in exc_info.value.detail


def test_create_meeting_rejects_owner_from_other_location(monkeypatch) -> None:
    monkeypatch.setattr("app.services.meetings.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.meetings.meeting_client_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.meetings.find_user_by_id", lambda *args, **kwargs: SimpleNamespace(primary_location_id=8))

    with pytest.raises(HTTPException) as exc_info:
        create_meeting_service(object(), _create_payload())

    assert exc_info.value.status_code == 400
    assert "same location" in exc_info.value.detail


def test_create_meeting_succeeds_with_valid_refs(monkeypatch) -> None:
    monkeypatch.setattr("app.services.meetings.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.meetings.meeting_client_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.meetings.find_user_by_id", lambda *args, **kwargs: SimpleNamespace(primary_location_id=4))
    monkeypatch.setattr("app.services.meetings.create_meeting", lambda *args, **kwargs: _meeting())

    response = create_meeting_service(object(), _create_payload())

    assert response.title == "Requirement Sync"
    assert response.meeting_type == "requirement_discussion"


def test_update_meeting_records_outcome(monkeypatch) -> None:
    monkeypatch.setattr("app.services.meetings.find_meeting_by_id", lambda *args, **kwargs: _meeting())
    monkeypatch.setattr("app.services.meetings.find_user_by_id", lambda *args, **kwargs: SimpleNamespace(primary_location_id=4))
    monkeypatch.setattr(
        "app.services.meetings.update_meeting",
        lambda *args, **kwargs: _meeting(
            attendance_status="attended",
            outcome_status="follow-up-required",
            minutes_of_meeting="Client requested two more profiles.",
        ),
    )

    response = update_meeting_service(
        object(),
        901,
        MeetingUpdate(
            attendance_status="attended",
            outcome_status="follow-up-required",
            minutes_of_meeting="Client requested two more profiles.",
        ),
    )

    assert response.attendance_status == "attended"
    assert response.outcome_status == "follow-up-required"
    assert response.minutes_of_meeting == "Client requested two more profiles."
