"""Phase 5.3 exit gate — privacy requests.

- A company export contains the company's rows (no secrets) and its files.
- A company purge removes every row the company owns, hands shared
  candidates over to the other company, holds audit/legal rows, and leaves
  the other company untouched.
- A company delete request needs a different admin; the requester can't
  approve it; it can be cancelled.
- A candidate can be exported and erased; a candidate another company also
  works with can't be erased from here.

Runs against the configured database (skipped when unreachable). Builds two
throw-away companies, so nothing real is ever purged.
"""
from __future__ import annotations

import io
import json
import uuid
import zipfile

import pytest
from sqlalchemy import text

from app.core.file_storage import get_storage, tenant_key
from app.services.tenant_data import predicate, tenant_tables
from app.services.tenant_purge import KEEP, purge_company, release_expired_holds
from tests.test_metric_buckets_db import _engine, admin, client  # noqa: F401  (fixtures)

MARK = "PRIV Gate"


def _one(connection, sql, **params):
    return connection.execute(text(sql), params).scalar_one()


def _make_company(connection, label: str) -> dict:
    tag = uuid.uuid4().hex[:8]
    tenant = _one(connection, "INSERT INTO dbo.tenants (slug, display_name, status) OUTPUT INSERTED.id VALUES (:s, :n, N'active')",
                  s=f"priv-{label}-{tag}", n=f"{MARK} {label}")
    branch = _one(connection, "INSERT INTO dbo.branches (name, code, location, status, tenant_id) OUTPUT INSERTED.id "
                  "VALUES (:n, :c, N'Test', N'active', :t)", n=f"{MARK} {label} office", c=f"P{tag[:6]}", t=tenant)
    role = _one(connection, "SELECT TOP (1) id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")
    user = _one(connection, "INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status, status, "
                "default_role_id, hierarchy_level, tenant_id) OUTPUT INSERTED.id VALUES (:n, :e, :code, N'x', N'completed', N'active', "
                ":r, N'admin', :t)",
                n=f"{MARK} {label} admin", e=f"priv-{label}-{tag}@example.test", code=f"PRIV-{label}-{tag}", r=role, t=tenant)
    client_id = _one(connection, "INSERT INTO dbo.client_companies (branch_id, name, relationship_type, status) OUTPUT INSERTED.id "
                     "VALUES (:b, :n, N'direct-client', N'active')", b=branch, n=f"{MARK} {label} client")
    requisition = _one(connection, "INSERT INTO dbo.requisitions (branch_id, hiring_type, title, owner_user_id, status, open_positions, "
                       "client_company_id, job_description, target_close_date) OUTPUT INSERTED.id VALUES (:b, N'external', :t, :u, "
                       "N'open', 1, :c, N'privacy test', CAST(SYSUTCDATETIME() AS DATE))",
                       b=branch, t=f"{MARK} {label} role", u=user, c=client_id)
    return {"tenant": tenant, "branch": branch, "user": user, "client": client_id, "requisition": requisition}


def _candidate(connection, owner: dict, name: str) -> int:
    return _one(connection, "INSERT INTO dbo.candidates (full_name, email, phone, source, created_by_user_id, branch_id) "
                "OUTPUT INSERTED.id VALUES (:n, :e, N'9999999999', N'test', :u, :b)",
                n=f"{MARK} {name}", e=f"{uuid.uuid4().hex[:8]}@cand.test", u=owner["user"], b=owner["branch"])


def _apply(connection, company: dict, candidate: int, stage: str = "interview") -> int:
    application = _one(connection, "INSERT INTO dbo.candidate_applications (candidate_id, requisition_id, owner_user_id, current_stage, "
                       "applied_at, stage_updated_at, stage_reason) OUTPUT INSERTED.id VALUES (:c, :r, :u, :s, SYSUTCDATETIME(), "
                       "SYSUTCDATETIME(), N'free text about the person')", c=candidate, r=company["requisition"], u=company["user"], s=stage)
    connection.execute(text("INSERT INTO dbo.candidate_stage_history (candidate_application_id, from_stage, to_stage, change_reason, "
                            "changed_by_user_id, changed_at, source_type) VALUES (:a, NULL, :s, N'private note', :u, SYSUTCDATETIME(), N'manual')"),
                       {"a": application, "s": stage, "u": company["user"]})
    return application


