"""Backfill the system Admin role's grants to the current ADMIN_PERMISSION_CODES.

Usage:
    .venv/bin/python scripts/008_sync_admin_permissions.py

Why this exists: app/core/rbac.py's ADMIN_PERMISSION_CODES is the single
source of truth for what the Admin role (roles.tenant_id IS NULL, code
'admin') is allowed to do. Every *fresh* database gets that list seeded
in full by scripts/seed_ci.py. But a database that already existed when a
code was ADDED to ADMIN_PERMISSION_CODES never automatically picks it up --
role_permissions is data, not something a code change touches -- so the
Admin role silently falls behind and every route gated on the new code
starts answering 403 for an account that is supposed to have full access.

This script re-applies exactly the backfill half of scripts/seed_ci.py
(the permission-catalog + role_permissions loop, byte-for-byte the same
SQL) on its own, against ANY existing database -- local dev included --
without seeding any of seed_ci.py's CI-only fixture data (its ci.admin@...
user, demo client, etc.). It is idempotent: every insert is IF NOT EXISTS /
NOT EXISTS guarded, so running it twice, or against a database that's
already in sync, changes nothing and is safe.

Run this any time ADMIN_PERMISSION_CODES gains a new code, against every
database that existed before that change (local dev, staging, ...).
"""
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.core.rbac import ADMIN_PERMISSION_CODES, split_code  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402


def main() -> None:
    engine = create_db_engine()
    with engine.begin() as connection:
        role_id = connection.execute(
            text("SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")
        ).scalar_one_or_none()
        if role_id is None:
            raise SystemExit(
                "No system Admin role (code='admin', tenant_id IS NULL) found -- "
                "run scripts/seed_ci.py (or provision a company) first."
            )

        before = connection.execute(
            text("SELECT COUNT(*) FROM dbo.role_permissions WHERE role_id = :role_id"),
            {"role_id": role_id},
        ).scalar_one()

        for code in ADMIN_PERMISSION_CODES:
            module_name, action_name = split_code(code)
            connection.execute(
                text(
                    """
                    IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = :code)
                        INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
                        VALUES (:code, :module, :action, :code, 0);
                    INSERT INTO dbo.role_permissions (role_id, permission_id)
                    SELECT :role_id, p.id FROM dbo.permissions AS p
                    WHERE p.code = :code
                      AND NOT EXISTS (SELECT 1 FROM dbo.role_permissions AS rp
                                      WHERE rp.role_id = :role_id AND rp.permission_id = p.id);
                    """
                ),
                {"code": code, "module": module_name, "action": action_name, "role_id": role_id},
            )

        after = connection.execute(
            text("SELECT COUNT(*) FROM dbo.role_permissions WHERE role_id = :role_id"),
            {"role_id": role_id},
        ).scalar_one()

    print(
        f"Admin role (id={role_id}): added {after - before} new grant(s). "
        f"Now holds {after}/{len(ADMIN_PERMISSION_CODES)} ADMIN_PERMISSION_CODES."
    )
    if after < len(ADMIN_PERMISSION_CODES):
        print(
            "NOTE: fewer grants than ADMIN_PERMISSION_CODES -- a permission code lookup "
            "may have failed above, or this role somehow holds duplicate rows."
        )


if __name__ == "__main__":
    main()
