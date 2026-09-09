# Database Design

## Important Note

This document originally evolved around the prototype hierarchy `Admin`, `Manager`, `HR`, and `Recruiter`.

For execution planning going forward, use `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md` as the primary source of truth for role design.

This database design should now be interpreted as moving toward:

- permission roles
- business titles
- reporting relationships
- visibility scopes
- workflow ownership

## Purpose

This database list is updated to match the current frontend in `frontend/`.

Use-case traceability reference:

- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`

It now covers:

- RBAC login and configurable page access
- dashboard support for multiple operating models
- location management
- user access management
- user invitation and first-login credential setup
- direct client and optional end-client relationships
- requisition intake and structured JD capture
- candidate screening, pipeline, interviews, and rejection tracking
- resume upload, parsing, duplicate review, draft save, and candidate finalization
- portal account access and usage windows
- approvals, notifications, and reports

## Design Goals

- keep permission roles stable and business titles configurable
- keep reporting relationships explicit without hard-coding one universal chain
- keep visibility scopes and ownership rules explicit
- Keep location ownership and reporting lines clear
- Support both `internal` and `external` hiring
- Keep end-client mapping optional
- Allow optional scheduled portal usage
- support both direct user creation and invitation-based onboarding
- keep parser output reviewable before it becomes trusted candidate data
- Capture only the structured data needed for reporting
- Separate operational records from dashboard summary data

## JS vs Database Responsibility

The frontend currently includes a shared JS automation layer for low-risk convenience behavior.

These do not need their own database tables:

- temporary password suggestion before save
- employee code suggestion before save
- local draft text generation for daily updates
- local notification rendering used only for prototype flows
- client-side report formatting and tab shaping from already loaded data

These still require database-backed persistence and auditability:

- user accounts and credential state
- invitations and password reset state
- official notifications
- official reports and reporting locks
- resume parsing output and duplicate decisions
- approvals, rejections, escalations, and audit logs
- location, user, requisition, candidate, and meeting performance data

## Recommended Table List

## Working Model First

For execution, this document should be read in two layers:

### Layer 1. Working Model Now

These tables are enough to support the first usable system:

- `permission_roles`
- `permissions`
- `permission_role_permissions`
- `business_titles`
- `locations`
- `users`
- `user_location_roles`
- `clients`
- `client_contacts`
- `requisitions`
- `requisition_assignments`
- `candidates`
- `candidate_requisition_links`
- `candidate_stage_history`
- `daily_updates`

These tables directly support the working lifecycle documented in `docs/system/WORKING_MODEL.md`.

### Layer 2. Extensions Later

These areas should be treated as future expansion, not day-one dependency:

- invitation orchestration
- advanced password recovery flows
- notifications and preferences
- parser output storage
- duplicate review queues
- approvals and escalations
- reporting locks and finalized reports
- portal slots and usage windows
- audit center and compliance trails
- automation jobs and integrations

## Recommended MVP Table Subset

If we want the smallest practical database for the first implementation pass, use this table subset first.

For the exact first-release column-level draft, use `docs/system/MVP_SCHEMA_DRAFT.md`.

## 0. Core Organizational Tables

- `permission_roles`
- `permissions`
- `permission_role_permissions`
- `business_titles`
- `locations`
- `users`
- `user_location_roles`

Why they matter:

- enable login and access control
- model the reporting chain in a simple way
- support role mapping such as Director, BDM, Account Manager, Lead Recruiter, Assistant Recruiter, and Recruiter without hard-coding those as software roles

## 0A. Core Commercial Tables

- `clients`
- `client_contacts`

Why they matter:

- allow account ownership
- support client intake before requisition creation

## 0B. Core Delivery Tables

- `requisitions`
- `requisition_assignments`
- `candidates`
- `candidate_requisition_links`
- `candidate_stage_history`
- `daily_updates`

Why they matter:

- support the end-to-end working flow from requirement creation to candidate movement and recruiter progress updates

## Working Model Notes

- `users.reporting_manager_user_id` is enough for the first release
- `users.primary_role_id` is the only active role field in the validated implementation
- `requisitions` should keep a direct `client_id` and `delivery_owner_user_id`
- `requisition_assignments` should support one requisition with multiple assigned recruiters
- `candidates` should be global candidate records, not requisition-specific duplicates
- `candidate_requisition_links` should track each candidate's status per requisition
- `candidate_stage_history` should record every stage movement for auditability and dashboard counts
- `daily_updates` should stay simple and attach to user, requisition, date, summary, blockers, and next action
- `candidates` should store `sourced_by_user_id` so recruiters can track candidates they originally sourced
- `candidate_requisition_links` should support recruiter visibility even after ownership changes later in the pipeline
- every core operational table should carry `location_id` so location isolation is enforceable in queries

## Extension Policy

Do not block implementation on advanced tables if the same business need can be covered by a simpler first-release design.

Examples:

- use `password_reset_tokens` only if reset flow is implemented in the first release
- use `candidate_documents` only if actual file upload is included in the first delivery
- postpone `user_notification_preferences` until official notifications exist
- postpone approvals, SLA history, billing, parser outputs, and audit-center structures until core data capture is stable

## 1. permission_roles

- `id`
- `code`
- `name`
- `description`
- `created_at`
- `updated_at`

Frontend usage:

- role and access bootstrap
- RBAC redirects
- user access matrix

Examples:

- `platform_admin`
- `operations_admin`
- `business_lead`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`