def _document(connection, company: dict, candidate: int) -> tuple[int, str]:
    key = tenant_key(company["tenant"], "candidates", candidate, f"{uuid.uuid4().hex}.pdf")
    get_storage().put(key, b"%PDF-1.4 privacy test", "application/pdf")
    doc = _one(connection, "INSERT INTO dbo.candidate_documents (candidate_id, document_type, file_name, file_path, verification_status, "
               "uploaded_by_user_id, storage_key, content_type, size_bytes) OUTPUT INSERTED.id VALUES (:c, N'resume', N'cv.pdf', :k, "
               "N'pending', :u, :k, N'application/pdf', 21)", c=candidate, k=key, u=company["user"])
    return doc, key


@pytest.fixture()
def companies(client):
    engine = _engine()
    with engine.begin() as connection:
        a = _make_company(connection, "A")
        b = _make_company(connection, "B")
        only_a = _candidate(connection, a, "only A")
        shared = _candidate(connection, a, "shared")
        _apply(connection, a, only_a)
        _apply(connection, a, shared)
        _apply(connection, b, shared)
        doc, key = _document(connection, a, only_a)
        connection.execute(text("INSERT INTO dbo.audit_logs (actor_user_id, branch_id, entity_type, entity_id, action_type) "
                                "VALUES (:u, :b, N'test', 1, N'privacy.test')"), {"u": a["user"], "b": a["branch"]})
        connection.execute(text("INSERT INTO dbo.notifications (location_id, user_id, title, message) VALUES (NULL, :u, N't', N'm')"),
                           {"u": a["user"]})
        legal_doc = _one(connection, "SELECT id FROM dbo.legal_documents WHERE doc_type = N'tos' AND status = N'active'")
        connection.execute(text("INSERT INTO dbo.legal_acceptances (tenant_id, user_id, document_id, doc_type, version) "
                                "SELECT :t, :u, id, doc_type, version FROM dbo.legal_documents WHERE id = :d"),
                           {"t": a["tenant"], "u": a["user"], "d": legal_doc})
    yield {"a": a, "b": b, "only_a": only_a, "shared": shared, "doc": doc, "key": key}
    _cleanup(engine, [a["tenant"], b["tenant"]])


def _cleanup(engine, tenants: list[int]) -> None:
    from app.db.maintenance import history_maintenance

    ids = ", ".join(str(int(t)) for t in tenants)
    with engine.begin() as connection, history_maintenance(connection):
        connection.execute(text(f"DELETE FROM dbo.privacy_audit_hold WHERE tenant_id IN ({ids})"))
        connection.execute(text(f"DELETE FROM dbo.privacy_requests WHERE tenant_id IN ({ids})"))
    for tenant in tenants:
        with engine.connect() as connection:
            still = connection.execute(text("SELECT purged_at FROM dbo.tenants WHERE id = :t"), {"t": tenant}).first()
        if still is not None and still[0] is None:
            purge_company(engine, tenant, 0, hold_days=1)
    with engine.begin() as connection:
        connection.execute(text(f"DELETE FROM dbo.privacy_audit_hold WHERE tenant_id IN ({ids})"))
        connection.execute(text(f"DELETE FROM dbo.candidates WHERE full_name LIKE N'{MARK}%' AND id NOT IN "
                                "(SELECT candidate_id FROM dbo.candidate_applications)"))
        connection.execute(text(f"DELETE FROM dbo.tenants WHERE id IN ({ids})"))


def _owned_counts(engine, tenant: int) -> dict[str, int]:
    counts = {}
    with engine.connect() as connection:
        for table in tenant_tables():
            if table in KEEP or connection.execute(text("SELECT OBJECT_ID(:n, N'U')"), {"n": f"dbo.{table}"}).scalar() is None:
                continue
            counts[table] = connection.execute(text(f"SELECT COUNT(*) FROM dbo.{table} a WHERE {predicate(table, 'a')}"),
                                               {"tenant": tenant}).scalar_one()
    return counts


