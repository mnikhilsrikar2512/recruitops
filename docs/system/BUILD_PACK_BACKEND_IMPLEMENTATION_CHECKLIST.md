# Backend Implementation Checklist

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document is the execution checklist for building the MVP backend.

Use it after planning is complete and before development starts for each module.

It is meant to answer:

- what should be built first
- what must be validated before coding
- what must be completed before a module is considered done

Read this together with:

- [BUILD_PACK_BACKEND_EXECUTION_PLAN.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/BUILD_PACK_BACKEND_EXECUTION_PLAN.md)
- [BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md)
- [MVP_SCHEMA_V2.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/MVP_SCHEMA_V2.md)
- [backend/db/schema.sql](/Users/bhargavnikhil/Desktop/recrutment%20system/backend/db/schema.sql) (canonical schema)

## Core Rule

Do not treat a backend module as complete just because the endpoint returns data.

A module is only complete when:

- DB structure is aligned
- validation is enforced
- permissions are enforced
- scope rules are enforced
- errors are predictable
- audit impact is understood
- the frontend can use it safely

## Phase Order

Build in this order:

1. foundation setup
2. auth and access
3. admin setup
4. client registry
5. requisition workflow
6. candidate workflow
7. pipeline workflow
8. daily updates
9. dashboards and notifications
10. hardening and QA

## 1. Foundation Setup

Complete these before endpoint work:

- confirm database engine and naming conventions
- confirm migration strategy
- confirm auth strategy: JWT, session, or hybrid
- confirm error envelope format
- confirm pagination format
- confirm permission-check middleware strategy
- confirm location-scope middleware strategy
- confirm audit-log strategy for write actions
- confirm file upload storage approach for resumes

Done when:

- all shared middleware contracts are decided
- shared response helpers are decided
- shared validation approach is decided

## 2. Database Checklist

Before building services, verify:

- `clients` includes `client_code`
- `clients` includes `business_source_owner_user_id`
- `candidates` are global, not location-partitioned
- `candidate_applications` is the canonical requisition-linked record
- `daily_updates` includes `requisition_id`
- required indexes exist for login, list pages, duplicate check, and pipeline queries
- foreign keys exist for all MVP-critical relations

Done when:

- schema matches current MVP decisions
- no endpoint depends on missing critical column or table

## 3. Auth And Access Checklist

Endpoints:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

Build checklist:

- create user authentication service
- implement password hash verification
- implement session or token issue logic
- implement logout revoke logic
- implement current-user lookup
- implement permission payload builder
- implement role and scope resolution

Validation checklist:

- invalid email or password returns `AUTH_INVALID`
- inactive user cannot log in
- expired or revoked session is rejected
- permission payload reflects role and extra permissions

Done when:

- frontend can log in and load current user
- protected routes can rely on user and permission context

## 4. Admin Setup Checklist

### Locations

Endpoints:

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`

Build checklist:

- list query with filters
- create service with uniqueness check on `location_code`
- update service with allowed editable fields
- location-head lookup validation

Done when:

- Admin can create, update, and list locations safely

### Users

Endpoints:

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`

Build checklist:

- user list with filters and pagination
- uniqueness checks for email and employee code
- reporting manager validation
- role and location validation
- credential reset workflow
- password setup or reset token persistence

Done when:

- Admin can create and update users
- credential reset is auditable and safe

### Roles

Endpoints:

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`

Build checklist:

- role list and create
- stable role code validation
- permission code validation
- scope rule storage strategy
- role-permission update transaction

Done when:

- Admin can create roles and assign permissions without partial saves

## 5. Client Registry Checklist

Endpoints:

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`
- `PATCH /api/v1/client-contacts/{contact_id}`

Build checklist:

- client list query with location and ownership filters
- client create service with `client_code` uniqueness
- business source owner validation
- location ownership validation
- client detail aggregation
- contact list and create
- contact edit service

Validation checklist:

- client must belong to one location
- cross-location access is denied unless elevated
- contact must belong to parent client

Done when:

- frontend can manage clients and contacts without ownership ambiguity

## 6. Requisition Workflow Checklist

Endpoints:

- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `GET /api/v1/requisitions/{requisition_id}/assignments`
- `POST /api/v1/requisitions/{requisition_id}/assignments`
- `DELETE /api/v1/requisition-assignments/{assignment_id}`