## 1A. business_titles

- `id`
- `code`
- `name`
- `description` (nullable)
- `is_active`
- `created_at`
- `updated_at`

Why this table is needed:

- customers need configurable titles without changing product permission logic
- one customer may use `Director` while another uses `Talent Head`
- one customer may use `Lead Recruiter` while another uses `Delivery Manager`

## 1B. permissions

- `id`
- `code`
- `module_name`
- `action_name`
- `description` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the API already exposes `permissions/me`
- frontend sidebar visibility and action gating should come from explicit permission codes, not only role names

## 1C. permission_role_permissions

- `id`
- `permission_role_id`
- `permission_id`
- `created_at`
- `updated_at`

Why this table is needed:

- keeps RBAC flexible as modules grow
- avoids hard-coding every future role action combination in application code only

## 2. users

- `id`
- `employee_code` (nullable)
- `full_name`
- `email`
- `phone`
- `password_hash`
- `password_setup_status` (`pending-setup`, `active`, `reset-required`, `invited`)
- `password_changed_at` (nullable)
- `force_password_change_on_first_login`
- `status`
- `default_permission_role_id`
- `business_title_id` (nullable)
- `reporting_manager_user_id` (nullable)
- `last_login_at`
- `created_at`
- `updated_at`

Frontend usage:

- login
- user management
- create user and invite user flows
- reset password and resend credentials
- configurable reporting visibility
- candidate and requisition ownership

Implementation note:

- this field supports simple reporting lines for MVP
- if matrix reporting, dotted-line reporting, or historical reporting changes are needed later, use a dedicated reporting relationships table instead of overloading this row

## 2B. user_sessions

- `id`
- `user_id`
- `session_token_hash`
- `refresh_token_hash` (nullable)
- `ip_address` (nullable)
- `user_agent` (nullable)
- `expires_at`
- `revoked_at` (nullable)
- `last_seen_at` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- supports login, logout, refresh token, and session invalidation APIs
- keeps security events auditable

## 2C. password_reset_tokens

- `id`
- `user_id`
- `token_hash`
- `purpose` (`forgot-password`, `first-password-setup`, `admin-reset`)
- `expires_at`
- `used_at` (nullable)
- `issued_by_user_id` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- supports forgot password, reset password, and setup-link flows cleanly
- avoids mixing one-time token state into the `users` table

## 2D. user_notification_preferences

- `id`
- `user_id`
- `email_enabled`
- `in_app_enabled`
- `report_ready_enabled`
- `approval_alert_enabled`
- `meeting_follow_up_enabled`
- `portal_slot_enabled`
- `daily_update_reminder_enabled`
- `created_at`
- `updated_at`

Why this table is needed:

- settings and notification pages need user-level control without bloating `users`
- helps automate alerts without disturbing users unnecessarily

## 2A. user_invitations

- `id`
- `user_id`
- `invite_email`
- `credential_setup_method` (`temporary-password`, `system-generated-password`, `setup-link`)
- `credential_delivery_method` (`email-credentials`, `manual-share`, `setup-instructions-only`)
- `temporary_password_hash` (nullable)
- `password_valid_until` (nullable)
- `setup_token` (nullable)
- `setup_token_expires_at` (nullable)
- `invite_status` (`draft`, `sent`, `accepted`, `expired`, `cancelled`)
- `sent_by_user_id`
- `sent_at` (nullable)
- `accepted_at` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- direct user creation and invitation-based onboarding are both present in the frontend
- first-login credential handling should not be overloaded into the `users` table only
- admins need resend, reset, and invite tracking without losing audit history

## 3. user_location_roles

- `id`
- `user_id`
- `location_id`
- `permission_role_id`
- `is_primary`
- `status`
- `start_date`
- `end_date` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- one user may move locations over time
- one user may need an explicit location-role assignment
- the frontend user matrix and location teams should not rely on a single field in `users`

