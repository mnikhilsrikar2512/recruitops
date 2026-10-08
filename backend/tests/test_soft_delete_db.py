"""Phase 4 exit gate — archived candidates and clients are hidden from lists
and from direct-ID reads for callers without the archive grant, and restore
works for callers with it (D-07, scripts/019_soft_delete.sql)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.services.candidates import get_candidate_detail_service
from app.services.clients import get_client_detail_service
from tests.test_metric_buckets_db import (  # noqa: F401  (fixtures)
    MARKER,
    _cleanup,
    _engine,
    _seed_application,
    admin,
    client,
)


def _cleanup_archives(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "DELETE a FROM dbo.candidate_archives AS a INNER JOIN dbo.candidates AS c ON c.id = a.candidate_id "
            "WHERE c.full_name LIKE :m"), {"m": f"{MARKER}%"})


@pytest.fixture()
def seeded(client, admin):
    engine = _engine()
    _cleanup_archives(engine)
    _cleanup(engine, admin["tenant_id"])
    application_id = _seed_application(engine, admin, stage="interview", suffix="archive")
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT ca.candidate_id, ca.requisition_id, r.client_company_id FROM dbo.candidate_applications ca "
            "JOIN dbo.requisitions r ON r.id = ca.requisition_id WHERE ca.id = :a"), {"a": application_id}).mappings().one()
    yield {"application_id": application_id, **{k: int(v) for k, v in row.items()}}
    _cleanup_archives(engine)
    _cleanup(engine, admin["tenant_id"])


def _caller(admin):
    with _engine().connect() as connection:
        location_id = connection.execute(text("SELECT location_id FROM dbo.users WHERE id = :u"), {"u": admin["user_id"]}).scalar()
    user = SimpleNamespace(id=admin["user_id"], location_id=location_id, role_code="admin", tenant_id=admin["tenant_id"])
    return SimpleNamespace(session_id=1, session_token_hash="x", user=user, tenant_id=admin["tenant_id"], company_wide=True)


def _names(client, admin, path, **params):
    response = client.get(f"/api/v1{path}", params={"page_size": 100, **params}, headers=admin["headers"])
    assert response.status_code == 200, response.text
    return response


def test_candidate_archive_hides_and_restore_returns(client, admin, seeded):
    candidate_id = seeded["candidate_id"]
    name = f"{MARKER} Candidate archive"

    blocked = client.post(f"/api/v1/candidates/{candidate_id}/archive", json={"reason": "duplicate profile"}, headers=admin["headers"])
    assert blocked.status_code == 409 and "open application" in blocked.json()["detail"]

    with _engine().begin() as connection:
        connection.execute(text("UPDATE dbo.candidate_applications SET application_status = N'rejected', version = version + 1 WHERE id = :a"),
                           {"a": seeded["application_id"]})

    archived = client.post(f"/api/v1/candidates/{candidate_id}/archive", json={"reason": "duplicate profile"}, headers=admin["headers"])
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None

    again = client.post(f"/api/v1/candidates/{candidate_id}/archive", json={"reason": "twice"}, headers=admin["headers"])
    assert again.status_code == 409

    listed = _names(client, admin, "/candidates/", search=name).json()["items"]
    assert all(item["id"] != candidate_id for item in listed)
    with_archived = _names(client, admin, "/candidates/", search=name, include_archived="true").json()["items"]
    assert any(item["id"] == candidate_id for item in with_archived)

    # A caller with the grant still opens it (marked archived); without it the
    # record is indistinguishable from a missing one.
    assert client.get(f"/api/v1/candidates/{candidate_id}", headers=admin["headers"]).json()["archived_at"] is not None
    with pytest.raises(HTTPException) as hidden:
        get_candidate_detail_service(_engine(), candidate_id, _caller(admin), include_archived=False)
    assert hidden.value.status_code == 404

    restored = client.post(f"/api/v1/candidates/{candidate_id}/restore", headers=admin["headers"])
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived_at"] is None
    assert any(item["id"] == candidate_id for item in _names(client, admin, "/candidates/", search=name).json()["items"])

    with _engine().connect() as connection:
        actions = connection.execute(text(
            "SELECT action_type FROM dbo.audit_logs WHERE entity_type = N'candidate' AND entity_id = :c ORDER BY id"
        ), {"c": candidate_id}).scalars().all()
        history = connection.execute(text(
            "SELECT COUNT(*) FROM dbo.candidate_archives WHERE candidate_id = :c AND restored_at IS NOT NULL"
        ), {"c": candidate_id}).scalar_one()
    assert actions[-2:] == ["candidate.archive", "candidate.restore"]
    assert history == 1


def test_client_archive_hides_and_restore_returns(client, admin, seeded):
    client_id = seeded["client_company_id"]
    name = f"{MARKER} Client archive"

    blocked = client.post(f"/api/v1/clients/{client_id}/archive", json={"reason": "no longer a client"}, headers=admin["headers"])
    assert blocked.status_code == 409 and "open requisition" in blocked.json()["detail"]

    with _engine().begin() as connection:
        connection.execute(text("UPDATE dbo.requisitions SET status = N'closed', version = version + 1 WHERE id = :r"),
                           {"r": seeded["requisition_id"]})

    archived = client.post(f"/api/v1/clients/{client_id}/archive", json={"reason": "no longer a client"}, headers=admin["headers"])
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None

    assert all(item["id"] != client_id for item in _names(client, admin, "/clients/", search=name).json()["items"])
    assert any(item["id"] == client_id for item in _names(client, admin, "/clients/", search=name, include_archived="true").json()["items"])
    with pytest.raises(HTTPException) as hidden:
        get_client_detail_service(_engine(), client_id, include_archived=False)
    assert hidden.value.status_code == 404

    restored = client.post(f"/api/v1/clients/{client_id}/restore", headers=admin["headers"])
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived_at"] is None
    assert any(item["id"] == client_id for item in _names(client, admin, "/clients/", search=name).json()["items"])


def test_archive_needs_a_reason(client, admin, seeded):
    response = client.post(f"/api/v1/candidates/{seeded['candidate_id']}/archive", json={"reason": " "}, headers=admin["headers"])
    assert response.status_code == 422
