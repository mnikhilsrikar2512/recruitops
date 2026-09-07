# Current Frontend Artifact Baseline

## Purpose

This document records the current frontend artifact set that already exists in the project.

It now covers both:

- the active lightweight live prototype
- the older reference artifacts kept for design and flow reuse

Its job is only to help us:

- separate live routes from reference artifacts
- understand what visual or flow ideas already exist
- compare future uploads against the current artifact set
- avoid accidentally treating legacy static pages as final implementation

## Important Rule

The frontend is now split into two layers:

- live route files in `frontend/pages/`
- reference artifacts in `frontend/pages/reference/`

Only the plain route files in `frontend/pages/` should be treated as the active frontend runtime.

The files in `frontend/pages/reference/` should be used only as:

- reference material
- feature inspiration
- layout idea sources
- flow idea sources

## Current Frontend Artifact Type

Current frontend evidence in the workspace is now a mix of:

- a small live routed HTML prototype
- standalone reference HTML pages
- standalone modal or drawer mockups
- standalone success toasts
- shared CSS and JS support files
- Stitch and design export assets

## Current Live Prototype Surface

The active lightweight prototype currently uses:

- `frontend/index.html`
- `frontend/pages/login.html`
- `frontend/pages/dashboard.html`
- `frontend/pages/users.html`
- `frontend/pages/locations.html`
- `frontend/pages/clients.html`
- `frontend/pages/requisitions.html`
- `frontend/pages/candidates.html`
- `frontend/pages/pipeline.html`
- `frontend/pages/daily-updates.html`
- `frontend/pages/notifications.html`
- `frontend/pages/access-denied.html`

This live layer is supported by:

- `frontend/shared/prototype.css`
- `frontend/shared/prototype.js`

These files are now part of the active product surface and should not be classified as legacy artifacts.

## Current Reference Artifact Type

Reference artifact evidence in the workspace is mainly:

- standalone HTML pages
- standalone modal or drawer mockups
- standalone success toasts
- shared CSS and JS support files
- Stitch and design export assets

This means the reference baseline is useful for comparison, but not as the frontend architecture we plan to ship.

## Current Shared Frontend Assets

These files appear reusable as shared assets:

- `frontend/shared/global.css`
- `frontend/shared/global.js`
- `frontend/shared/tailwind-generated.css`
- `frontend/shared/tailwind-source.css`
- `frontend/shared/brand-logo.svg`
- `frontend/shared/avatar-placeholder.svg`

Some of these support the live prototype directly, while others remain visual references only.

## Current Artifact Groups By MVP Relevance

## Group 1. Core Auth And Access References

These map loosely to MVP auth-related reference screens:

- `frontend/pages/reference/login_executive_heritage.html`
- `frontend/pages/reference/access_denied_executive_heritage.html`
- `frontend/pages/reference/404_not_found_executive_heritage.html`

Possible reusable ideas:

- auth layout structure
- login form spacing
- access denial wording

## Group 2. Admin And Governance References

These map loosely to admin and setup reference flows:

- `frontend/pages/reference/location_management_executive_heritage.html`
- `frontend/pages/reference/user_management_executive_heritage.html`
- `frontend/pages/reference/create_user_executive_heritage.html`
- `frontend/pages/reference/update_user_executive_heritage.html`
- `frontend/pages/reference/invite_user_step_1_identity_role.html`
- `frontend/pages/reference/invite_user_step_2_reporting_access.html`
- `frontend/pages/reference/invite_user_step_3_review_send.html`
- `frontend/pages/reference/delete_user_step_1_summary_choice.html`
- `frontend/pages/reference/delete_user_step_2_impact_reassignment.html`
- `frontend/pages/reference/delete_user_step_3_final_confirmation_delete.html`
- `frontend/pages/reference/deactivate_user_step_2_impact_timing.html`
- `frontend/pages/reference/deactivate_user_step_3_success_confirmation.html`
- `frontend/pages/reference/audit_center_executive_heritage.html`
- `frontend/pages/reference/audit_exception_queue_executive_heritage.html`
- `frontend/pages/reference/approvals_inbox_executive_heritage.html`
- `frontend/pages/reference/approval_decision_detail_drawer_executive_heritage.html`

Possible reusable ideas:

- management table layout
- multi-step user lifecycle flows
- review dialog patterns
- audit table structure

Risk:

- some of these belong to approval or audit extensions, not the MVP working model

## Group 3. Client And Company References

These map loosely to client-related views:

- `frontend/pages/client_companies_executive_heritage.html`
- `frontend/pages/client_portfolio_executive_heritage.html`
- `frontend/pages/company_details_executive_heritage.html`

Possible reusable ideas:

- client list table structure
- client summary card structure
- profile header patterns

Risk:

- naming and ownership structure may not exactly match the configurable MVP model

## Group 4. Requisition And Assignment References

These map loosely to requisition-related views:

- `frontend/pages/managed_requisitions_perfectly_balanced_layout.html`
- `frontend/pages/structured_requisition_intake_layout_fixes.html`
- `frontend/pages/structured_requisition_approval_modal.html`
- `frontend/pages/requisition_approval_success_toast_executive_heritage.html`

Possible reusable ideas:

- requisition form sections
- requisition detail layout
- approval or review dialog treatment

Risk:

- approval-heavy behavior may exceed MVP scope

## Group 5. Candidate And Resume References

These map loosely to candidate management:

- `frontend/pages/candidate_profiles_refined_structure.html`
- `frontend/pages/candidate_profile_arjun_mehta.html`
- `frontend/pages/candidate_screening_arjun_mehta.html`
- `frontend/pages/upload_resume_parse_review_modal_executive_heritage.html`
- `frontend/pages/resume_duplicate_check_modal_executive_heritage.html`
- `frontend/pages/resume_save_candidate_modal_executive_heritage.html`
- `frontend/pages/candidate_rejection_classification_reason.html`
- `frontend/pages/candidate_rejection_success_confirmation.html`

Possible reusable ideas:

- candidate profile sections
- resume review flow
- duplicate warning flow
- screening layout

## Group 6. Pipeline And Delivery References

These map loosely to live workflow tracking:

- `frontend/pages/pipeline_board_executive_heritage.html`
- `frontend/pages/submit_daily_update_executive_heritage.html`
- `frontend/pages/record_meeting_outcome_modal_executive_heritage.html`
- `frontend/pages/report_delivery_success_toast_executive_heritage.html`

Possible reusable ideas:

- board lane structure
- candidate card density
- daily update form structure

Risk:

- some meeting-specific patterns may not belong in MVP

## Group 7. Dashboard, Reports, And Notification References

These map loosely to reporting and summary pages:

- `frontend/pages/admin_dashboard_executive_heritage_fixed.html`
- `frontend/pages/manager_dashboard_executive_heritage_fixed.html`
- `frontend/pages/hr_dashboard_executive_heritage.html`
- `frontend/pages/reports_center_executive_heritage.html`
- `frontend/pages/team_performance_executive_heritage.html`
- `frontend/pages/recruiter_reports_productivity_executive_heritage.html`
- `frontend/pages/recruiter_performance_detail_executive_heritage.html`
- `frontend/pages/manager_reports_executive_heritage.html`
- `frontend/pages/hr_reports_executive_heritage.html`
- `frontend/pages/admin_notifications_executive_heritage.html`
- `frontend/pages/manager_notifications_executive_heritage.html`
- `frontend/pages/hr_notifications_executive_heritage.html`

Possible reusable ideas:

- KPI block arrangement
- report section structure
- notification list treatment

Risk:

- hard-coded role-specific dashboards conflict with the configurable-role product model

## Group 8. Likely Non-MVP Or Future-Extension References

These are useful as idea sources only and should not be treated as MVP priority:

- `frontend/pages/interview_schedule_executive_heritage.html`
- `frontend/pages/meetings_follow_ups_executive_heritage.html`
- `frontend/pages/portal_accounts_executive_heritage.html`
- `frontend/pages/assign_portal_slot_modal_executive_heritage.html`
- `frontend/pages/portal_slot_success_toast_executive_heritage.html`
- `frontend/pages/settings_executive_heritage.html`
- `frontend/pages/user_profile_account_settings_executive_heritage.html`
- `frontend/pages/profile_preferences_success_toast_executive_heritage.html`

## What We Should Reuse Carefully

From the current artifact baseline, the most likely reusable idea categories are:

- auth page composition
- management table layout
- form section grouping
- detail header structure
- candidate profile sectioning
- duplicate review modal logic pattern
- pipeline board visual organization
- dashboard KPI card grouping

## What We Should Avoid Carrying Forward By Default

- hard-coded role-specific dashboards
- approval-heavy flows beyond MVP
- portal-account management flows
- meeting or interview scheduling flows unless re-approved
- settings and profile extras not part of MVP
- role names or workflow assumptions that conflict with configurable roles

## How To Use This Baseline After New Uploads Arrive

When new foundation and MVP pages are uploaded, compare them against this baseline in four steps:

1. identify the matching MVP page or module
2. extract useful visual and flow ideas from both old and new artifacts
3. choose the version that better fits the configurable-role recruitment MVP
4. document the final selected features before building the real frontend

## Final Rule

This baseline is reference-only.

It must never be used as evidence that the target MVP frontend is already implemented.
