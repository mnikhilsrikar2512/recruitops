# MVP Page API Payload Map

## Purpose

This document maps MVP pages and actions to exact API payload expectations.

It is the handoff reference for:

- frontend integration
- backend request and response shaping
- QA action-level verification
- page-level success and error state planning

Use this document with:

- `docs/system/MVP_USE_CASE_PAGE_EXECUTION_MAP.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md`
- `docs/system/BUILD_PACK_SCREEN_FIELD_SPEC.md`

## How To Read This Document

Each action block below defines:

- the page or UI container
- the button or action name
- the API endpoint
- the minimum request payload
- the minimum response payload the page needs
- the expected success result in UI
- the expected error states in UI

## Shared API Envelope

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
  "message": "Saved successfully",
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

## Standard UI Error Handling Rule

Frontend should handle errors in these groups:

- `field error`
  show below the input or section
- `form error`
  show inside a visible error banner
- `permission error`
  show restricted-action message and remove retry loop
- `scope error`
  show access-denied state
- `conflict or duplicate error`
  redirect or open the defined review flow
- `unexpected error`
  show retry state and preserve user input when safe

## 1. Login

### Page: `Login`

#### Action: `Sign In`

- Endpoint:
  `POST /api/v1/auth/login`
- Request payload:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

- Minimum response `data`:

```json
{
  "token": "jwt-or-session-token",
  "user": {
    "id": 12,
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "status": "active"
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

- UI success state:
  store session, call access bootstrap endpoints, redirect to `Role Dashboard`
- UI error states:
  invalid credential banner, inactive-user banner, required-field errors

#### Action: `Load Current User Context`

- Endpoints:
  `GET /api/v1/auth/me`
  `GET /api/v1/permissions/me`
- Request payload:
  none beyond auth token
- Minimum response `data`:

```json
{
  "user": {
    "id": 12,
    "employee_code": "EMP-1001",
    "full_name": "Jane Doe",
    "business_title": "Lead Recruiter"
  },
  "primary_role": {
    "code": "delivery_lead",
    "name": "Delivery Lead"
  },
  "primary_location": {
    "id": 1,
    "location_name": "Hyderabad"
  },
  "permissions": [
    "requisition.read",
    "pipeline.stage.move"
  ],
  "allowed_pages": [
    "Role Dashboard",
    "Pipeline Board"
  ]
}
```

- UI success state:
  load shell navigation and landing widgets
- UI error states:
  expired-session redirect to `Login`, permission-load failure banner

## 2. Location Management

### Page: `Location Management`

#### Action: `Load Location List`

- Endpoint:
  `GET /api/v1/locations?page=1&page_size=20&status=active&search=hyd`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 1,
      "location_code": "HYD",
      "location_name": "Hyderabad",
      "status": "active",
      "location_head": {
        "id": 10,
        "full_name": "Alex Rao"
      }
    }
  ]
}
```

- UI success state:
  render table, counts, filters
- UI error states:
  table error state, empty state, permission denied state

#### Action: `Create Location`

- Endpoint:
  `POST /api/v1/locations`
- Request payload:

```json
{
  "location_name": "Hyderabad",
  "location_code": "HYD",
  "address": "Optional text",
  "status": "active",
  "location_head_user_id": 10
}
```

- Minimum response `data`:

```json
{
  "id": 1,
  "location_name": "Hyderabad",
  "location_code": "HYD",
  "status": "active"
}
```

- UI success state:
  close dialog or drawer, refresh table, show success toast
- UI error states:
  duplicate code error, missing required field errors, invalid head-user error

#### Action: `Update Location`

- Endpoint:
  `PUT /api/v1/locations/{location_id}`
- Request payload:

```json
{
  "location_name": "Hyderabad",
  "location_code": "HYD",
  "address": "Updated address",
  "status": "inactive",
  "location_head_user_id": 12
}
```

- Minimum response `data`:

