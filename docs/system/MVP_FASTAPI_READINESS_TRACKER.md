# MVP FastAPI Readiness Tracker

## Purpose

This document measures the current FastAPI backend against the MVP use cases.

It is not a future-state plan only.

It is an evidence-based readiness tracker grounded in the current codebase as of Wednesday, August 19, 2026.

It answers:

- which MVP use cases already have backend support
- which use cases are only partially implemented
- which use cases are still mostly planning-stage
- what evidence supports the status
- what is the next backend priority

Read this together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`
- `docs/system/FASTAPI_RULEBOOK_ALIGNMENT.md`

## Evidence Reviewed

Reviewed backend surfaces:

- `backend/app/api/v1`
- `backend/app/services`
- `backend/app/repositories`
- `backend/app/schemas`
- `backend/tests`

Direct implementation evidence includes:

- route modules for auth, permissions, locations, roles, users, clients, requisitions, candidates, pipeline, daily updates, dashboards, and notifications
- reusable dependencies in `backend/app/api/deps.py`
- auth guard tests in `backend/tests/test_route_auth_guard.py`
- permission dependency tests in `backend/tests/test_permission_dependency.py`
- location-scope tests in `backend/tests/test_scope_dependency.py`

## Status Legend

- `Implemented`
  - route surface exists and core use-case backend behavior is materially present for MVP
- `Partial`
  - major route surface exists, but important permission, scope, validation, audit, or lifecycle behavior is still incomplete
- `Planned`
  - the use case is well planned in docs, but backend support is not materially present yet

## Current Backend Surface

Current route groups present:

- `auth`
- `permissions`
- `locations`
- `roles`
- `users`
- `clients`
- `requisitions`
- `candidates`
- `pipeline`
- `daily_updates`
- `dashboards`
- `notifications`

Current cross-cutting backend strengths:

- auth dependency is applied across core operational routers
- permission-code dependency is applied across most operational routers
- location-scope dependency exists and is already used for selected list and create flows
- ownership-aware candidate and pipeline checks now protect key detail and workflow operations
- Pydantic request schemas exist across active modules

Current cross-cutting backend gaps:

- upward visibility versus edit-right separation is not yet fully modeled in code
- some business validation and exception-routing rules remain incomplete
- readiness is stronger for route presence than for deep workflow enforcement

## Use Case Status

### UC-01 User Login

Status:

- `Implemented`

Evidence:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`
- session and auth behavior audited in `FASTAPI_RULEBOOK_ALIGNMENT.md`
- supporting auth and security tests exist in `backend/tests`

Notes:

- core login flow is present
- failed-login throttling and fuller audit behavior are still later hardening items

### UC-02 View Current Access Context

Status:

- `Implemented`

Evidence:

- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

Notes:

- current-user and resolved permission payloads exist
- this supports frontend role-aware rendering and route gating

### UC-03 Create Custom Role

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/roles.py`
- permission enforcement present on:
  - `role.read`
  - `role.create`
  - `role.update`
  - `role.permissions.assign`

Notes:

- backend route surface for role CRUD and permission assignment exists
- risky-combination review logic is still not implemented

### UC-04 Assign Role To User

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/users.py`
- create, update, and detail routes are present
- role, location, and reporting-manager validations are enforced in `backend/app/services/users.py`
- schema coverage exists in:
  - `backend/tests/test_user_schemas.py`

Notes:

- user-role assignment now has direct backend route support and validation coverage
- deeper active-location policy enforcement is still a broader hardening concern, not a route-surface gap

### UC-05 Create Location

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/locations.py`
- permission enforcement for:
  - `location.read`
  - `location.create`
  - `location.update`
- auth-guard coverage exists

Notes:

- core location create and update backend support is present

### UC-06 Create User

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/users.py`
- permission enforcement for:
  - `user.read`
  - `user.create`
  - `user.update`
  - `user.credentials.manage`
- explicit user detail route exists:
  - `GET /api/v1/users/{user_id}`
- controlled move-review route exists:
  - `POST /api/v1/users/{user_id}/move`
