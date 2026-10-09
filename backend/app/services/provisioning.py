"""Create a company from nothing (Phase 5.2). Used by self-serve signup and
by ops (scripts/provision_company.py), so both paths build the same thing:

- dbo.tenants (status 'pending' until activation), onboarding source
- company profile (company_entities, primary)
- head office: dbo.branches + mirrored dbo.locations row with the SAME id
  (the codebase treats branch id == location id)
- first Admin: the shared system Admin role (D-03), primary office role
- legal acceptance records (see callers)
- an audit row 'company.provisioned'
Activation (pending → active) is separate: app/services/tenants.activate_tenant,
which refuses until every active Admin has two-step verification (D-09).
"""
from __future__ import annotations

import re
import secrets

from sqlalchemy import Connection, Engine, text


class EmailTaken(Exception):
    pass


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "company"
    return f"{base}-{secrets.token_hex(3)}"


def email_taken(connection: Connection, email: str) -> bool:
    return connection.execute(text("SELECT 1 FROM dbo.users WHERE email = :e"), {"e": email}).first() is not None


def provision_company(
    engine: Engine,
    *,
    company_name: str,
    admin_name: str,
    admin_email: str,
    city: str | None,
    password_hash: str,
    password_ready: bool,
    onboarding: str,
    email_verified: bool,
) -> dict:
    """One transaction. password_ready=False → the admin must set a password
    through a setup link (ops path); the caller issues the token."""
    with engine.begin() as connection:
        if email_taken(connection, admin_email):
            raise EmailTaken(admin_email)
        tenant_id = int(connection.execute(text(
            "INSERT INTO dbo.tenants (slug, display_name, status, onboarding) OUTPUT INSERTED.id "
            "VALUES (:slug, :name, N'pending', :onboarding);"),
            {"slug": _slug(company_name), "name": company_name, "onboarding": onboarding}).scalar_one())
        office_code = f"HO{tenant_id}"
        branch_id = int(connection.execute(text(
            "INSERT INTO dbo.branches (name, code, location, status, offers_enabled, tenant_id) OUTPUT INSERTED.id "
            "VALUES (N'Head Office', :code, :city, N'active', 1, :t);"),
            {"code": office_code, "city": city or "Head Office", "t": tenant_id}).scalar_one())
        connection.execute(text(
            """
            IF NOT EXISTS (SELECT 1 FROM dbo.locations WHERE id = :id)
            BEGIN
                SET IDENTITY_INSERT dbo.locations ON;
                INSERT INTO dbo.locations (id, name, code, location, city, status, tenant_id)
                VALUES (:id, N'Head Office', :code, :city, :city, N'active', :t);
                SET IDENTITY_INSERT dbo.locations OFF;
            END
            """), {"id": branch_id, "code": office_code, "city": city or "Head Office", "t": tenant_id})
        connection.execute(text(
            "INSERT INTO dbo.company_entities (display_name, legal_name, company_code, hq_city, support_email, is_primary, status, tenant_id) "
            "VALUES (:name, :name, :code, :city, :email, 1, N'active', :t);"),
            {"name": company_name, "code": f"C{tenant_id}", "city": city, "email": admin_email, "t": tenant_id})
        role_id = int(connection.execute(text(
            "SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")).scalar_one())
        admin_id = int(connection.execute(text(
            """
            INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status,
                                   force_password_change_on_first_login, status, default_role_id, hierarchy_level,
                                   location_id, tenant_id, email_verified_at)
            OUTPUT INSERTED.id
            VALUES (:name, :email, :code, :hash, :setup, :force, N'active', :role, N'L5', :office, :t,
                    CASE WHEN :verified = 1 THEN SYSUTCDATETIME() ELSE NULL END);
            """),
            {"name": admin_name, "email": admin_email, "code": f"ADMIN-{tenant_id}", "hash": password_hash,
             "setup": "active" if password_ready else "reset-required", "force": 0 if password_ready else 1,
             "role": role_id, "office": branch_id, "t": tenant_id, "verified": 1 if email_verified else 0}).scalar_one())
        connection.execute(text(
            "INSERT INTO dbo.user_branch_roles (user_id, branch_id, role_id, is_primary, status, start_date) "
            "VALUES (:u, :b, :r, 1, N'active', CAST(SYSUTCDATETIME() AS DATE));"),
            {"u": admin_id, "b": branch_id, "r": role_id})
        connection.execute(text(
            "INSERT INTO dbo.audit_logs (actor_user_id, branch_id, entity_type, entity_id, action_type, new_values_json) "
            "VALUES (:u, :b, N'tenant', :t, N'company.provisioned', :j);"),
            {"u": admin_id, "b": branch_id, "t": tenant_id, "j": f'{{"onboarding": "{onboarding}"}}'})
    return {"tenant_id": tenant_id, "branch_id": branch_id, "admin_id": admin_id}


def record_signup_acceptances(engine: Engine, *, tenant_id: int, user_id: int, accepted: dict[str, int],
                              ip: str | None, user_agent: str | None) -> None:
    """Self-serve: the new admin accepts Terms and Privacy for themselves
    and the DPA for the company, at the versions shown on the form."""
    from app.repositories.legal import list_active_documents, record_acceptance

    for doc in list_active_documents(engine):
        record_acceptance(engine, tenant_id=tenant_id, user_id=user_id, document=doc,
                          on_behalf_of_company=doc["doc_type"] == "dpa", ip_address=ip, user_agent=user_agent)
