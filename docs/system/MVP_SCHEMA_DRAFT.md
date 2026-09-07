# MVP Schema Draft

## Purpose

This document defines the exact first-release database structure for the working recruitment model.

It is intentionally smaller than the full long-term design.

This draft is built for:

- `Director -> BDM -> Account Manager -> Lead Recruiter -> Recruiter -> Assistant / Jr. Recruiter`
- location-isolated execution
- admin-only cross-location reporting
- recruiter visibility into candidates they sourced

## Core Modeling Rules

- business hierarchy and software permissions are not the same thing
- location data is isolated by default
- every operational record belongs to one location
- admin can view all locations
- non-admin users can only query within their location scope
- candidate ownership and candidate sourcing must both be stored
- requisition assignment and candidate stage movement must be auditable

## Working Role Mapping

- `Director` -> `platform_admin`
- `BDM` -> `business_development`
- `Account Manager` -> `client_manager`
- `Lead Recruiter` -> `delivery_lead`
- `Recruiter` -> `recruiter`
- `Assistant / Jr. Recruiter` -> `sourcing_support`

## Table 1. `locations`

Purpose:

- isolate operational data
- support location-level reporting
- allow admin roll-up across all locations

Columns:

- `id` bigint primary key
- `location_code` varchar(50) unique not null
- `location_name` varchar(150) not null
- `city` varchar(100) null
- `state` varchar(100) null
- `country` varchar(100) null
- `timezone` varchar(100) null
- `status` varchar(30) not null default `active`
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- use `status` values such as `active`, `inactive`
- do not use location name as a unique identifier in code

## Table 2. `users`

Purpose:

- authenticate users
- store reporting hierarchy
- store primary location relationship

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `employee_code` varchar(50) null
- `full_name` varchar(150) not null
- `email` varchar(190) unique not null
- `phone` varchar(30) null
- `password_hash` varchar(255) not null
- `status` varchar(30) not null default `active`
- `permission_role_code` varchar(50) not null
- `business_title` varchar(100) not null
- `reporting_manager_user_id` bigint null
- `can_view_cross_location` bit not null default 0
- `last_login_at` datetime null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- keep `permission_role_code` stable for backend authorization
- keep `business_title` human-friendly for company-specific hierarchy labels
- only admin should have `can_view_cross_location = 1` in the MVP

## Table 3. `user_location_roles`

Purpose:

- support future location transfers and optional multi-location assignment without changing the main user row design

Columns:

- `id` bigint primary key
- `user_id` bigint not null
- `location_id` bigint not null
- `permission_role_code` varchar(50) not null
- `is_primary` bit not null default 0
- `status` varchar(30) not null default `active`
- `effective_from` date not null
- `effective_to` date null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- for MVP, each user should usually have one active primary row
- this table gives us future flexibility without complicating queries too much

## Table 4. `clients`

Purpose:

- store clients owned inside a location
- preserve the business source owner from upstream business development for location operations

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `client_code` varchar(50) unique not null
- `client_name` varchar(200) not null
- `industry` varchar(100) null
- `status` varchar(30) not null default `active`
- `client_owner_user_id` bigint not null
- `business_source_owner_user_id` bigint null
- `notes` text null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- keep one location owner for the client in MVP
- `business_source_owner_user_id` identifies who originated the business
- `client_owner_user_id` identifies the location-side owner for that client context
- shared-client multi-location operation can be a future extension

## Table 5. `client_contacts`

Purpose:

- store client-side contact persons used for requisitions and communication

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `client_id` bigint not null
- `contact_name` varchar(150) not null
- `email` varchar(190) null
- `phone` varchar(30) null
- `designation` varchar(100) null
- `status` varchar(30) not null default `active`
- `is_primary_contact` bit not null default 0
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

## Table 6. `requisitions`

Purpose:

- store hiring requirements raised for a client within a location
- connect the client-facing intake side to the lead-recruiter delivery side

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `client_id` bigint not null
- `client_contact_id` bigint null
- `requisition_code` varchar(50) unique not null
- `job_title` varchar(150) not null
- `employment_type` varchar(50) null
- `work_mode` varchar(50) null
- `experience_min_years` decimal(4,1) null
- `experience_max_years` decimal(4,1) null
- `location_text` varchar(200) null
- `openings_count` int not null default 1
- `priority` varchar(30) not null default `medium`
- `status` varchar(30) not null default `open`
- `target_closure_date` date null
- `jd_text` text null
- `must_have_skills` text null
- `good_to_have_skills` text null
- `primary_owner_user_id` bigint not null
- `delivery_owner_user_id` bigint not null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Status suggestions:

