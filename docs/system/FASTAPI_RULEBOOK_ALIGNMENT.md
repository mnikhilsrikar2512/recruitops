# FastAPI Rulebook Alignment

## Purpose

This document audits the current FastAPI implementation against the API rulebook in:

- [API_VALIDATION_RULES.md](/Users/bhargavnikhil/Desktop/recrutment system/docs/system/API_VALIDATION_RULES.md)

It answers:

- what is already implemented
- what is partially implemented
- what is still missing
- what should be prioritized next

Use-case readiness companion:

- [MVP_FASTAPI_READINESS_TRACKER.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/MVP_FASTAPI_READINESS_TRACKER.md)

Audit date:

- Wednesday, August 19, 2026

## Scope Reviewed

Reviewed implementation areas:

- [backend/app/api/v1](/Users/bhargavnikhil/Desktop/recrutment system/backend/app/api/v1)
- [backend/app/services](/Users/bhargavnikhil/Desktop/recrutment system/backend/app/services)
- [backend/app/repositories](/Users/bhargavnikhil/Desktop/recrutment system/backend/app/repositories)
- [backend/app/schemas](/Users/bhargavnikhil/Desktop/recrutment system/backend/app/schemas)

## Status Legend

- `Aligned`
  - current implementation materially matches the rulebook for MVP
- `Partial`
  - important parts exist, but rulebook requirements are only partly enforced
- `Gap`
  - rulebook expects behavior that is not currently implemented

## Overall Summary

Current backend status:

- core FastAPI modules exist for:
  - auth
  - permissions
  - locations
  - roles
  - users
  - clients
  - requisitions
  - candidates
  - pipeline
  - daily updates
  - dashboards
  - notifications
- route shape and base CRUD/workflow coverage are strong for MVP
- request-shape validation is mostly present through Pydantic schemas
- many key reference validations exist in services
- core auth and permission enforcement are now in place across most business modules
- targeted audit logging now exists for several sensitive workflow actions
- the biggest remaining gap is authorization depth:
  - ownership-aware and upward-visibility policy is not yet complete across every workflow
- several business-rule validations from the rulebook are still missing
- exception-routing exists only in limited form, mainly around duplicate candidates

## Cross-Cutting Alignment

### 1. Request Shape Validation

Status:

- `Aligned` for most implemented payloads

Evidence:

- Pydantic schemas are present for all active modules
- create/update payloads generally enforce:
  - required fields
  - min/max lengths
  - enum-like literals
  - numeric bounds
  - non-empty update payloads

Remaining gaps:

- some rulebook-required business completeness checks are not enforced beyond schema shape

### 2. Authentication Coverage

Status:

- `Aligned`

What is aligned:

- `auth` endpoints are implemented
- `permissions/me` is protected
- `dashboards` endpoints are protected
- `notifications` endpoints are protected
- operational route groups now require authenticated session context:
  - locations
  - roles
  - users
  - clients
  - requisitions
  - candidates
  - pipeline
  - daily updates

Remaining gaps:

- authenticated access is now enforced, and route-level permission enforcement is broadly applied
- the main remaining gap is deeper workflow-aware scope enforcement

Impact:

- the backend no longer behaves like an open internal API
- the next missing layer is fine-grained authorization rather than basic authentication

### 3. Permission And Scope Enforcement

Status:

- `Partial`

What exists:

- resolved permission payload is available from `GET /api/v1/permissions/me`
- session context includes role and location data
- reusable permission dependencies now exist for:
  - all-permissions-required checks
  - any-one-permission checks
- route-level permission checks are now applied across:
  - locations
  - roles
  - users
  - clients
  - requisitions
  - candidates
  - pipeline
  - daily updates
  - dashboards
- reusable location-scope dependency now exists
- location-scope enforcement is now applied on selected location-bound flows:
  - client list and create
  - requisition list and create
  - daily update list
  - pipeline board list
- ownership-aware candidate access is now enforced in service-level detail, update, document, duplicate, and finalize flows
- ownership-aware pipeline access is now enforced in service-level detail, stage-move, and history flows
- audit logging now exists for selected sensitive actions:
  - candidate duplicate decisions
  - candidate owner reassignment
  - requisition owner reassignment
  - requisition status changes
