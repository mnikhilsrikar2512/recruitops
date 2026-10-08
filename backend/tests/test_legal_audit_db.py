"""Phase 5.1 / 5.4 exit gate — legal versions are recorded with timestamp
and user id, a new version asks for acceptance again, and the audit log
viewer shows the company's own events only.

Runs against the configured database (skipped when unreachable)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.repositories.legal import publish_document
from tests.test_metric_buckets_db import _engine, admin, client  # noqa: F401  (fixtures)


@pytest.fixture()
def clean_acceptances(client, admin):
    """The admin starts with no acceptances; whatever existed is restored."""
    engine = _engine()
    with engine.begin() as connection:
        saved = connection.execute(text(
            "SELECT tenant_id, user_id, document_id, doc_type, version, on_behalf_of_company, accepted_at, user_agent "
            "FROM dbo.legal_acceptances WHERE user_id = :u OR (tenant_id = :t AND doc_type = N'dpa')"),
            {"u": admin["user_id"], "t": admin["tenant_id"]}).mappings().all()
        connection.execute(text("DELETE FROM dbo.legal_acceptances WHERE user_id = :u OR (tenant_id = :t AND doc_type = N'dpa')"),
                           {"u": admin["user_id"], "t": admin["tenant_id"]})
        active_tos = connection.execute(text(
            "SELECT id FROM dbo.legal_documents WHERE doc_type = N'tos' AND status = N'active'")).scalar_one()
    yield
    with engine.begin() as connection:
        newer = connection.execute(text(
            "SELECT id FROM dbo.legal_documents WHERE doc_type = N'tos' AND id > :id"), {"id": active_tos}).scalars().all()
        if newer:
            ids = ", ".join(str(int(i)) for i in newer)
            connection.execute(text(f"DELETE FROM dbo.legal_acceptances WHERE document_id IN ({ids})"))
            connection.execute(text(f"DELETE FROM dbo.legal_documents WHERE id IN ({ids})"))
            connection.execute(text("UPDATE dbo.legal_documents SET status = N'active' WHERE id = :id"), {"id": active_tos})
        connection.execute(text("DELETE FROM dbo.legal_acceptances WHERE user_id = :u OR (tenant_id = :t AND doc_type = N'dpa')"),
                           {"u": admin["user_id"], "t": admin["tenant_id"]})
        for row in saved:
            connection.execute(text(
                "INSERT INTO dbo.legal_acceptances (tenant_id, user_id, document_id, doc_type, version, on_behalf_of_company, accepted_at, user_agent) "
                "VALUES (:tenant_id, :user_id, :document_id, :doc_type, :version, :on_behalf_of_company, :accepted_at, :user_agent)"), dict(row))


def _status(client, admin):
    response = client.get("/api/v1/legal/acceptances", headers=admin["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def test_documents_are_public_and_marked_placeholder(client):
    response = client.get("/api/v1/legal/documents")
    assert response.status_code == 200, response.text
    types = {d["doc_type"]: d for d in response.json()["items"]}
    assert set(types) == {"tos", "privacy", "dpa"}
    assert "automated tool" in types["privacy"]["body"]  # AI-scoring disclosure topic


def test_accept_records_version_user_and_time_and_new_version_asks_again(client, admin, clean_acceptances):
    status = _status(client, admin)
    assert set(status["pending"]) == {"tos", "privacy", "dpa"}  # the admin may accept the DPA for the company
    versions = {i["doc_type"]: i["current_version"] for i in status["items"]}

    stale = client.post("/api/v1/legal/acceptances", json={"doc_type": "tos", "version": versions["tos"] + 5},
                        headers=admin["headers"])
    assert stale.status_code == 409, stale.text

    for doc_type in ("tos", "privacy", "dpa"):
        done = client.post("/api/v1/legal/acceptances", json={"doc_type": doc_type, "version": versions[doc_type]},
                           headers={**admin["headers"], "User-Agent": "legal-test"})
        assert done.status_code == 201, done.text
    assert _status(client, admin)["pending"] == []

    with _engine().connect() as connection:
        rows = connection.execute(text(
            "SELECT doc_type, version, user_id, tenant_id, accepted_at, on_behalf_of_company, user_agent "
            "FROM dbo.legal_acceptances WHERE user_id = :u ORDER BY id"), {"u": admin["user_id"]}).mappings().all()
    assert [(r["doc_type"], r["version"]) for r in rows] == [(t, versions[t]) for t in ("tos", "privacy", "dpa")]
    assert all(r["accepted_at"] is not None and r["tenant_id"] == admin["tenant_id"] for r in rows)
    assert rows[-1]["on_behalf_of_company"] and rows[-1]["user_agent"] == "legal-test"

    record = client.get("/api/v1/legal/acceptances/company", headers=admin["headers"])
    assert record.status_code == 200 and len(record.json()) >= 3

    # Ops publishes Terms v+1: only Terms is asked again.
    publish_document(_engine(), doc_type="tos", title="Terms of Service", body="Updated terms " * 30,
                     is_placeholder=True, published_by="legal-test")
    again = _status(client, admin)
    assert again["pending"] == ["tos"]
    tos = [i for i in again["items"] if i["doc_type"] == "tos"][0]
    assert tos["accepted_version"] == versions["tos"] and tos["current_version"] == versions["tos"] + 1

    # The acceptance shows up in the audit log viewer.
    audit = client.get("/api/v1/audit-logs/?action_type=legal.accepted", headers=admin["headers"])
    assert audit.status_code == 200, audit.text
    assert audit.json()["meta"]["total"] >= 3
    first = audit.json()["items"][0]
    detail = client.get(f"/api/v1/audit-logs/{first['id']}", headers=admin["headers"])
    assert detail.status_code == 200 and detail.json()["new_values"]["doc_type"] in ("tos", "privacy", "dpa")


def test_audit_log_is_company_only_and_filters_are_strict(client, admin):
    with _engine().connect() as connection:
        foreign = connection.execute(text(
            """
            SELECT TOP (1) a.id FROM dbo.audit_logs a
            JOIN dbo.branches b ON b.id = a.branch_id
            WHERE b.tenant_id <> :t ORDER BY a.id DESC
            """), {"t": admin["tenant_id"]}).scalar()
    if foreign is not None:
        assert client.get(f"/api/v1/audit-logs/{foreign}", headers=admin["headers"]).status_code == 404
    assert client.get("/api/v1/audit-logs/?colour=red", headers=admin["headers"]).status_code == 400
    assert client.get("/api/v1/audit-logs/?date_from=2026-02-01&date_to=2026-01-01", headers=admin["headers"]).status_code == 422
    facets = client.get("/api/v1/audit-logs/facets", headers=admin["headers"])
    assert facets.status_code == 200 and isinstance(facets.json()["action_types"], list)
    assert client.get("/api/v1/audit-logs/").status_code == 401
