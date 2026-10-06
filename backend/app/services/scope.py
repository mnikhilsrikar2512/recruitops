"""Company (tenant) and office (location) scoping — the single place that
decides what data a signed-in user may reach.

Model (docs/decisions-2026-10-06.md):
- A company (tenant) owns a head office and branches.
- A **company-wide** user (today: the company Admin) reaches every office of
  their own company and nothing outside it.
- Everyone else reaches their primary office only.
- Nobody reaches another company's data. There is no global "see
  everything" user in the product API.

Company-wide reach is the ``scope.company`` grant (Admin template, D-03).
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Engine, text

# SQL fragment: the ids of every office belonging to :tenant_id. Lists append
# "AND (:tenant_id IS NULL OR <office column> IN {TENANT_OFFICES_SQL})".
TENANT_OFFICES_SQL = "(SELECT tb.id FROM dbo.branches AS tb WHERE tb.tenant_id = :tenant_id)"
# Users of :tenant_id (for rows whose only tenant link is a user).
TENANT_USERS_SQL = "(SELECT tu.id FROM dbo.users AS tu WHERE tu.tenant_id = :tenant_id)"


def tenant_id_of(auth_context) -> int | None:
    return getattr(auth_context.user, "tenant_id", None)


def is_company_wide(auth_context) -> bool:
    """Company-wide reach inside the caller's own company: the scope.company
    grant (resolved by api/deps.get_current_auth_context). Contexts built by
    hand (unit tests, scripts) carry no flag and fall back to the Admin role,
    whose template holds that grant."""
    flag = getattr(auth_context, "company_wide", None)
    if flag is not None:
        return bool(flag)
    return getattr(auth_context.user, "role_code", None) == "admin"


def office_in_tenant(engine: Engine, office_id: int | None, tenant_id: int | None) -> bool:
    if office_id is None:
        return False
    if tenant_id is None:  # legacy/unit-test contexts without a tenant
        return True
    query = text("SELECT 1 FROM dbo.branches WHERE id = :office_id AND tenant_id = :tenant_id")
    with engine.connect() as connection:
        return connection.execute(query, {"office_id": office_id, "tenant_id": tenant_id}).first() is not None


def tenant_of_office(engine: Engine, office_id: int | None) -> int | None:
    if office_id is None:
        return None
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT tenant_id FROM dbo.branches WHERE id = :office_id"), {"office_id": office_id}
        ).first()
    return int(row[0]) if row and row[0] is not None else None


def can_reach_office(engine: Engine, auth_context, office_id: int | None) -> bool:
    """May this user act on data that belongs to ``office_id``?"""
    if office_id is None:
        return False
    if is_company_wide(auth_context):
        return office_in_tenant(engine, office_id, tenant_id_of(auth_context))
    return office_id == auth_context.user.location_id


def assert_office_reachable(engine: Engine, auth_context, office_id: int | None, not_found_detail: str) -> None:
    """404 (not 403) for anything outside reach, so foreign ids can't be probed."""
    if not can_reach_office(engine, auth_context, office_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)


def assert_user_in_tenant(engine: Engine, auth_context, user_id: int | None, not_found_detail: str) -> None:
    tenant_id = tenant_id_of(auth_context)
    if user_id is None or tenant_id is None:
        return
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT 1 FROM dbo.users WHERE id = :user_id AND tenant_id = :tenant_id"),
            {"user_id": user_id, "tenant_id": tenant_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)


def company_office_ids(engine: Engine, auth_context) -> frozenset[int] | None:
    """Every office id of the caller's company (None = no tenant on the
    caller, i.e. legacy/unit-test contexts — no extra restriction)."""
    tenant_id = tenant_id_of(auth_context)
    if tenant_id is None:
        return None
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id FROM dbo.branches WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id}
        ).all()
    return frozenset(int(row[0]) for row in rows)


