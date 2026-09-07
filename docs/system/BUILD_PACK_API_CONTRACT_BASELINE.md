# Final API Contract Baseline

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document defines the MVP API baseline for implementation.

It is narrower than the full API planning file and contains only the first build slice.

It should be read together with frontend responsibility planning:

- lightweight UI-only interactions may stay in JS
- persisted business data, permission logic, scope logic, and auditable workflow actions must go through APIs

Use-case traceability reference:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`

## Canonical Backend Naming

Use these names consistently in API implementation:

- `clients` for location-bound client records
- `business_source_owner_user_id` for the BDM-side business source ownership on clients
- `primary_owner_user_id` and optional `delivery_owner_user_id` for requisitions
- `candidate_applications` for requisition-linked candidate workflow records
- `candidate_stage_history` for stage audit
- `daily_updates` for requisition-linked execution updates

Implementation note:

- older planning files may still use `candidate_requisition_links`
- for the backend MVP, treat `candidate_applications` as the canonical name

## Global Standards

### Base Path

- `/api/v1`

### Response Model

Successful read response:

```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

Successful write response:

```json
{
  "success": true,
  "message": "Created successfully",
  "data": {}
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid",
    "details": []
  }
}
```

### Standard Error Codes

- `AUTH_REQUIRED`
- `AUTH_INVALID`
- `FORBIDDEN`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `CONFLICT`
- `DUPLICATE_DETECTED`
- `APPROVAL_REQUIRED`
- `LOCATION_ACCESS_DENIED`

### Pagination

List endpoints should support:

- `page`
- `page_size`
- `sort_by`
- `sort_order`

### Auth Rules

- authenticated routes require a valid session or bearer token
- permission checks are server-side only
- scope checks are server-side only

## Frontend Responsibility Split

### Allowed In Frontend JS Only

These can be handled in frontend JS because they are presentation, convenience, or temporary client-side behavior:

- local form step transitions
- client-side field formatting
- inline required-field hints
- password strength meter display
- local search inside already-loaded table rows
- local table sorting on already-loaded data when server sorting is not required
- local filter chip rendering
- sticky action bars
- drawer open and close state
- dialog open and close state
- success toasts
- warning banners
- empty-state switching
- loading skeleton switching
- local draft save for unfinished form input
- page-level tab switching
- local KPI card animation or count-up effect
- local board drag preview before final submit

### Must Use API

These must be backend-backed because they change business state, require validation, or must be auditable:

- login and logout
- user creation and user updates
- role creation and permission assignment
- location creation and updates
- client creation and updates
- contact creation and updates
- requisition creation and updates
- ownership reassignment
- candidate creation and final save
- duplicate candidate lookup against company data
- duplicate decision persistence
- pipeline stage movement
- screening result persistence
- daily update submission
- notifications persistence
- dashboard metrics sourced from live records

### Hybrid Pattern

Some flows may use JS first and API second:

- candidate form draft can be stored locally before final save
- pipeline drag action can animate locally before submit confirmation
- filter bars can work locally after API list load
- success and reminder notifications can appear locally even when the source event came from an API response

## 1. Auth

### `POST /auth/login`

Request:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Response data:

- user id
- full name
- email
- primary role
- primary location
- token or session summary

### `POST /auth/logout`

Response:

- success message only

### `GET /auth/me`

Response data:

- user profile
- primary role
- business title
- primary location
- scope summary

### `GET /permissions/me`

Response data:

- module permissions
- action permissions
- scope permissions
- allowed pages if returned by backend

Frontend JS may handle:

- login form validation display
- password visibility toggle
- loading state visuals

API remains required for:

- authentication
- current user context
- permission payload

## 2. Locations

### `GET /locations`

Filters:

- status
- search

### `POST /locations`

Request:

```json
{
  "name": "Hyderabad",
  "code": "HYD",
  "address": "Optional",
  "status": "active",
  "location_head_user_id": 10
}
```

### `PATCH /locations/{location_id}`

Editable fields:

- name
- address
- status
- location_head_user_id

Frontend JS may handle:

- drawer state
- unsaved-change warning
- client-side code format hint

## 3. Users

### `GET /users`

Filters:

- location_id
- role_id
- status
- search