Build checklist:

- requisition list query with filters
- create service with client and contact validation
- owner and delivery-owner validation
- requisition detail aggregation
- structured status transition logic
- assignment creation and delete logic
- duplicate assignment prevention where needed

Validation checklist:

- requisition location must match client location
- contacts must belong to client
- open positions must be positive
- date rules must be enforced
- status change reason required when necessary

Done when:

- requisitions can be created, edited, assigned, and tracked cleanly

## 7. Candidate Workflow Checklist

Endpoints:

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `POST /api/v1/candidates/{candidate_id}/resume`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`
- `GET /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/duplicate-decision`
- `POST /api/v1/candidates/{candidate_id}/finalize`

Build checklist:

- candidate list query
- draft save and final save behavior
- resume upload handling
- candidate detail retrieval
- duplicate candidate lookup by normalized fields
- duplicate review persistence
- finalize flow that creates `candidate_applications`

Validation checklist:

- candidate must support draft-first workflow
- duplicate detection must search globally
- duplicate decision must be persisted
- finalization must fail if duplicate decision is unresolved
- requisition must be accessible before finalization

Done when:

- recruiters can create candidates, review duplicates, and finalize into requisitions

## 8. Pipeline Workflow Checklist

Endpoints:

- `GET /api/v1/pipeline/board`
- `POST /api/v1/pipeline/{application_id}/move-stage`
- `GET /api/v1/pipeline/{application_id}/history`

Build checklist:

- board query based on `candidate_applications`
- stage-grouped response builder
- stage transition validator
- stage history insert logic
- conditional field rules for stage move
- stale candidate computation

Validation checklist:

- only valid stage transitions allowed
- stage move must write both application state and history
- history must be returned in audit-friendly order

Done when:

- frontend board can load, move stage, and open history reliably

## 9. Daily Updates Checklist

Endpoints:

- `POST /api/v1/daily-updates`
- `GET /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`

Build checklist:

- create update service
- requisition linkage validation
- location-scope validation
- count-field validation
- list query with filters
- detail response with requisition and user summary

Validation checklist:

- update must be tied to accessible requisition
- count fields must be non-negative
- submission status must be valid

Done when:

- users can submit updates and reviewers can filter and inspect them

## 10. Dashboards And Notifications Checklist

### Dashboards

Endpoints:

- `GET /api/v1/dashboards/role`
- `GET /api/v1/dashboards/my-work`

Build checklist:

- KPI aggregation queries
- stale work summary query
- due tasks summary query
- personal work aggregation
- location-safe filtering

Done when:

- dashboards read from live records, not mock logic

### Notifications

Endpoints:

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

Build checklist:

- notifications list query
- unread and read filter support
- own-notification scope enforcement
- mark-read update logic

Done when:

- frontend can list and mark notifications read without unsafe cross-user access

## 11. Cross-Cutting Checklist

Complete for every module:

- request validation exists
- permission checks exist
- scope checks exist
- `NOT_FOUND` handling is consistent
- `FORBIDDEN` handling is consistent
- audit logging exists for critical writes
- pagination is consistent
- sorting is constrained to safe fields

## 12. Testing Checklist

Minimum test coverage per module:

- success path
- validation failure path
- forbidden path
- wrong-location path where applicable
- not-found path

Important integration tests:

- user login and permission payload
- create client then create requisition under same location
- create candidate then finalize into application
- move application stage and verify history write
- create daily update for requisition and read it back

## 13. Ready-For-Frontend Checklist

An endpoint is frontend-ready only when:

- request and response shape are stable
- example payload exists
- error codes are documented
- frontend can map field names directly
- pagination shape is final
- permission failure behavior is predictable

## 14. Release Readiness Checklist

Before calling the MVP backend ready:

1. all phase-1 endpoints are implemented
2. all phase-1 schema dependencies exist
3. all high-risk permission and scope tests pass
4. duplicate detection flow works end to end
5. pipeline move and history work end to end
6. daily updates work end to end
7. dashboard summaries run from live data

## Final Rule

If a module is blocked by uncertainty:

1. check the backend execution plan
2. check the API implementation contract
3. check the MVP schema
4. then update the plan before coding around the ambiguity