```json
{
  "id": 1,
  "status": "inactive"
}
```

- UI success state:
  update visible row and detail state
- UI error states:
  conflict error, validation error, forbidden error

## 3. Role Management

### Page: `Role Management`

#### Action: `Load Role List`

- Endpoint:
  `GET /api/v1/roles?page=1&page_size=20&status=active&search=lead`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 3,
      "code": "lead_recruiter",
      "name": "Lead Recruiter",
      "status": "active",
      "assigned_users_count": 8
    }
  ]
}
```

- UI success state:
  render role table and open edit actions
- UI error states:
  empty table state, permission denied state

#### Action: `Create Role`

- Endpoint:
  `POST /api/v1/roles`
- Request payload:

```json
{
  "name": "Lead Recruiter",
  "code": "lead_recruiter",
  "description": "Delivery supervision role",
  "status": "active"
}
```

- Minimum response `data`:

```json
{
  "id": 3,
  "name": "Lead Recruiter",
  "code": "lead_recruiter",
  "status": "active"
}
```

- UI success state:
  open permission assignment state or return to table with success toast
- UI error states:
  duplicate role code, invalid status, forbidden error

#### Action: `Assign Role Permissions`

- Endpoint:
  `PUT /api/v1/roles/{role_id}/permissions`
- Request payload:

```json
{
  "permission_codes": [
    "client.read",
    "requisition.read",
    "requisition.update",
    "pipeline.read",
    "pipeline.stage.move"
  ],
  "scope_rules": {
    "clients": "location",
    "requisitions": "location",
    "candidates": "location",
    "pipeline": "location"
  },
  "allowed_pages": [
    "Role Dashboard",
    "Requisition Detail",
    "Pipeline Board"
  ]
}
```

- Minimum response `data`:

```json
{
  "role_id": 3,
  "permission_codes": [
    "client.read",
    "requisition.read",
    "pipeline.stage.move"
  ],
  "scope_rules": {
    "clients": "location",
    "pipeline": "location"
  }
}
```

- UI success state:
  matrix reflects saved access immediately
- UI error states:
  invalid permission code, invalid scope rule, forbidden error

## 4. User Management

### Page: `User Management`

#### Action: `Load User List`

- Endpoint:
  `GET /api/v1/users?page=1&page_size=20&status=active&location_id=1&search=jane`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 12,
      "employee_code": "EMP-1001",
      "full_name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "9999999999",
      "status": "active",
      "primary_role": {
        "id": 3,
        "name": "Lead Recruiter"
      },
      "primary_location": {
        "id": 1,
        "location_name": "Hyderabad"
      }
    }
  ]
}
```

- UI success state:
  render user table and row actions
- UI error states:
  empty state, permission denied state

#### Action: `Create User`

- Endpoint:
  `POST /api/v1/users`
