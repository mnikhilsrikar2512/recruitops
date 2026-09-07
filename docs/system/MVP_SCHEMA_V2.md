# MVP Schema V2

## Purpose

This document defines the revised MVP database structure after aligning the schema with:

- final product decisions
- system rules and validations
- configurable role model
- permission code model

This version replaces the earlier assumptions that:

- operational roles are fixed
- candidates are location-bound
- duplicate handling is only a warning
- pipeline stages are globally fixed

## Core MVP Principles

- `Admin` is the only fixed product role
- all other roles are configurable
- every operational user belongs to a location
- every operational record belongs to a location unless it is a global configuration record
- clients are location-bound
- candidates are global at company level
- candidate access is controlled by role, scope, and requisition linkage
- one requisition has one primary owner and optional delivery owner
- duplicate handling is a persisted review workflow
- report locks are persisted
- audit access is permission-controlled and auditable

## Table Groups

The MVP schema should be organized into these groups:

1. Location and user identity
2. Role and permission configuration
3. Client and requisition workflow
4. Candidate and pipeline workflow
5. Duplicate review and transfer control
6. Daily updates and reporting
7. Audit and approval support

## 1. Location And User Identity

## 1.1 `locations`

Purpose:

- define operating boundaries
- support location-scoped access and reporting

Columns:

- `id` bigint primary key
- `location_code` varchar(50) unique not null
- `location_name` varchar(150) not null
- `city` varchar(100) null
- `state` varchar(100) null
- `country` varchar(100) null
- `timezone` varchar(100) null
- `status` varchar(30) not null default `active`
- `location_head_user_id` bigint null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

## 1.2 `users`

Purpose:

- store user identity, login, reporting, and primary operating location

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `employee_code` varchar(50) unique not null
- `full_name` varchar(150) not null
- `email` varchar(190) unique not null
- `phone` varchar(30) not null
- `password_hash` varchar(255) not null
- `status` varchar(30) not null default `active`
- `primary_role_id` bigint not null
- `business_title` varchar(100) null
- `reporting_manager_user_id` bigint not null
- `last_login_at` datetime null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- Admin may exist outside normal operational location rules if needed by implementation, but operational users should always have a location
- one primary role is required
- extra permissions are handled separately

## 1.3 `user_role_assignments`

Purpose:

- keep history of user-role-location assignment

Columns:

- `id` bigint primary key
- `user_id` bigint not null
- `role_id` bigint not null
- `location_id` bigint not null
- `is_primary` bit not null default 0
- `status` varchar(30) not null default `active`
- `effective_from` date not null
- `effective_to` date null
- `created_at` datetime not null
- `updated_at` datetime not null

## 1.4 `user_extra_permissions`

Purpose:

- support one primary role plus extra permissions

Columns:

- `id` bigint primary key
- `user_id` bigint not null
- `permission_id` bigint not null
- `granted_by_user_id` bigint not null
- `status` varchar(30) not null default `active`
- `created_at` datetime not null
- `updated_at` datetime not null

## 2. Role And Permission Configuration

## 2.1 `roles`

Purpose:

- store configurable operational roles

Columns:

- `id` bigint primary key
- `code` varchar(50) unique not null
- `name` varchar(100) not null
- `description` varchar(300) null
- `is_system_role` bit not null default 0
- `status` varchar(30) not null default `active`
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- `Admin` is the only mandatory system role
- all others may be created by Admin

## 2.2 `permissions`

Purpose:

- store stable backend permission codes

Columns:

- `id` bigint primary key
- `code` varchar(100) unique not null
- `module_name` varchar(100) not null
- `action_name` varchar(100) not null
- `description` varchar(500) null
- `is_sensitive` bit not null default 0
- `created_at` datetime not null
- `updated_at` datetime not null

## 2.3 `role_permissions`

Purpose:

- map roles to permission codes

Columns:

- `id` bigint primary key
- `role_id` bigint not null
- `permission_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

## 2.4 `role_templates`

Purpose:

- provide protected starter role templates

Columns:

- `id` bigint primary key
- `code` varchar(50) unique not null
- `name` varchar(100) not null
- `description` varchar(300) null
- `is_protected` bit not null default 1
- `status` varchar(30) not null default `active`
- `created_at` datetime not null
- `updated_at` datetime not null

## 2.5 `role_template_permissions`

Purpose:

- define permission bundles for starter templates

Columns:

- `id` bigint primary key
- `role_template_id` bigint not null
- `permission_id` bigint not null
- `created_at` datetime not null

## 3. Client And Requisition Workflow

## 3.1 `clients`

Purpose:

- store client records owned by one location

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `client_code` varchar(50) unique not null
- `client_name` varchar(200) not null
- `industry` varchar(100) null
- `status` varchar(30) not null default `active`
- `business_source_owner_user_id` bigint not null
- `created_by_user_id` bigint not null
- `client_owner_user_id` bigint not null
- `notes` text null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- one client belongs to one location
- no default multi-location sharing in MVP

## 3.2 `client_contacts`

Purpose:

- store client contact records

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `client_id` bigint not null
- `contact_name` varchar(150) not null
- `email` varchar(190) null
- `phone` varchar(30) null
- `designation` varchar(100) null
- `is_primary_contact` bit not null default 0
- `is_secondary_contact` bit not null default 0
- `status` varchar(30) not null default `active`
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

## 3.3 `client_access_requests`

Purpose:

- allow another location to request access to a location-bound client

Columns:

- `id` bigint primary key
- `client_id` bigint not null
- `requested_by_user_id` bigint not null
- `requesting_location_id` bigint not null
- `approval_status` varchar(30) not null default `pending`
- `approved_by_user_id` bigint null
- `approval_notes` text null
- `created_at` datetime not null
- `updated_at` datetime not null

## 3.4 `requisitions`

Purpose:

- store structured hiring requirements

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `client_id` bigint not null
- `primary_contact_id` bigint not null
- `secondary_contact_id` bigint not null
- `requisition_code` varchar(50) unique not null
- `job_title` varchar(150) not null
- `employment_type` varchar(50) null
- `work_mode` varchar(50) null
- `experience_min_years` decimal(4,1) null
- `experience_max_years` decimal(4,1) null
- `current_work_location_text` varchar(200) null
- `openings_count` int not null default 1
- `priority` varchar(30) not null default `medium`
- `status` varchar(30) not null default `open`
- `target_closure_date` date not null
- `jd_text` text null
- `required_skills_json` text not null
- `good_to_have_skills_json` text null
- `acceptable_career_gap_months` int null
- `preferred_update_time_text` varchar(100) not null
- `primary_owner_user_id` bigint not null
- `delivery_owner_user_id` bigint null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

## 3.5 `requisition_assignments`

Purpose:

- assign one requisition to one primary owner and additional contributors

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `requisition_id` bigint not null
- `assigned_user_id` bigint not null
- `assignment_type` varchar(30) not null
- `assigned_by_user_id` bigint not null
- `assigned_at` datetime not null
- `status` varchar(30) not null default `active`
- `created_at` datetime not null
- `updated_at` datetime not null

Suggested assignment types:

- `primary_owner`
- `delivery_owner`
- `contributor`
- `support`

## 4. Candidate And Pipeline Workflow

## 4.1 `candidates`

Purpose:

- store global company-level candidate identity

Columns:

- `id` bigint primary key
- `candidate_code` varchar(50) unique not null
- `full_name` varchar(150) not null
- `email` varchar(190) null
- `phone` varchar(30) null
- `current_company` varchar(150) not null
- `current_designation` varchar(150) null
- `total_experience_years` decimal(4,1) null
- `current_location_text` varchar(150) null
- `preferred_location_text` varchar(150) null
- `notice_period_days` int null
- `current_ctc` decimal(14,2) null
- `expected_ctc` decimal(14,2) null
- `source_type` varchar(50) not null
- `source_detail` varchar(150) null
- `resume_file_path` varchar(500) not null
- `linkedin_url` varchar(500) null
- `github_url` varchar(500) null
- `portfolio_url` varchar(500) null
- `social_profiles_json` text null
- `profile_summary` text null
- `status` varchar(30) not null default `active`
- `source_owner_user_id` bigint not null
- `primary_owner_user_id` bigint not null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- candidate identity is global
- location is ownership metadata, not a hard partition boundary

## 4.2 `candidate_applications`

Purpose:

- connect candidates to requisitions
- store requisition-specific pipeline progress

Columns:

- `id` bigint primary key
- `requisition_id` bigint not null
- `candidate_id` bigint not null
- `submitted_by_user_id` bigint not null
- `owner_user_id` bigint not null
- `pipeline_template_id` bigint not null
- `current_stage_code` varchar(50) not null
- `stage_updated_at` datetime not null
- `last_activity_at` datetime not null
- `stale_after_days` int null
- `is_shortlisted` bit not null default 0
- `is_joined` bit not null default 0
- `rejection_reason` varchar(200) null
- `rejection_notes` text null
- `status` varchar(30) not null default `active`
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- this is the canonical MVP name for requisition-linked candidate workflow
- older planning language may still refer to `candidate_requisition_links`
- backend implementation should use `candidate_applications`

## 4.3 `candidate_stage_history`

Purpose:

- audit every stage change

Columns:

- `id` bigint primary key
- `candidate_application_id` bigint not null
- `candidate_id` bigint not null
- `requisition_id` bigint not null
- `from_stage_code` varchar(50) null
- `to_stage_code` varchar(50) not null
- `changed_by_user_id` bigint not null
- `change_notes` text null
- `changed_at` datetime not null

## 4.4 `pipeline_stage_library`

Purpose:

- store reusable master stage definitions

Columns:

- `id` bigint primary key
- `code` varchar(50) unique not null
- `name` varchar(100) not null
- `sequence_order` int not null
- `is_terminal` bit not null default 0
- `created_at` datetime not null
- `updated_at` datetime not null

## 4.5 `pipeline_templates`

Purpose:

- store Admin-managed stage templates

Columns:

- `id` bigint primary key
- `name` varchar(150) not null
- `description` varchar(300) null
- `status` varchar(30) not null default `active`
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

## 4.6 `pipeline_template_stages`

Purpose:

- store ordered stage membership for each template

Columns:

- `id` bigint primary key
- `pipeline_template_id` bigint not null
- `stage_library_id` bigint not null
- `display_name` varchar(100) not null
- `sequence_order` int not null
- `is_required` bit not null default 1

## 5. Duplicate Review And Transfer Control

## 5.1 `duplicate_review_cases`

Purpose:

- persist compare-first duplicate review workflow

Columns:

- `id` bigint primary key
- `existing_candidate_id` bigint not null
- `new_candidate_payload_json` text not null
- `requested_by_user_id` bigint not null
- `review_status` varchar(30) not null default `pending`
- `decision` varchar(30) null
- `decided_by_user_id` bigint null
- `decision_notes` text null
- `created_at` datetime not null
- `updated_at` datetime not null

Suggested decision values:

- `override`
- `discard`
- `link_existing`

## 5.2 `candidate_location_transfer_requests`

Purpose:

- persist candidate transfer approval between locations

Columns:

- `id` bigint primary key
- `candidate_id` bigint not null
- `from_location_id` bigint not null
- `to_location_id` bigint not null
- `requested_by_user_id` bigint not null
- `approval_status` varchar(30) not null default `pending`
- `approved_by_user_id` bigint null
- `approval_notes` text null
- `created_at` datetime not null
- `updated_at` datetime not null

## 6. Daily Updates And Reporting

## 6.1 `daily_updates`

Purpose:

- store one main daily summary and optional extra updates

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `submitted_by_user_id` bigint not null
- `requisition_id` bigint not null
- `update_date` date not null
- `summary` text not null
- `profiles_sourced_count` int null
- `profiles_screened_count` int null
- `profiles_submitted_count` int null
- `interviews_scheduled_count` int null
- `offers_closed_count` int null
- `blockers` text null
- `planned_next_actions` text null
- `submission_status` varchar(30) not null default `submitted`
- `reviewed_by_user_id` bigint null
- `reviewed_at` datetime null
- `submitted_at` datetime not null
- `created_at` datetime not null
- `updated_at` datetime not null

## 6.2 `report_locks`

Purpose:

- persist weekly and monthly report lock state

Columns:

- `id` bigint primary key
- `report_type` varchar(30) not null
- `location_id` bigint null
- `period_start` date not null
- `period_end` date not null
- `lock_status` varchar(30) not null
- `locked_by_user_id` bigint not null
- `locked_at` datetime not null
- `unlocked_by_user_id` bigint null
- `unlocked_at` datetime null

Suggested report types:

- `weekly`
- `monthly`

Suggested statuses:

- `locked`
- `unlocked`

## 7. Audit And Approval Support

## 7.1 `approval_requests`

Purpose:

- store approval workflows for critical actions

Columns:

- `id` bigint primary key
- `request_type` varchar(50) not null
- `source_type` varchar(50) not null
- `source_id` bigint not null
- `location_id` bigint not null
- `requested_by_user_id` bigint not null
- `assigned_to_user_id` bigint null
- `priority` varchar(30) not null default `normal`
- `status` varchar(30) not null default `pending`
- `decision` varchar(30) null
- `decision_notes` text null
- `decided_by_user_id` bigint null
- `decided_at` datetime null
- `created_at` datetime not null
- `updated_at` datetime not null

## 7.2 `audit_logs`

Purpose:

- store sensitive action history

Columns:

- `id` bigint primary key
- `actor_user_id` bigint not null
- `location_id` bigint null
- `entity_type` varchar(50) not null
- `entity_id` bigint not null
- `action_type` varchar(50) not null
- `old_values_json` text null
- `new_values_json` text null
- `created_at` datetime not null

## 7.3 `audit_log_access_events`

Purpose:

- log audit-log viewing itself

Columns:

- `id` bigint primary key
- `actor_user_id` bigint not null
- `accessed_user_id` bigint null
- `location_id` bigint null
- `access_type` varchar(50) not null
- `source_type` varchar(50) not null
- `source_id` bigint null
- `access_notes` text null
- `created_at` datetime not null

## Key Foreign Keys

- `users.location_id -> locations.id`
- `users.primary_role_id -> roles.id`
- `users.reporting_manager_user_id -> users.id`
- `locations.location_head_user_id -> users.id`
- `user_role_assignments.user_id -> users.id`
- `user_role_assignments.role_id -> roles.id`
- `user_role_assignments.location_id -> locations.id`
- `user_extra_permissions.user_id -> users.id`
- `user_extra_permissions.permission_id -> permissions.id`
- `roles.created_by_user_id -> users.id`
- `role_permissions.role_id -> roles.id`
- `role_permissions.permission_id -> permissions.id`
- `role_template_permissions.role_template_id -> role_templates.id`
- `role_template_permissions.permission_id -> permissions.id`
- `clients.location_id -> locations.id`
- `clients.business_source_owner_user_id -> users.id`
- `clients.created_by_user_id -> users.id`
- `clients.client_owner_user_id -> users.id`
- `client_contacts.location_id -> locations.id`
- `client_contacts.client_id -> clients.id`
- `client_access_requests.client_id -> clients.id`
- `client_access_requests.requesting_location_id -> locations.id`
- `requisitions.location_id -> locations.id`
- `requisitions.client_id -> clients.id`
- `requisitions.primary_contact_id -> client_contacts.id`
- `requisitions.secondary_contact_id -> client_contacts.id`
- `requisitions.primary_owner_user_id -> users.id`
- `requisitions.delivery_owner_user_id -> users.id`
- `requisition_assignments.requisition_id -> requisitions.id`
- `requisition_assignments.assigned_user_id -> users.id`
- `candidates.source_owner_user_id -> users.id`
- `candidates.primary_owner_user_id -> users.id`
- `candidate_applications.candidate_id -> candidates.id`
- `candidate_applications.requisition_id -> requisitions.id`
- `candidate_applications.pipeline_template_id -> pipeline_templates.id`
- `candidate_stage_history.candidate_application_id -> candidate_applications.id`
- `pipeline_template_stages.pipeline_template_id -> pipeline_templates.id`
- `pipeline_template_stages.stage_library_id -> pipeline_stage_library.id`
- `duplicate_review_cases.existing_candidate_id -> candidates.id`
- `candidate_location_transfer_requests.candidate_id -> candidates.id`
- `candidate_location_transfer_requests.from_location_id -> locations.id`
- `candidate_location_transfer_requests.to_location_id -> locations.id`
- `daily_updates.location_id -> locations.id`
- `daily_updates.submitted_by_user_id -> users.id`
- `daily_updates.requisition_id -> requisitions.id`
- `report_locks.location_id -> locations.id`
- `approval_requests.location_id -> locations.id`
- `approval_requests.requested_by_user_id -> users.id`
- `audit_logs.actor_user_id -> users.id`
- `audit_log_access_events.actor_user_id -> users.id`

## Key Indexes

Recommended indexes:

- `users(email)`
- `users(employee_code)`
- `users(location_id, primary_role_id, status)`
- `clients(location_id, status)`
- `requisitions(location_id, status, target_closure_date)`
- `requisitions(primary_owner_user_id, status)`
- `candidates(email)`
- `candidates(phone)`
- `candidates(full_name)`
- `candidates(source_owner_user_id, primary_owner_user_id, status)`
- `candidate_applications(requisition_id, current_stage_code, status)`
- `candidate_applications(candidate_id, requisition_id)`
- `duplicate_review_cases(existing_candidate_id, review_status)`
- `candidate_location_transfer_requests(candidate_id, approval_status)`
- `daily_updates(location_id, submitted_by_user_id, update_date)`
- `report_locks(location_id, report_type, period_start, period_end, lock_status)`

## Implementation Note

The validated implementation SQL as of Tuesday, August 18, 2026 uses these finalized names:

- `clients` instead of `client_companies`
- `daily_updates` instead of `recruiter_daily_updates`
- `locations.location_head_user_id`
- `users.primary_role_id` without a separate `default_role_id`
- `meetings.meeting_owner_user_id`
- `report_rows.lead_user_id`

## Final Notes

This schema version is the correct direction for MVP because it:

- matches the Admin-configured role model
- keeps location control strong
- keeps clients location-bound
- keeps candidates global but controlled
- keeps client business source ownership explicit
- persists duplicate review logic
- supports pipeline template variation
- uses canonical `candidate_applications` naming for requisition-linked candidate workflow
- keeps daily updates tied to requisitions for execution reporting
- supports report locking
- supports auditable approval and access control
