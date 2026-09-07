# MVP Backend Build Sequence Pack

## Purpose

This document converts the MVP backend planning set into an execution sequence that can be built in controlled batches.

It is meant to answer:

- what backend slice should be built first
- what each slice depends on
- which DB, API, service, validation, and test work belongs in each slice
- what must be true before the next slice begins

Use this together with:

- `docs/system/BUILD_PACK_BACKEND_EXECUTION_PLAN.md`
- `docs/system/BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_FASTAPI_READINESS_TRACKER.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`

## Core Rule

Backend work should move in stable business slices, not just by router file order.

Each batch should complete:

- DB or schema readiness
- route surface
- service validation
- permission and scope enforcement
- test coverage

before the next batch depends on it.

## Recommended Backend Build Batches

1. Foundation And Access
2. Admin Setup
3. Client And Requisition Operations
4. Candidate And Pipeline Operations
5. Daily Updates, Dashboards, And Notifications
6. Hardening And Final Alignment

## Batch 1. Foundation And Access

### Goal

Create the backend foundation required for all later operational modules.

### Must Be Built In This Batch

- app bootstrap and router registration
- auth dependency
- permission dependency
- scope dependency base
- response envelope consistency
- error model consistency
- session handling
- current user and permission context endpoints

### Main Deliverables

- auth router
- permissions router
- dependency layer
- base schema patterns
- base repository and service patterns
- shared test patterns for auth and guards

### APIs In Scope

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

### DB Or Model Scope

- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_location_roles`
- `user_extra_permissions`
- `user_sessions`
- password reset and credential support tables if used

### Test Scope

- auth guard tests
- permission dependency tests
- session validation tests
- current-user payload tests

### Entry Criteria

- core backend stack and project structure are available

### Exit Criteria

- valid login works
- invalid or inactive login is blocked
- permission context endpoint works
- protected routes can rely on stable auth and permission dependencies

## Batch 2. Admin Setup

### Goal

Enable company setup and user lifecycle management.

### Must Be Built In This Batch

- location lifecycle
- role lifecycle
- user lifecycle
- user detail and move review support
- deactivation review support

### APIs In Scope

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PUT or PATCH /api/v1/locations/{location_id}`
- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PUT or PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PUT or PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/deactivate`
- `POST /api/v1/users/{user_id}/move`
- `POST /api/v1/users/{user_id}/credentials/reset`

### DB Or Model Scope

- `locations`
- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_location_roles`
- assignment reference checks used for move and deactivate review

### Service Rules In Scope

- duplicate user identity validation
- manager validation
- active-work deactivation review
- transfer target enforcement when active work exists
- role assignment validation
- location assignment validation

### Test Scope

- location schema and workflow tests
- role permission assignment tests
- user schema tests
- user deactivation workflow tests
- user move workflow tests

### Dependencies

- Batch 1 complete

### Exit Criteria

- Admin can create location
- Admin can create and update role
- Admin can create and update user
- user detail route exists
- deactivation and move review flows enforce business rules

## Batch 3. Client And Requisition Operations

### Goal

Enable commercial intake and delivery-start workflows.

### Must Be Built In This Batch

- client lifecycle
- client contact lifecycle
- requisition lifecycle
- requisition assignment lifecycle
- requisition status lifecycle
- owner reassignment support

### APIs In Scope

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PUT or PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`
- `PUT or PATCH /api/v1/client-contacts/{contact_id}`
- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/{requisition_id}`
- `PUT or PATCH /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `GET /api/v1/requisitions/{requisition_id}/assignments`
- `POST /api/v1/requisitions/{requisition_id}/assignments`
- `DELETE /api/v1/requisition-assignments/{assignment_id}`
- `POST /api/v1/requisitions/{requisition_id}/reassign`

### DB Or Model Scope

- `clients`
- `client_contacts`
- `requisitions`
- `requisition_assignments`
- `requisition_skill_requirements`
- `pipeline_templates`
- `pipeline_template_stages`

### Service Rules In Scope

- client location ownership
- client duplicate handling baseline
- client contact-to-client integrity
- requisition location inheritance from client
- inactive client protection
- owner location validation
- assignment location validation
- reassignment review when active work exists

### Test Scope

- client schema and workflow tests
- requisition schema tests
- requisition workflow tests
- assignment workflow tests
- reassignment workflow tests

### Dependencies

- Batch 2 complete because users, roles, and locations are required

### Exit Criteria

- permitted user can create and update client
- permitted user can manage client contacts
- permitted user can create and update requisition
- status changes are validated
- assignments and reassignment are enforced and tested

## Batch 4. Candidate And Pipeline Operations

### Goal

Enable the main recruitment execution workflow from candidate creation to pipeline movement.

### Must Be Built In This Batch

- candidate lifecycle
- duplicate detection and decision support
- candidate-to-requisition linking
- pipeline application detail
- pipeline stage movement
- pipeline history

### APIs In Scope

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/{candidate_id}`
- `PUT or PATCH /api/v1/candidates/{candidate_id}`
- `POST /api/v1/candidates/{candidate_id}/documents` or resume upload endpoint
- `POST /api/v1/candidates/duplicate-check`
- `GET /api/v1/candidates/duplicate-cases/{case_id}`
- `POST /api/v1/candidates/duplicate-cases/{case_id}/decision`
- `POST /api/v1/candidates/{candidate_id}/applications`
- `GET /api/v1/pipeline/board`
- `GET /api/v1/pipeline/applications/{application_id}`
- `POST /api/v1/pipeline/applications/{application_id}/move-stage`
- `GET /api/v1/pipeline/applications/{application_id}/history`