- Request payload:

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
  "secondary_contact": "8888888888",
  "status": "active"
}
```

- Minimum response `data`:

```json
{
  "id": 12,
  "employee_code": "EMP-1001",
  "full_name": "Jane Doe",
  "status": "active"
}
```

- UI success state:
  close create drawer, refresh list, optionally show invite or reset step
- UI error states:
  duplicate email, duplicate phone, duplicate employee code, self-manager error, invalid location or role

#### Action: `Update User`

- Endpoint:
  `PUT /api/v1/users/{user_id}`
- Request payload:

```json
{
  "full_name": "Jane Doe",
  "phone": "9999999998",
  "primary_location_id": 1,
  "primary_role_id": 4,
  "reporting_manager_user_id": 5,
  "business_title": "Senior Recruiter",
  "status": "active"
}
```

- Minimum response `data`:

```json
{
  "id": 12,
  "full_name": "Jane Doe",
  "primary_role": {
    "id": 4,
    "name": "Senior Recruiter"
  }
}
```

- UI success state:
  update row and detail view
- UI error states:
  validation banner, forbidden error, conflict error

#### Action: `Deactivate User`

- Endpoint:
  `POST /api/v1/users/{user_id}/deactivate`
- Request payload:

```json
{
  "replacement_user_id": 20,
  "review_note": "Moved active ownership before deactivation"
}
```

- Minimum response `data`:

```json
{
  "id": 12,
  "status": "inactive",
  "reassigned_records_count": 6
}
```

- UI success state:
  close deactivation flow, show updated inactive state
- UI error states:
  active work review required, missing replacement user, forbidden error

## 5. Client Directory And Client Detail

### Page: `Client Directory`

#### Action: `Load Client List`

- Endpoint:
  `GET /api/v1/clients?page=1&page_size=20&location_id=1&status=active&search=tech`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 7,
      "client_code": "CLI-001",
      "client_name": "Tech Corp",
      "status": "active",
      "location": {
        "id": 1,
        "location_name": "Hyderabad"
      },
      "client_owner": {
        "id": 4,
        "full_name": "Asha"
      },
      "business_source_owner": {
        "id": 9,
        "full_name": "Ravi"
      }
    }
  ]
}
```

- UI success state:
  render client grid or table
- UI error states:
  empty state, location access denied

#### Action: `Create Client`

- Endpoint:
  `POST /api/v1/clients`
- Request payload:

```json
{
  "client_name": "Tech Corp",
  "client_code": "CLI-001",
  "location_id": 1,
  "industry": "IT Services",
  "client_owner_user_id": 4,
  "business_source_owner_user_id": 9,
  "status": "active",
  "notes": "Strategic client"
}
```

- Minimum response `data`:

```json
{
  "id": 7,
  "client_code": "CLI-001",
  "client_name": "Tech Corp"
}
```

- UI success state:
  refresh list or navigate to `Client Detail`
- UI error states:
  duplicate client, invalid owner, invalid location, forbidden error

### Page: `Client Detail`

#### Action: `Load Client Detail`

- Endpoint:
  `GET /api/v1/clients/{client_id}`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "id": 7,
  "client_code": "CLI-001",
  "client_name": "Tech Corp",
  "status": "active",
  "location": {
    "id": 1,
    "location_name": "Hyderabad"
  },
  "contacts": [],
  "active_requisitions_count": 3
}
```

- UI success state:
  show summary, contacts, linked requisitions
- UI error states:
  not found, location access denied

#### Action: `Create Or Update Client Contact`

- Endpoints:
  `POST /api/v1/clients/{client_id}/contacts`
  `PUT /api/v1/client-contacts/{contact_id}`
- Request payload:

```json
{
  "contact_name": "Meera Singh",
  "email": "meera@example.com",
  "phone": "9000000000",
  "designation": "HR Manager",
  "is_primary": true,
  "is_secondary": false
}
```

- Minimum response `data`:

```json
{
  "id": 31,
  "contact_name": "Meera Singh",
  "is_primary": true
}
```

- UI success state:
  close dialog and refresh contacts table
- UI error states:
  invalid client mapping, validation error, forbidden error

## 6. Requisition List, Intake, And Detail

### Page: `Requisition List`

#### Action: `Load Requisition List`

- Endpoint:
  `GET /api/v1/requisitions?page=1&page_size=20&location_id=1&status=open&client_id=7`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 18,
      "requisition_code": "REQ-2026-018",
      "title": "Java Developer",
      "status": "open",
      "priority": "high",
      "client": {
        "id": 7,
        "client_name": "Tech Corp"
      }
    }
  ]
}
```

- UI success state:
  render list and filters
- UI error states:
  empty state, access denied

### Page: `Requisition Intake`

#### Action: `Create Requisition`

- Endpoint:
  `POST /api/v1/requisitions`
- Request payload:

```json
{
  "title": "Java Developer",
  "client_id": 7,
  "client_contact_id": 31,
  "location_id": 1,
  "openings": 3,
  "priority": "high",
  "skills": [
    "Java",
    "Spring Boot"
  ],
  "acceptable_career_gap": "Up to 1 year",
  "target_closure_date": "2026-09-15",
  "profile_update_availability_time": "15:00-17:00",
  "primary_owner_user_id": 4,
  "delivery_owner_user_id": 10,
  "pipeline_template_id": 2,
  "status": "open"
}
```

- Minimum response `data`:

```json
{
  "id": 18,
  "requisition_code": "REQ-2026-018",
  "status": "open"
}
```

- UI success state:
  redirect to `Requisition Detail`
- UI error states:
  inactive client, wrong-location owner, invalid contact, missing required fields

#### Action: `Update Requisition`

- Endpoint:
  `PUT /api/v1/requisitions/{requisition_id}`
- Request payload:

```json
{
  "title": "Senior Java Developer",
  "openings": 2,
  "priority": "medium",
  "skills": [
    "Java",
    "Spring Boot",
    "Microservices"
  ],
  "acceptable_career_gap": "Up to 1 year",
  "profile_update_availability_time": "14:00-16:00"
}
```

- Minimum response `data`:

```json
{
  "id": 18,
  "title": "Senior Java Developer"
}
```

- UI success state:
  stay on detail or return to detail with refreshed data
- UI error states:
  validation error, forbidden error, conflict error

### Page: `Requisition Detail`

#### Action: `Load Requisition Detail`

- Endpoint:
  `GET /api/v1/requisitions/{requisition_id}`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "id": 18,
  "requisition_code": "REQ-2026-018",
  "title": "Java Developer",
  "status": "open",
  "priority": "high",
  "client": {
    "id": 7,
    "client_name": "Tech Corp"
  },
  "owners": {
    "primary_owner": {
      "id": 4,
      "full_name": "Asha"
    },
    "delivery_owner": {
      "id": 10,
      "full_name": "Rahul"
    }
  }
}
```

- UI success state:
  render summary, assignments, pipeline snapshot, status history
- UI error states:
  not found, access denied

#### Action: `Update Requisition Status`

- Endpoint:
  `PATCH /api/v1/requisitions/{requisition_id}/status`
- Request payload:

```json
{
  "status": "closed",
  "reason": "Position filled"
}
```

- Minimum response `data`:

```json
{
  "id": 18,
  "status": "closed",
  "status_reason": "Position filled"
}
```

- UI success state:
  update status chip and history panel
- UI error states:
  invalid transition, missing reason, forbidden error

#### Action: `Add Assignment`

- Endpoint:
  `POST /api/v1/requisitions/{requisition_id}/assignments`
- Request payload:

```json
{
  "user_id": 25,
  "assignment_role": "recruiter",
  "note": "Primary sourcing support"
}
```

- Minimum response `data`:

```json
{
  "assignment_id": 90,
  "user": {
    "id": 25,
    "full_name": "Neha"
  },
  "assignment_role": "recruiter",
  "status": "active"
}
```

- UI success state:
  refresh assignment panel and counts
- UI error states:
  wrong-location assignee, duplicate assignment, forbidden error

#### Action: `Remove Assignment`

- Endpoint:
  `DELETE /api/v1/requisition-assignments/{assignment_id}`
- Request payload:

```json
{
  "review_note": "Capacity rebalanced"
}
```

- Minimum response `data`:

```json
{
  "assignment_id": 90,
  "status": "removed"
}
```

- UI success state:
  row removed or marked inactive in history-aware view
- UI error states:
  active work review required, forbidden error, not found

#### Action: `Reassign Owner`

- Endpoint:
  `POST /api/v1/requisitions/{requisition_id}/reassign`
- Request payload:

```json
{
  "from_user_id": 10,
  "to_user_id": 30,
  "reason": "Planned leave coverage"
}
```

- Minimum response `data`:

```json
{
  "requisition_id": 18,
  "from_user_id": 10,
  "to_user_id": 30,
  "active_work_impacted": true
}
```

- UI success state:
  refresh owner card and show audit confirmation
- UI error states:
  active work review missing, forbidden error, location scope denial

## 7. Candidate Profiles And Duplicate Review

### Page: `Candidate Profiles`

#### Action: `Load Candidate List`

- Endpoint:
  `GET /api/v1/candidates?page=1&page_size=20&search=rao&owner_id=25`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 101,
      "full_name": "Priya Rao",
      "primary_phone": "9999990000",
      "primary_email": "priya@example.com",
      "owner": {
        "id": 25,
        "full_name": "Neha"
      },
      "duplicate_state": "clear"
    }
  ]
}
```