def test_company_export_then_purge(companies):
    from app.services.privacy_export import build_company_export

    engine = _engine()
    a, b = companies["a"], companies["b"]
    key, size, summary = build_company_export(engine, a["tenant"], 999001)
    archive = zipfile.ZipFile(io.BytesIO(get_storage().get(key)))
    users = json.loads(archive.read("data/users.json"))
    assert users and all("password_hash" not in u for u in users)
    assert len(json.loads(archive.read("data/requisitions.json"))) == 1
    assert len(json.loads(archive.read("data/candidates.json"))) == 2  # incl. the shared one
    assert any(n.startswith("files/") for n in archive.namelist()) and summary["files"] == 1
    get_storage().delete(key)

    before_b = _owned_counts(engine, b["tenant"])
    report = purge_company(engine, a["tenant"], 999002, hold_days=90)

    left = {t: n for t, n in _owned_counts(engine, a["tenant"]).items() if n}
    assert left == {}, left
    assert _owned_counts(engine, b["tenant"]) == before_b
    assert report["handed_over_candidates"] == 1
    with engine.connect() as connection:
        shared = connection.execute(text("SELECT created_by_user_id, branch_id FROM dbo.candidates WHERE id = :c"),
                                    {"c": companies["shared"]}).one()
        assert (shared[0], shared[1]) == (b["user"], b["branch"])
        assert connection.execute(text("SELECT COUNT(*) FROM dbo.candidates WHERE id = :c"), {"c": companies["only_a"]}).scalar_one() == 0
        held = dict(connection.execute(text("SELECT source_table, COUNT(*) FROM dbo.privacy_audit_hold WHERE tenant_id = :t "
                                            "GROUP BY source_table"), {"t": a["tenant"]}).all())
        tomb = connection.execute(text("SELECT status, purged_at FROM dbo.tenants WHERE id = :t"), {"t": a["tenant"]}).one()
    assert held.get("audit_logs", 0) >= 1 and held.get("legal_acceptances", 0) == 1
    assert tomb[0] == "archived" and tomb[1] is not None
    assert not get_storage().exists(companies["key"])

    with engine.begin() as connection:
        connection.execute(text("UPDATE dbo.privacy_audit_hold SET hold_until = DATEADD(DAY, -1, SYSUTCDATETIME()) WHERE tenant_id = :t"),
                           {"t": a["tenant"]})
    assert release_expired_holds(engine) >= 2


def test_delete_request_needs_another_admin_and_can_be_cancelled(client, admin):
    response = client.post("/api/v1/privacy/delete-request", json={"reason": "test", "confirm": "nope"}, headers=admin["headers"])
    assert response.status_code == 422
    response = client.post("/api/v1/privacy/delete-request", json={"reason": "privacy gate test", "confirm": "DELETE"},
                           headers=admin["headers"])
    assert response.status_code == 202, response.text
    request = response.json()
    try:
        assert request["status"] == "pending_approval" and request["approval_id"]
        again = client.post("/api/v1/privacy/delete-request", json={"reason": "twice", "confirm": "DELETE"}, headers=admin["headers"])
        assert again.status_code == 409
        own = client.patch(f"/api/v1/approvals/{request['approval_id']}/decide",
                           json={"decision": "approved", "decision_user_id": admin["user_id"]}, headers=admin["headers"])
        assert own.status_code == 403, own.text
        bad_code = client.post(f"/api/v1/privacy/requests/{request['id']}/confirm", json={"code": "000000"}, headers=admin["headers"])
        assert bad_code.status_code in (400, 409)
    finally:
        cancelled = client.post(f"/api/v1/privacy/requests/{request['id']}/cancel", headers=admin["headers"])
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    listed = client.get("/api/v1/privacy/requests", headers=admin["headers"]).json()
    assert any(r["id"] == request["id"] and r["status"] == "cancelled" for r in listed)


