"""Ops break-glass (Phase 3.6): remove a user's authenticator when they have
lost both the device and their recovery codes. Signs the user out everywhere
and writes an audit row. Identity must be verified out of band first.

    cd backend && .venv/bin/python scripts/mfa_break_glass.py --email someone@company.com \\
        --reason "lost phone, identity verified by video call (ticket 123)" --operator-email ops@yourco.com
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.db.session import create_db_engine  # noqa: E402
from app.repositories.audit import insert_audit_log  # noqa: E402
from app.repositories.auth import revoke_user_sessions  # noqa: E402
from app.repositories.mfa import remove_mfa  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--operator-email", required=True, help="an existing user who performs the reset")
    opts = ap.parse_args()
    if len(opts.reason.strip()) < 10:
        raise SystemExit("give a real reason (at least 10 characters)")
    engine = create_db_engine()
    with engine.connect() as connection:
        user = connection.execute(text("SELECT id, location_id FROM dbo.users WHERE email = :e"), {"e": opts.email}).first()
        operator = connection.execute(text("SELECT id FROM dbo.users WHERE email = :e"), {"e": opts.operator_email}).scalar()
    if user is None or operator is None:
        raise SystemExit("user or operator not found")
    remove_mfa(engine, int(user[0]))
    revoked = revoke_user_sessions(engine, int(user[0]), "mfa-break-glass")
    insert_audit_log(engine, actor_user_id=int(operator), location_id=user[1], entity_type="user", entity_id=int(user[0]),
                     action_type="mfa_break_glass", new_values={"reason": opts.reason.strip()})
    print(f"✓ two-step verification removed for {opts.email}; {revoked} sessions ended. They must set it up again at next sign-in.")


if __name__ == "__main__":
    main()