- schema and workflow coverage exist in:
  - `backend/tests/test_user_schemas.py`
  - `backend/tests/test_user_deactivation_workflow.py`
  - `backend/tests/test_user_move_workflow.py`

Notes:

- core user creation and core user lifecycle backend behavior are now materially present for MVP

### UC-07 Deactivate User With Active Work

Status:

- `Implemented`

Evidence:

- dedicated user deactivation route exists:
  - `POST /api/v1/users/{user_id}/deactivate`
- service-level review confirmation is required when active work exists
- transfer target is required when active work exists
- deactivation writes an audit event
- coverage is verified by:
  - `backend/tests/test_user_deactivation_workflow.py`

Gaps:

- broader lifecycle browsing UX is still a frontend and productization concern
- deeper company-specific active-location policies are still hardening work

### UC-08 Create Client Under A Location

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/clients.py`
- permission enforcement for:
  - `client.read`
  - `client.create`
  - `client.update`
- location-scope dependency is applied on list and create flows

Notes:

- this is one of the stronger location-bound modules in the current backend

### UC-09 Add Client Contact

Status:

- `Implemented`

Evidence:

- client-contact list, create, and update routes exist in `backend/app/api/v1/clients.py`
- permission enforcement for:
  - `client.contact.read`
  - `client.contact.create`
  - `client.contact.update`

Notes:

- route surface is present and protected

### UC-10 Create Requisition

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/requisitions.py`
- permission enforcement for:
  - `requisition.read`
  - `requisition.create`
  - `requisition.update`
  - `requisition.status.update`
- location-scope dependency is applied on list and create flows
- service-level validation now covers:
  - active client requirement
  - same-location client ownership
  - contact-to-client mapping
  - same-location owner validation
- workflow coverage exists in:
  - `backend/tests/test_requisition_workflows.py`

Notes:

- core requisition management backend exists

### UC-11 Update Requisition Status

Status:

- `Implemented`

Evidence:

- requisition status route exists
- dedicated `requisition.status.update` permission enforcement is applied
- status-change audit behavior is covered in:
  - `backend/tests/test_requisition_workflows.py`

Notes:

- deeper status-transition audit semantics may still need hardening

### UC-12 Assign Requisition To Delivery Team

Status:

- `Implemented`

Evidence:

- requisition assignment routes exist in `backend/app/api/v1/requisitions.py`
- permission enforcement for:
  - `assignment.read`
  - `assignment.create`
  - `assignment.update`
- location-safe assignment validation and owner reassignment review coverage exist in:
  - `backend/tests/test_requisition_workflows.py`
  - `backend/tests/test_reassignment_workflows.py`

Gaps:

- richer reassignment history and approval depth are still limited

