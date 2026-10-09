"""Data exports (Phase 5.3): the whole company, or one candidate.

A zip with one JSON file per table (secrets removed) plus the stored
files, written to storage under the company's prefix; a signed link is
handed out for download. Company exports include AI run logs (agent_runs)
as PRD §4.17 requires.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

from sqlalchemy import Engine, text

from app.core.file_storage import get_storage, tenant_key
from app.services.tenant_data import EXPORT_SKIP, is_secret_column, predicate, tenant_tables
from app.services.tenant_purge import _json_default

README = """RecruitOps data export
=====================
{scope}
Created: {created} (UTC)

data/<table>.json  one file per table, a list of rows (secrets such as
                   password hashes and session tokens are left out)
files/...          the stored documents (resumes etc.) as uploaded
"""


def _rows(connection, sql: str, params: dict) -> list[dict]:
    result = connection.execute(text(sql), params).mappings().all()
    return [{k: v for k, v in dict(r).items() if not is_secret_column(k)} for r in result]


def _add_files(zf: zipfile.ZipFile, documents: list[dict]) -> int:
    storage = get_storage()
    count = 0
    for doc in documents:
        key = doc.get("storage_key")
        if not key:
            continue
        try:
            content = storage.get(key)
        except Exception:  # noqa: BLE001 — a missing file is noted, not fatal
            zf.writestr(f"files/MISSING-{doc['id']}.txt", f"File for document {doc['id']} could not be read.")
            continue
        name = (doc.get("file_name") or f"document-{doc['id']}").replace("/", "_")
        zf.writestr(f"files/{doc.get('candidate_id', 'x')}/{doc['id']}-{name}", content)
        count += 1
    return count


def build_company_export(engine: Engine, tenant_id: int, request_id: int) -> tuple[str, int, dict]:
    buffer = io.BytesIO()
    summary: dict = {"tables": {}}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf, engine.connect() as connection:
        for table in tenant_tables():
            if table in EXPORT_SKIP:
                continue
            exists = connection.execute(text("SELECT OBJECT_ID(:n, N'U')"), {"n": f"dbo.{table}"}).scalar()
            if exists is None:
                continue
            rows = _rows(connection, f"SELECT a.* FROM dbo.{table} AS a WHERE {predicate(table, 'a')};", {"tenant": tenant_id})
            summary["tables"][table] = len(rows)
            zf.writestr(f"data/{table}.json", json.dumps(rows, default=_json_default, indent=1))
            if table == "candidate_documents":
                summary["files"] = _add_files(zf, rows)
        created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        zf.writestr("README.txt", README.format(scope=f"Company export (company {tenant_id}, request {request_id})", created=created))
    content = buffer.getvalue()
    key = tenant_key(tenant_id, "privacy-exports", request_id, "company-export.zip")
    get_storage().put(key, content, "application/zip")
    return key, len(content), summary


def build_candidate_export(engine: Engine, tenant_id: int, candidate_id: int, request_id: int) -> tuple[str, int, dict]:
    """One candidate as this company holds them: the profile, skills and
    documents, plus this company's applications, history, interviews."""
    params = {"tenant": tenant_id, "cid": candidate_id}
    ours = "(SELECT r.id FROM dbo.requisitions r JOIN dbo.branches b ON b.id = r.branch_id WHERE b.tenant_id = :tenant)"
    queries = {
        "candidate": "SELECT * FROM dbo.candidates WHERE id = :cid",
        "skills": "SELECT * FROM dbo.candidate_skills WHERE candidate_id = :cid",
        "documents": "SELECT * FROM dbo.candidate_documents WHERE candidate_id = :cid",
        "applications": f"SELECT * FROM dbo.candidate_applications WHERE candidate_id = :cid AND requisition_id IN {ours}",
        "stage_history": ("SELECT h.* FROM dbo.candidate_stage_history h JOIN dbo.candidate_applications ca ON ca.id = h.candidate_application_id "
                          f"WHERE ca.candidate_id = :cid AND ca.requisition_id IN {ours}"),
        "interviews": ("SELECT i.* FROM dbo.interview_rounds i JOIN dbo.candidate_applications ca ON ca.id = i.candidate_application_id "
                       f"WHERE ca.candidate_id = :cid AND ca.requisition_id IN {ours}"),
        "screening_checks": ("SELECT s.* FROM dbo.candidate_screening_checks s JOIN dbo.candidate_applications ca ON ca.id = s.candidate_application_id "
                             f"WHERE ca.candidate_id = :cid AND ca.requisition_id IN {ours}"),
    }
    buffer = io.BytesIO()
    summary: dict = {"tables": {}}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf, engine.connect() as connection:
        for name, sql in queries.items():
            rows = _rows(connection, sql, params)
            summary["tables"][name] = len(rows)
            zf.writestr(f"data/{name}.json", json.dumps(rows, default=_json_default, indent=1))
            if name == "documents":
                summary["files"] = _add_files(zf, rows)
        created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        zf.writestr("README.txt", README.format(scope=f"Candidate export (candidate {candidate_id})", created=created))
    content = buffer.getvalue()
    key = tenant_key(tenant_id, "privacy-exports", request_id, f"candidate-{candidate_id}.zip")
    get_storage().put(key, content, "application/zip")
    return key, len(content), summary