## 3A. user_scope_assignments

- `id`
- `user_id`
- `scope_type` (`global`, `business_unit`, `location`, `team`, `account`, `requisition`)
- `scope_id`
- `access_level`
- `created_at`
- `updated_at`

Why this table is needed:

- visibility must be configurable beyond one role name
- some users need team-level access while others need location-level or account-level access

## 3B. teams

- `id`
- `name`
- `code`
- `location_id` (nullable)
- `business_unit_id` (nullable)
- `manager_user_id` (nullable)
- `status`
- `created_at`
- `updated_at`

## 3C. team_memberships

- `id`
- `team_id`
- `user_id`
- `membership_role` (nullable)
- `is_primary`
- `start_date`
- `end_date` (nullable)
- `created_at`
- `updated_at`

## MVP Schema Contract

The first release should implement a reduced schema that matches the universal architecture but avoids overbuilding.

### Required MVP Tables

These tables should be included in the first backend implementation:

- `permission_roles`
- `business_titles`
- `permissions`
- `permission_role_permissions`
- `users`
- `user_sessions`
- `password_reset_tokens`
- `user_invitations`
- `locations`
- `teams`
- `team_memberships`
- `user_location_roles`
- `user_scope_assignments`
- `clients`
- `client_contacts`
- `requisitions`
- `requisition_end_clients`
- `requisition_skill_requirements`
- `requisition_documents_required`
- `candidates`
- `candidate_documents`
- `candidate_duplicate_checks`
- `candidate_applications`
- `candidate_stage_history`

### Deferred Tables

These can wait until after the first operational release:

- `candidate_resume_parse_logs`
- `candidate_screening_checks`
- `interview_rounds`
- `reports`
- `report_rows`
- `approval_requests`
- `notifications`
- `automation_jobs`
- `audit_logs`
- advanced analytics summary tables

### Required MVP User Fields

The `users` table must support:

- permission role reference
- business title reference
- reporting manager reference
- active/inactive status
- first-login credential state
- location assignment through separate tables
- team assignment through separate tables

### Required MVP Scope Rules

The `user_scope_assignments` table should support only:

- `global`
- `location`
- `team`
- `own`

If a user has no explicit scope rows, the backend should derive default access from:

- primary location assignment
- primary team membership
- ownership fields on records

### Required MVP Requisition Fields

The `requisitions` table must support:

- `hiring_type`
- `location_id`
- `client_id` nullable
- `title`
- `primary_owner_user_id`
- `priority`
- `status`
- `open_positions`
- `target_close_date`
- `sla_days` nullable
- `client_round_required`
- `structured_jd_json`

The MVP may defer:

- advanced scoring models
- complex difficulty modeling
- multiple commercial pricing structures

### Required MVP Candidate Fields

The `candidates` table and related workflow tables must support:

- identity fields such as name, email, phone
- source and sourcing notes
- owner and requisition linkage
- document linkage
- duplicate-check status
- current stage and stage history
- rejection reason and rejection side

The MVP may defer:

- parser-confidence history
- document-compliance scoring
- AI-generated enrichment fields

## 4. locations

- `id`
- `name`
- `code`
- `location`
- `address`
- `status`
- `location_head_user_id`
- `monthly_target_internal`
- `monthly_target_external`
- `weekly_target_internal`
- `weekly_target_external`
- `created_at`
- `updated_at`

Frontend usage:

- location management
- admin dashboard
- manager dashboard
- location-level reports

## 5. clients

- `id`
- `location_id`
- `parent_client_id` (nullable)
- `name`
- `relationship_type` (`direct-client`, `end-client`)
- `industry`
- `status`
- `client_owner_user_id`
- `business_source_owner_user_id` (nullable)
- `primary_contact_name`
- `primary_contact_email`
- `primary_contact_phone`
- `notes`
- `created_at`
- `updated_at`

Frontend usage:

- admin clients page
- manager clients page
- external requisitions
- meeting logs

## 6. client_contacts

- `id`
- `client_id`
- `full_name`
- `designation`
- `email`
- `phone`
- `is_primary`
- `status`
- `notes`
- `created_at`
- `updated_at`

Why this table is needed:

- the frontend will eventually need more than one contact per client
- meetings and follow-ups should be linkable to actual attendees

## 7. requisitions

