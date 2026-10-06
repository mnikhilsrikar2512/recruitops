from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.auth import AuthContext
from app.services.dashboards import (
    get_company_summary_service,
    get_location_summary_service,
    get_my_work_dashboard_service,
    get_role_dashboard_service,
)


def _auth_context(user_id: int, location_id: int | None, role_code: str) -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def test_location_summary_defaults_to_actor_location_for_non_admin(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dashboards.get_location_summary_counts",
        lambda engine, location_id: SimpleNamespace(
            location_id=location_id,
            location_name="Hyderabad",
            open_requisitions=2,
            active_candidates=5,
            active_applications=4,
            submitted_profiles=3,
            submitted_updates=6,
            joined_applications=1,
        ),
    )

    response = get_location_summary_service(object(), _auth_context(1, 9, "recruiter"), None)

    assert response.location_id == 9


def test_role_dashboard_uses_actor_context(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dashboards.get_role_dashboard_counts",
        lambda engine, actor_user_id, actor_location_id, is_admin, tenant_id=None: SimpleNamespace(
            open_requisitions=2,
            active_candidates=5,
            active_applications=4,
            pending_daily_updates=3,
        ),
    )

    response = get_role_dashboard_service(object(), _auth_context(7, 9, "recruiter"))

    assert response.role_code == "recruiter"
    assert response.location_id == 9
    assert response.pending_daily_updates == 3


def test_my_work_dashboard_uses_user_context(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dashboards.get_my_work_dashboard_counts",
        lambda engine, user_id: SimpleNamespace(
            owned_requisitions=1,
            sourced_candidates=6,
            active_pipeline_items=4,
            submitted_updates=2,
        ),
    )

    response = get_my_work_dashboard_service(object(), _auth_context(12, 9, "recruiter"))

    assert response.user_id == 12
    assert response.sourced_candidates == 6


def test_location_summary_blocks_other_location_for_non_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_location_summary_service(object(), _auth_context(1, 9, "recruiter"), 11)

    assert exc_info.value.status_code == 403


def test_location_summary_returns_not_found_when_location_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dashboards.get_location_summary_counts",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("missing")),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_location_summary_service(object(), _auth_context(1, None, "admin"), 11)

    assert exc_info.value.status_code == 404


def test_company_summary_blocks_non_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_company_summary_service(object(), _auth_context(1, 9, "recruiter"))

    assert exc_info.value.status_code == 403


def test_company_summary_aggregates_admin_view(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dashboards.list_company_location_summaries",
        lambda engine, tenant_id=None: [
            SimpleNamespace(
                location_id=1,
                location_name="Hyderabad",
                open_requisitions=2,
                active_candidates=5,
                active_applications=4,
                submitted_profiles=3,
                submitted_updates=6,
                joined_applications=1,
            ),
            SimpleNamespace(
                location_id=2,
                location_name="Pune",
                open_requisitions=1,
                active_candidates=2,
                active_applications=3,
                submitted_profiles=2,
                submitted_updates=4,
                joined_applications=0,
            ),
        ],
    )

    response = get_company_summary_service(object(), _auth_context(1, None, "admin"))

    assert response.total_locations == 2
    assert response.total_open_requisitions == 3
    assert response.total_joined_applications == 1
