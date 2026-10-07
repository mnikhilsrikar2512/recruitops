"""Phase 4 exit gate — two concurrent edits: the second gets 409 with the
fresh row (optimistic locking, scripts/018_row_versions.sql)."""
from __future__ import annotations

import pytest

from tests.test_metric_buckets_db import (  # noqa: F401  (fixtures)
    _cleanup,
    _engine,
    _seed_application,
    admin,
    client,
)
from sqlalchemy import text


@pytest.fixture()
def seeded(client, admin):
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    application_id = _seed_application(engine, admin, stage="interview", suffix="versions")
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT candidate_id, requisition_id FROM dbo.candidate_applications WHERE id = :a"
        ), {"a": application_id}).mappings().one()
    yield {"application_id": application_id, "candidate_id": int(row["candidate_id"]), "requisition_id": int(row["requisition_id"])}
    _cleanup(engine, admin["tenant_id"])


def _get(client, admin, path):
    response = client.get(f"/api/v1{path}", headers=admin["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def test_second_candidate_edit_gets_409_with_fresh_row(client, admin, seeded):
    path = f"/candidates/{seeded['candidate_id']}"
    loaded = _get(client, admin, path)["version"]

    first = client.patch(f"/api/v1{path}", json={"current_company": "Edit One", "version": loaded}, headers=admin["headers"])
    assert first.status_code == 200, first.text
    assert first.json()["version"] == loaded + 1

    second = client.patch(f"/api/v1{path}", json={"current_company": "Edit Two", "version": loaded}, headers=admin["headers"])
    assert second.status_code == 409, second.text
    body = second.json()
    assert body["code"] == "stale_write"
    assert body["current_version"] == loaded + 1
    assert body["current"]["version"] == loaded + 1

    # Without a version (older clients) the edit is not checked.
    legacy = client.patch(f"/api/v1{path}", json={"current_company": "Edit Three"}, headers=admin["headers"])
    assert legacy.status_code == 200, legacy.text


def test_second_requisition_edit_gets_409(client, admin, seeded):
    path = f"/requisitions/{seeded['requisition_id']}"
    loaded = _get(client, admin, path)["version"]
    first = client.patch(f"/api/v1{path}", json={"title": "MB Gate Requisition versions A", "version": loaded}, headers=admin["headers"])
    assert first.status_code == 200, first.text
    second = client.patch(f"/api/v1{path}", json={"title": "MB Gate Requisition versions B", "version": loaded}, headers=admin["headers"])
    assert second.status_code == 409, second.text
    assert second.json()["current"]["title"] == "MB Gate Requisition versions A"


def test_second_stage_move_gets_409(client, admin, seeded):
    path = f"/pipeline/applications/{seeded['application_id']}"
    loaded = _get(client, admin, path)["version"]
    first = client.patch(f"/api/v1{path}/stage", json={"to_stage": "Technical Interview", "version": loaded}, headers=admin["headers"])
    assert first.status_code == 200, first.text
    assert first.json()["version"] == loaded + 1
    second = client.patch(
        f"/api/v1{path}/stage",
        json={"to_stage": "interview", "notes": "stale tab", "version": loaded},
        headers=admin["headers"],
    )
    assert second.status_code == 409, second.text
    assert second.json()["current"]["current_stage"] == "Technical Interview"