- `id`
- `location_id`
- `hiring_type` (`internal`, `external`)
- `client_id` (nullable)
- `department_name` (nullable)
- `title`
- `primary_owner_user_id`
- `priority`
- `priority_score`
- `status`
- `open_positions`
- `target_close_date`
- `sla_days` (nullable)
- `criticality`
- `difficulty`
- `client_round_required`
- `budget_min` (nullable)
- `budget_max` (nullable)
- `currency_code` (nullable)
- `job_description`
- `important_notes` (nullable)
- `structured_jd_json`
- `created_at`
- `updated_at`

Frontend usage:

- structured requisition intake
- HR dashboard priority queue
- manager requisitions
- reports and pipeline

Implementation note:

- keep `client_id` on the requisition
- do not keep a single `end_client_id` here because one direct client can provide requirements for multiple optional end clients

## 7A. requisition_end_clients

- `id`
- `requisition_id`
- `client_id`
- `end_client_id`
- `is_primary`
- `notes` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the business flow now allows multiple optional end clients under one direct client
- a junction table keeps external hiring reporting accurate without forcing only one end client per requisition

## 8. requisition_skill_requirements

- `id`
- `requisition_id`
- `skill_name`
- `skill_type` (`must-have`, `good-to-have`)
- `priority_order`
- `notes` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the frontend shows structured skill expectations
- searchable and reportable skills work better here than only in JSON

## 9. requisition_screening_rules

- `id`
- `requisition_id`
- `allowed_gap_min_months` (nullable)
- `allowed_gap_max_months` (nullable)
- `max_notice_period_days` (nullable)
- `document_rules_json` (nullable)
- `compensation_rules_json` (nullable)
- `location_rules_json` (nullable)
- `custom_notes` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- HR screening desk
- structured JD notes
- rejection before client round

## 10. requisition_documents_required

- `id`
- `requisition_id`
- `document_type` (`resume`, `payslip`, `relieving-letter`, `offer-copy`, `government-id`, `other`)
- `is_mandatory`
- `notes` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the frontend explicitly tracks mandatory documents
- this keeps reporting cleaner than a free-form list only

## 11. candidates

- `id`
- `full_name`
- `email`
- `phone`
- `current_location` (nullable)
- `source`
- `source_portal` (nullable)
- `profile_status` (`draft`, `active`, `archived`)
- `intake_stage` (`uploaded`, `parsed`, `needs-review`, `duplicate-review`, `ready-to-save`, `finalized`)
- `total_experience_years` (nullable)
- `notice_period_days` (nullable)
- `current_ctc` (nullable)
- `expected_ctc` (nullable)
- `candidate_score` (nullable)
- `status`
- `created_by_user_id`
- `primary_owner_user_id` (nullable)
- `resume_file_name` (nullable)
- `resume_file_path` (nullable)
- `resume_uploaded_at` (nullable)
- `resume_parsing_status` (`pending`, `parsed`, `needs-review`, `failed`)
- `resume_parsing_confidence` (nullable)
- `resume_last_parsed_at` (nullable)
- `duplicate_check_status` (`not-started`, `in-review`, `cleared`, `merged`, `blocked`)
- `profile_expires_at` (nullable)
- `finalized_at` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- candidate profiles
- screening
- pipeline
- interviews
- resume upload with automatic prefill
- save draft and finalize candidate profile
- 1 month candidate profile life tracking

## 12. candidate_skills

- `id`
- `candidate_id`
- `skill_name`
- `experience_years` (nullable)
- `last_used_year` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- frontend candidate fit and skill matching become easier to filter
- useful for search and shortlist quality reporting

## 13. candidate_resume_parse_logs

- `id`
- `candidate_id`
- `source_document_id` (nullable)
- `parse_job_uuid`
- `parser_version`
- `raw_text_path` (nullable)
- `parsed_json`
- `field_confidence_json` (nullable)
- `duplicate_summary_json` (nullable)
- `review_status` (`pending`, `reviewed`, `rejected`)
- `reviewed_by_user_id` (nullable)
- `reviewed_at` (nullable)
- `failure_reason` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- resume parsing should be auditable
- parsed values should be reviewable before becoming trusted structured data
- useful when parser output needs correction or reprocessing

## 13A. candidate_duplicate_checks

- `id`
- `candidate_id`
- `parse_log_id` (nullable)
- `matched_candidate_id`
- `match_score`
- `match_level` (`low`, `possible`, `likely`, `exact`)
- `match_reason_json`
- `decision_status` (`pending`, `continue-as-new`, `merge-into-existing`, `cancelled`)
- `decided_by_user_id` (nullable)
- `decided_at` (nullable)
- `decision_notes` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the HR resume flow now includes an explicit duplicate review step
- duplicate suggestions and recruiter decisions should be stored separately from parser logs
- reporting needs to distinguish possible duplicates from actual merges or blocked saves

