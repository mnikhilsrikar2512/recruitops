"""How every table belongs to a company (tenant) — plan 2.3.

Each table is either owned by a company directly (``tenant``), owned through
an office (``office:<column>`` → dbo.branches/locations.tenant_id), through a
parent row (``parent:<column>-><table>``), through a user
(``user:<column>`` → users.tenant_id), or deliberately shared
(``shared:<reason>``). tests/test_tenancy_coverage.py fails the build when a
table is added without a line here, or when a named column does not exist.

Reads and writes go through app/services/scope.py, which applies exactly
these paths.
"""
from __future__ import annotations

TABLE_TENANCY: dict[str, str] = {
    # ---- company roots -------------------------------------------------
    "tenants": "shared:the companies themselves (platform ops)",
    "branches": "tenant",
    "locations": "tenant",
    "users": "tenant",
    "roles": "tenant",  # tenant_id NULL = shared system role (Admin template)
    "company_entities": "tenant",  # company profile / letterhead (012)
    "master_data_values": "tenant",  # NULL = shared template values (012)
    "stage_bucket_map": "tenant",
    "candidate_archives": "tenant",  # an archive hides a shared candidate from ONE company (019)  # NULL = platform default label map (016)
    # ---- through an office --------------------------------------------
    "agent_runs": "office:location_id",
    "approvals": "office:location_id",
    "approval_requests": "office:branch_id",
    "audit_logs": "office:branch_id",
    "audit_log_access_events": "office:location_id",
    "client_companies": "office:branch_id",
    "clients": "office:location_id",
    "client_contacts": "office:location_id",
    "daily_updates": "office:location_id",
    "display_id_sequences": "office:branch_id",
    "meetings": "office:location_id",
    "notifications": "user:user_id",
    "pipeline_templates": "office:location_id",
    "portal_accounts": "office:branch_id",
    "recruiter_daily_updates": "office:branch_id",
    "report_locks": "office:branch_id",
    "reports": "office:branch_id",
    "requisitions": "office:branch_id",
    "requisition_assignments": "office:location_id",
    "workflow_action_items": "office:location_id",
    "user_branch_roles": "office:branch_id",
    "user_location_roles": "office:location_id",
    "candidate_location_transfer_requests": "office:from_location_id",
    "client_access_requests": "office:requesting_location_id",
    # ---- through a parent row -----------------------------------------
    "candidate_applications": "parent:requisition_id->requisitions",
    "candidate_stage_history": "parent:candidate_application_id->candidate_applications",
    "candidate_screening_checks": "parent:candidate_application_id->candidate_applications",
    "interview_rounds": "parent:candidate_application_id->candidate_applications",
    "requisition_documents_required": "parent:requisition_id->requisitions",
    "requisition_end_clients": "parent:requisition_id->requisitions",
    "requisition_screening_rules": "parent:requisition_id->requisitions",
    "requisition_skill_requirements": "parent:requisition_id->requisitions",
    "meeting_attendees": "parent:meeting_id->meetings",
    "pipeline_template_stages": "parent:pipeline_template_id->pipeline_templates",
    "portal_account_slots": "parent:portal_account_id->portal_accounts",
    "report_rows": "parent:report_id->reports",
    "workflow_action_events": "parent:action_item_id->workflow_action_items",
    "role_permissions": "parent:role_id->roles",
    "role_scope_rules": "parent:role_id->roles",
    # candidates are global identity records; a company reaches one through
    # scope.CANDIDATE_IN_TENANT_SQL (its office, its creator, or an application)
    "candidates": "parent:created_by_user_id->users",
    "candidate_documents": "parent:candidate_id->candidates",
    "candidate_skills": "parent:candidate_id->candidates",
    "candidate_resume_parse_logs": "parent:candidate_id->candidates",
    "candidate_duplicate_checks": "parent:candidate_id->candidates",
    "duplicate_review_cases": "parent:candidate_id->candidates",
    # ---- through a user -----------------------------------------------
    "user_sessions": "user:user_id",
    "user_refresh_tokens": "parent:session_id->user_sessions",
    "user_mfa": "user:user_id",
    "user_mfa_recovery_codes": "user:user_id",
    "password_reset_tokens": "user:user_id",
    "user_invitations": "user:user_id",
    "user_notification_preferences": "user:user_id",
    "user_extra_permissions": "user:user_id",
    "automation_jobs": "user:triggered_by_user_id",
    # ---- shared on purpose ----------------------------------------------
    "permissions": "shared:the permission catalog",
    "master_data_categories": "shared:list definitions; the values are per company",
    "role_templates": "shared:system role templates",
    "role_template_permissions": "shared:system role templates",
    "backend_sql_executions": "shared:migration bookkeeping",
    "metric_buckets": "shared:the fixed reporting bucket enum (016)",
}
