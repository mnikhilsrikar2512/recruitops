"""Phase 4 exit gate — an .exe renamed .pdf is rejected; an EICAR file is
quarantined and never linkable; clean uploads are stored under the
company's prefix and downloaded only through a short-lived signed link."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.malware import EICAR
from tests.test_metric_buckets_db import _cleanup, _engine, _seed_application, admin, client  # noqa: F401
from tests.test_file_pipeline import EXE, PDF


@pytest.fixture()
def candidate(client, admin):
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    application_id = _seed_application(engine, admin, stage="interview", suffix="upload")
    with engine.connect() as connection:
        candidate_id = int(connection.execute(
            text("SELECT candidate_id FROM dbo.candidate_applications WHERE id = :a"), {"a": application_id}).scalar_one())
    yield candidate_id
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM dbo.upload_idempotency WHERE entity_type = N'candidate' AND entity_id = :c"), {"c": candidate_id})
        connection.execute(text("DELETE FROM dbo.upload_quarantine WHERE entity_type = N'candidate' AND entity_id = :c"), {"c": candidate_id})
        connection.execute(text("DELETE FROM dbo.candidate_documents WHERE candidate_id = :c"), {"c": candidate_id})
    _cleanup(engine, admin["tenant_id"])


def _upload(client, admin, candidate_id, name, content, key=None):
    headers = dict(admin["headers"])
    if key:
        headers["Idempotency-Key"] = key
    return client.post(f"/api/v1/candidates/{candidate_id}/upload?document_type=resume",
                       files={"file": (name, content, "application/pdf")}, headers=headers)


def test_renamed_exe_is_rejected(client, admin, candidate):
    response = _upload(client, admin, candidate, "resume.pdf", EXE)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_eicar_is_quarantined_and_never_linked(client, admin, candidate):
    response = _upload(client, admin, candidate, "resume.pdf", PDF + b"\n" + EICAR)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "MALWARE_DETECTED"
    with _engine().connect() as connection:
        documents = connection.execute(text("SELECT COUNT(*) FROM dbo.candidate_documents WHERE candidate_id = :c"),
                                       {"c": candidate}).scalar_one()
        quarantined = connection.execute(text(
            "SELECT storage_key FROM dbo.upload_quarantine WHERE entity_type = N'candidate' AND entity_id = :c"),
            {"c": candidate}).scalars().all()
    assert documents == 0, "an infected upload must never become a document"
    assert len(quarantined) == 1 and quarantined[0].startswith(f"quarantine/tenant_{admin['tenant_id']}/")


def test_clean_upload_is_linked_only_through_a_signed_link(client, admin, candidate):
    first = _upload(client, admin, candidate, "cv.pdf", PDF, key="retry-123")
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["scan_status"] == "clean" and body["content_type"] == "application/pdf"
    assert body["file_path"].startswith(f"tenant_{admin['tenant_id']}/candidates/{candidate}/")

    again = _upload(client, admin, candidate, "cv.pdf", PDF, key="retry-123")
    assert again.status_code == 201 and again.json()["id"] == body["id"], "same Idempotency-Key -> same document"

    link = client.get(f"/api/v1/candidates/{candidate}/documents/{body['id']}/link", headers=admin["headers"])
    assert link.status_code == 200, link.text
    url = link.json()["url"]
    downloaded = client.get(url)
    assert downloaded.status_code == 200 and downloaded.content == PDF
    assert "attachment" in downloaded.headers["content-disposition"]

    # The raw storage path is not reachable, and a forged link is refused.
    assert client.get(f"/api/v1/files/{body['file_path']}", headers=admin["headers"]).status_code == 404
    assert client.get(url[:-3] + "xyz").status_code == 403