- UI success state:
  render list, duplicate badges, quick actions
- UI error states:
  empty state, permission denied

#### Action: `Create Candidate`

- Endpoint:
  `POST /api/v1/candidates`
- Request payload:

```json
{
  "full_name": "Priya Rao",
  "primary_phone": "9999990000",
  "primary_email": "priya@example.com",
  "secondary_contact": "8888880000",
  "skills": [
    "Java",
    "Spring Boot"
  ],
  "current_location": "Hyderabad",
  "source_type": "linkedin",
  "source_owner_user_id": 25,
  "candidate_owner_user_id": 25,
  "social_profiles": [
    {
      "platform": "linkedin",
      "url": "https://linkedin.com/in/priyarao"
    }
  ],
  "status": "draft"
}
```

- Minimum response `data`:

```json
{
  "id": 101,
  "full_name": "Priya Rao",
  "status": "draft",
  "duplicate_state": "pending_check"
}
```

- UI success state:
  remain on form or open detail with saved draft state
- UI error states:
  validation errors, forbidden error

#### Action: `Update Candidate`

- Endpoint:
  `PUT /api/v1/candidates/{candidate_id}`
- Request payload:

```json
{
  "skills": [
    "Java",
    "Spring Boot",
    "Microservices"
  ],
  "status": "ready_for_finalization"
}
```

- Minimum response `data`:

```json
{
  "id": 101,
  "status": "ready_for_finalization"
}
```

- UI success state:
  refresh detail state, enable next action
- UI error states:
  incomplete required data, forbidden error

#### Action: `Run Duplicate Check`

- Endpoint:
  `POST /api/v1/candidates/duplicate-check`
- Request payload:

```json
{
  "full_name": "Priya Rao",
  "primary_phone": "9999990000",
  "primary_email": "priya@example.com"
}
```

- Minimum response `data`:

```json
{
  "duplicate_state": "possible_duplicate",
  "matches": [
    {
      "candidate_id": 88,
      "full_name": "Priya Rao",
      "primary_phone": "9999990000",
      "primary_email": "priya.old@example.com"
    }
  ]
}
```

- UI success state:
  either allow finalization or open duplicate warning flow
- UI error states:
  duplicate service failure banner, validation errors

#### Action: `Link Candidate To Requisition`

- Endpoint:
  `POST /api/v1/candidates/{candidate_id}/applications`
- Request payload:

```json
{
  "requisition_id": 18,
  "submitted_by_user_id": 25,
  "initial_stage_code": "sourced",
  "note": "Strong backend profile"
}
```

- Minimum response `data`:

```json
{
  "application_id": 400,
  "candidate_id": 101,
  "requisition_id": 18,
  "current_stage_code": "sourced"
}
```

- UI success state:
  show successful linkage, enable pipeline tracking
- UI error states:
  duplicate same-requisition submission, forbidden error, invalid requisition

### Page: `Candidate Duplicate Review`

#### Action: `Load Duplicate Review Case`

