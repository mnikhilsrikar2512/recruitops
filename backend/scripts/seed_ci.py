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

from app.core.rbac import ADMIN_PERMISSION_CODES, split_code  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402

ADMIN_PASSWORD = "admin123"

# (code, module, action) — codes mirror the live permission catalog
PERMISSIONS = [
    # AI agents (PRD §4.16): base ai.use + one ai.agent.<id> code per registry
    # agent (app/agents/registry.py). Without these rows only the admin role
    # (check bypass in app/api/deps.py) can reach the agents API.
    ("ai.use", "ai", "use"),
    ("ai.agent.resume_screener", "ai", "agent.resume_screener"),
    ("ai.agent.daily_brief", "ai", "agent.daily_brief"),
    ("ai.agent.inbox_triage", "ai", "agent.inbox_triage"),
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


# (name, query, description) — post-seed invariants; each must return >= 1 row
VERIFICATIONS = [
    (
        "open requisition 'CI Test Requisition'",
        "SELECT 1 FROM dbo.requisitions WHERE title = N'CI Test Requisition' AND status = N'open'",
    ),
    (
        "candidate 'CI Test Candidate'",
        "SELECT 1 FROM dbo.candidates WHERE full_name = N'CI Test Candidate'",
    ),
    (
        "portal account 'CI Shared Portal Account'",
        "SELECT 1 FROM dbo.portal_accounts WHERE account_name = N'CI Shared Portal Account' AND status = N'active'",
    ),
    (
        "primary company entity (letterhead)",
        "SELECT 1 FROM dbo.company_entities WHERE is_primary = 1 AND status = N'active'",
    ),
    (
        "AI agent permission catalog (ai.use + ai.agent.*)",
        "SELECT 1 FROM dbo.permissions WHERE code = N'ai.use' AND ("
        "SELECT COUNT(*) FROM dbo.permissions WHERE code IN ("
        "N'ai.agent.resume_screener', N'ai.agent.daily_brief', N'ai.agent.inbox_triage')) = 3",
    ),
]


def verify_seed(engine) -> None:
    """Fail loudly (non-zero exit) if any seeded row the tests depend on is missing."""
    with engine.connect() as connection:
        missing = [
            description
            for description, query in VERIFICATIONS
            if connection.execute(text(query)).first() is None
        ]
    if missing:
        for item in missing:
            print(f"SEED VERIFICATION FAILED: missing {item}", file=sys.stderr)
        raise SystemExit(1)
    print(
        "CI seed verified: requisition/candidate pair and portal account are present"
    )


def seed_display_ids(engine, location_id: int) -> None:
    """Display-ID fixtures (scripts/008_display_ids.sql) on a fresh database.

    tests/test_display_ids_db.py expects an HYD01 branch with sequence rows and
    at least one coded requisition and candidate. A dev database gets these
    from 008's backfill; a fresh one has nothing to backfill, so give the
    seeded rows codes through the real allocator. Skipped when 008 has not
    been applied.
    """
    from app.repositories.display_ids import (  # noqa: PLC0415
        ENTITY_CANDIDATE,
        ENTITY_REQUISITION,
        _seed_sequence_row,
        allocate_display_id,
    )

    with engine.begin() as connection:
        if connection.execute(text("SELECT OBJECT_ID(N'dbo.display_id_sequences')")).scalar() is None:
            print("display-ID tables absent (008 not applied) — skipping display-ID fixtures")
            return
        hyd_id = connection.execute(
            text(
                """
                SET NOCOUNT ON;
                IF NOT EXISTS (SELECT 1 FROM dbo.branches WHERE code = N'HYD01')
                    INSERT INTO dbo.branches (name, code, location, status, tenant_id)
                    VALUES (N'Hyderabad', N'HYD01', N'Hyderabad', N'active', (SELECT id FROM dbo.tenants WHERE slug = N'default'));
                SELECT id FROM dbo.branches WHERE code = N'HYD01';
                """
            )
        ).scalar_one()
        for branch_id in (location_id, hyd_id):
            for entity in (ENTITY_REQUISITION, ENTITY_CANDIDATE):
                _seed_sequence_row(connection, entity, int(branch_id))

        requisition_id = connection.execute(
            text("SELECT TOP 1 id FROM dbo.requisitions WHERE title = N'CI Test Requisition' AND requisition_code IS NULL")
        ).scalar()
        if requisition_id:
            code = allocate_display_id(connection, ENTITY_REQUISITION, int(location_id))
            connection.execute(
                text("UPDATE dbo.requisitions SET requisition_code = :code WHERE id = :id"),
                {"code": code, "id": requisition_id},
            )
        candidate_id = connection.execute(
            text("SELECT TOP 1 id FROM dbo.candidates WHERE full_name = N'CI Test Candidate' AND candidate_code IS NULL")
        ).scalar()
        if candidate_id:
            code = allocate_display_id(connection, ENTITY_CANDIDATE, int(location_id))
            connection.execute(
                text("UPDATE dbo.candidates SET candidate_code = :code, branch_id = COALESCE(branch_id, :branch) WHERE id = :id"),
                {"code": code, "branch": location_id, "id": candidate_id},
            )


def main() -> None:
    engine = create_db_engine()
    with engine.begin() as connection:
        # Company (tenant, 010_tenants.sql): the CI database is one company.
        if connection.execute(text("SELECT OBJECT_ID(N'dbo.tenants')")).scalar() is None:
            raise SystemExit("dbo.tenants is missing — apply scripts/010_tenants.sql before seeding")
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.tenants WHERE slug = N'default')
                    INSERT INTO dbo.tenants (slug, display_name, status)
                    VALUES (N'default', N'CI Company', N'active');
                """
            )
        )
        # Location: user creation validates primary_location_id against
        # dbo.branches (see location_exists), so the branch IS the location row.
        location_id = connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.branches WHERE code = N'HO')
                BEGIN
                    INSERT INTO dbo.branches (name, code, location, status, tenant_id)
                    OUTPUT INSERTED.id
                    VALUES (N'Head Office', N'HO', N'Head Office', N'active', (SELECT id FROM dbo.tenants WHERE slug = N'default'));
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
                    INSERT INTO dbo.locations (name, code, location, status, tenant_id)
                    VALUES (N'Head Office', N'HO', N'Head Office', N'active', (SELECT id FROM dbo.tenants WHERE slug = N'default'));
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

        # Admin template = the control plane only (D-03, app/core/rbac.py).
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

        # The CI admin also recruits: a CI-company role holding EVERY code, so
        # the DB-backed tests can drive execution routes as this user. (An
        # admin who also recruits holds an execution role — PRD §3.1.)
        full_role_id = connection.execute(
            text(
                """
                SET NOCOUNT ON;
                IF NOT EXISTS (SELECT 1 FROM dbo.roles WHERE code = N'ci-full-access')
                    INSERT INTO dbo.roles (name, code, description, is_system_role, status, tenant_id)
                    VALUES (N'CI Full Access', N'ci-full-access', N'CI only: every permission', 0, N'active',
                            (SELECT id FROM dbo.tenants WHERE slug = N'default'));
                SELECT id FROM dbo.roles WHERE code = N'ci-full-access';
                """
            )
        ).scalar_one()
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
            {"role_id": full_role_id},
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
                        default_role_id, hierarchy_level, location_id, tenant_id
                    )
                    OUTPUT INSERTED.id
                    VALUES (
                        N'Admin', N'ci.admin@recruitops-test.com', :password_hash, N'active',
                        0, N'active', :role_id, N'L5', :location_id, (SELECT id FROM dbo.tenants WHERE slug = N'default')
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

        # Second (non-primary) office role for the CI admin: CI Full Access.
        connection.execute(
            text(
                """
                DECLARE @uid BIGINT = (SELECT id FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com');
                IF NOT EXISTS (SELECT 1 FROM dbo.user_branch_roles WHERE user_id = @uid AND role_id = :role_id)
                    INSERT INTO dbo.user_branch_roles (
                        user_id, branch_id, role_id, is_primary, status, start_date
                    )
                    VALUES (@uid, :location_id, :role_id, 0, N'active', CAST(SYSUTCDATETIME() AS DATE));
                """
            ),
            {"location_id": location_id, "role_id": full_role_id},
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
                        default_role_id, hierarchy_level, location_id, tenant_id
                    )
                    VALUES (
                        N'Admin', N'ci.admin@recruitops-test.com', :password_hash, N'active',
                        0, N'active', :role_id, N'L5', :location_id, (SELECT id FROM dbo.tenants WHERE slug = N'default')
                    )
                """
            ),
            {"password_hash": password_hash, "role_id": role_id, "location_id": location_id},
        )

        # Open requisition + candidate pair — the pipeline-template validation
        # fixture hangs a test application on a candidate × open-requisition
        # pair, so a bare CI database must provide one.
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.requisitions WHERE title = N'CI Test Requisition')
                    INSERT INTO dbo.requisitions (
                        branch_id, hiring_type, title, owner_user_id, status,
                        open_positions, target_close_date, job_description
                    )
                    VALUES (
                        :location_id, N'internal', N'CI Test Requisition', 1, N'open',
                        1, CAST(DATEADD(day, 30, CAST(SYSUTCDATETIME() AS DATE)) AS DATE),
                        N'CI-seeded requisition for pipeline tests.'
                    );
                """
            ),
            {"location_id": location_id},
        )
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.candidates WHERE full_name = N'CI Test Candidate')
                    INSERT INTO dbo.candidates (full_name, source, created_by_user_id)
                    VALUES (N'CI Test Candidate', N'ci-seed', 1);
                """
            )
        )

        # Portal account — portal-accounts integration asserts the list shows
        # at least one seeded row with the branch join resolved.
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.portal_accounts WHERE account_name = N'CI Shared Portal Account')
                    INSERT INTO dbo.portal_accounts (
                        branch_id, platform_name, account_name, status,
                        ownership_type, is_shared, has_full_access
                    )
                    VALUES (
                        :location_id, N'LinkedIn', N'CI Shared Portal Account', N'active',
                        N'company-shared', 1, 0
                    );
                """
            ),
            {"location_id": location_id},
        )

        # Primary company entity — the letterhead source of truth that the
        # settings endpoints and report letterheads read.
        connection.execute(
            text(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM dbo.company_entities WHERE is_primary = 1 AND status = N'active'
                )
                    INSERT INTO dbo.company_entities (
                        display_name, legal_name, company_code, company_type_code,
                        hq_city, country_name, support_email, website_url, is_primary, status
                    )
                    VALUES (
                        N'RecruitOps Demo', N'RecruitOps Demo Pvt Ltd', N'RCI', N'recruitment-agency',
                        N'Hyderabad', N'India', N'hello@recruitops-demo.test', N'https://recruitops-demo.test',
                        1, N'active'
                    );
                """
            ),
        )

    seed_display_ids(engine, location_id)
    verify_seed(engine)
    print("CI seed complete: permissions, admin role/user (ci.admin@recruitops-test.com / admin123), Head Office location, requisition/candidate pair, portal account")


if __name__ == "__main__":
    main()