### `POST /users`

Request:

```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "9999999999",
  "employee_id": "EMP-1001",
  "primary_location_id": 1,
  "primary_role_id": 3,
  "reporting_manager_user_id": 2,
  "status": "active"
}
```

### `PATCH /users/{user_id}`

Editable fields:

- full_name
- phone
- primary_location_id
- primary_role_id
- reporting_manager_user_id
- status

### `POST /users/{user_id}/credentials/reset`

Response:

- reset confirmation

Frontend JS may handle:

- temporary password suggestion UI
- inline duplicate email warning before submit
- create and edit drawer flow

## 4. Roles

### `GET /roles`

### `POST /roles`

Request:

```json
{
  "name": "Lead Recruiter",
  "description": "Delivery supervision role",
  "status": "active"
}
```

### `PATCH /roles/{role_id}`

### `PUT /roles/{role_id}/permissions`

Request:

```json
{
  "modules": [],
  "actions": [],
  "scopes": []
}
```

Frontend JS may handle:

- permission group expand and collapse
- role summary preview
- unsaved-change warning

## 5. Clients

### `GET /clients`

Filters:

- location_id
- status
- client_owner_user_id
- search

### `POST /clients`

Request:

```json
{
  "client_name": "Acme Corp",
  "client_code": "CLI-1001",
  "location_id": 1,
  "industry": "Technology",
  "client_owner_user_id": 5,
  "business_source_owner_user_id": 3,
  "status": "active",
  "notes": "Optional"
}
```

### `GET /clients/{client_id}`

### `PATCH /clients/{client_id}`

Editable fields:

- client_name
- industry
- client_owner_user_id
- business_source_owner_user_id
- status
- notes

### `GET /clients/{client_id}/contacts`

### `POST /clients/{client_id}/contacts`

Request:

```json
{
  "contact_name": "Ravi Kumar",
  "email": "ravi@example.com",
  "phone": "9999999999",
  "designation": "HR Manager",
  "is_primary_contact": true
}
```

Frontend JS may handle:

- contact form dialog state
- inline duplicate contact warning inside the open dialog
- local contact card preview before save

API remains required for:

- location ownership validation
- client code uniqueness
- business source owner persistence

## 6. Requisitions

### `GET /requisitions`

Filters:

- location_id
- client_id
- primary_owner_user_id
- delivery_owner_user_id
- status
- priority
- due_date_from
- due_date_to

### `POST /requisitions`

Request:

```json
{
  "client_id": 11,
  "end_client_id": 15,
  "location_id": 1,
  "client_contact_id": 4,
  "title": "Senior Java Developer",
  "primary_owner_user_id": 8,
  "delivery_owner_user_id": 10,
  "openings_count": 3,
  "priority": "high",
  "target_closure_date": "2026-09-15",
  "employment_type": "permanent",
  "work_mode": "hybrid",
  "must_have_skills": ["Java", "Spring Boot"],
  "good_to_have_skills": ["AWS"],
  "acceptable_career_gap_months": 6,
  "profile_update_window_text": "11 AM to 1 PM",
  "client_round_required": true,
  "stage_template_code": "client-default"
}
```

### `GET /requisitions/{requisition_id}`

Response must include:

- client summary
- business source owner summary
- owner summary
- assignment summary
- screening rule summary
- pipeline counter summary

### `PATCH /requisitions/{requisition_id}`

Editable fields:

- title
- client_contact_id
- primary_owner_user_id
- delivery_owner_user_id
- openings_count
- priority
- target_closure_date
- must_have_skills
- good_to_have_skills
- acceptable_career_gap_months
- profile_update_window_text

### `PATCH /requisitions/{requisition_id}/status`

### `POST /requisitions/{requisition_id}/assignments`

Request:

```json
{
  "assigned_user_id": 12,
  "assignment_type": "support"
}
```

Frontend JS may handle:

- structured form section switching
- skill chip entry UI
- local due-date urgency hint
- local priority recommendation preview

API remains required for:

- final priority persistence
- ownership changes
- assignment persistence
- status updates

## 7. Candidates

### `GET /candidates`

Filters:

- search
- requisition_id
- source_type
- stage
- duplicate_state
- owner_user_id
- sourced_by_user_id

