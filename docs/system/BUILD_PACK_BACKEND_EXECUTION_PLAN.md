# Backend Execution Plan

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document is the working execution plan for building the MVP backend.

It is the source of truth for:

- backend build order
- canonical DB entity names
- canonical API entity names
- what must exist in phase 1
- what can stay as future extension

Read this together with:

- [BUILD_PACK_API_CONTRACT_BASELINE.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/BUILD_PACK_API_CONTRACT_BASELINE.md)
- [MVP_SCHEMA_V2.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/MVP_SCHEMA_V2.md)
- [DATABASE_DESIGN.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/DATABASE_DESIGN.md)
- [backend/db/schema.sql](/Users/bhargavnikhil/Desktop/recrutment%20system/backend/db/schema.sql) (canonical schema)

## Core Rule

Do not build the backend from the older prototype hierarchy.

Build it from these stable MVP rules:

- `Admin` is the only fixed product role
- all other operational roles are configurable
- locations are isolated by default for operational data
- clients are location-bound
- candidates are global across the company for duplicate detection
- candidate pipeline visibility is controlled by requisition linkage and permissions
- recruiter visibility must survive ownership changes through application linkage
- daily updates are requisition-linked operational records

## Canonical Backend Names

Use these names consistently in code, SQL, and API work.

### Organizational

- `locations`
- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_location_roles`
- `user_extra_permissions`

### Commercial

- `clients`
- `client_contacts`
- `client_access_requests`

### Delivery

- `requisitions`
- `requisition_assignments`
- `requisition_skill_requirements`
- `requisition_screening_rules`
- `pipeline_templates`
- `pipeline_template_stages`

### Candidate Workflow

- `candidates`
- `candidate_applications`
- `candidate_stage_history`
- `candidate_screening_checks`
- `duplicate_review_cases`

### Execution Tracking

- `daily_updates`
- `notifications`

## Naming Decisions

These decisions are now locked for MVP:

- use `candidate_applications` as the canonical requisition-linked candidate record
- treat `candidate_requisition_links` as older planning language only
- use `business_source_owner_user_id` on `clients`
- use `primary_owner_user_id` and optional `delivery_owner_user_id` on `requisitions`
- keep `requisition_assignments` for additional contributors and support users
- keep `daily_updates.requisition_id` for operational traceability

## Phase 1. Database First

Build and validate these table groups first.

### Identity And Access

- `roles`
- `permissions`
- `role_permissions`
- `locations`
- `users`
- `user_location_roles`
- `user_extra_permissions`
- `user_sessions`
- `password_reset_tokens`

### Commercial

- `clients`
- `client_contacts`

### Delivery

- `requisitions`
- `requisition_assignments`
- `requisition_skill_requirements`
- `requisition_screening_rules`

### Candidate Workflow

- `candidates`
- `candidate_applications`
- `candidate_stage_history`
- `duplicate_review_cases`
- `candidate_screening_checks`

### Operational Tracking

- `daily_updates`
- `notifications`

## Phase 2. API Build Order

Implement APIs in this order.

### Slice 1. Auth And Access

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

### Slice 2. Admin Setup

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`
- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`

### Slice 3. Client Registry

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`
- `PATCH /api/v1/client-contacts/{contact_id}`

### Slice 4. Requisition Workflow

- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `GET /api/v1/requisitions/{requisition_id}/assignments`
- `POST /api/v1/requisitions/{requisition_id}/assignments`
- `DELETE /api/v1/requisition-assignments/{assignment_id}`

### Slice 5. Candidate Workflow

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `POST /api/v1/candidates/{candidate_id}/resume`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`
- `GET /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/duplicate-decision`
- `POST /api/v1/candidates/{candidate_id}/finalize`

### Slice 6. Pipeline Workflow

- `GET /api/v1/pipeline/board`
- `POST /api/v1/pipeline/{application_id}/move-stage`
- `GET /api/v1/pipeline/{application_id}/history`

### Slice 7. Daily Execution

- `POST /api/v1/daily-updates`
- `GET /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`

### Slice 8. Summary APIs

- `GET /api/v1/dashboards/role`
- `GET /api/v1/dashboards/my-work`
- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

## Phase 3. MVP Extension Later

Do not block phase 1 on these unless we explicitly decide to build them now.

- interview scheduling engine
- portal usage scheduling
- report locks and reporting engine
- approvals and escalation engine
- advanced automation jobs
- audit-center reporting UI
- external integrations

## DB Validation Checklist

Before API work starts, validate:

1. all core foreign keys exist
2. location-bound records carry `location_id`
3. client records include business source ownership
4. candidate records are global and not location-partitioned
5. candidate applications are requisition-linked
6. daily updates are requisition-linked
7. indexes exist for login, list pages, duplicate lookup, and pipeline views

## API Validation Checklist

Before an endpoint is marked ready:

1. request payload is defined
2. response payload is defined
3. validation rules are written
4. permission rule is written
5. location-scope rule is written
6. audit impact is understood
7. linked dashboard effect is understood

## Final Rule

If a DB or API decision conflicts with older planning files:

1. prefer this execution plan
2. prefer `BUILD_PACK_API_CONTRACT_BASELINE.md`
3. prefer `MVP_SCHEMA_V2.md`
4. update older files later for consistency