- access coverage is backed by:
  - `backend/tests/test_candidate_access_scope.py`
  - `backend/tests/test_pipeline_access_scope.py`
  - `backend/tests/test_audit_logging_workflows.py`

What is missing:

- notifications still rely on authenticated ownership rather than explicit permission code checks
- no reusable scope-check dependency yet for:
  - upward visibility versus edit-right separation
- location-scope enforcement is not yet applied consistently across every location-sensitive detail and update flow

Impact:

- the backend now enforces permission codes on most core business routes
- scope-aware authorization is materially stronger now, but full route coverage and broader visibility-policy modeling are still pending

### 4. Error Semantics

Status:

- `Partial`

What is aligned:

- `401`, `403`, `404`, and `409` are used in sensible places

What is inconsistent with the rulebook:

- several business-rule failures currently return `400`
- many rulebook scenarios would be better represented as `422`

Examples:

- wrong-location owner or contact mismatch currently returns `400`
- invalid stage or business transition logic is not consistently separated from malformed requests

## Module-Wise Alignment

## Module 1. Authentication And Session Control

Status:

- `Aligned`

Implemented:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

Aligned behaviors:

- email normalization
- non-empty password check
- session hashing and lookup
- expired and revoked session rejection
- inactive user rejection

Minor gaps:

- no failed login throttling or audit trail implementation yet
- no first-login setup endpoint yet

## Module 2. Roles, Permissions, And Access Configuration

Status:

- `Partial`

Implemented:

- list roles
- create role
- update role
- assign role permissions

Aligned behaviors:

- role code uniqueness check
- role existence check
- invalid permission list detection

Gaps:

- no permission enforcement for role administration
- no active/inactive role enforcement during downstream user assignment
- no review flow for risky permission combinations

## Module 3. Location And User Administration

Status:

- `Partial`

Locations:

- list, create, update exist
- location code uniqueness exists
- location head existence validation exists

Users:

- list, create, detail, update, credential reset, deactivate, and move-review routes exist
- email uniqueness exists
- employee code uniqueness exists
- role existence exists
- location existence exists
- reporting manager existence exists
- self-reporting is blocked
- active-work deactivation review exists
- active-work move review exists
- permission enforcement exists on user administration routes

Gaps:

- no location active-status validation when assigning operational users
- no user status-specific business restrictions beyond existence

Aligned additions:

- explicit user deactivation workflow exists for active-work review and transfer handling
- explicit user move workflow exists for active-work review and controlled transfer handling
- explicit user detail route now exists in the FastAPI route set

## Module 4. Client Directory

Status:

- `Partial`

Implemented:

- client list, create, detail, update
- contact list, create, update

Aligned behaviors:

- client code uniqueness check
- location existence validation
- owner existence validation
- same-location owner validation
- client existence validation

Gaps:

- no action/scope permission enforcement
- no active/inactive client restriction during requisition creation at client service level
- no likely-duplicate client review flow by name similarity
- no explicit cross-location exception workflow

## Module 5. Requisition Management

Status:

- `Partial`

Implemented:

- list, create, detail, update, status update
- assignment list, create, delete

Aligned behaviors:

- client existence check
- active client status check
- client same-location check
- owner existence check
- owner same-location check
- contact-to-client mapping check
- route-level permission enforcement exists
- route-level location-scope enforcement exists on requisition list and create flows
- owner reassignment review confirmation when active work exists
- status-change audit logging

Gaps:

- no explicit status-transition validation matrix
- no controlled reopen workflow beyond generic status update
- reassignment exception handling now exists for explicit owner reassignment flows
- deeper reassignment history, approval behavior, and audit browsing are still limited

## Module 6. Candidate Management

Status:

- `Partial`

Implemented:

- list, create, detail, update
- document create
- duplicate check
- duplicate decision
- finalize profile

Aligned behaviors:

- key user existence checks
- route-level permission enforcement exists
- ownership-aware detail, update, document, duplicate, and finalize access checks exist
- duplicate detection endpoint
- duplicate review case creation
- duplicate clearance is now enforced before finalization
- requisition existence check for finalize
- duplicate same-candidate same-requisition link prevention now exists
- application owner existence and same-location check
- duplicate-decision audit logging
- owner-reassignment audit logging

