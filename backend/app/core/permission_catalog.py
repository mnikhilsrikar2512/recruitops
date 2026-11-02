"""The permission catalog: every code a role can be granted (Phase 6.2).

One list for every environment. ``scripts/seed_reference_data.py`` (run by
``scripts/migrate.py`` on every deploy) inserts any code that's missing, so a
brand-new production database gets the same catalog as CI.
``tests/test_permission_catalog.py`` fails when an API route checks a code
that isn't listed here, so a new permission can't ship ungrantable.
"""
from __future__ import annotations

from app.core.rbac import ADMIN_PERMISSION_CODES, COMPANY_OVERVIEW_PERMISSION_CODES, split_code

# (code, module, action) — module/action are display grouping only.
PERMISSIONS: list[tuple[str, str, str]] = [
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
    # Added by later migrations (017, 019) and the duplicate-review routes,
    # which were never in any seed, so no role could be granted them.
    ("pipeline.stage.reopen", "pipeline", "stage.reopen"),
    ("candidate.delete.soft", "candidate", "delete.soft"),
    ("client.delete.soft", "client", "delete.soft"),
    ("candidate.duplicate.discard_draft", "candidate", "duplicate.discard_draft"),
    ("candidate.duplicate.link_existing", "candidate", "duplicate.link_existing"),
    ("candidate.duplicate.request_override", "candidate", "duplicate.request_override"),
]


def catalog() -> list[tuple[str, str, str]]:
    """PERMISSIONS plus every Admin and Company Overview code, de-duplicated."""
    rows: dict[str, tuple[str, str, str]] = {code: (code, module, action) for code, module, action in PERMISSIONS}
    for code in (*ADMIN_PERMISSION_CODES, *COMPANY_OVERVIEW_PERMISSION_CODES):
        if code not in rows:
            module, action = split_code(code)
            rows[code] = (code, module, action)
    return sorted(rows.values())
