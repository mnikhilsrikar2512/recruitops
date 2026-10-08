"""Every row a company owns, found from app/core/tenancy.py (Phase 5.3).

Used by the company export (which rows to copy) and the company purge
(which rows to delete). The tenancy map is already enforced complete by
tests/test_tenancy_coverage.py, so a new table is covered here as soon as
it gets its tenancy line.
"""
from __future__ import annotations

import re

from app.core.tenancy import TABLE_TENANCY
from app.services.scope import CANDIDATE_IN_TENANT_SQL

# Rows of these tables are never exported (secrets, sessions) …
EXPORT_SKIP = {
    "user_sessions", "user_refresh_tokens", "user_mfa", "user_mfa_recovery_codes",
    "password_reset_tokens", "user_invitations", "upload_idempotency", "privacy_audit_hold",
}
# … and columns that look like secrets are dropped from what is exported.
SECRET_COLUMN_HINTS = ("password", "secret", "token", "_hash", "otp")

# A candidate is a global identity record. "Ours" for export = the company
# can see it; "ours" for purge = only this company uses it (shared ones are
# handed over to the other company first, see tenant_purge).
CANDIDATE_USED_ELSEWHERE_SQL = (
    "EXISTS (SELECT 1 FROM dbo.candidate_applications AS ox"
    " INNER JOIN dbo.requisitions AS orq ON orq.id = ox.requisition_id"
    " INNER JOIN dbo.branches AS ob ON ob.id = orq.branch_id"
    " WHERE ox.candidate_id = {a}.id AND ob.tenant_id <> :tenant)"
)


def tenant_tables() -> list[str]:
    return sorted(t for t, rule in TABLE_TENANCY.items() if not rule.startswith("shared:"))


def predicate(table: str, alias: str, *, purpose: str = "export", depth: int = 0) -> str:
    """SQL condition: row `alias` of `table` belongs to company :tenant."""
    if depth > 6:
        raise ValueError(f"tenancy chain too deep at {table}")
    if table == "candidates":
        mine = re.sub(r"\bc\.", f"{alias}.", CANDIDATE_IN_TENANT_SQL).replace(":tenant_id", ":tenant")
        if purpose == "purge":
            return f"({mine} AND NOT {CANDIDATE_USED_ELSEWHERE_SQL.format(a=alias)})"
        return mine
    rule = TABLE_TENANCY[table]
    kind, _, rest = rule.partition(":")
    if kind == "tenant":
        return f"{alias}.tenant_id = :tenant"
    if kind == "office":
        return f"{alias}.{rest} IN (SELECT ob{depth}.id FROM dbo.branches AS ob{depth} WHERE ob{depth}.tenant_id = :tenant)"
    if kind == "user":
        return f"{alias}.{rest} IN (SELECT ou{depth}.id FROM dbo.users AS ou{depth} WHERE ou{depth}.tenant_id = :tenant)"
    if kind == "parent":
        column, _, parent = rest.partition("->")
        inner = f"p{depth}"
        return (f"{alias}.{column} IN (SELECT {inner}.id FROM dbo.{parent} AS {inner} WHERE "
                f"{predicate(parent, inner, purpose=purpose, depth=depth + 1)})")
    raise ValueError(f"{table}: no company rule ({rule})")


def is_secret_column(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in SECRET_COLUMN_HINTS)