## 14. candidate_documents

- `id`
- `candidate_id`
- `document_type`
- `file_name`
- `file_path`
- `verification_status`
- `uploaded_by_user_id`
- `verified_by_user_id` (nullable)
- `verified_at` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- candidate profile page
- screening desk
- document-based rejection rules

## 15. candidate_applications

- `id`
- `candidate_id`
- `requisition_id`
- `owner_user_id`
- `current_stage`
- `screening_status`
- `application_status`
- `stage_reason` (nullable)
- `applied_at`
- `stage_updated_at`
- `expected_joining_date` (nullable)
- `rejection_side` (`internal`, `client`, `none`)
- `rejection_stage` (nullable)
- `rejection_reason` (nullable)
- `rejected_by_user_id` (nullable)
- `client_feedback_status` (`pending`, `positive`, `negative`, `hold`, `needs-more-profiles`, `duplicate-acknowledged`) (nullable)
- `client_feedback_notes` (nullable)
- `client_feedback_received_at` (nullable)
- `client_feedback_recorded_by_user_id` (nullable)
- `profiles_escalated_at` (nullable)
- `client_duplicate_flag`
- `client_duplicate_notes` (nullable)
- `risk_flags_json` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- candidate tracker
- screening queue
- pipeline board
- HR reports
- external escalation should depend on client feedback state

## 15A. candidate_stage_history

- `id`
- `candidate_application_id`
- `from_stage` (nullable)
- `to_stage`
- `change_reason` (nullable)
- `changed_by_user_id`
- `changed_at`
- `source_type` (`manual`, `automation`, `client-feedback`, `screening`, `interview`)
- `created_at`

Why this table is needed:

- the API exposes application timeline and stage movement
- reports need auditable stage transitions and aging calculations

## 16. candidate_screening_checks

- `id`
- `candidate_application_id`
- `check_type` (`must-have-skill`, `experience`, `employment-gap`, `document`, `compensation`, `notice-period`, `other`)
- `expected_value`
- `actual_value`
- `result` (`pass`, `fail`, `partial`, `not-applicable`)
- `notes` (nullable)
- `checked_by_user_id`
- `checked_at`
- `created_at`
- `updated_at`

Frontend usage:

- HR screening page
- structured rejection logic
- reporting quality checks

## 17. interview_rounds

- `id`
- `candidate_application_id`
- `round_type` (`internal`, `manager`, `client`)
- `round_name`
- `scheduled_at` (nullable)
- `interviewer_name` (nullable)
- `interviewer_user_id` (nullable)
- `status` (`scheduled`, `completed`, `rescheduled`, `cancelled`, `no-show`)
- `feedback_status`
- `decision` (nullable)
- `feedback_notes` (nullable)
- `created_by_user_id`
- `created_at`
- `updated_at`

Frontend usage:

- interview schedule
- candidate pipeline
- client round or no-client-round handling
- feedback capture handled by HR or Manager rather than Recruiter

## 18. meetings

- `id`
- `location_id`
- `client_id`
- `end_client_id` (nullable)
- `meeting_owner_user_id`
- `title`
- `meeting_type`
- `scheduled_at` (nullable)
- `attendance_status`
- `outcome_status`
- `agenda` (nullable)
- `minutes_of_meeting` (nullable)
- `decision_summary` (nullable)
- `next_steps` (nullable)
- `follow_up_owner_user_id` (nullable)
- `follow_up_due_date` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- manager meetings page
- client follow-up queue
- location report summaries

## 19. meeting_attendees

- `id`
- `meeting_id`
- `attendee_type` (`internal-user`, `client-contact`)
- `user_id` (nullable)
- `client_contact_id` (nullable)
- `attendance_status`
- `notes` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the frontend talks about client attendance and no-shows
- this allows more than one attendee to be tracked properly

## 20. portal_accounts

- `id`
- `location_id`
- `platform_name`
- `account_name`
- `login_identifier`
- `status`
- `ownership_type`
- `owned_by_user_id` (nullable)
- `is_shared`
- `has_full_access`
- `daily_usage_limit_hours` (nullable)
- `notes` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- HR portal access page
- user access review
- productivity reporting

## 21. portal_account_slots

- `id`
- `portal_account_id`
- `assigned_user_id`
- `usage_date`
- `start_time`
- `end_time`
- `status`
- `approved_by_user_id` (nullable)
- `notes` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- scheduled Naukri or LinkedIn usage windows
- location utilization reporting
- approval queue

## 22. daily_updates

