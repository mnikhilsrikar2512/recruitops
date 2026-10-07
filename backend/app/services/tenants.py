"""Company (tenant) lifecycle for platform operations (Phase 3.6 / 5).

A company may only become ``active`` once every one of its active Admins has
confirmed two-step verification (D-09). Used by ops provisioning
(scripts/activate_company.py) and, later, by self-serve signup (Phase 5).
"""
from __future__ import annotations

from sqlalchemy import Engine, text

from app.repositories.mfa import admins_without_mfa


class ActivationBlocked(Exception):
    def __init__(self, emails: list[str]) -> None:
        self.emails = emails
        super().__init__("Admins without two-step verification: " + ", ".join(emails))


def activate_tenant(engine: Engine, tenant_id: int) -> None:
    missing = admins_without_mfa(engine, tenant_id)
    if missing:
        raise ActivationBlocked(missing)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE dbo.tenants SET status = N'active', updated_at = SYSUTCDATETIME() WHERE id = :t"),
            {"t": tenant_id},
        )