# A candidate is a global identity record; it is "in" a company when the
# company created it, it sits on one of the company's offices, or it has an
# application on one of the company's requisitions.
CANDIDATE_IN_TENANT_SQL = (
    "(c.branch_id IN " + TENANT_OFFICES_SQL
    + " OR c.created_by_user_id IN " + TENANT_USERS_SQL
    + " OR EXISTS (SELECT 1 FROM dbo.candidate_applications AS ca_t"
    " INNER JOIN dbo.requisitions AS r_t ON r_t.id = ca_t.requisition_id"
    " WHERE ca_t.candidate_id = c.id AND r_t.branch_id IN " + TENANT_OFFICES_SQL + "))"
)


def candidate_in_tenant(engine: Engine, candidate_id: int, tenant_id: int | None) -> bool:
    if tenant_id is None:
        return True
    query = text(f"SELECT 1 FROM dbo.candidates AS c WHERE c.id = :candidate_id AND {CANDIDATE_IN_TENANT_SQL}")
    with engine.connect() as connection:
        return connection.execute(query, {"candidate_id": candidate_id, "tenant_id": tenant_id}).first() is not None


def assert_role_usable(engine: Engine, auth_context, role_id: int | None, not_found_detail: str = "Role was not found") -> None:
    """A company may assign its own roles and shared system roles
    (tenant_id NULL), never another company's."""
    tenant_id = tenant_id_of(auth_context)
    if role_id is None or tenant_id is None:
        return
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT 1 FROM dbo.roles WHERE id = :role_id AND (tenant_id IS NULL OR tenant_id = :tenant_id)"),
            {"role_id": role_id, "tenant_id": tenant_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)


def role_is_system(engine: Engine, role_id: int) -> bool:
    with engine.connect() as connection:
        row = connection.execute(text("SELECT tenant_id FROM dbo.roles WHERE id = :role_id"), {"role_id": role_id}).first()
    return row is not None and row[0] is None


# ---- payload references -------------------------------------------------
# Every id a write payload carries must point inside the caller's company;
# otherwise a company could attach another company's client, user or
# requisition to its own records. Unknown/foreign ids answer 404.
_REF_SQL = {
    "office": "SELECT 1 FROM dbo.branches WHERE id = :id AND tenant_id = :tenant_id",
    "user": "SELECT 1 FROM dbo.users WHERE id = :id AND tenant_id = :tenant_id",
    "client": "SELECT 1 FROM dbo.client_companies AS c WHERE c.id = :id AND c.branch_id IN " + TENANT_OFFICES_SQL,
    "requisition": "SELECT 1 FROM dbo.requisitions AS r WHERE r.id = :id AND r.branch_id IN " + TENANT_OFFICES_SQL,
    "candidate": "SELECT 1 FROM dbo.candidates AS c WHERE c.id = :id AND " + CANDIDATE_IN_TENANT_SQL,
    "contact": "SELECT 1 FROM dbo.client_contacts AS cc INNER JOIN dbo.client_companies AS c"
    " ON c.id = cc.client_company_id WHERE cc.id = :id AND c.branch_id IN " + TENANT_OFFICES_SQL,
}
_FIELD_KIND = {
    "location_id": "office",
    "new_primary_location_id": "office",
    "client_id": "client",
    "end_client_id": "client",
    "requisition_id": "requisition",
    "matched_candidate_id": "candidate",
    "primary_contact_id": "contact",
    "secondary_contact_id": "contact",
    "client_contact_id": "contact",
}


def _kind_of(field: str) -> str | None:
    if field in _FIELD_KIND:
        return _FIELD_KIND[field]
    if field.endswith("_user_id"):
        return "user"
    return None


def assert_payload_refs_in_company(engine: Engine, auth_context, payload) -> None:
    tenant_id = tenant_id_of(auth_context)
    if tenant_id is None or payload is None:
        return
    fields = getattr(type(payload), "model_fields", {})
    checks = []
    for name in fields:
        kind = _kind_of(name)
        value = getattr(payload, name, None)
        if kind and isinstance(value, int):
            checks.append((name, kind, value))
    if not checks:
        return
    with engine.connect() as connection:
        for name, kind, value in checks:
            if connection.execute(text(_REF_SQL[kind]), {"id": value, "tenant_id": tenant_id}).first() is None:
                label = name.removesuffix("_id").replace("_", " ").capitalize()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} was not found")
