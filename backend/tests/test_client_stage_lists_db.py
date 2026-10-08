"""Phase 4.10 — each client has its own stage list (per client only).

Runs against the configured database (skipped when unreachable)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.maintenance import history_maintenance
from tests.test_metric_buckets_db import (  # noqa: F401  (fixtures)
    MARKER,
    _cleanup,
    _engine,
    _seed_application,
    admin,
    client,
)


def _drop_lists(engine) -> None:
    with engine.begin() as connection:
        ids = connection.execute(text(
            "SELECT t.id FROM dbo.pipeline_templates t JOIN dbo.client_companies c ON c.id = t.client_company_id "
            "WHERE c.name LIKE :m"), {"m": f"{MARKER}%"}).scalars().all()
        for template_id in ids:
            connection.execute(text("UPDATE dbo.requisitions SET pipeline_template_id = NULL, version = version + 1 "
                                    "WHERE pipeline_template_id = :t"), {"t": template_id})
            connection.execute(text("DELETE FROM dbo.pipeline_template_stages WHERE pipeline_template_id = :t"), {"t": template_id})
            connection.execute(text("DELETE FROM dbo.pipeline_templates WHERE id = :t"), {"t": template_id})


@pytest.fixture()
def two_clients(client, admin):
    engine = _engine()
    _drop_lists(engine)
    _cleanup(engine, admin["tenant_id"])
    first = _seed_application(engine, admin, stage="interview", suffix="stagesA")
    second = _seed_application(engine, admin, stage="interview", suffix="stagesB")
    yield first, second
    _drop_lists(engine)
    with engine.begin() as connection, history_maintenance(connection):
        connection.execute(text(
            "DELETE h FROM dbo.candidate_stage_history h JOIN dbo.candidate_applications ca ON ca.id = h.candidate_application_id "
            "JOIN dbo.requisitions r ON r.id = ca.requisition_id WHERE r.title LIKE :m"), {"m": f"{MARKER}%"})
    _cleanup(engine, admin["tenant_id"])


def _client_of(application_id):
    with _engine().connect() as connection:
        return connection.execute(text(
            "SELECT r.client_company_id FROM dbo.candidate_applications ca JOIN dbo.requisitions r ON r.id = ca.requisition_id "
            "WHERE ca.id = :a"), {"a": application_id}).scalar_one()


STAGES = [
    {"name": "Sourced", "bucket": "sourced"},
    {"name": "Tech Round", "bucket": "interview"},
    {"name": "Client Round", "bucket": "interview"},
    {"name": "Offer", "bucket": "offer"},
]


def test_client_list_needs_remap_then_governs_moves(client, admin, two_clients):
    first, second = two_clients
    client_a = _client_of(first)
    url = f"/api/v1/settings/stage-lists/clients/{client_a}"

    blocked = client.put(url, json={"stages": STAGES}, headers=admin["headers"])
    assert blocked.status_code == 409, blocked.text
    detail = blocked.json()["detail"]
    assert detail["unmapped"] == [{"stage": "interview", "candidates": 1}]
    assert "Tech Round" in detail["allowed_targets"]

    saved = client.put(url, json={"stages": STAGES, "remap": {"interview": "Tech Round"}}, headers=admin["headers"])
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["source"] == "client"
    names = [s["name"] for s in body["stages"]]
    assert names[:4] == ["Sourced", "Tech Round", "Client Round", "Offer"]
    assert {"Joined", "Rejected", "Withdrawn"} <= set(names)  # closing stages added

    detail_after = client.get(f"/api/v1/pipeline/applications/{first}", headers=admin["headers"]).json()
    assert detail_after["current_stage"] == "Tech Round"
    history = client.get(f"/api/v1/pipeline/applications/{first}/history", headers=admin["headers"]).json()
    assert any(h["source_type"] == "stage-list-change" for h in history)

    options = client.get(f"/api/v1/pipeline/applications/{first}/stages", headers=admin["headers"]).json()
    assert options["source"] == "client" and "Client Round" in [s["name"] for s in options["stages"]]

    off_list = client.patch(f"/api/v1/pipeline/applications/{first}/stage", json={"to_stage": "Panel"},
                            headers=admin["headers"])
    assert off_list.status_code == 422, off_list.text
    moved = client.patch(f"/api/v1/pipeline/applications/{first}/stage", json={"to_stage": "client round"},
                         headers=admin["headers"])
    assert moved.status_code == 200, moved.text
    assert moved.json()["to_stage"] == "Client Round"

    # The other client is untouched: it still uses the company / platform stages.
    other = client.get(f"/api/v1/pipeline/applications/{second}/stages", headers=admin["headers"]).json()
    assert other["source"] in ("company", "platform")

    overview = client.get("/api/v1/settings/stage-lists", headers=admin["headers"]).json()
    mine = [c for c in overview["clients"] if c["client_id"] == client_a]
    assert mine and mine[0]["has_own_list"] is True


def test_new_requisition_follows_its_client_list(client, admin, two_clients):
    from app.repositories.stage_lists import point_requisition_at_list

    first, _ = two_clients
    client_a = _client_of(first)
    saved = client.put(f"/api/v1/settings/stage-lists/clients/{client_a}",
                       json={"stages": STAGES, "remap": {"interview": "Tech Round"}}, headers=admin["headers"])
    assert saved.status_code == 200, saved.text
    engine = _engine()
    with engine.begin() as connection:
        branch_id = connection.execute(text("SELECT branch_id FROM dbo.client_companies WHERE id = :c"), {"c": client_a}).scalar_one()
        requisition_id = connection.execute(text(
            """
            INSERT INTO dbo.requisitions (branch_id, hiring_type, title, owner_user_id, status, open_positions,
                                          client_company_id, job_description, target_close_date)
            OUTPUT INSERTED.id
            VALUES (:b, N'external', :t, :u, N'open', 1, :c, N'stage list test',
                    CAST(DATEADD(day, 30, CAST(SYSUTCDATETIME() AS DATE)) AS DATE))
            """), {"b": branch_id, "t": f"{MARKER} Requisition stagesNew", "u": admin["user_id"], "c": client_a}).scalar_one()
    point_requisition_at_list(engine, int(requisition_id))
    detail = client.get(f"/api/v1/requisitions/{requisition_id}", headers=admin["headers"]).json()
    assert detail["stage_template_id"] == saved.json()["template_id"]


def test_client_list_needs_a_working_stage(client, admin, two_clients):
    first, _ = two_clients
    response = client.put(f"/api/v1/settings/stage-lists/clients/{_client_of(first)}", json={"stages": [
        {"name": "Joined", "bucket": "joined"}, {"name": "Rejected", "bucket": "rejected"}]}, headers=admin["headers"])
    assert response.status_code == 422