Gaps:

- no mandatory final-completeness enforcement for:
  - usable contact method
  - resume presence
  - social profile expectations
- no restore/unlink exception workflow for wrong finalization target

## Module 7. Pipeline Management

Status:

- `Partial`

Implemented:

- board
- application detail
- stage move
- history

Aligned behaviors:

- application existence check
- changed-by user existence check
- stage history persistence
- basic joined/rejected application status updates in repository logic
- route-level permission enforcement exists
- ownership-aware detail, move, and history access checks exist
- target stage now must belong to the requisition application template when assigned
- backward stage movement is blocked without an exception workflow
- invalid post-joined transitions are blocked
- rejection stages require rejection reason
- joining stages require joining date

Gaps:

- no approval-driven skip or backward-stage exception handling

## Module 8. Daily Updates

Status:

- `Partial`

Implemented:

- list
- create
- detail

Aligned behaviors:

- submitting user existence check
- requisition existence check
- submitting-user same-location check
- submitter-to-requisition linkage check
- non-negative counters via schema
- route-level permission enforcement exists
- route-level location-scope enforcement exists on list flow
- duplicate same-user same-requisition same-date blocking now exists

Gaps:

- no draft-versus-submitted business logic beyond enum field
- no catch-up or reporting-period exception behavior

## Module 9. Dashboards

Status:

- `Partial`

Implemented:

- role dashboard
- my-work dashboard
- location summary dashboard
- company summary dashboard

Aligned behaviors:

- authentication required
- permission enforcement via dashboard permission codes
- current user context is used
- role dashboard respects location/admin context in current aggregation logic
- my-work dashboard respects current user context in service logic
- location summary respects location/admin scope in service logic
- missing location summary now returns controlled not-found behavior
- company summary is restricted to admin in service logic

Gaps:

- no freshness indicators
- no export, lock, or finalized reporting-period support yet

## Module 10. Notifications

Status:

- `Aligned` for current MVP scope

Implemented:

- list notifications
- mark notification as read

Aligned behaviors:

- authentication required
- explicit permission enforcement now exists for notification read and mark-read actions
- notification ownership check
- not-found handling
- mark-read behavior is effectively idempotent enough for MVP

Gaps:

- no archive or delivery-state update APIs yet

## Endpoint Coverage Gaps Versus Planning Docs

The rulebook and API planning docs still expect some endpoints or flows that are not yet in the active FastAPI implementation.

Current notable gaps:

- no `GET /api/v1/locations/{id}`
- no `GET /api/v1/users/{id}`
- no candidate resume-upload or parsing workflow
- no approval APIs
- no audit APIs
- no exception management APIs
- no report lock / unlock APIs
- no invitation and onboarding setup flow APIs

These are acceptable only if treated as pending work, not as already covered.

## Highest Priority Backend Gaps

### Priority 1

- extend scope validators beyond location filtering
- separate read visibility from edit visibility using scope-aware checks

### Priority 2

- enforce missing business validations:
  - candidate final completeness rules
  - work-allocation depth and assignment-history coverage
  - richer reporting controls

### Priority 3

- add approval and exception workflow endpoints
- add audit trail APIs for sensitive actions
- add missing detail endpoints from planning baseline

## Recommended Execution Sequence

1. Add ownership-scope and upward-visibility validators.
2. Extend location-scope coverage to remaining location-sensitive detail and update flows.
3. Extend permission coverage to notifications and remaining sensitive flows.
4. Add module-specific missing business validations.
5. Add approval and exception workflow APIs.

## Conclusion

The current FastAPI backend is structurally strong and covers the main MVP modules.

However, it is not yet fully aligned with the API rulebook because:

- scope-aware authorization is still incomplete
- several important business-rule and exception validations are still pending

In short:

- module coverage is strong
- validation depth is moderate
- authentication coverage is now in place
- permission-code enforcement is largely in place
- location-scope enforcement has started
- ownership-aware and full scope-aware authorization are still the main missing layers
