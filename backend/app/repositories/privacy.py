"""Privacy requests (Phase 5.3, scripts/027_privacy.sql)."""
from __future__ import annotations

import json

from sqlalchemy import Engine, text

COLUMNS = """
    id, tenant_id, request_type, candidate_id, status, reason, requested_by_user_id, requested_by_name,
    requested_at, approval_id, approved_by_user_id, approved_at, approval_method, execute_after,
    cancelled_by_user_id, cancelled_at, started_at, completed_at, result_storage_key, result_bytes,
    result_expires_at, summary_json, error
"""
OPEN_STATUSES = ("pending_approval", "scheduled", "processing")


def _map(row) -> dict:
    record = dict(row)
    summary = record.pop("summary_json", None)
    try:
        record["summary"] = json.loads(summary) if summary else None
    except ValueError:
        record["summary"] = None
    return record


def create_request(engine: Engine, **fields) -> int:
    names = ", ".join(fields)
    values = ", ".join(f":{name}" for name in fields)
    with engine.begin() as connection:
        return int(connection.execute(
            text(f"INSERT INTO dbo.privacy_requests ({names}) OUTPUT INSERTED.id VALUES ({values});"), fields
        ).scalar_one())


def update_request(engine: Engine, request_id: int, **fields) -> None:
    if "summary" in fields:
        fields["summary_json"] = json.dumps(fields.pop("summary"), default=str)
    assignments = ", ".join(f"{name} = :{name}" for name in fields)
    with engine.begin() as connection:
        connection.execute(text(f"UPDATE dbo.privacy_requests SET {assignments} WHERE id = :id;"), {**fields, "id": request_id})


def find_request(engine: Engine, request_id: int) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(text(f"SELECT {COLUMNS} FROM dbo.privacy_requests WHERE id = :id;"), {"id": request_id}).mappings().first()
    return _map(row) if row else None


def list_requests(engine: Engine, tenant_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(text(
            f"SELECT TOP (200) {COLUMNS} FROM dbo.privacy_requests WHERE tenant_id = :t ORDER BY requested_at DESC, id DESC;"),
            {"t": tenant_id}).mappings().all()
    return [_map(r) for r in rows]


def open_company_delete(engine: Engine, tenant_id: int) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(text(
            f"SELECT TOP (1) {COLUMNS} FROM dbo.privacy_requests WHERE tenant_id = :t AND request_type = N'company_delete' "
            "AND status IN (N'pending_approval', N'scheduled', N'processing') ORDER BY id DESC;"), {"t": tenant_id}).mappings().first()
    return _map(row) if row else None


def due_company_deletes(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(text(
            f"SELECT {COLUMNS} FROM dbo.privacy_requests WHERE request_type = N'company_delete' AND status = N'scheduled' "
            "AND execute_after <= SYSUTCDATETIME() ORDER BY execute_after;")).mappings().all()
    return [_map(r) for r in rows]


def expired_exports(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(text(
            f"SELECT {COLUMNS} FROM dbo.privacy_requests WHERE result_storage_key IS NOT NULL "
            "AND result_expires_at <= SYSUTCDATETIME();")).mappings().all()
    return [_map(r) for r in rows]


def other_privacy_admins(engine: Engine, tenant_id: int, user_id: int) -> list[int]:
    """Active users of the company, other than user_id, who hold
    privacy_request.write (directly or through a role)."""
    from app.repositories.auth import list_resolved_permissions

    with engine.connect() as connection:
        ids = connection.execute(text(
            "SELECT id FROM dbo.users WHERE tenant_id = :t AND status = N'active' AND id <> :u;"),
            {"t": tenant_id, "u": user_id}).scalars().all()
    return [int(i) for i in ids if "privacy_request.write" in set(list_resolved_permissions(engine, int(i)))]