- `id`
- `location_id`
- `submitted_by_user_id`
- `update_date`
- `summary`
- `blockers` (nullable)
- `planned_next_actions` (nullable)
- `portal_usage_summary` (nullable)
- `high_priority_roles_json` (nullable)
- `candidate_movements_json` (nullable)
- `internal_call_count` (nullable)
- `profiles_escalated_count` (nullable)
- `hiring_type_summary_json` (nullable)
- `submitted_at`
- `created_at`
- `updated_at`

Why this table is needed:

- the business flow treats daily inputs as feeder data for weekly and monthly reports
- this table supports operational follow-up and reporting summaries
- external hiring reporting can ignore recruiter call count while still using escalation totals

## 23. reports

- `id`
- `location_id` (nullable)
- `submitted_by_user_id` (nullable)
- `report_scope`
- `report_type` (`weekly`, `monthly`)
- `period_start`
- `period_end`
- `status`
- `quality_score` (nullable)
- `submitted_at` (nullable)
- `reviewed_by_user_id` (nullable)
- `reviewed_at` (nullable)
- `summary_json`
- `generated_by_system`
- `report_rules_json` (nullable)
- `generated_from_daily_inputs`
- `generation_job_id` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- admin reports
- manager reports
- HR reports
- recruiter reports

Why these extra fields are needed:

- weekly and monthly reports are now expected to be generated from daily feeder data where possible
- linking reports to automation jobs keeps report generation traceable and easier to rerun

## 23A. report_rows

- `id`
- `report_id`
- `report_scope` (`admin`, `manager`, `hr`, `recruiter`)
- `report_type` (`weekly`, `monthly`)
- `row_date`
- `recruiter_user_id` (nullable)
- `hr_user_id` (nullable)
- `lead_user_id` (nullable)
- `candidate_id` (nullable)
- `candidate_application_id` (nullable)
- `client_id` (nullable)
- `requisition_id` (nullable)
- `role_title` (nullable)
- `employment_type` (`contract`, `permanent`) (nullable)
- `current_status` (nullable)
- `internal_screen_reject`
- `client_reject`
- `l1_status` (nullable)
- `l2_status` (nullable)
- `interview_mode` (nullable)
- `offer_letter_status` (nullable)
- `date_of_joining` (nullable)
- `remarks` (nullable)
- `profiles_escalated_count` (nullable)
- `internal_call_count` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- weekly and monthly reports now need a structured tabular format
- keeps export-ready report rows separate from raw operational tables
- allows role-specific reporting rules, such as hiding external recruiter call counts while preserving internal call metrics

## 23B. report_locks

- `id`
- `report_scope`
- `location_id` (nullable)
- `report_type` (`weekly`, `monthly`)
- `period_start`
- `period_end`
- `lock_status` (`open`, `locked`, `reopened`)
- `locked_by_user_id` (nullable)
- `locked_at` (nullable)
- `reopened_by_user_id` (nullable)
- `reopened_at` (nullable)
- `notes` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- the admin reports flow includes period locking behavior
- official reporting periods should not depend on a free-form report status only
- this gives the backend a clear source of truth for editability and regeneration rules

## 24. approval_requests

- `id`
- `location_id`
- `request_type`
- `source_type`
- `source_id`
- `requested_by_user_id`
- `assigned_to_user_id` (nullable)
- `priority`
- `status`
- `decision` (nullable)
- `decision_notes` (nullable)
- `decided_by_user_id` (nullable)
- `decided_at` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- approvals inbox
- access review queue
- portal extension approvals
- exceptional screening decisions

## 25. notifications

- `id`
- `location_id` (nullable)
- `user_id`
- `event_type`
- `source_type`
- `source_id`
- `message`
- `priority`
- `status`
- `read_at` (nullable)
- `delivered_at` (nullable)
- `action_url` (nullable)
- `created_at`
- `updated_at`

Frontend usage:

- admin notifications
- manager notifications
- HR notifications

Implementation note:

- this table is for persistent in-app notifications only
- prototype-only local notifications generated in frontend JS should not be written here unless the backend notification service explicitly promotes them

## 25A. automation_jobs

- `id`
- `job_type` (`resume-parse`, `duplicate-check`, `report-generation`, `priority-queue-rebuild`, `notification-batch`)
- `scope_type` (`system`, `location`, `user`, `report`, `candidate`)
- `scope_id` (nullable)
- `status` (`queued`, `running`, `completed`, `failed`, `cancelled`)
- `triggered_by_user_id` (nullable)
- `input_json` (nullable)
- `output_json` (nullable)
- `warning_json` (nullable)
- `error_message` (nullable)
- `started_at` (nullable)
- `completed_at` (nullable)
- `created_at`
- `updated_at`