- `draft`
- `open`
- `in_progress`
- `on_hold`
- `closed`
- `cancelled`

Notes:

- the primary owner owns the requisition intake and follow-up flow
- the lead recruiter or delivery lead owns recruitment execution
- this keeps requisition follow-up and delivery supervision separate but connected

## Table 7. `requisition_assignments`

Purpose:

- assign one requisition to one or more delivery users

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `requisition_id` bigint not null
- `assigned_user_id` bigint not null
- `assigned_role_code` varchar(50) not null
- `assignment_type` varchar(30) not null
- `assigned_by_user_id` bigint not null
- `assigned_at` datetime not null
- `status` varchar(30) not null default `active`
- `created_at` datetime not null
- `updated_at` datetime not null

Assignment type suggestions:

- `owner`
- `recruiter`
- `support`

## Table 8. `candidates`

Purpose:

- store global candidate identity within one location
- preserve recruiter sourcing attribution

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `candidate_code` varchar(50) unique not null
- `full_name` varchar(150) not null
- `email` varchar(190) null
- `phone` varchar(30) null
- `current_company` varchar(150) null
- `current_designation` varchar(150) null
- `total_experience_years` decimal(4,1) null
- `current_location` varchar(150) null
- `preferred_location` varchar(150) null
- `notice_period_days` int null
- `current_ctc` decimal(14,2) null
- `expected_ctc` decimal(14,2) null
- `source_type` varchar(50) not null
- `source_detail` varchar(150) null
- `resume_file_path` varchar(500) null
- `profile_summary` text null
- `status` varchar(30) not null default `active`
- `sourced_by_user_id` bigint not null
- `primary_owner_user_id` bigint not null
- `created_by_user_id` bigint not null
- `created_at` datetime not null
- `updated_at` datetime not null

Notes:

- use duplicate checks on `location_id + email` and `location_id + phone`
- keep `sourced_by_user_id` even if `primary_owner_user_id` changes later

## Table 9. `candidate_requisition_links`

Purpose:

- connect a candidate to a specific requisition
- store pipeline stage per requisition
- preserve recruiter visibility on sourced candidates

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `candidate_id` bigint not null
- `requisition_id` bigint not null
- `submitted_by_user_id` bigint not null
- `current_stage` varchar(50) not null
- `stage_updated_at` datetime not null
- `owner_user_id` bigint not null
- `sourced_by_user_id` bigint not null
- `is_shortlisted` bit not null default 0
- `is_joined` bit not null default 0
- `rejection_reason` varchar(200) null
- `rejection_notes` text null
- `status` varchar(30) not null default `active`
- `created_at` datetime not null
- `updated_at` datetime not null

Stage suggestions:

- `sourced`
- `screening`
- `submitted`
- `interview`
- `offered`
- `joined`
- `rejected`
- `dropped`

Notes:

- this table is the main live candidate pipeline table
- recruiters can view rows where they are `sourced_by_user_id`, `submitted_by_user_id`, or `owner_user_id`

## Table 10. `candidate_stage_history`

Purpose:

- audit every candidate movement in the pipeline

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `candidate_requisition_link_id` bigint not null
- `candidate_id` bigint not null
- `requisition_id` bigint not null
- `from_stage` varchar(50) null
- `to_stage` varchar(50) not null
- `changed_by_user_id` bigint not null
- `change_notes` text null
- `changed_at` datetime not null

## Table 11. `daily_updates`

Purpose:

- store recruiter and delivery execution updates for daily tracking

Columns:

- `id` bigint primary key
- `location_id` bigint not null
- `user_id` bigint not null
- `requisition_id` bigint null
- `update_date` date not null
- `summary_text` text not null
- `profiles_sourced_count` int not null default 0
- `profiles_screened_count` int not null default 0
- `profiles_submitted_count` int not null default 0
- `interviews_scheduled_count` int not null default 0
- `offers_closed_count` int not null default 0
- `blockers_text` text null
- `next_action_text` text null
- `created_at` datetime not null
- `updated_at` datetime not null

## Foreign Key Map

