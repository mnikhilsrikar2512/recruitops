# API Implementation Contract

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document expands the MVP API baseline into implementation-ready contracts.

Each endpoint in this file includes:

- request shape
- response shape
- validation rules
- permission rule
- scope rule
- main error conditions

Read this together with:

- [BUILD_PACK_BACKEND_EXECUTION_PLAN.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/BUILD_PACK_BACKEND_EXECUTION_PLAN.md)
- [BUILD_PACK_API_CONTRACT_BASELINE.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/BUILD_PACK_API_CONTRACT_BASELINE.md)
- [MVP_SCHEMA_V2.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/MVP_SCHEMA_V2.md)
- [MVP_USE_CASE_API_CONTRACTS.md](/Users/bhargavnikhil/Desktop/recrutment%20system/docs/system/MVP_USE_CASE_API_CONTRACTS.md)

## Global Rules

### Base Path

- `/api/v1`

### Canonical Backend Names

- `clients`
- `business_source_owner_user_id`
- `requisitions`
- `candidate_applications`
- `candidate_stage_history`
- `daily_updates`

### Response Envelope

Successful read:

```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

Successful write:

```json
{
  "success": true,
  "message": "Created successfully",
  "data": {}
}
```

Error:

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

### Common Pagination

List endpoints support:

- `page`
- `page_size`
- `sort_by`
- `sort_order`

## 1. Auth And Access

### `POST /auth/login`

Request:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Response `data`:

```json
{
  "token": "jwt-or-session-token",
  "user": {
    "id": 12,
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "status": "active",
    "business_title": "Lead Recruiter"
  },
  "primary_role": {
    "id": 3,
    "code": "delivery_lead",
    "name": "Delivery Lead"
  },
  "primary_location": {
    "id": 1,
    "location_code": "HYD",
    "location_name": "Hyderabad"
  }
}
```

Validation:

- `email` required and normalized to lowercase
- `password` required
- user must exist
- password must match stored hash
- user status must be `active`

Permission rule:

- public endpoint

Scope rule:

- none

Main errors:

- `AUTH_INVALID`
- `FORBIDDEN`

### `POST /auth/logout`

Validation:

- active authenticated session required

Permission rule:

- authenticated user

Scope rule:

- own session only

Main errors:

- `AUTH_REQUIRED`

### `GET /auth/me`

Response `data`:

```json
{
  "user": {
    "id": 12,
    "employee_code": "EMP-1001",
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "9999999999",
    "status": "active",
    "business_title": "Lead Recruiter"
  },
  "primary_role": {
    "id": 3,
    "code": "delivery_lead",
    "name": "Delivery Lead"
  },
  "primary_location": {
    "id": 1,
    "location_code": "HYD",
    "location_name": "Hyderabad"
  }
}
```

Validation:

- authenticated session required

Permission rule:

- authenticated user

Scope rule:

- own profile only

### `GET /permissions/me`

Response `data`:

```json
{
  "role_code": "delivery_lead",
  "permissions": [
    "clients.view",
    "requisitions.manage",
    "pipeline.move_stage"
  ],
  "scopes": {
    "clients": "location",
    "requisitions": "location",
    "candidates": "team"
  },
  "allowed_pages": [
    "Role Dashboard",
    "Requisition Detail",
    "Pipeline Board"
  ]
}
```

Validation:

- authenticated session required

Permission rule:

- authenticated user

Scope rule:

- own permission context only

## 2. Locations

### `GET /locations`

Query:

- `status`
- `search`
- `page`
- `page_size`

Permission rule:

- `locations.view`

Scope rule:

- Admin all
- others only if explicitly granted

### `POST /locations`

Request:

```json
{
  "location_name": "Hyderabad",
  "location_code": "HYD",
  "address": "Optional text",
  "status": "active",
  "location_head_user_id": 10
}
```

Validation:

- `location_name` required
- `location_code` required and unique
- `status` must be valid
- `location_head_user_id` must exist if provided

Permission rule:

- `locations.create`

Scope rule:

- Admin only for MVP

### `PATCH /locations/{location_id}`

Editable fields:

- `location_name`
- `address`
- `status`
- `location_head_user_id`

Permission rule:

- `locations.edit`

Scope rule:

- Admin only for MVP

## 3. Users

### `GET /users`

Query:

- `location_id`
- `role_id`
- `status`
- `search`
- `page`
- `page_size`

Permission rule:

- `users.view`

Scope rule:

- Admin all
- others by configured scope

### `POST /users`

Request:

```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "9999999999",
  "employee_code": "EMP-1001",
  "primary_location_id": 1,
  "primary_role_id": 3,
  "reporting_manager_user_id": 2,
  "business_title": "Lead Recruiter",
  "status": "active"
}
```

Validation:

- `full_name`, `email`, `employee_code`, `primary_location_id`, `primary_role_id` required
- email unique
- employee code unique
- related ids must exist

Permission rule:

- `users.create`

Scope rule:

- Admin only for MVP

### `PATCH /users/{user_id}`

Editable fields:

- `full_name`
- `phone`
- `primary_location_id`
- `primary_role_id`
- `reporting_manager_user_id`
- `business_title`
- `status`

Permission rule:

- `users.edit`

Scope rule:

- Admin only for MVP

### `POST /users/{user_id}/credentials/reset`

Request:

```json
{
  "mode": "setup-link"
}
```

Validation:

- `mode` in `temporary-password`, `setup-link`

Permission rule:

- `users.reset_credentials`

Scope rule:

- Admin only for MVP

## 4. Roles

### `GET /roles`

Permission rule:

- `roles.view`

Scope rule:

- Admin only for MVP

### `POST /roles`

Request:

```json
{
  "name": "Lead Recruiter",
  "code": "lead_recruiter",
  "description": "Delivery supervision role",
  "status": "active"
}
```

Validation:

- `name` required
- `code` required and unique

Permission rule:

- `roles.create`

Scope rule:

- Admin only for MVP

### `PATCH /roles/{role_id}`

Editable fields:

- `name`
- `description`
- `status`

Permission rule:

- `roles.edit`

Scope rule:

- Admin only for MVP

### `PUT /roles/{role_id}/permissions`

Request:

```json
{
  "permission_codes": [
    "clients.view",
    "requisitions.manage",
    "pipeline.move_stage"
  ],
  "scope_rules": {
    "clients": "location",
    "requisitions": "location",
    "candidates": "team"
  }
}
```

Validation:

- role must exist
- permission codes must exist
- scopes must be valid

Permission rule:

- `roles.assign_permissions`

Scope rule:

- Admin only for MVP

## 5. Clients

### `GET /clients`

Query:

- `location_id`
- `status`
- `client_owner_user_id`
- `business_source_owner_user_id`
- `search`
- `page`
- `page_size`

Permission rule:

- `clients.view`

Scope rule:

- location-bound by default

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

Validation:

- `client_name`, `client_code`, `location_id`, `client_owner_user_id`, `business_source_owner_user_id` required
- client code unique
- related ids valid

Permission rule:

- `clients.create`

Scope rule:

- create only in allowed location

### `GET /clients/{client_id}`

Permission rule:

- `clients.view`

Scope rule:

- same as client list

### `PATCH /clients/{client_id}`

Editable fields:

- `client_name`
- `industry`
- `client_owner_user_id`
- `business_source_owner_user_id`
- `status`
- `notes`

Permission rule:

- `clients.edit`

Scope rule:

- same as client create

### `GET /clients/{client_id}/contacts`

Permission rule:

- `client_contacts.view`

Scope rule:

- same as parent client

### `POST /clients/{client_id}/contacts`

Request:

```json
{
  "contact_name": "Ravi Kumar",
  "email": "ravi@example.com",
  "phone": "9999999999",
  "designation": "HR Manager",
  "is_primary_contact": true,
  "is_secondary_contact": false
}
```

Permission rule:

- `client_contacts.create`

Scope rule:

- same as parent client

### `PATCH /client-contacts/{contact_id}`

Permission rule:

- `client_contacts.edit`

Scope rule:

- same as parent client

## 6. Requisitions

### `GET /requisitions`

Query:

- `location_id`
- `client_id`
- `primary_owner_user_id`
- `delivery_owner_user_id`
- `status`
- `priority`
- `due_date_from`
- `due_date_to`
- `search`
- `page`
- `page_size`

Permission rule:

- `requisitions.view`

Scope rule:

- location-bound by default

### `POST /requisitions`

Request:

```json
{
  "client_id": 11,
  "primary_contact_id": 4,
  "secondary_contact_id": 5,
  "location_id": 1,
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
  "job_description": "Structured JD text",
  "stage_template_id": 2
}
```

Validation:

- core ids and title required
- client must belong to location
- contact ids must belong to client if supplied
- openings positive
- priority valid

Permission rule:

- `requisitions.create`

Scope rule:

- create only in allowed location

### `GET /requisitions/{requisition_id}`

Permission rule:

- `requisitions.view`

Scope rule:

- same as requisition list

### `PATCH /requisitions/{requisition_id}`

Permission rule:

- `requisitions.edit`

Scope rule:

- same as requisition edit scope

### `PATCH /requisitions/{requisition_id}/status`

Request:

```json
{
  "status": "on-hold",
  "reason": "Awaiting client confirmation"
}
```

Permission rule:

- `requisitions.change_status`

Scope rule:

- same as requisition edit scope

### `GET /requisitions/{requisition_id}/assignments`

Permission rule:

- `requisition_assignments.view`

Scope rule:

- same as requisition view

### `POST /requisitions/{requisition_id}/assignments`

Request:

```json
{
  "assigned_user_id": 12,
  "assignment_type": "support"
}
```

Validation:

- assignment type in `primary_owner`, `delivery_owner`, `contributor`, `support`

Permission rule:

- `requisition_assignments.create`

Scope rule:

- same as requisition edit

### `DELETE /requisition-assignments/{assignment_id}`

Permission rule:

- `requisition_assignments.delete`

Scope rule:

- same as parent requisition edit scope

## 7. Candidates

### `GET /candidates`

Query:

- `search`
- `requisition_id`
- `source_type`
- `duplicate_state`
- `owner_user_id`
- `sourced_by_user_id`
- `page`
- `page_size`

Permission rule:

- `candidates.view`

Scope rule:

- permission-based candidate visibility

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
  "total_experience_years": 5.5,
  "notice_period_days": 30,
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

Validation:

- `full_name` required
- `source_type` required
- owner ids valid
- `save_mode` in `draft`, `final`

Permission rule:

- `candidates.create`

Scope rule:

- allowed owned or location workflow

### `POST /candidates/{candidate_id}/resume`

Permission rule:

- `candidates.upload_resume`

Scope rule:

- same as candidate edit

### `GET /candidates/{candidate_id}`

Permission rule:

- `candidates.view`

Scope rule:

- same as candidate list

### `PATCH /candidates/{candidate_id}`

Permission rule:

- `candidates.edit`

Scope rule:

- same as candidate edit scope

### `GET /candidates/{candidate_id}/duplicate-check`

Permission rule:

- `candidates.duplicate_check`

Scope rule:

- global duplicate search allowed
- returned details still permission-controlled

### `POST /candidates/{candidate_id}/duplicate-decision`

Request:

```json
{
  "decision": "request_override",
  "matched_candidate_id": 55,
  "decision_notes": "Possible same candidate with newer resume"
}
```

Permission rule:

- `candidates.duplicate_decide`

Scope rule:

- same as candidate edit

### `POST /candidates/{candidate_id}/finalize`

Request:

```json
{
  "requisition_id": 21,
  "initial_stage": "sourced"
}
```

Response `data`:

```json
{
  "candidate_id": 21,
  "application_id": 301,
  "requisition_id": 21,
  "current_stage": "sourced"
}
```

Permission rule:

- `candidates.finalize`

Scope rule:

- requisition must be inside allowed scope

## 8. Pipeline

### `GET /pipeline/board`

Query:

- `requisition_id`
- `owner_user_id`
- `sourced_by_user_id`
- `stage`

Permission rule:

- `pipeline.view`

Scope rule:

- tied to requisition visibility

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

Validation:

- target stage valid
- stage transition allowed

Permission rule:

- `pipeline.move_stage`

Scope rule:

- tied to application and requisition access

### `GET /pipeline/{application_id}/history`

Permission rule:

- `pipeline.history.view`

Scope rule:

- same as application visibility

## 9. Daily Updates

### `GET /daily-updates`

Query:

- `location_id`
- `user_id`
- `requisition_id`
- `update_date`
- `page`
- `page_size`

Permission rule:

- `daily_updates.view`

Scope rule:

- own, team, location, or global depending on config

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

Validation:

- `update_date`, `requisition_id`, `summary` required
- counts non-negative
- status in `draft`, `submitted`

Permission rule:

- `daily_updates.create`

Scope rule:

- create only for accessible requisition

### `GET /daily-updates/{daily_update_id}`

Permission rule:

- `daily_updates.view`

Scope rule:

- tied to update visibility

## 10. Dashboards

### `GET /dashboards/role`

Permission rule:

- `dashboards.role.view`

Scope rule:

- configured role scope

### `GET /dashboards/my-work`

Permission rule:

- `dashboards.my_work.view`

Scope rule:

- own user context only

## 11. Notifications

### `GET /notifications`

Query:

- `status`
- `priority`
- `page`
- `page_size`

Permission rule:

- `notifications.view`

Scope rule:

- own notifications only for MVP

### `PATCH /notifications/{notification_id}/read`

Request:

```json
{
  "status": "read"
}
```

Validation:

- notification must belong to current user

Permission rule:

- `notifications.mark_read`

Scope rule:

- own notification only

## Final Rule

An endpoint is not implementation-ready until:

1. request shape is locked
2. response shape is locked
3. validation rules are explicit
4. permission rule is explicit
5. scope rule is explicit
6. main error conditions are explicit
