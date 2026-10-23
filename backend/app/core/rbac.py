"""Role templates and permission codes that the code relies on by name.

Decision D-03 (docs/decisions-2026-10-06.md): the Admin is the CONTROL
PLANE of one company — users, offices, roles, settings, approvals, reports,
portal accounts, work assignment. It does not run recruiting; an admin who
also recruits holds an execution role in addition.

The Admin system role (roles.tenant_id IS NULL, code 'admin') holds exactly
ADMIN_PERMISSION_CODES. scripts/seed_ci.py writes the same list into the
database (looping over this constant directly, so it can't drift from it);
tests/test_admin_seed.py keeps the two in step. A database seeded before a
code was added to this tuple needs scripts/seed_ci.py re-run to backfill the
role_permissions rows -- it's idempotent, safe to run against an existing
database. Nothing in the API checks the role code: admins pass routes
through these grants like every other user (plan 2.5).
"""

from __future__ import annotations

# Reach over every office of the caller's own company (app/services/scope.py).
COMPANY_SCOPE_CODE = "scope.company"

ADMIN_PERMISSION_CODES: tuple[str, ...] = (
    # users
    "user.read", "user.create", "user.update", "user.credentials.manage", "user.write",
    # offices
    "location.read", "location.create", "location.update", "location.write",
    # roles
    "role.read", "role.create", "role.update", "role.permissions.assign", "role.write",
    # settings, master data, visibility rules
    "settings.read", "settings.create", "settings.update", "settings.write", "visibility_rules.write",
    # approvals
    "approval.read", "approval.decide",
    # dashboards and reports
    "dashboard.view_admin", "dashboard.read_pipeline_summary", "report.read",
    # notifications
    "notification.read", "notification.mark_read",
    # portal accounts
    "portal.read", "portal.create", "portal.update", "portal.assign_slot", "portal_accounts.write",
    # work assignment
    "assignment.read", "assignment.create", "assignment.update", "work_assignment.write",
    # governance (no routes yet; PRD §3.2 rows)
    "ai.policy.write", "audit_log.read", "privacy_request.write",
    # company-wide reach
    COMPANY_SCOPE_CODE,
)

# Read-only, cross-module visibility into day-to-day recruiting work --
# candidates, clients, requisitions, offers, interviews, meetings, the
# pipeline (summary, detail and stage history), daily updates, workflow
# actions, assignments and portal accounts. No create/update/decide/assign
# code appears here; this grants *seeing* everything, never *changing*
# anything.
#
# This is NOT a fixed system role like Admin -- it is an ordinary custom
# role any company admin can create via Roles -> Permissions Editor (or see
# scripts/seed_staging.py for a worked example), typically for someone who
# needs full drill-down visibility without execution rights: an owner,
# investor, or auditor, or an admin who wants their own role to include it.
#
# RecruitOps still gives a user exactly one active role at a time
# (dbo.user_branch_roles' is_primary slot is replaced, not stacked, by every
# role-change in the API) -- but an admin who wants both the Admin
# control-plane and this overview in one login no longer needs a combined
# custom role for it. PUT /users/{user_id}/extra-permissions
# (app/api/v1/users.py, backed by the pre-existing but previously-unused
# dbo.user_extra_permissions table) grants a permission bundle like this one
# directly to a user, on top of whatever their one role already gives them.
# app/repositories/auth.py's list_resolved_permissions unions both sources.
# The user's role, title, and hierarchy level are untouched -- only their
# permission reach grows. See frontend/pages/user-detail.html's "Additional
# permissions" card for the UI, and scripts/seed_staging.py for a worked
# example granting this exact bundle to a tenant's admin.
COMPANY_OVERVIEW_PERMISSION_CODES: tuple[str, ...] = (
    "candidate.read",
    "client.read", "client.contact.read",
    "requisition.read",
    "offer.read",
    "interview.read",
    "meeting.read",
    "pipeline.read.summary", "pipeline.read.detail", "pipeline.stage.history.read",
    "daily_update.read",
    "workflow_action.read",
    "assignment.read",
    "portal.read",
)


def split_code(code: str) -> tuple[str, str]:
    """(module_name, action_name) for a catalog row, e.g. 'role.permissions.assign'
    → ('role', 'permissions.assign')."""
    module, _, action = code.partition(".")
    return module, action
