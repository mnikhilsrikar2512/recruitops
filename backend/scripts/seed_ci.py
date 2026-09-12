"""Minimal seed for a fresh (CI) database: permissions, admin role + user, one location.

Usage:
    .venv/bin/python scripts/seed_ci.py

Idempotent — safe to run multiple times. The admin user gets password "admin123",
matching scripts/seed_passwords.py.
"""

from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402

ADMIN_PASSWORD = "admin123"

# (code, module, action) — codes mirror the live permission catalog
PERMISSIONS = [
    ("approval.decide", "approval", "decide"),
    ("approval.read", "approval", "read"),
    ("assignment.read", "assignment", "read"),
    ("candidate.create", "candidate", "create"),
    ("candidate.link_requisition", "candidate", "link_requisition"),
    ("candidate.read", "candidate", "read"),
    ("client.contact.create", "client", "contact_create"),
    ("client.create", "client", "create"),
    ("client.read", "client", "read"),
    ("dashboard.read_my_work", "dashboard", "read_my_work"),
    ("daily_update.create_main", "daily_update", "create_main"),
    ("daily_update.read", "daily_update", "read"),
    ("interview.create", "interview", "create"),
    ("location.create", "location", "create"),
    ("location.read", "location", "read"),
    ("meeting.create", "meeting", "create"),
    ("notification.read", "notification", "read"),
    ("offer.create", "offer", "create"),
    ("offer.read", "offer", "read"),
    ("pipeline.read.summary", "pipeline", "read_summary"),
    ("pipeline.stage.move", "pipeline", "stage_move"),
    ("requisition.assign", "requisition", "assign"),
    ("requisition.create", "requisition", "create"),
    ("requisition.read", "requisition", "read"),
    ("report.read", "report", "read"),
    ("role.create", "role", "create"),
    ("role.permissions.assign", "role", "permissions_assign"),
    ("role.read", "role", "read"),
    ("role.update", "role", "update"),
    ("settings.create", "settings", "create"),
    ("settings.read", "settings", "read"),
    ("settings.update", "settings", "update"),
    ("user.create", "user", "create"),
    ("user.read", "user", "read"),
    ("user.update", "user", "update"),
    ("approval.create", "approval", "create"),
    ("assignment.create", "assignment", "create"),
    ("assignment.update", "assignment", "update"),
    ("candidate.duplicate.check", "candidate", "duplicate.check"),
    ("candidate.resume.upload", "candidate", "resume.upload"),
    ("candidate.update", "candidate", "update"),
    ("client.contact.read", "client", "contact.read"),
    ("client.contact.update", "client", "contact.update"),
    ("client.update", "client", "update"),
    ("dashboard.read_pipeline_summary", "dashboard", "read_pipeline_summary"),
    ("interview.feedback.submit", "interview", "feedback.submit"),
    ("interview.read", "interview", "read"),
    ("location.update", "location", "update"),
    ("meeting.read", "meeting", "read"),
    ("meeting.update", "meeting", "update"),
    ("notification.mark_read", "notification", "mark_read"),
    ("offer.decide", "offer", "decide"),
    ("pipeline.read.detail", "pipeline", "read.detail"),
    ("pipeline.stage.history.read", "pipeline", "stage.history.read"),
    ("portal.assign_slot", "portal", "assign_slot"),
    ("portal.create", "portal", "create"),
    ("portal.read", "portal", "read"),
    ("portal.update", "portal", "update"),
    ("requisition.status.update", "requisition", "status.update"),
    ("requisition.update", "requisition", "update"),
    ("user.credentials.manage", "user", "credentials.manage"),
    ("workflow_action.nudge", "workflow_action", "nudge"),
    ("workflow_action.read", "workflow_action", "read"),
    ("workflow_action.resolve", "workflow_action", "resolve"),
    ("workflow_action.run", "workflow_action", "run"),
    ("workflow_overlay.submit", "workflow_overlay", "submit"),
]