Why this table is needed:

- automation is now part of the product direction
- resume parsing, duplicate review, priority generation, and report generation all need trackable background execution

Implementation note:

- do not create automation job records for lightweight frontend-only helpers
- only backend-executed or auditable automations should be stored here
- local daily-update draft writing, local duplicate warnings, local report summaries, and local notification counters remain frontend-only and should not create database rows

## 26. audit_logs

- `id`
- `actor_user_id`
- `location_id` (nullable)
- `entity_type`
- `entity_id`
- `action_type`
- `old_values_json` (nullable)
- `new_values_json` (nullable)
- `ip_address` (nullable)
- `user_agent` (nullable)
- `created_at`

Why this table is needed:

- approvals, access changes, and rejection changes should be auditable
- useful for compliance and debugging

## Dashboard and Reporting Views

These should usually be implemented as SQL views or materialized views, not editable tables.

## 1. vw_location_performance_summary

Includes:

- location
- manager
- open requisitions
- weekly update completion
- closure counts
- risk status

## 2. vw_recruiter_productivity_summary

Includes:

- recruiter
- location
- active requisitions
- sourced candidates
- screened candidates
- portal usage hours
- daily update completion

## 3. vw_client_delivery_summary

Includes:

- client
- end client
- open external roles
- meeting count
- shortlist count
- client rejection count
- closure rate

## 4. vw_pipeline_stage_summary

Includes:

- requisition
- current stage counts
- stalled profiles
- interview counts
- offer counts

## 5. vw_notification_summary

Includes:

- user
- unread count
- urgent count
- overdue action count

## Frontend to Database Mapping

Page names below are the live routed pages under `frontend/pages/` (see
`frontend/route-manifest.json`).

## Admin frontend

- Role Dashboard (`role-dashboard.html`)
  Uses `locations`, `user_location_roles`, `requisitions`, `approval_requests`, `reports`
- Location Management (`location-management.html`)
  Uses `locations`, `user_location_roles`
- User Management (`user-management.html`)
  Uses `users`, `roles`, `user_location_roles`, `user_invitations`, `portal_account_slots`
- Client Directory (`client-directory.html`)
  Uses `clients`, `client_contacts`, `meetings`, `requisitions`
- Reports (`reports.html`)
  Uses `reports`, `report_rows`, `report_locks`, `daily_updates`, dashboard views
- Approvals Inbox (`approvals-inbox.html`)
  Uses `approval_requests`, `audit_logs`
- Notifications Center (`notifications-center.html`)
  Uses `notifications`

## Manager frontend

- Role Dashboard (`role-dashboard.html`)
  Uses `user_location_roles`, `requisitions`, `meetings`, `reports`
- Client Directory (`client-directory.html`), Client Detail (`client-detail.html`)
  Uses `clients`, `client_contacts`, `requisitions`
- Meetings (`meetings.html`)
  Uses `meetings`, `meeting_attendees`
- Requisition List (`requisition-list.html`)
  Uses `requisitions`, `candidate_applications`, `requisition_screening_rules`
- Reports (`reports.html`)
  Uses `reports`, `report_rows`, dashboard views
- Notifications Center (`notifications-center.html`)
  Uses `notifications`

## HR frontend

- Role Dashboard (`role-dashboard.html`)
  Uses `requisitions`, `candidate_applications`, `portal_account_slots`, `daily_updates`
- Requisition Intake (`requisition-intake.html`)
  Uses `requisitions`, `requisition_end_clients`, `requisition_skill_requirements`, `requisition_screening_rules`, `requisition_documents_required`
- Candidate Profiles (`candidate-profiles.html`)
  Uses `candidates`, `candidate_skills`, `candidate_resume_parse_logs`, `candidate_duplicate_checks`, `candidate_documents`, `candidate_applications`
- Candidate Screening (`candidate-screening.html`)
  Uses `candidate_applications`, `candidate_screening_checks`, `requisition_screening_rules`
- Pipeline Board (`pipeline-board.html`)
  Uses `candidate_applications`, `interview_rounds`
- Interview Scheduler (`interview-scheduler.html`)
  Uses `interview_rounds`, `candidate_applications`
- Portal Accounts (`portal-accounts.html`)
  Uses `portal_accounts`, `portal_account_slots`
- Delivery Reports (`reports.html`)
  Uses `daily_updates`, `reports`, `report_rows`
- Notifications Center (`notifications-center.html`)
  Uses `notifications`

## Recruiter frontend

- Role Dashboard (`role-dashboard.html`)
  Uses `requisitions`, `candidates`, `portal_account_slots`, `daily_updates`