- Endpoint:
  `GET /api/v1/candidates/duplicate-cases/{case_id}`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "case_id": 14,
  "submitted_candidate": {},
  "possible_matches": [],
  "review_status": "pending"
}
```

- UI success state:
  render side-by-side comparison
- UI error states:
  not found, forbidden error

#### Action: `Resolve Duplicate Case`

- Endpoint:
  `POST /api/v1/candidates/duplicate-cases/{case_id}/decision`
- Request payload:

```json
{
  "decision": "keep_existing_and_discard_new",
  "approved_by_user_id": 1,
  "note": "Confirmed same candidate by phone and email"
}
```

- Minimum response `data`:

```json
{
  "case_id": 14,
  "decision": "keep_existing_and_discard_new",
  "review_status": "resolved"
}
```

- UI success state:
  mark case resolved and navigate to the kept candidate or close review state
- UI error states:
  unauthorized reviewer, invalid decision, missing audit note

## 8. Pipeline Board

### Page: `Pipeline Board`

#### Action: `Load Pipeline Board`

- Endpoint:
  `GET /api/v1/pipeline/board?requisition_id=18&owner_id=25`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "stages": [
    {
      "stage_code": "sourced",
      "stage_name": "Sourced",
      "count": 4,
      "applications": [
        {
          "application_id": 400,
          "candidate": {
            "id": 101,
            "full_name": "Priya Rao"
          },
          "owner": {
            "id": 25,
            "full_name": "Neha"
          },
          "aging_days": 2
        }
      ]
    }
  ]
}
```

- UI success state:
  render board, counts, filters, quick actions
- UI error states:
  access denied, empty pipeline state

#### Action: `Load Application Detail`

- Endpoint:
  `GET /api/v1/pipeline/applications/{application_id}`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "application_id": 400,
  "candidate": {
    "id": 101,
    "full_name": "Priya Rao"
  },
  "requisition": {
    "id": 18,
    "title": "Java Developer"
  },
  "current_stage_code": "sourced",
  "history_count": 3
}
```

- UI success state:
  open application drawer
- UI error states:
  not found, access denied

#### Action: `Move Candidate Stage`

- Endpoint:
  `POST /api/v1/pipeline/applications/{application_id}/move-stage`
- Request payload:

```json
{
  "target_stage_code": "screening",
  "note": "Shortlisted for internal screening",
  "rejection_reason": null,
  "joining_date": null
}
```

- Minimum response `data`:

```json
{
  "application_id": 400,
  "previous_stage_code": "sourced",
  "current_stage_code": "screening",
  "moved_at": "2026-08-19T12:30:00Z"
}
```

- UI success state:
  move card to target stage and refresh counts
- UI error states:
  invalid stage, backward move blocked, rejection reason required, joining date required

#### Action: `Load Pipeline History`

- Endpoint:
  `GET /api/v1/pipeline/applications/{application_id}/history`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "items": [
    {
      "stage_code": "sourced",
      "stage_name": "Sourced",
      "moved_by": {
        "id": 25,
        "full_name": "Neha"
      },
      "moved_at": "2026-08-18T10:00:00Z",
      "note": "Initial submission"
    }
  ]
}
```

- UI success state:
  open history drawer with timeline
- UI error states:
  not found, access denied

## 9. Daily Updates

### Page: `Daily Updates Submission`

#### Action: `Load My Daily Updates`