def main() -> None:
    engine = create_db_engine()
    with engine.begin() as connection:
        # Location: user creation validates primary_location_id against
        # dbo.branches (see location_exists), so the branch IS the location row.
        location_id = connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.branches WHERE code = N'HO')
                BEGIN
                    INSERT INTO dbo.branches (name, code, location, status)
                    OUTPUT INSERTED.id
                    VALUES (N'Head Office', N'HO', N'Head Office', N'active');
                END
                ELSE
                BEGIN
                    SELECT id FROM dbo.branches WHERE code = N'HO';
                END
                """
            )
        ).scalar_one()

        # Mirror into dbo.locations for consumers that read the locations table
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.locations WHERE code = N'HO')
                    INSERT INTO dbo.locations (name, code, location, status)
                    VALUES (N'Head Office', N'HO', N'Head Office', N'active');
                """
            )
        )

        # Permission catalog (id is IDENTITY — no explicit ids)
        for code, module_name, action_name in PERMISSIONS:
            connection.execute(
                text(
                    """
                    IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = :code)
                        INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
                        VALUES (:code, :module, :action, :code, 0)
                    """
                ),
                {"code": code, "module": module_name, "action": action_name},
            )

        # Admin role
        role_id = connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.roles WHERE code = N'admin')
                BEGIN
                    INSERT INTO dbo.roles (name, code, description, is_system_role, status)
                    OUTPUT INSERTED.id
                    VALUES (N'Administrator', N'admin', N'Full access', 0, N'active');
                END
                ELSE
                BEGIN
                    SELECT id FROM dbo.roles WHERE code = N'admin';
                END
                """
            )
        ).scalar_one()

        # Grant every permission to admin
        connection.execute(
            text(
                """
                INSERT INTO dbo.role_permissions (role_id, permission_id)
                SELECT :role_id, p.id FROM dbo.permissions p
                WHERE NOT EXISTS (
                    SELECT 1 FROM dbo.role_permissions rp
                    WHERE rp.role_id = :role_id AND rp.permission_id = p.id
                )
                """
            ),
            {"role_id": role_id},
        )

        # Admin user
        password_hash = hash_password(ADMIN_PASSWORD)
        admin_user_id = connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com')
                BEGIN
                    INSERT INTO dbo.users (
                        full_name, email, password_hash, password_setup_status,
                        force_password_change_on_first_login, status,
                        default_role_id, hierarchy_level, location_id
                    )
                    OUTPUT INSERTED.id
                    VALUES (
                        N'Admin', N'ci.admin@recruitops-test.com', :password_hash, N'active',
                        0, N'active', :role_id, N'L5', :location_id
                    );
                END
                ELSE
                BEGIN
                    SELECT id FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com';
                END
                """
            ),
            {"password_hash": password_hash, "role_id": role_id, "location_id": location_id},
        ).scalar_one()

        # Primary branch link — the API resolves a user's location through
        # dbo.user_branch_roles (is_primary = 1)
        connection.execute(
            text(
                """
                DECLARE @uid BIGINT = (SELECT id FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com');
                IF NOT EXISTS (SELECT 1 FROM dbo.user_branch_roles WHERE user_id = @uid AND branch_id = :location_id)
                    INSERT INTO dbo.user_branch_roles (
                        user_id, branch_id, role_id, is_primary, status, start_date
                    )
                    VALUES (@uid, :location_id, :role_id, 1, N'active', CAST(SYSUTCDATETIME() AS DATE));
                """
            ),
            {"location_id": location_id, "role_id": role_id},
        )

        # Client id=1 — requisition creation reads clients from dbo.client_companies
        # (branch_id IS the location reference), so seed there.
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.client_companies WHERE id = 1)
                    INSERT INTO dbo.client_companies (
                        name, branch_id, relationship_type, status
                    )
                    VALUES (
                        N'CI Test Client', :location_id, N'direct-client', N'active'
                    );
                """
            ),
            {"location_id": location_id},
        )
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com')
                    INSERT INTO dbo.users (
                        full_name, email, password_hash, password_setup_status,
                        force_password_change_on_first_login, status,
                        default_role_id, hierarchy_level, location_id
                    )
                    VALUES (
                        N'Admin', N'ci.admin@recruitops-test.com', :password_hash, N'active',
                        0, N'active', :role_id, N'L5', :location_id
                    )
                """
            ),
            {"password_hash": password_hash, "role_id": role_id, "location_id": location_id},
        )

    print("CI seed complete: permissions, admin role/user (ci.admin@recruitops-test.com / admin123), Head Office location")


if __name__ == "__main__":
    main()