### UC-13 Create Candidate Profile

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/candidates.py`
- permission enforcement for:
  - `candidate.read`
  - `candidate.create`
  - `candidate.update`
  - `candidate.resume.upload`

Notes:

- base candidate CRUD is present
- detail, update, duplicate, document, and finalize flows now enforce ownership-aware access

### UC-14 Upload Resume Or Document

Status:

- `Implemented`

Evidence:

- candidate document create route exists
- `candidate.resume.upload` permission enforcement exists
- document upload validation coverage exists in:
  - `backend/tests/test_candidate_workflows.py`

Notes:

- this is implemented at route and permission level

### UC-15 Detect Candidate Duplicate

Status:

- `Implemented`

Evidence:

- candidate duplicate-check route exists
- `candidate.duplicate.check` permission enforcement exists
- duplicate-state transition coverage now exists in:
  - `backend/tests/test_candidate_workflows.py`

Notes:

- duplicate workflow is one of the clearer exception-handling areas already represented in backend routes

### UC-16 Compare And Resolve Duplicate

Status:

- `Implemented`

Evidence:

- duplicate decision route exists in `backend/app/api/v1/candidates.py`
- any-of permission dependency exists for:
  - `candidate.duplicate.request_override`
  - `candidate.duplicate.link_existing`
  - `candidate.duplicate.discard_draft`
- duplicate-decision audit behavior is covered in:
  - `backend/tests/test_candidate_workflows.py`

Gaps:

- senior-role-only business governance is permission-ready, but final policy mapping still depends on role configuration

### UC-17 Link Candidate To Requisition

Status:

- `Implemented`

Evidence:

- candidate finalize/profile-linking route exists
- `candidate.link_requisition` permission enforcement exists
- finalize workflow now enforces:
  - duplicate clearance before finalization
  - same-candidate same-requisition conflict prevention
  - requisition owner same-location validation
- workflow coverage exists in:
  - `backend/tests/test_candidate_workflows.py`

Notes:

- route surface exists for moving a candidate into requisition-linked workflow

### UC-18 View Candidate Pipeline

Status:

- `Partial`

Evidence:

- `backend/app/api/v1/pipeline.py`
- board route exists
- `pipeline.read.summary` permission enforcement exists
- location-scope dependency is applied on board list
- detail, move, and history flows now call ownership-aware service checks
- access coverage is verified by:
  - `backend/tests/test_pipeline_access_scope.py`
  - `backend/tests/test_pipeline_workflows.py`

Gaps:

- upward-visibility modeling is still not fully separated from edit rights
- recruiter source/submission visibility rules are not yet fully enforced in code

### UC-19 Move Candidate To Next Stage

Status:

- `Implemented`

Evidence:

- stage move route exists
- `pipeline.stage.move` permission enforcement exists
- ownership-aware detail access is reused before stage changes are applied
- stage governance now enforces:
  - target stage must belong to active pipeline template when assigned
  - backward stage moves are blocked without exception flow
  - joined applications cannot move to another stage without restore workflow
  - rejection stages require rejection reason
  - joining stages require joining date
- workflow coverage is verified by:
  - `backend/tests/test_pipeline_workflows.py`

### UC-20 View Pipeline History

Status:

- `Partial`

Evidence:

- history route exists
- `pipeline.stage.history.read` permission enforcement exists
- ownership-aware detail access is reused before history is returned
- successful stage-move behavior continues to append history through repository workflow coverage in:
  - `backend/tests/test_pipeline_workflows.py`

Gaps:

- full scope-aware visibility rules are not yet broadly evidenced across every module

### UC-21 Track Recruiter-Owned Progress

Status:

- `Partial`

Evidence:

- candidate list and pipeline board routes exist
- recruiter-relevant query fields such as `owner_user_id` and `sourced_by_user_id` exist on list flows
- pipeline detail access now explicitly allows source-linked recruiter visibility
- access coverage is verified by:
  - `backend/tests/test_candidate_access_scope.py`
  - `backend/tests/test_pipeline_access_scope.py`

Gaps:

- broader upward-visibility policy remains more limited than the final product rulebook

### UC-22 Submit Daily Update

Status:

- `Implemented`

Evidence:

- `backend/app/api/v1/daily_updates.py`
- permission enforcement for:
  - `daily_update.read`
  - `daily_update.create_main`
- location-scope dependency applied to list flow
- service-level validation now covers:
  - submitting user existence
  - requisition existence
  - submitter same-location validation
  - submitter requisition-link validation
  - duplicate same-user same-requisition same-date blocking
- workflow coverage exists in:
  - `backend/tests/test_daily_update_workflows.py`
  - `backend/tests/test_daily_update_schemas.py`

Notes:

- core daily update create and read support exists

### UC-23 Review Team Progress

Status:

- `Implemented`

Evidence:

- dashboard routes exist in `backend/app/api/v1/dashboards.py`
- permissions exist for:
  - `dashboard.read_pipeline_summary`
  - `dashboard.read_my_work`
- explicit reporting routes now exist:
  - `GET /api/v1/dashboards/location-summary`
  - `GET /api/v1/dashboards/company-summary`
- requisition, pipeline, and daily update modules exist to feed reporting
- coverage is verified by:
  - `backend/tests/test_dashboard_services.py`
- role and my-work dashboard service coverage now exists in:
  - `backend/tests/test_dashboard_services.py`

Gaps:

- complete upward-visibility modeling is still limited beyond the current summary set

### UC-24 View Location Performance

Status:

- `Implemented`

Evidence:

- dedicated location summary route exists:
  - `GET /api/v1/dashboards/location-summary`
- non-admin users are restricted to their own location in service logic
- missing location summaries now return controlled not-found behavior
- coverage is verified by:
  - `backend/tests/test_dashboard_services.py`

Gaps:

- current support is still summary-oriented rather than full historical reporting productization

### UC-25 View Combined Company Reporting

Status:

- `Implemented`

Evidence:

- dedicated company summary route exists:
  - `GET /api/v1/dashboards/company-summary`
- company summary is restricted to admin in service logic
- company aggregation behavior is covered in:
  - `backend/tests/test_dashboard_services.py`
- coverage is verified by:
  - `backend/tests/test_dashboard_services.py`

Gaps:

- broader report slicing, export, and lock behavior are still not implemented

### UC-26 Reassign Ownership On Active Work

Status:

- `Implemented`

Evidence:

- dedicated requisition owner reassignment route exists:
  - `POST /api/v1/requisitions/{requisition_id}/reassign-owners`
- dedicated candidate owner reassignment route exists:
  - `POST /api/v1/candidates/{candidate_id}/reassign-owner`
- service-level review confirmation is required when active work exists
- coverage is verified by:
  - `backend/tests/test_reassignment_workflows.py`

Gaps:

- deeper audit browsing and review tooling are still limited

### UC-27 Handle Access Denial

Status:

- `Implemented`

Evidence:

- auth dependency returns `401` on protected routes
- permission dependency tests prove `403` behavior
- location-scope dependency tests prove `403` behavior on wrong-location access

Test evidence:

- `backend/tests/test_route_auth_guard.py`
- `backend/tests/test_permission_dependency.py`
- `backend/tests/test_scope_dependency.py`

### UC-28 Audit Sensitive Changes

Status:

- `Implemented`

Evidence:

- audit repository exists:
  - `backend/app/repositories/audit.py`
- audit logging is now written for:
  - candidate duplicate decisions
  - candidate owner reassignment
  - requisition owner reassignment
  - requisition status changes
- coverage is verified by:
  - `backend/tests/test_audit_logging_workflows.py`

Gaps:

- no audit browsing API or audit-center UI exists yet
- coverage is still limited to selected sensitive flows rather than every important mutation

## Readiness Summary

### Strongest MVP Backend Areas

- authentication and session access
- permission payload retrieval
- location CRUD
- role CRUD and permission assignment
- user create, detail, move-review, and deactivation workflows
- client and contact CRUD
- requisition CRUD and status updates
- assignment CRUD
- controlled user deactivation with transfer
- controlled candidate and requisition owner reassignment
- candidate CRUD, duplicate-related routes, and finalize-to-requisition protections
- daily update create and read
- location and company summary reporting
- sensitive workflow audit logging for key actions

### Most Important Partial Areas

- pipeline visibility and stage-governance depth
- recruiter ownership visibility across later pipeline stages
- broader reporting depth beyond the current summary endpoints

### Most Important Missing Workflow Areas

- advanced reporting controls such as report locks, exports, and finalized periods
- broader audit coverage and audit browsing surfaces

## Recommended Next Backend Priorities

1. Separate upward read visibility from edit permissions more explicitly across the remaining business modules.
2. Expand reporting depth with exports, locks, finalized periods, and richer filters.
3. Extend audit logging to more sensitive flows and add audit browsing APIs.
4. Deepen pipeline-governance enforcement and recruiter visibility behavior across later-stage workflows.

## Current Delivery Interpretation

The FastAPI backend is no longer only a planning skeleton.

It already supports a meaningful MVP operational core.

However, the backend should still be considered:

- operationally usable for core CRUD and workflow capture
- partially hardened for permissions and location access
- not yet fully complete for the full business-governed MVP described in the planning pack

That means:

- the product plan is now much closer to buildable end to end
- the backend core exists
- the remaining work is mostly depth, governance, visibility modeling, and reporting completeness