- Candidate Profiles (`candidate-profiles.html`)
  Uses `candidates`, `candidate_resume_parse_logs`, `candidate_duplicate_checks`, `candidate_documents`
- Recruiter Productivity Reports (`user-performance-reports.html`)
  Uses `daily_updates`, `reports`, `report_rows`
- Notifications Center (`notifications-center.html`)
  Uses `notifications`

## Key Relationships

- `users.primary_role_id -> roles.id`
- `users.reporting_manager_user_id -> users.id`
- `user_invitations.user_id -> users.id`
- `user_invitations.sent_by_user_id -> users.id`
- `user_location_roles.user_id -> users.id`
- `user_location_roles.location_id -> locations.id`
- `user_location_roles.role_id -> roles.id`
- `locations.location_head_user_id -> users.id`
- `clients.location_id -> locations.id`
- `clients.parent_client_id -> clients.id`
- `client_contacts.client_id -> clients.id`
- `requisitions.location_id -> locations.id`
- `requisitions.client_id -> clients.id`
- `requisitions.primary_owner_user_id -> users.id`
- `requisition_end_clients.requisition_id -> requisitions.id`
- `requisition_end_clients.client_id -> clients.id`
- `requisition_end_clients.end_client_id -> clients.id`
- `requisition_skill_requirements.requisition_id -> requisitions.id`
- `requisition_screening_rules.requisition_id -> requisitions.id`
- `requisition_documents_required.requisition_id -> requisitions.id`
- `candidate_skills.candidate_id -> candidates.id`
- `candidate_resume_parse_logs.candidate_id -> candidates.id`
- `candidate_duplicate_checks.candidate_id -> candidates.id`
- `candidate_duplicate_checks.parse_log_id -> candidate_resume_parse_logs.id`
- `candidate_duplicate_checks.matched_candidate_id -> candidates.id`
- `candidate_documents.candidate_id -> candidates.id`
- `candidate_applications.candidate_id -> candidates.id`
- `candidate_applications.requisition_id -> requisitions.id`
- `candidate_applications.owner_user_id -> users.id`
- `candidate_applications.client_feedback_recorded_by_user_id -> users.id`
- `candidate_screening_checks.candidate_application_id -> candidate_applications.id`
- `interview_rounds.candidate_application_id -> candidate_applications.id`
- `meetings.client_id -> clients.id`
- `meetings.end_client_id -> clients.id`
- `meetings.meeting_owner_user_id -> users.id`
- `meeting_attendees.meeting_id -> meetings.id`
- `meeting_attendees.user_id -> users.id`
- `meeting_attendees.client_contact_id -> client_contacts.id`
- `portal_accounts.location_id -> locations.id`
- `portal_accounts.owned_by_user_id -> users.id`
- `portal_account_slots.portal_account_id -> portal_accounts.id`
- `portal_account_slots.assigned_user_id -> users.id`
- `daily_updates.location_id -> locations.id`
- `daily_updates.submitted_by_user_id -> users.id`
- `reports.location_id -> locations.id`
- `reports.submitted_by_user_id -> users.id`
- `reports.generation_job_id -> automation_jobs.id`
- `report_rows.report_id -> reports.id`
- `report_locks.location_id -> locations.id`
- `report_locks.locked_by_user_id -> users.id`
- `report_locks.reopened_by_user_id -> users.id`
- `approval_requests.requested_by_user_id -> users.id`
- `approval_requests.assigned_to_user_id -> users.id`
- `notifications.user_id -> users.id`
- `audit_logs.actor_user_id -> users.id`

## Priority Logic Inputs

The frontend priority queue should be calculated from:

- `requisitions.target_close_date`
- `requisitions.priority`
- `requisitions.priority_score`
- `requisitions.criticality`
- `requisitions.sla_days`
- number of open positions
- age of current stage in `candidate_applications`
- pending portal slot timing in `portal_account_slots`

## Implementation Notes

- Keep JSON only for flexible summary payloads and snapshots
- Keep reporting-critical inputs normalized where possible
- Store rejection side and rejection reason separately
- Do not make optional business fields mandatory in schema unless reporting truly requires them
- Add indexes early on:
  `users.email`, `user_invitations(user_id, invite_status)`, `user_location_roles(location_id, role_id)`, `requisitions(location_id, status, target_close_date)`, `candidates(email, phone, intake_stage)`, `candidate_duplicate_checks(candidate_id, decision_status)`, `candidate_applications(requisition_id, current_stage)`, `notifications(user_id, status)`, `approval_requests(status, priority)`
