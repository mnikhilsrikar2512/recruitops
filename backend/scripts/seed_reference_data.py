"""Reference data every environment needs (Phase 6.2): the permission
catalog and the shared Admin system role (D-03). Never companies, users or
demo records. Idempotent; ``scripts/migrate.py`` runs it after migrations
on every deploy.

    cd backend && .venv/bin/python scripts/seed_reference_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def seed_reference_data(cursor) -> dict[str, int]:
    """``cursor`` is an autocommit pyodbc cursor on the target database."""
    from app.core.permission_catalog import catalog
    from app.core.rbac import ADMIN_PERMISSION_CODES

    rows = catalog()
    before = cursor.execute("SELECT COUNT(*) FROM dbo.permissions").fetchone()[0]
    for code, module, action in rows:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = ?) "
            "INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive) "
            "VALUES (?, ?, ?, ?, 0);",
            code, code, module, action, code)
    after = cursor.execute("SELECT COUNT(*) FROM dbo.permissions").fetchone()[0]

    # The shared Admin template: tenant_id NULL makes it a read-only system
    # role every company's first admin is given (app/services/provisioning.py).
    cursor.execute(
        "IF NOT EXISTS (SELECT 1 FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL) "
        "INSERT INTO dbo.roles (name, code, description, is_system_role, status) "
        "VALUES (N'Administrator', N'admin', N'Company control plane (users, offices, roles, settings)', 1, N'active');")
    role_id = cursor.execute(
        "SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL").fetchone()[0]

    # Exactly the Admin codes, like 011_admin_seed.sql: add missing, remove extras.
    codes = list(ADMIN_PERMISSION_CODES)
    marks = ", ".join("?" for _ in codes)
    cursor.execute(
        "INSERT INTO dbo.role_permissions (role_id, permission_id) "
        f"SELECT ?, p.id FROM dbo.permissions p WHERE p.code IN ({marks}) "
        "AND NOT EXISTS (SELECT 1 FROM dbo.role_permissions rp WHERE rp.role_id = ? AND rp.permission_id = p.id);",
        role_id, *codes, role_id)
    cursor.execute(
        "DELETE rp FROM dbo.role_permissions rp JOIN dbo.permissions p ON p.id = rp.permission_id "
        f"WHERE rp.role_id = ? AND p.code NOT IN ({marks});",
        role_id, *codes)
    grants = cursor.execute("SELECT COUNT(*) FROM dbo.role_permissions WHERE role_id = ?", role_id).fetchone()[0]
    if grants != len(set(codes)):
        raise SystemExit(f"✗ Admin role holds {grants} grants, expected {len(set(codes))}")
    return {"permissions_added": after - before, "permissions_total": after, "admin_grants": grants}


def main() -> None:
    import pyodbc

    from app.core.config import settings
    from app.db.sql_runner import build_pyodbc_connection_string

    connection = pyodbc.connect(build_pyodbc_connection_string(settings.db_name), autocommit=True)
    try:
        counts = seed_reference_data(connection.cursor())
    finally:
        connection.close()
    print(f"✓ {counts['permissions_added']} permissions added ({counts['permissions_total']} total); "
          f"Admin role holds {counts['admin_grants']} grants")


if __name__ == "__main__":
    main()
