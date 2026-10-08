"""Audit log reads (Phase 5.4). Writes stay in app/repositories/audit.py."""
from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import Engine, text

# A row belongs to a company through its office (branch_id) or, when it
# has no office, through the user who acted.
_IN_TENANT = """
    (a.branch_id IN (SELECT b.id FROM dbo.branches AS b WHERE b.tenant_id = :tenant)
     OR (a.branch_id IS NULL AND a.actor_user_id IN (SELECT u.id FROM dbo.users AS u WHERE u.tenant_id = :tenant)))
"""


def _decode(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def list_audit_logs(
    engine: Engine,
    *,
    tenant_id: int,
    actor_user_id: int | None,
    entity_type: str | None,
    entity_id: int | None,
    action_type: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    params = {
        "tenant": tenant_id,
        "actor": actor_user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": f"%{action_type}%" if action_type else None,
        "date_from": date_from,
        "date_to": (date_to + timedelta(days=1)) if date_to else None,
        "offset": (page - 1) * page_size,
        "limit": page_size,
    }
    where = f"""
        WHERE {_IN_TENANT}
          AND (:actor IS NULL OR a.actor_user_id = :actor)
          AND (:entity_type IS NULL OR a.entity_type = :entity_type)
          AND (:entity_id IS NULL OR a.entity_id = :entity_id)
          AND (:action IS NULL OR a.action_type LIKE :action)
          AND (:date_from IS NULL OR a.created_at >= :date_from)
          AND (:date_to IS NULL OR a.created_at < :date_to)
    """
    with engine.connect() as connection:
        total = connection.execute(text(f"SELECT COUNT(*) FROM dbo.audit_logs AS a {where};"), params).scalar_one()
        rows = connection.execute(
            text(
                f"""
                SELECT a.id, a.actor_user_id, u.full_name AS actor_name, u.email AS actor_email,
                       a.branch_id AS location_id, br.name AS location_name,
                       a.entity_type, a.entity_id, a.action_type, a.created_at,
                       a.ip_address
                FROM dbo.audit_logs AS a
                LEFT JOIN dbo.users AS u ON u.id = a.actor_user_id
                LEFT JOIN dbo.branches AS br ON br.id = a.branch_id
                {where}
                ORDER BY a.created_at DESC, a.id DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
                """
            ),
            params,
        ).mappings().all()
    return [dict(row) for row in rows], int(total)


def find_audit_log(engine: Engine, tenant_id: int, audit_id: int) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT a.id, a.actor_user_id, u.full_name AS actor_name, u.email AS actor_email,
                       a.branch_id AS location_id, br.name AS location_name,
                       a.entity_type, a.entity_id, a.action_type, a.created_at,
                       a.ip_address, a.user_agent, a.old_values_json, a.new_values_json
                FROM dbo.audit_logs AS a
                LEFT JOIN dbo.users AS u ON u.id = a.actor_user_id
                LEFT JOIN dbo.branches AS br ON br.id = a.branch_id
                WHERE a.id = :id AND {_IN_TENANT};
                """
            ),
            {"id": audit_id, "tenant": tenant_id},
        ).mappings().first()
    if row is None:
        return None
    record = dict(row)
    record["old_values"] = _decode(record.pop("old_values_json"))
    record["new_values"] = _decode(record.pop("new_values_json"))
    return record


def list_audit_facets(engine: Engine, tenant_id: int) -> dict:
    """Distinct entity and action types seen in this company (filter menus)."""
    with engine.connect() as connection:
        entities = connection.execute(
            text(f"SELECT DISTINCT a.entity_type FROM dbo.audit_logs AS a WHERE {_IN_TENANT} ORDER BY a.entity_type;"),
            {"tenant": tenant_id},
        ).scalars().all()
        actions = connection.execute(
            text(f"SELECT DISTINCT a.action_type FROM dbo.audit_logs AS a WHERE {_IN_TENANT} ORDER BY a.action_type;"),
            {"tenant": tenant_id},
        ).scalars().all()
    return {"entity_types": list(entities), "action_types": list(actions)}