- `users.location_id -> locations.id`
- `users.reporting_manager_user_id -> users.id`
- `user_location_roles.user_id -> users.id`
- `user_location_roles.location_id -> locations.id`
- `clients.location_id -> locations.id`
- `clients.client_owner_user_id -> users.id`
- `clients.business_source_owner_user_id -> users.id`
- `client_contacts.location_id -> locations.id`
- `client_contacts.client_id -> clients.id`
- `requisitions.location_id -> locations.id`
- `requisitions.client_id -> clients.id`
- `requisitions.client_contact_id -> client_contacts.id`
- `requisitions.primary_owner_user_id -> users.id`
- `requisitions.delivery_owner_user_id -> users.id`
- `requisition_assignments.location_id -> locations.id`
- `requisition_assignments.requisition_id -> requisitions.id`
- `requisition_assignments.assigned_user_id -> users.id`
- `candidates.location_id -> locations.id`
- `candidates.sourced_by_user_id -> users.id`
- `candidates.primary_owner_user_id -> users.id`
- `candidate_requisition_links.location_id -> locations.id`
- `candidate_requisition_links.candidate_id -> candidates.id`
- `candidate_requisition_links.requisition_id -> requisitions.id`
- `candidate_requisition_links.submitted_by_user_id -> users.id`
- `candidate_requisition_links.owner_user_id -> users.id`
- `candidate_requisition_links.sourced_by_user_id -> users.id`
- `candidate_stage_history.location_id -> locations.id`
- `candidate_stage_history.candidate_requisition_link_id -> candidate_requisition_links.id`
- `daily_updates.location_id -> locations.id`
- `daily_updates.user_id -> users.id`
- `daily_updates.requisition_id -> requisitions.id`

## Required Indexes

- `users(email)`
- `users(location_id, permission_role_code, status)`
- `clients(location_id, client_owner_user_id, status)`
- `requisitions(location_id, client_id, status, priority)`
- `requisition_assignments(location_id, requisition_id, assigned_user_id, status)`
- `candidates(location_id, email)`
- `candidates(location_id, phone)`
- `candidates(location_id, sourced_by_user_id, primary_owner_user_id, status)`
- `candidate_requisition_links(location_id, requisition_id, current_stage, status)`
- `candidate_requisition_links(location_id, candidate_id, requisition_id)`
- `candidate_requisition_links(location_id, sourced_by_user_id, current_stage)`
- `daily_updates(location_id, user_id, update_date)`

## API Query Rules

### Admin

- can query all locations
- can request location-wise or combined roll-up reports

### Location Users

- every query must include location-safe filtering from authenticated user context
- location ID should come from auth context, not only from request input

### Recruiter

- can view candidates if:
  - `primary_owner_user_id = current_user`
  - or `sourced_by_user_id = current_user`
  - or `submitted_by_user_id = current_user` through candidate-requisition link
- can view requisitions assigned to them
- can view pipeline counts for their sourced and assigned candidates

### Delivery Lead

- can view all requisitions and candidate links in their location
- can view all recruiters assigned under them within location scope

### Client Manager

- can view requisitions assigned to them
- can view pipeline summaries for their requisitions inside the same location
- can coordinate recruitment execution through the assigned lead recruiter or delivery lead

### Business Development

- can view clients they originated where allowed by location policy
- primarily acts as the business source, not the daily delivery owner

## Pipeline Visibility Matrix

### Recruiter

- view level: full profile-level visibility for sourced, submitted, and owned candidates
- action level: operational update access
- default depth: candidate stage, notes, feedback, linked requisitions

### Sourcing Support

- view level: profile-level visibility for created and assigned support records
- action level: limited operational support access
- default depth: candidate details, sourcing status, enrichment status

### Delivery Lead

- view level: full team and requisition pipeline inside location scope
- action level: delivery control access
- default depth: candidate pipeline, recruiter allocation, blockers, aging

### Client Manager

- view level: requisition-wise pipeline visibility
- action level: follow-up and coordination access
- default depth: stage summaries, shortlisted profiles, delays, blockers, joins, rejections

### Business Development

- view level: account and requisition summary visibility for originated business
- action level: summary monitoring access
- default depth: requisition counts, shortlist counts, interview progress, closures, delays

### Platform Admin or Director

- view level: location-wise and combined all-location pipeline visibility
- action level: governance and audit-level access
- default depth: rollups first, then requisition drill-down, then candidate drill-down when needed

## Pipeline Access Rule

- one pipeline should exist in the system
- different roles should consume different views of the same pipeline
- candidate-level edit actions should stay with delivery roles
- account and business roles should mostly use summary, follow-up, and escalation views

## Recommended MVP Seed Roles

- `platform_admin`
- `business_development`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`

## Out Of Scope For This Schema Draft

- multi-tenant shared clients across locations
- advanced approvals
- interview panel workflows
- notification center
- file-versioned document storage
- audit engine
- AI parsing tables
- billing and invoicing
- external client portal users

This schema is the right first backend model because it is strict enough for real execution and still small enough to build without getting buried in extension logic.