- Endpoint:
  `GET /api/v1/daily-updates?user_id=25&date=2026-08-19`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 800,
      "requisition": {
        "id": 18,
        "title": "Java Developer"
      },
      "status": "submitted",
      "submitted_at": "2026-08-19T17:00:00Z"
    }
  ]
}
```

- UI success state:
  render today list and submission state
- UI error states:
  empty state, access denied

#### Action: `Submit Daily Update`

- Endpoint:
  `POST /api/v1/daily-updates`
- Request payload:

```json
{
  "requisition_id": 18,
  "update_date": "2026-08-19",
  "submitted_by_user_id": 25,
  "profiles_sourced_count": 5,
  "profiles_submitted_count": 2,
  "interviews_scheduled_count": 1,
  "blockers": "Waiting for client feedback on two profiles",
  "next_steps": "Share three more profiles tomorrow",
  "note": "Progress aligned with target"
}
```

- Minimum response `data`:

```json
{
  "id": 800,
  "requisition_id": 18,
  "status": "submitted"
}
```

- UI success state:
  clear form, show submitted state, refresh history strip
- UI error states:
  duplicate same-day update per company rule, unlinked requisition, forbidden error

### Page: `Daily Updates Review`

#### Action: `Load Team Updates`

- Endpoint:
  `GET /api/v1/daily-updates?location_id=1&date=2026-08-19&status=submitted`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 800,
      "submitted_by": {
        "id": 25,
        "full_name": "Neha"
      },
      "requisition": {
        "id": 18,
        "title": "Java Developer"
      },
      "status": "submitted"
    }
  ]
}
```

- UI success state:
  render review table and side panel detail
- UI error states:
  access denied, empty team state

## 10. Dashboards

### Page: `My Work Dashboard`

#### Action: `Load My Work`

- Endpoint:
  `GET /api/v1/dashboard/my-work`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "open_requisitions_count": 4,
  "my_pipeline_count": 12,
  "daily_update_pending_count": 2,
  "stalled_candidates_count": 3
}
```

- UI success state:
  render KPI cards and work widgets
- UI error states:
  partial-widget fallback or page error state

### Page: `Location Dashboard`

#### Action: `Load Location Summary`

- Endpoint:
  `GET /api/v1/dashboard/location-summary?location_id=1`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "location": {
    "id": 1,
    "location_name": "Hyderabad"
  },
  "open_requisitions_count": 15,
  "active_pipeline_count": 66,
  "submitted_updates_count": 21
}
```

- UI success state:
  render charts, KPI cards, summary widgets
- UI error states:
  location access denied, not found

### Page: `Company Dashboard`

#### Action: `Load Company Summary`

- Endpoint:
  `GET /api/v1/dashboard/company-summary`
- Request payload:
  none beyond auth
- Minimum response `data`:

```json
{
  "total_locations_count": 5,
  "open_requisitions_count": 72,
  "active_pipeline_count": 310,
  "submitted_updates_count": 104
}
```

- UI success state:
  render multi-location company overview
- UI error states:
  forbidden error, reporting permission missing

## 11. Notifications

### Page: `Notifications Center`

#### Action: `Load Notifications`

- Endpoint:
  `GET /api/v1/notifications?page=1&page_size=20&status=unread`
- Request payload:
  query only
- Minimum response `data`:

```json
{
  "items": [
    {
      "id": 900,
      "type": "duplicate_candidate_review",
      "title": "Duplicate review pending",
      "is_read": false,
      "linked_entity_type": "candidate_duplicate_case",
      "linked_entity_id": 14
    }
  ]
}
```

- UI success state:
  render notification list and counters
- UI error states:
  empty state, access denied

#### Action: `Mark Notification Read`

- Endpoint:
  `POST /api/v1/notifications/{notification_id}/read`
- Request payload:

```json
{}
```

- Minimum response `data`:

```json
{
  "id": 900,
  "is_read": true
}
```

- UI success state:
  update badge count and row state
- UI error states:
  not found, forbidden error

## Frontend Wiring Checklist

For each page action above, frontend should confirm:

- request payload keys match backend contract exactly
- page uses the correct success redirect or refresh behavior
- field-level errors map to the right input
- duplicate and approval cases route to the defined review page
- forbidden and scope-denied responses do not retry blindly

## QA Verification Checklist

For each action above, QA should verify:

- valid request succeeds
- invalid request returns correct field or form error
- wrong role is blocked
- wrong scope is blocked
- success response provides enough data for the page to update
- no action depends on frontend-only enforcement
