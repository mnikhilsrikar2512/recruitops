# MVP Use Case DB Contracts

## Purpose

This document turns the MVP use cases into database-side implementation contracts.

It does not replace the schema reference documents.

Instead, it explains what the database must guarantee for each important MVP business flow.

This file answers:

- which tables are required per use case
- which fields are mandatory
- which foreign keys are required
- which unique or conflict rules are required
- which statuses or enum-like values are needed
- which lifecycle rules must be preserved in data

Use this document when:

- preparing migrations
- validating schema completeness
- writing service-level validations
- reviewing whether a use case is truly supported end to end

Read this together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`
- `docs/system/MVP_SCHEMA_V2.md`
- `docs/system/DATABASE_DESIGN.md`

## Contract Style

Each use case below includes:

- required tables
- required fields
- key relationships
- constraint rules
- status or lifecycle rules
- completion proof

## Group 1. Access And Setup

### UC-01 User Login

Required tables:

- `users`
- `roles`
- `permissions`
- `role_permissions`
- session store or `user_sessions` if persisted

Required fields:

- `users.email`
- `users.password_hash`
- `users.status`
- `users.location_id`
- `users.primary_role_id`
- `users.last_login_at`

Key relationships:

- `users.location_id -> locations.id`
- `users.primary_role_id -> roles.id`
- `role_permissions.role_id -> roles.id`
- `role_permissions.permission_id -> permissions.id`

Constraint rules:

- `users.email` must be unique
- `users.password_hash` must never be null for active login-based users

Status or lifecycle rules:

- user status must support at least `active` and non-active blocked states
- last login should be writable without breaking identity history

Completion proof:

- one active user row can resolve to one valid role and one valid location context for login

### UC-03 Create Custom Role

Required tables:

- `roles`
- `permissions`
- `role_permissions`

Required fields:

- `roles.code`
- `roles.name`
- `roles.status`
- `permissions.code`

Key relationships:

- `role_permissions.role_id -> roles.id`
- `role_permissions.permission_id -> permissions.id`

Constraint rules:

- `roles.code` unique
- `permissions.code` unique
- one role-permission mapping should not duplicate

Recommended unique rule:

- unique `role_permissions(role_id, permission_id)`

Status or lifecycle rules:

- `roles.status` should support `active` and `inactive`
- Admin remains the only mandatory system role, others are configurable records

Completion proof:

- a newly created role can store a unique code and a reusable permission mapping set

### UC-05 Create Location

Required tables:

- `locations`

Required fields:

- `locations.location_code`
- `locations.location_name`
- `locations.status`
- `locations.created_by_user_id`

Key relationships:

- `locations.location_head_user_id -> users.id`
- `locations.created_by_user_id -> users.id`

Constraint rules:

- `location_code` unique

Status or lifecycle rules:

- `status` should support at least `active` and `inactive`
- location deactivation should not automatically delete linked operational data

Completion proof:

- location can be referenced safely by users, clients, requisitions, and daily updates

### UC-06 Create User

Required tables:

- `users`
- `locations`
- `roles`
- `user_role_assignments`

Required fields:

- `users.employee_code`
- `users.full_name`
- `users.email`
- `users.phone`
- `users.location_id`
- `users.primary_role_id`
- `users.reporting_manager_user_id`
- `users.status`
- `user_role_assignments.user_id`
- `user_role_assignments.role_id`
- `user_role_assignments.location_id`

Key relationships:

- `users.location_id -> locations.id`
- `users.primary_role_id -> roles.id`
- `users.reporting_manager_user_id -> users.id`
- `user_role_assignments.user_id -> users.id`
- `user_role_assignments.role_id -> roles.id`
- `user_role_assignments.location_id -> locations.id`

Constraint rules:

- `employee_code` unique if company requires it globally
- `email` unique
- self-reference for reporting manager must be blocked at application level

Recommended unique rules:

- unique `user_role_assignments(user_id, role_id, location_id, effective_from)` or equivalent non-duplicating history rule

Status or lifecycle rules:

- `users.status` should support `active`, `inactive`, `suspended`
- role-assignment history should preserve prior mappings rather than overwrite them invisibly

Completion proof:

- one user can be stored with one primary location, one primary role, and traceable assignment history

## Group 2. Client And Requisition Operations

### UC-08 Create Client Under A Location

Required tables:

- `clients`
- `locations`
- `users`

Required fields:

- `clients.location_id`
- `clients.client_code`
- `clients.client_name`
- `clients.business_source_owner_user_id`
- `clients.client_owner_user_id`
- `clients.status`
- `clients.created_by_user_id`

Key relationships:

- `clients.location_id -> locations.id`
- `clients.business_source_owner_user_id -> users.id`
- `clients.client_owner_user_id -> users.id`
- `clients.created_by_user_id -> users.id`

Constraint rules:

- `client_code` unique

Recommended duplicate-control rule:

- soft duplicate check on `client_name` within the same location

Status or lifecycle rules:

- `clients.status` should support at least `active`, `inactive`
- client remains owned by one location in MVP

Completion proof:

- one client row has one location boundary and two valid owner references

### UC-09 Add Client Contact

Required tables:

- `client_contacts`
- `clients`
- `locations`

Required fields:

- `client_contacts.client_id`
- `client_contacts.location_id`
- `client_contacts.contact_name`
- `client_contacts.status`

Key relationships:

- `client_contacts.client_id -> clients.id`
- `client_contacts.location_id -> locations.id`

Constraint rules:

- contact must belong to an existing client
- `location_id` should match the parent client location by service validation

Recommended unique rule:

- avoid exact duplicate active contacts for same client with same email or phone where possible

Status or lifecycle rules:

- contact status should support active or inactive records
- primary versus secondary contact flags should not conflict with business policy

Completion proof:

- contact can be linked safely from a requisition

### UC-10 Create Requisition

Required tables:

- `requisitions`
- `clients`
- `client_contacts`
- `locations`
- `users`

Required fields:

- `requisitions.location_id`
- `requisitions.client_id`
- `requisitions.requisition_code`
- `requisitions.job_title`
- `requisitions.openings`
- `requisitions.priority`
- `requisitions.status`
- `requisitions.primary_contact_id`
- `requisitions.primary_owner_user_id`
- `requisitions.delivery_owner_user_id` nullable
- `requisitions.required_skills_json` or equivalent
- `requisitions.acceptable_career_gap_months` or text equivalent
- `requisitions.preferred_update_time_text` or structured equivalent

Key relationships:

- `requisitions.location_id -> locations.id`
- `requisitions.client_id -> clients.id`
- `requisitions.primary_contact_id -> client_contacts.id`
- `requisitions.secondary_contact_id -> client_contacts.id`
- `requisitions.primary_owner_user_id -> users.id`
- `requisitions.delivery_owner_user_id -> users.id`

Constraint rules:

- `requisition_code` unique
- openings must be positive
- delivery owner may be null

Cross-record rules:

- requisition location must match client location
- selected contacts must belong to the same client

Status or lifecycle rules:

- `status` should support at least `draft`, `open`, `on_hold`, `closed`, `cancelled`
- custom pipeline configuration must remain traceable if stored separately

Completion proof:

- one requisition row can safely represent a client-owned requirement with valid contacts and owners

### UC-12 Assign Requisition To Delivery Team

Required tables:

- `requisition_assignments`
- `requisitions`
- `users`

Required fields:

- `requisition_assignments.requisition_id`
- `requisition_assignments.assignee_user_id`
- `requisition_assignments.assignment_role`
- `requisition_assignments.status`

Key relationships:

- `requisition_assignments.requisition_id -> requisitions.id`
- `requisition_assignments.assignee_user_id -> users.id`

Constraint rules:

- one assignment must reference an existing requisition and user

Recommended unique rule:

- unique active assignment on `(requisition_id, assignee_user_id, assignment_role, status-active-concept)` or equivalent partial uniqueness

Status or lifecycle rules:

- status should support `active`, `reassigned`, `inactive`, `completed`
- reassignment should preserve prior rows or history rather than overwrite

Completion proof:

- a requisition can show one or more active working users with intact history

## Group 3. Candidate And Duplicate Control

### UC-13 Create Candidate Profile

Required tables:

- `candidates`
- `users`
- optional `candidate_documents`

Required fields:

- `candidates.candidate_code`
- `candidates.full_name`
- `candidates.primary_email` nullable by company rule
- `candidates.primary_phone` nullable by company rule
- `candidates.status`
- `candidates.sourced_by_user_id`
- `candidates.primary_owner_user_id`
- `candidates.owning_location_id` if used as ownership context instead of hard partition

Key relationships:

- `candidates.sourced_by_user_id -> users.id`
- `candidates.primary_owner_user_id -> users.id`
- `candidates.owning_location_id -> locations.id` if present

Constraint rules:

- `candidate_code` unique
- candidate should not require `location_id` as a hard partition key in MVP

Recommended duplicate-help indexes:

- index on `primary_email`
- index on `primary_phone`
- index on owner and source fields

Status or lifecycle rules:

- candidate status should support at least `draft`, `active`, `archived`
- duplicate-review state should be stored or derivable

Completion proof:

- one candidate record can exist globally and still remain linkable to many requisitions

### UC-15 Detect Candidate Duplicate

Required tables:

- `candidates`
- `duplicate_review_cases` if persistence is enabled

Required fields:

- candidate identity fields used by policy
- `duplicate_review_cases.review_status`
- `duplicate_review_cases.requested_by_user_id`

Key relationships:

- `duplicate_review_cases.existing_candidate_id -> candidates.id`
- `duplicate_review_cases.requested_candidate_id -> candidates.id`
- `duplicate_review_cases.requested_by_user_id -> users.id`

Constraint rules:

- duplicate review rows must reference real candidate records

Recommended index rules:

- index on duplicate identity fields such as email and phone
- index on `duplicate_review_cases(existing_candidate_id, review_status)`

Status or lifecycle rules:

- review status should support `pending`, `approved_override`, `merged`, `rejected`, `cancelled` or equivalent business-safe set

Completion proof:

- possible duplicate can be persisted as a controlled review item, not just a transient warning

### UC-16 Compare And Resolve Duplicate

Required tables:

- `duplicate_review_cases`
- `candidates`
- `audit_logs` later or equivalent audit store

Required fields:

- `duplicate_review_cases.review_status`
- `duplicate_review_cases.decision_notes`
- `duplicate_review_cases.decided_by_user_id`
- `duplicate_review_cases.decided_at`

Key relationships:

- `duplicate_review_cases.decided_by_user_id -> users.id`

Constraint rules:

- decision fields must not be writable without a valid review row

Status or lifecycle rules:

- once final decision is recorded, review state should move out of pending
- destructive cleanup should remain auditable

Completion proof:

- duplicate decisions are stored with actor, time, and reason

### UC-17 Link Candidate To Requisition

Required tables:

- `candidate_applications`
- `candidates`
- `requisitions`

Required fields:

- `candidate_applications.candidate_id`
- `candidate_applications.requisition_id`
- `candidate_applications.submitted_by_user_id`
- `candidate_applications.owner_user_id`
- `candidate_applications.sourced_by_user_id`
- `candidate_applications.current_stage_code`
- `candidate_applications.status`
- `candidate_applications.pipeline_template_id` if template-linked

Key relationships:

- `candidate_applications.candidate_id -> candidates.id`
- `candidate_applications.requisition_id -> requisitions.id`
- `candidate_applications.submitted_by_user_id -> users.id`
- `candidate_applications.owner_user_id -> users.id`
- `candidate_applications.sourced_by_user_id -> users.id`
- `candidate_applications.pipeline_template_id -> pipeline_templates.id` if present

Constraint rules:

- existing candidate and requisition required

Recommended unique rule:

- unique `candidate_applications(candidate_id, requisition_id)` for active business meaning, unless deliberate re-entry is supported with versioning

Status or lifecycle rules:

- application status should support at least `active`, `rejected`, `closed`, `joined`, `withdrawn`
- current stage code must stay consistent with stage history

Completion proof:

- one candidate can be linked once per requisition and then tracked separately from the base candidate record

## Group 4. Pipeline Operations

### UC-18 View Candidate Pipeline

Required tables:

- `candidate_applications`
- `candidate_stage_history`
- `requisitions`
- `candidates`

Required fields:

- `candidate_applications.current_stage_code`
- `candidate_applications.status`
- `candidate_applications.last_activity_at`
- `candidate_stage_history.from_stage_code`
- `candidate_stage_history.to_stage_code`
- `candidate_stage_history.changed_at`

Key relationships:

- `candidate_stage_history.candidate_application_id -> candidate_applications.id`

Constraint rules:

- each history row must reference a real application

Recommended indexes:

- `candidate_applications(requisition_id, current_stage_code, status)`
- `candidate_stage_history(candidate_application_id, changed_at)`

Status or lifecycle rules:

- current stage in application row is the latest working state
- history rows remain append-only

Completion proof:

- board can be reconstructed from application rows and explained from stage history

### UC-19 Move Candidate To Next Stage

Required tables:

- `candidate_applications`
- `candidate_stage_history`
- `pipeline_templates`
- `pipeline_template_stages`

Required fields:

- `candidate_applications.current_stage_code`
- `candidate_applications.last_activity_at`
- `candidate_stage_history.from_stage_code`
- `candidate_stage_history.to_stage_code`
- `candidate_stage_history.changed_by_user_id`
- `candidate_stage_history.change_reason`

Key relationships:

- `candidate_applications.pipeline_template_id -> pipeline_templates.id`
- `pipeline_template_stages.pipeline_template_id -> pipeline_templates.id`
- `candidate_stage_history.changed_by_user_id -> users.id`

Constraint rules:

- new stage must be valid for the linked template

Status or lifecycle rules:

- every successful move updates the application row and inserts one history row
- backward or terminal moves may require reason by business rule

Completion proof:

- stage changes are durable, ordered, and traceable

### UC-20 View Pipeline History

Required tables:

- `candidate_stage_history`
- `candidate_applications`

Required fields:

- `from_stage_code`
- `to_stage_code`
- `changed_by_user_id`
- `changed_at`
- `change_reason`
- `change_note`

Key relationships:

- `changed_by_user_id -> users.id`

Constraint rules:

- history rows should not be updated in normal business flow

Status or lifecycle rules:

- timeline should remain chronological and append-only

Completion proof:

- every application stage can be explained by ordered history rows

### UC-21 Track Recruiter-Owned Progress

Required tables:

- `candidate_applications`
- `candidates`
- `users`

Required fields:

- `candidate_applications.sourced_by_user_id`
- `candidate_applications.submitted_by_user_id`
- `candidate_applications.owner_user_id`
- `candidate_applications.status`

Key relationships:

- all ownership fields must resolve to real users

Constraint rules:

- recruiter-linked visibility depends on these ownership references being stored consistently

Status or lifecycle rules:

- later owner changes must not destroy source or submitter history

Completion proof:

- recruiter-linked candidate tracking remains possible after pipeline ownership changes

## Group 5. Daily Updates And Reporting

### UC-22 Submit Daily Update

Required tables:

- `daily_updates`
- `requisitions`
- `users`
- `locations`

Required fields:

- `daily_updates.location_id`
- `daily_updates.requisition_id`
- `daily_updates.submitted_by_user_id`
- `daily_updates.update_date`
- `daily_updates.update_type`
- `daily_updates.sourced_count`
- `daily_updates.screened_count`
- `daily_updates.submitted_count`
- `daily_updates.interview_count`
- `daily_updates.closure_count`
- `daily_updates.blockers_text`
- `daily_updates.next_action_text`
- `daily_updates.submission_status`

Key relationships:

- `daily_updates.location_id -> locations.id`
- `daily_updates.requisition_id -> requisitions.id`
- `daily_updates.submitted_by_user_id -> users.id`

Constraint rules:

- counts should be non-negative at application or DB-check level

Recommended unique rule:

- unique `daily_updates(requisition_id, submitted_by_user_id, update_date, update_type)` for company-configurable same-day behavior

Status or lifecycle rules:

- `update_type` should support `main` and `extra`
- `submission_status` should support at least `submitted`, `revised`, `locked`

Completion proof:

- one requisition can store daily output rows without accidental duplicate collision

### UC-23 Review Team Progress

Required tables:

- `requisitions`
- `candidate_applications`
- `daily_updates`
- reporting views or query layer

Required fields:

- status and date fields needed for aggregation

Constraint rules:

- operational summary queries depend on stable owner, stage, and date fields

Status or lifecycle rules:

- reporting should read current operational truth unless report locks are in effect

Completion proof:

- team summary can be computed from current requisition, pipeline, and update tables

### UC-24 View Location Performance

Required tables:

- `locations`
- `requisitions`
- `candidate_applications`
- `daily_updates`
- optional `report_locks`

Required fields:

- date fields for reporting windows
- location ids on operational rows

Constraint rules:

- all location-level reporting depends on location keys being present and consistent

Status or lifecycle rules:

- report lock model may preserve finalized reporting periods later

Completion proof:

- location-level metrics can be grouped from live operational records

### UC-25 View Combined Company Reporting

Required tables:

- all location-scoped operational tables
- optional reporting snapshot tables later

Constraint rules:

- cross-location rollups require consistent location ids and comparable statuses across records

Status or lifecycle rules:

- combined reporting does not change operational ownership rules

Completion proof:

- all-location aggregation is possible without changing base record ownership

## Cross-Use-Case Rules

### Required Core Foreign Keys

- `users.location_id -> locations.id`
- `users.primary_role_id -> roles.id`
- `clients.location_id -> locations.id`
- `clients.business_source_owner_user_id -> users.id`
- `clients.client_owner_user_id -> users.id`
- `client_contacts.client_id -> clients.id`
- `requisitions.location_id -> locations.id`
- `requisitions.client_id -> clients.id`
- `requisitions.primary_contact_id -> client_contacts.id`
- `requisitions.primary_owner_user_id -> users.id`
- `candidate_applications.candidate_id -> candidates.id`
- `candidate_applications.requisition_id -> requisitions.id`
- `candidate_stage_history.candidate_application_id -> candidate_applications.id`
- `daily_updates.requisition_id -> requisitions.id`
- `daily_updates.submitted_by_user_id -> users.id`

### Required Core Uniqueness

- unique `locations.location_code`
- unique `users.email`
- unique `users.employee_code` if globally enforced
- unique `roles.code`
- unique `permissions.code`
- unique `clients.client_code`
- unique `requisitions.requisition_code`
- unique `candidates.candidate_code`
- unique active candidate-to-requisition link or equivalent controlled duplicate prevention

### Required Core Status Families

- user status
- location status
- role status
- client status
- requisition status
- assignment status
- candidate status
- candidate application status
- duplicate review status
- daily update submission status

These statuses do not all need database-native enums in MVP, but they do need stable allowed-value governance.

### Required Lifecycle Preservation Rules

- candidate records stay global, not location-partitioned
- client records stay location-bound
- requisition rows inherit the client operating boundary
- recruiter source and submitter history must survive later owner changes
- stage history remains append-only
- reassignment should preserve history
- duplicate decisions should remain auditable

## MVP Completion Standard For Database Work

A use case should not be called DB-ready unless all of these are true:

1. Required tables exist.
2. Required fields exist.
3. Required foreign keys or equivalent integrity rules exist.
4. Required unique and conflict rules are defined.
5. Required statuses and lifecycle states are supported.
6. The schema preserves ownership and auditability needed by the workflow.

If one of these is missing, the use case is only partially supported in data design.
