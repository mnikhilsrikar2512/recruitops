# Frontend API And JS Responsibility Split

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document tells the frontend team exactly what should be handled in frontend JS and what must be handled by APIs for the current MVP.

Use this as the handoff sheet when multiple people are building frontend pages in parallel.

## Rule Of Thumb

### Handle In JS

Use frontend JS for:

- presentation
- interaction state
- temporary draft behavior
- local visual feedback
- local calculations that do not change source-of-truth business data

### Handle In API

Use API for:

- persistence
- validation that affects business truth
- permissions
- scope enforcement
- cross-record lookup
- auditable workflow actions
- dashboard metrics based on real data

## Module-Wise Split

## 1. Authentication

### JS

- login form validation
- password show and hide toggle
- inline credential error display
- loading spinner on submit

### API

- login
- logout
- current user load
- permission payload load

### APIs

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

## 2. Location Management

### JS

- open create drawer
- open edit drawer
- local form validation hints
- optimistic success toast after response

### API

- list locations
- create location
- update location

### APIs

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`

## 3. User Management

### JS

- drawer open and close state
- temporary password suggestion display
- inline email format validation
- local unsaved-change warning

### API

- list users
- create user
- update user
- reset credentials

### APIs

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`

## 4. Role Management

### JS

- accordion expand and collapse
- permission selection UI
- scope selection UI
- unsaved-change warning

### API

- list roles
- create role
- update role
- save permissions

### APIs

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`

## 5. Client Management

### JS

- filter bar interactions
- client form drawer state if used
- contact dialog state
- optimistic success toast

### API

- list clients
- create client
- get client detail
- update client
- list contacts
- create contact

### APIs

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`

## 6. Requisition Management

### JS

- multi-section requisition form
- skill chip entry
- local priority hint
- local due-date urgency hint
- open reassign dialog

### API

- list requisitions
- create requisition
- get requisition detail
- update requisition
- change status
- assign support user

### APIs

- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `POST /api/v1/requisitions/{requisition_id}/assignments`

## 7. Candidate Management

### JS

- local draft form save
- resume upload progress display
- candidate detail drawer state if used
- side-by-side duplicate comparison UI

### API

- list candidates
- create candidate draft
- upload resume
- get candidate detail
- update candidate
- duplicate lookup
- duplicate decision
- finalize candidate

### APIs

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `POST /api/v1/candidates/{candidate_id}/resume`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`
- `GET /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/duplicate-decision`
- `POST /api/v1/candidates/{candidate_id}/finalize`

## 8. Screening And Pipeline

### JS

- board drag preview
- stage dialog open and close
- history drawer open and close
- temporary card movement preview before confirm

### API

- load pipeline board
- move stage
- load stage history

### APIs

- `GET /api/v1/pipeline/board`
- `POST /api/v1/pipeline/{application_id}/move-stage`
- `GET /api/v1/pipeline/{application_id}/history`

## 9. Daily Updates

### JS

- draft helper text
- local narrative preview
- submit success toast
- return-to-dashboard redirect

### API

- create daily update
- list daily updates
- get daily update detail

### APIs

- `POST /api/v1/daily-updates`
- `GET /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`

## 10. Dashboards

### JS

- widget expand and collapse
- refresh animation
- local visual ranking styles

### API

- role dashboard data
- my work dashboard data

### APIs

- `GET /api/v1/dashboards/role`
- `GET /api/v1/dashboards/my-work`

## 11. Notifications

### JS

- unread badge animation
- notification panel open and close
- optimistic mark-read UI

### API

- list notifications
- mark notification read

### APIs

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

## Do Not Put In JS Only

These must not be treated as frontend-only:

- permission decisions
- scope filtering across locations
- duplicate detection across all candidates
- final stage transitions
- official KPI counts
- official daily update submission
- ownership reassignment persistence

## Frontend Team Handoff Rule

If a feature:

- changes saved business data
- affects another user
- affects dashboards
- needs auditability
- depends on cross-record comparison

then it must be treated as API-backed even if the UI also shows local helper behavior.