### DB Or Model Scope

- `candidates`
- `candidate_applications`
- `candidate_stage_history`
- `duplicate_review_cases`
- `candidate_screening_checks`

### Service Rules In Scope

- global duplicate detection
- same-candidate same-requisition protection
- duplicate review authority
- recruiter visibility through linkage
- stage-template validation
- invalid backward movement handling
- joined and rejected state protection

### Test Scope

- candidate schema tests
- candidate workflow tests
- candidate access scope tests
- pipeline schema tests
- pipeline workflow tests
- pipeline access scope tests

### Dependencies

- Batch 3 complete because requisitions and assignments must exist

### Exit Criteria

- recruiter can create candidate
- duplicate detection works
- duplicate decision flow is enforced
- candidate can be linked to requisition
- pipeline can be viewed and moved with correct validation

## Batch 5. Daily Updates, Dashboards, And Notifications

### Goal

Enable execution tracking, reporting summaries, and alert delivery.

### Must Be Built In This Batch

- daily update lifecycle
- role and personal dashboard summaries
- location summary
- company summary
- notifications list and read-state updates

### APIs In Scope

- `GET /api/v1/daily-updates`
- `POST /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`
- `GET /api/v1/dashboard/my-work`
- `GET /api/v1/dashboard/pipeline-summary`
- `GET /api/v1/dashboard/location-summary`
- `GET /api/v1/dashboard/company-summary`
- `GET /api/v1/notifications`
- `POST or PATCH /api/v1/notifications/{notification_id}/read`

### DB Or Model Scope

- `daily_updates`
- `notifications`
- reporting queries or summary views that read:
  - `requisitions`
  - `candidate_applications`
  - `candidate_stage_history`
  - `locations`

### Service Rules In Scope

- duplicate same-day update behavior
- linked requisition validation
- management summary visibility
- reporting scope control
- notification ownership protection

### Test Scope

- daily update schema tests
- daily update workflow tests
- dashboard service tests
- dashboard schema tests
- notification schema tests
- notification workflow tests

### Dependencies

- Batch 4 complete enough for live execution data to exist

### Exit Criteria

- recruiters can submit updates
- managers can review summaries
- location and company reporting work with permission-aware access
- notifications can be listed and marked read

## Batch 6. Hardening And Final Alignment

### Goal

Stabilize the backend for integrated MVP execution and reduce cross-module inconsistencies.

### Must Be Built In This Batch

- audit behavior alignment
- response-shape consistency checks
- final permission and scope rule review
- cross-module validation cleanup
- rulebook and readiness tracker alignment
- regression coverage for critical end-to-end slices

### Work In Scope

- strengthen upward-visibility versus edit-right separation where still thin
- confirm canonical endpoint naming consistency
- eliminate older prototype terminology from active code paths
- verify every route has schema, permission, and scope coverage
- verify review-required responses are explicit and stable

### Test Scope

- full test suite
- cross-module regression tests
- route auth guard coverage
- permission dependency coverage
- scope dependency coverage

### Dependencies

- Batches 1 through 5 functionally complete

### Exit Criteria

- full MVP route surface is stable
- critical validation rules are covered by tests
- readiness tracker can justify implemented status with direct evidence
- no major planning-to-code naming mismatches remain in active backend modules

## Suggested Sprint Grouping

If the team wants sprint-style packaging:

### Sprint 1

- Batch 1 Foundation And Access

### Sprint 2

- Batch 2 Admin Setup

### Sprint 3

- Batch 3 Client And Requisition Operations

### Sprint 4

- Batch 4 Candidate And Pipeline Operations

### Sprint 5

- Batch 5 Daily Updates, Dashboards, And Notifications

### Sprint 6

- Batch 6 Hardening And Final Alignment

## Parallel Work Guidance

These workstreams can overlap after the earlier dependency is stable:

- DB migrations
- Pydantic schemas
- repository layer
- service layer
- route layer
- test creation

Safe parallel split example:

- Developer A:
  migrations and ORM or model layer
- Developer B:
  repositories and service rules
- Developer C:
  route handlers and schema wiring
- Developer D:
  tests and readiness evidence updates

## Handoff Checklist Per Batch

Before a backend batch is called done, confirm:

- DB entities or models exist
- request schemas exist
- response schemas exist
- router endpoints exist
- service validation exists
- permission checks exist
- scope checks exist where required
- tests exist for key success and failure paths

## Relationship To Frontend Batches

This backend sequence intentionally mirrors the frontend build sequence:

- backend batch 1 matches frontend batch 1 foundation
- backend batch 2 matches frontend batch 2 admin setup
- backend batch 3 matches frontend batch 3 client and requisition work
- backend batch 4 matches frontend batch 4 candidate and pipeline work
- backend batch 5 matches frontend batch 5 daily updates and reporting
- backend batch 6 matches frontend batch 6 hardening

This makes parallel planning easier.

## Final Delivery Rule

Backend execution planning is incomplete if the team cannot answer, for each batch:

- what DB and API scope is included
- what it depends on
- what validation and tests must exist
- what done means

If one of those is unclear, the backend build sequence is not yet safe for execution.