### `POST /candidates`

Request:

```json
{
  "full_name": "Asha Reddy",
  "email": "asha@example.com",
  "phone": "9999999999",
  "source_type": "naukri",
  "source_detail": "Direct sourcing",
  "current_company": "ABC Ltd",
  "current_designation": "Developer",
  "social_profiles": [
    {
      "type": "linkedin",
      "url": "https://linkedin.com/in/example"
    }
  ],
  "sourced_by_user_id": 12,
  "primary_owner_user_id": 10,
  "save_mode": "draft"
}
```

### `POST /candidates/{candidate_id}/resume`

Multipart upload:

- file

### `GET /candidates/{candidate_id}`

### `PATCH /candidates/{candidate_id}`

### `GET /candidates/{candidate_id}/duplicate-check`

Response must include:

- matched candidates
- match reasons
- suggested actions

### `POST /candidates/{candidate_id}/duplicate-decision`

Request:

```json
{
  "decision": "request_override",
  "matched_candidate_id": 55,
  "decision_notes": "Possible same candidate with newer resume"
}
```

### `POST /candidates/{candidate_id}/finalize`

Request:

```json
{
  "requisition_id": 21,
  "initial_stage": "sourced"
}
```

Response should include:

- `candidate_id`
- `application_id`
- `requisition_id`
- `current_stage`

Frontend JS may handle:

- local candidate draft
- resume upload progress UI
- compare view layout for duplicate review
- social profile chip editing

API remains required for:

- final candidate save
- duplicate lookup across company records
- duplicate decision persistence

## 8. Pipeline

### `GET /pipeline/board`

Filters:

- requisition_id
- owner_user_id
- sourced_by_user_id
- stage

Response should be built from:

- `candidate_applications`
- `candidates`
- `candidate_stage_history`
- `pipeline_templates`

### `POST /pipeline/{application_id}/move-stage`

Request:

```json
{
  "to_stage": "submitted",
  "notes": "Passed screening",
  "rejection_reason": null,
  "interview_date": null,
  "joining_date": null
}
```

### `GET /pipeline/{application_id}/history`

Frontend JS may handle:

- board drag preview
- stage column collapse or expand
- stage card hover actions

API remains required for:

- stage movement validation
- final stage update
- history persistence
- audit-safe stage transitions on `candidate_applications`

## 9. Daily Updates

### `GET /daily-updates`

Filters:

- location_id
- user_id
- requisition_id
- update_date

### `POST /daily-updates`

Request:

```json
{
  "update_date": "2026-08-18",
  "requisition_id": 21,
  "summary": "Worked on screening and submissions",
  "profiles_sourced_count": 6,
  "profiles_screened_count": 4,
  "profiles_submitted_count": 2,
  "interviews_scheduled_count": 1,
  "offers_closed_count": 0,
  "blockers": "Awaiting client feedback",
  "next_actions": "Submit two more profiles",
  "submission_status": "submitted"
}
```

### `GET /daily-updates/{daily_update_id}`

Response should include:

- requisition summary
- submitted by summary
- counts block
- blockers
- next actions
- submission status
- review status if available

Frontend JS may handle:

- draft narrative helper text
- count-total preview
- submit-success routing

API remains required for:

- requisition linkage validation
- one-location scope enforcement
- submission status persistence

## 10. Dashboards

### `GET /dashboards/role`

Returns:

- KPI cards
- work queue summary
- stale items summary
- duplicate review summary

### `GET /dashboards/my-work`

Returns:

- assigned requisitions
- due tasks
- interviews today
- update submission status

Dashboard source rule:

- role dashboard and my-work dashboard must read from live `requisitions`, `candidate_applications`, `daily_updates`, and `notifications`
- do not compute source-of-truth KPIs only in frontend JS

Frontend JS may handle:

- widget expand and collapse
- local widget refresh animation
- drill-down highlight state

## 11. Notifications

### `GET /notifications`

### `PATCH /notifications/{notification_id}/read`

Frontend JS may handle:

- optimistic mark-read state
- unread badge animation
- local notification drawer open state

## Contract Completion Rule

An endpoint is not implementation-ready until it has:

- request shape
- response shape
- validation rules
- permission rule
- scope rule
- error conditions
