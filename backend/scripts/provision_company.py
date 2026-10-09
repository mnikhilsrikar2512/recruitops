"""Ops: create a company for a customer who isn't signing up themselves
(Phase 5.2). Runbook: docs/runbooks/provision-company.md.

    cd backend
    .venv/bin/python scripts/provision_company.py --company "Acme Staffing" \
        --admin-name "Priya Rao" --admin-email priya@acme.example --city Hyderabad \
        --dpa-signed-by "Priya Rao (Director), signed DPA dated 2026-10-09"

Creates the company (pending), head office and first Admin, records the DPA
the customer signed offline on the company's behalf, and prints a one-time
password setup link (24 h). The admin sets a password, signs in, accepts the
Terms and Privacy Policy, and sets up two-step verification; then:

    .venv/bin/python scripts/activate_company.py --slug <slug printed below>
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--company")
    ap.add_argument("--admin-name")
    ap.add_argument("--admin-email")
    ap.add_argument("--city", default=None)
    ap.add_argument("--dpa-signed-by", help="who signed the DPA offline, and the document reference")
    ap.add_argument("--reissue-link", metavar="EMAIL", help="new setup link for the first admin of a still-pending company")
    opts = ap.parse_args()
    if opts.reissue_link:
        return reissue(opts.reissue_link.strip().lower())
    if not (opts.company and opts.admin_name and opts.admin_email and opts.dpa_signed_by):
        ap.error("--company, --admin-name, --admin-email and --dpa-signed-by are required")

    from sqlalchemy import text

    from app.core.config import settings
    from app.core.security import generate_session_token, hash_password, hash_session_token, random_secret
    from app.db.session import create_db_engine
    from app.repositories.legal import find_active_document, record_acceptance
    from app.repositories.users import create_password_reset_token
    from app.services.provisioning import EmailTaken, provision_company

    engine = create_db_engine()
    try:
        created = provision_company(
            engine, company_name=opts.company.strip(), admin_name=opts.admin_name.strip(),
            admin_email=opts.admin_email.strip().lower(), city=opts.city, password_hash=hash_password(random_secret(24)),
            password_ready=False, onboarding="ops", email_verified=False,
        )
    except EmailTaken:
        raise SystemExit(f"✗ {opts.admin_email} already has an account") from None
    dpa = find_active_document(engine, "dpa")
    if dpa:
        record_acceptance(engine, tenant_id=created["tenant_id"], user_id=created["admin_id"], document=dpa,
                          on_behalf_of_company=True, ip_address=None,
                          user_agent=f"ops-provisioning: {opts.dpa_signed_by}"[:400])
    token = generate_session_token()
    create_password_reset_token(engine, user_id=created["admin_id"], token_hash=hash_session_token(token),
                                purpose="admin-reset", issued_by_user_id=None,
                                expires_at=datetime.now(timezone.utc) + timedelta(hours=24))
    with engine.connect() as connection:
        slug = connection.execute(text("SELECT slug FROM dbo.tenants WHERE id = :t"), {"t": created["tenant_id"]}).scalar_one()
    print(f"✓ company {opts.company!r} created (id {created['tenant_id']}, slug {slug}, status pending)")
    print(f"  admin: {opts.admin_email} — send them this one-time link (24 h):")
    print(f"  {settings.frontend_base_url}/pages/password-setup.html?token={token}")
    print(f"  after they set up two-step verification: scripts/activate_company.py --slug {slug}")


def reissue(email: str) -> None:
    from sqlalchemy import text

    from app.core.config import settings
    from app.core.security import generate_session_token, hash_session_token
    from app.db.session import create_db_engine
    from app.repositories.users import create_password_reset_token

    engine = create_db_engine()
    with engine.begin() as connection:
        row = connection.execute(text(
            "SELECT u.id FROM dbo.users u JOIN dbo.tenants t ON t.id = u.tenant_id WHERE u.email = :e AND t.status = N'pending'"),
            {"e": email}).first()
        if row is None:
            raise SystemExit(f"✗ no pending company admin with email {email}")
        connection.execute(text("UPDATE dbo.password_reset_tokens SET used_at = SYSUTCDATETIME() "
                                "WHERE user_id = :u AND purpose = N'admin-reset' AND used_at IS NULL"), {"u": row[0]})
    token = generate_session_token()
    create_password_reset_token(engine, user_id=int(row[0]), token_hash=hash_session_token(token), purpose="admin-reset",
                                issued_by_user_id=None, expires_at=datetime.now(timezone.utc) + timedelta(hours=24))
    print(f"✓ new one-time link (24 h): {settings.frontend_base_url}/pages/password-setup.html?token={token}")


if __name__ == "__main__":
    main()