@pytest.fixture()
def own_candidate(client, admin):
    engine = _engine()
    with engine.begin() as connection:
        branch = _one(connection, "SELECT TOP (1) id FROM dbo.branches WHERE tenant_id = :t ORDER BY id", t=admin["tenant_id"])
        company = {"tenant": admin["tenant_id"], "branch": branch, "user": admin["user_id"]}
        company["requisition"] = _one(connection, "INSERT INTO dbo.requisitions (branch_id, hiring_type, title, owner_user_id, status, "
                                      "open_positions, job_description, target_close_date) OUTPUT INSERTED.id VALUES (:b, N'internal', :t, :u, "
                                      "N'open', 1, N'privacy test', CAST(SYSUTCDATETIME() AS DATE))", b=branch, t=f"{MARK} own role", u=admin["user_id"])
        candidate = _candidate(connection, company, "erase me")
        application = _apply(connection, company, candidate)
        doc, key = _document(connection, company, candidate)
    yield {"candidate": candidate, "application": application, "key": key, "requisition": company["requisition"]}
    from app.db.maintenance import history_maintenance

    with engine.begin() as connection, history_maintenance(connection):
        connection.execute(text("DELETE FROM dbo.candidate_stage_history WHERE candidate_application_id = :a"), {"a": application})
        connection.execute(text("DELETE FROM dbo.candidate_documents WHERE candidate_id = :c"), {"c": candidate})
        connection.execute(text("DELETE FROM dbo.candidate_applications WHERE id = :a"), {"a": application})
        connection.execute(text("DELETE FROM dbo.candidates WHERE id = :c"), {"c": candidate})
        connection.execute(text("DELETE FROM dbo.requisitions WHERE id = :r"), {"r": company["requisition"]})
        connection.execute(text("DELETE FROM dbo.privacy_requests WHERE candidate_id = :c"), {"c": candidate})


def test_candidate_export_and_erase(client, admin, own_candidate):
    cid = own_candidate["candidate"]
    export = client.post(f"/api/v1/privacy/candidates/{cid}/export", headers=admin["headers"])
    assert export.status_code == 201, export.text
    assert export.json()["status"] == "completed" and export.json()["download_ready"]
    link = client.post(f"/api/v1/privacy/requests/{export.json()['id']}/download", headers=admin["headers"])
    assert link.status_code == 200, link.text
    got = client.get(link.json()["url"])
    assert got.status_code == 200 and zipfile.ZipFile(io.BytesIO(got.content)).read("data/candidate.json")

    with _engine().connect() as connection:
        code = connection.execute(text("SELECT COALESCE(candidate_code, CAST(id AS NVARCHAR(20))) FROM dbo.candidates WHERE id = :c"),
                                  {"c": cid}).scalar_one()
    wrong = client.post(f"/api/v1/privacy/candidates/{cid}/erase", json={"confirm": "nope"}, headers=admin["headers"])
    assert wrong.status_code == 422
    erased = client.post(f"/api/v1/privacy/candidates/{cid}/erase", json={"confirm": code, "reason": "candidate asked"},
                         headers=admin["headers"])
    assert erased.status_code == 200, erased.text
    assert erased.json()["status"] == "completed"
    with _engine().connect() as connection:
        row = connection.execute(text("SELECT full_name, email, phone, erased_at FROM dbo.candidates WHERE id = :c"), {"c": cid}).one()
        app_row = connection.execute(text("SELECT current_stage, stage_reason FROM dbo.candidate_applications WHERE id = :a"),
                                     {"a": own_candidate["application"]}).one()
        reasons = connection.execute(text("SELECT change_reason FROM dbo.candidate_stage_history WHERE candidate_application_id = :a"),
                                     {"a": own_candidate["application"]}).scalars().all()
        docs = connection.execute(text("SELECT COUNT(*) FROM dbo.candidate_documents WHERE candidate_id = :c"), {"c": cid}).scalar_one()
    assert row[0].startswith("Erased candidate") and row[1] is None and row[2] is None and row[3] is not None
    assert app_row[0] == "interview" and app_row[1] is None  # the stage stays; the note goes
    assert reasons == [None] and docs == 0
    assert not get_storage().exists(own_candidate["key"])
    again = client.post(f"/api/v1/privacy/candidates/{cid}/erase", json={"confirm": code}, headers=admin["headers"])
    assert again.status_code == 409


def test_shared_candidate_is_not_erased(companies):
    from app.services.candidate_erasure import CandidateShared, erase_candidate

    with pytest.raises(CandidateShared):
        erase_candidate(_engine(), companies["a"]["tenant"], companies["shared"])
