from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from tests.stubs import make_user_record
from app.schemas.daily_update import DailyUpdateCreate
from app.services.daily_updates import create_daily_update_service


def _payload() -> DailyUpdateCreate:
    return DailyUpdateCreate(
        update_date="2026-08-19",
        requisition_id=55,
        submitted_by_user_id=22,
        summary="Worked on sourcing and screening",
        profiles_sourced_count=4,
        profiles_screened_count=2,
        profiles_submitted_count=1,
        blockers="Waiting for client response",
        next_actions="Follow up in afternoon",
        submission_status="submitted",
    )


def test_create_daily_update_rejects_missing_submitter(monkeypatch) -> None:
    monkeypatch.setattr("app.services.daily_updates.find_user_by_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        create_daily_update_service(object(), _payload())

    assert exc_info.value.status_code == 404


def test_create_daily_update_rejects_wrong_location_submitter(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.daily_updates.find_user_by_id",
        lambda *args, **kwargs: make_user_record(user_id=22, primary_location_id=9),
    )
    monkeypatch.setattr(
        "app.services.daily_updates.find_requisition_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=55, location_id=4),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_daily_update_service(object(), _payload())

    assert exc_info.value.status_code == 400
    assert "same location" in exc_info.value.detail


def test_create_daily_update_rejects_unlinked_submitter(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.daily_updates.find_user_by_id",
        lambda *args, **kwargs: make_user_record(user_id=22, primary_location_id=4),
    )
    monkeypatch.setattr(
        "app.services.daily_updates.find_requisition_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=55, location_id=4),
    )
    monkeypatch.setattr("app.services.daily_updates.has_user_requisition_link", lambda *args, **kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        create_daily_update_service(object(), _payload())

    assert exc_info.value.status_code == 403
    assert "linked to the requisition" in exc_info.value.detail


def test_create_daily_update_rejects_duplicate_same_date(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.daily_updates.find_user_by_id",
        lambda *args, **kwargs: make_user_record(user_id=22, primary_location_id=4),
    )
    monkeypatch.setattr(
        "app.services.daily_updates.find_requisition_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=55, location_id=4),
    )
    monkeypatch.setattr("app.services.daily_updates.has_user_requisition_link", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.services.daily_updates.count_daily_updates_for_user_requisition_date",
        lambda *args, **kwargs: 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_daily_update_service(object(), _payload())

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


def test_create_daily_update_succeeds_when_valid(monkeypatch) -> None:
    created = SimpleNamespace(
        id=501,
        location_id=4,
        submitted_by_user_id=22,
        submitted_by_name="Recruiter One",
        requisition_id=55,
        requisition_title="Java Developer",
        update_date="2026-08-19",
        summary="Worked on sourcing and screening",
        profiles_sourced_count=4,
        profiles_screened_count=2,
        profiles_submitted_count=1,
        interviews_scheduled_count=None,
        offers_closed_count=None,
        blockers="Waiting for client response",
        next_actions="Follow up in afternoon",
        submission_status="submitted",
        submitted_at="2026-08-19T10:00:00Z",
        created_at="2026-08-19T10:00:00Z",
        updated_at="2026-08-19T10:00:00Z",
    )
    monkeypatch.setattr(
        "app.services.daily_updates.find_user_by_id",
        lambda *args, **kwargs: make_user_record(user_id=22, primary_location_id=4),
    )
    monkeypatch.setattr(
        "app.services.daily_updates.find_requisition_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=55, location_id=4),
    )
    monkeypatch.setattr("app.services.daily_updates.has_user_requisition_link", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.services.daily_updates.count_daily_updates_for_user_requisition_date",
        lambda *args, **kwargs: 0,
    )
    monkeypatch.setattr("app.services.daily_updates.create_daily_update", lambda *args, **kwargs: created)

    response = create_daily_update_service(object(), _payload())

    assert response.id == 501
    assert response.requisition_id == 55
