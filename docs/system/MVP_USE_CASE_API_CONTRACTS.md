# MVP Use Case API Contracts

## Purpose

This document turns the MVP use cases into execution-ready API flow contracts.

It is different from the generic endpoint catalog.

This file answers:

- which endpoints are used for each business use case
- in what sequence they are used
- what minimum request data is required
- what minimum response data the frontend needs
- what permission and scope checks must happen
- what validation checkpoints must block the flow

Use this document when:

- implementing backend services
- connecting frontend pages to APIs
- designing QA scenarios
- validating whether a use case is truly complete

Read this together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`
- `docs/system/BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md`
- `docs/system/API_VALIDATION_RULES.md`

## Contract Style

Each use case below includes:

- goal
- endpoint sequence
- minimum request contract
- minimum response contract
- access enforcement
- validation checkpoints
- completion proof

## Group 1. Access And Setup

### UC-01 User Login

Goal:

- authenticate the user and load working context

Endpoint sequence:

1. `POST /api/v1/auth/login`
2. `GET /api/v1/auth/me`
3. `GET /api/v1/permissions/me`

Minimum request contract:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Minimum response contract:

- auth token or session confirmation
- user id
- full name
- active status
- primary role code
- primary location id and name
- permission codes
- scope summary
- allowed pages or module visibility payload

Access enforcement:

- public only for login
- authenticated only for follow-up context endpoints

Validation checkpoints:

- email normalized
- password required
- user must exist
- password hash must match
- user must be active
- user must have valid primary role and location context

Completion proof:

- login succeeds for valid active user
- inactive user is blocked
- frontend can render the correct navigation and landing context from the returned payloads

### UC-03 Create Custom Role

Goal:

- let Admin create a company-specific operational role without code changes

Endpoint sequence:

1. `GET /api/v1/roles`
2. `POST /api/v1/roles`
3. `PUT /api/v1/roles/{role_id}/permissions`
4. `GET /api/v1/roles/{role_id}`

Minimum request contract:

Create role:

```json
{
  "name": "Lead Recruiter",
  "code": "lead_recruiter",
  "description": "Delivery supervision role",
  "status": "active"
}
```

Assign permissions:

```json
{
  "permission_codes": [
    "requisition.read",
    "requisition.update",
    "assignment.read",
    "assignment.update",
    "candidate.read",
    "pipeline.read.summary",
    "pipeline.stage.move"
  ],
  "scope_rules": {
    "clients": "location",
    "requisitions": "location",
    "candidates": "location",
    "pipeline": "location"
  }
}
```

Minimum response contract:

- role id
- role code
- role status
- effective permission codes
- effective scope rules

Access enforcement:

- Admin only in MVP

Validation checkpoints:

- role code unique
- permission codes must exist
- scope values must be valid configured scope types
- status must be valid

Completion proof:

- new role can be created
- permissions can be assigned
- a later user assignment can use the created role immediately

### UC-05 Create Location

Goal:

- create a valid operating location for users, clients, and requisitions

Endpoint sequence:

1. `POST /api/v1/locations`
2. `GET /api/v1/locations/{location_id}`
3. `GET /api/v1/locations`

Minimum request contract:

```json
{
  "location_name": "Hyderabad",
  "location_code": "HYD",
  "address": "Optional text",
  "status": "active",
  "location_head_user_id": 10
}
```

Minimum response contract:

- location id
- location code
- location name
- active status
- optional location head reference

Access enforcement:

- Admin only in MVP

Validation checkpoints:

- location name required
- location code required
- location code unique
- head user must exist if provided

Completion proof:

- location appears in user-create and client-create forms as a selectable valid location

### UC-06 Create User

Goal:

- onboard an operational user with the correct title, role, and location

Endpoint sequence:

1. `POST /api/v1/users`
2. `GET /api/v1/users/{user_id}`
3. `GET /api/v1/users`
4. `POST /api/v1/users/{user_id}/credentials/reset` when access setup is needed

Minimum request contract:

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

Minimum response contract:

- user id
- employee code
- role id and code
- business title
- primary location
- reporting manager reference
- active status

Access enforcement:

- Admin only in MVP

Validation checkpoints:

- full name required
- email required and unique
- employee code unique if company requires it
- phone uniqueness depends on company policy
- related role, location, and manager ids must exist
- reporting manager cannot equal the same user

Completion proof:

- new user appears in list views
- new user can later authenticate after credential setup

## Group 2. Client And Requisition Operations

### UC-08 Create Client Under A Location

Goal:

- create a client that only one operating location can work on in MVP

Endpoint sequence:

1. `POST /api/v1/clients`
2. `GET /api/v1/clients/{client_id}`
3. `GET /api/v1/clients?location_id={id}`

Minimum request contract:

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

Minimum response contract:

- client id
- client code
- client name
- location id
- owner references
- status

Access enforcement:

- authenticated user with `client.create`
- scope limited to allowed location

Validation checkpoints:

- client name required
- location required
- owner references must exist
- client must not violate location ownership rule
- duplicate client warning policy should run when name or code conflicts are detected

Completion proof:

- client is visible only to allowed location users and Admin-level reporting views

### UC-09 Add Client Contact

Goal:

- attach operational contacts to a client for requisition use

Endpoint sequence:

1. `POST /api/v1/clients/{client_id}/contacts`
2. `GET /api/v1/clients/{client_id}/contacts`

Minimum request contract:

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

Minimum response contract:

- contact id
- client id
- contact name
- email
- phone
- designation
- primary or secondary flags

Access enforcement:

- `client.contact.create`
- same scope as parent client

Validation checkpoints:

- parent client must exist
- client must be in the actor’s visible scope
- email or phone format must be valid if provided

Completion proof:

- contact appears as a selectable requisition contact for that client

### UC-10 Create Requisition

Goal:

- convert a client requirement into structured recruitment work

Endpoint sequence:

1. `POST /api/v1/requisitions`
2. `GET /api/v1/requisitions/{requisition_id}`
3. `GET /api/v1/requisitions?client_id={id}`

Minimum request contract:

```json
{
  "client_id": 11,
  "client_contact_id": 25,
  "location_id": 1,
  "job_title": "Senior Java Developer",
  "openings": 3,
  "priority": "high",
  "employment_type": "full_time",
  "work_mode": "hybrid",
  "required_skills": [
    "Java",
    "Spring Boot",
    "Microservices"
  ],
  "acceptable_career_gap_text": "Up to 6 months",
  "available_time_for_updates_text": "3 PM to 6 PM",
  "target_closure_date": "2026-09-15",
  "primary_owner_user_id": 8,
  "delivery_owner_user_id": 12,
  "status": "open"
}
```

Minimum response contract:

- requisition id
- requisition code or public reference
- client reference
- location id
- ownership fields
- status
- current pipeline template or stage configuration summary

Access enforcement:

- `requisition.create`
- same-location enforcement

Validation checkpoints:

- client must exist and belong to the same location
- selected contact must belong to the same client
- owner users must exist
- owner assignments must satisfy location rules for MVP
- required skills and operational update fields must be saved
- custom pipeline template reference must be valid if used

Completion proof:

- requisition is visible in list and detail views
- requisition is assignable to delivery users

### UC-12 Assign Requisition To Delivery Team

Goal:

- create working ownership from the requisition

Endpoint sequence:

1. `POST /api/v1/requisitions/{requisition_id}/assignments`
2. `GET /api/v1/requisitions/{requisition_id}/assignments`
3. `PUT /api/v1/requisition-assignments/{assignment_id}` when reassignment is needed

Minimum request contract:

```json
{
  "assignee_user_id": 18,
  "assignment_role": "recruiter",
  "status": "active",
  "notes": "Primary working recruiter"
}
```

Minimum response contract:

- assignment id
- requisition id
- assignee id and name
- assignment status
- assignment role
- created at

Access enforcement:

- `assignment.update` or equivalent assignment-manage permission
- same-location enforcement unless later exception support is introduced

Validation checkpoints:

- requisition must be active enough to assign
- assignee must be active
- assignee must belong to the same location in MVP
- duplicate active assignment rules should be controlled

Completion proof:

- assignee sees the requisition in their work queue
- assignment list shows current active working users

## Group 3. Candidate And Duplicate Control

### UC-13 Create Candidate Profile

Goal:

- create a reusable company-level candidate record

Endpoint sequence:

1. `POST /api/v1/candidates`
2. `GET /api/v1/candidates/{candidate_id}`
3. `GET /api/v1/candidates`

Minimum request contract:

```json
{
  "full_name": "Asha Verma",
  "primary_email": "asha@example.com",
  "primary_phone": "9999999999",
  "secondary_phone": "8888888888",
  "current_location": "Hyderabad",
  "skills": [
    "Java",
    "Spring Boot"
  ],
  "total_experience_years": 5,
  "source_type": "linkedin",
  "sourced_by_user_id": 18,
  "primary_owner_user_id": 18,
  "social_profiles": [
    {
      "platform": "linkedin",
      "url": "https://linkedin.com/in/example"
    }
  ]
}
```

Minimum response contract:

- candidate id
- full name
- primary contact summary
- source summary
- owner summary
- duplicate status summary if available

Access enforcement:

- `candidate.create`

Validation checkpoints:

- minimum identity fields per company configuration
- source owner must exist if provided
- owner must exist if provided
- system should prepare duplicate-check path before final workflow usage

Completion proof:

- candidate becomes reusable across requisitions
- candidate list and detail can be opened by permitted users

### UC-15 Detect Candidate Duplicate

Goal:

- prevent duplicate candidate pollution before active submission

Endpoint sequence:

1. `POST /api/v1/candidates/duplicate-check`

Minimum request contract:

```json
{
  "candidate_id": 101,
  "primary_email": "asha@example.com",
  "primary_phone": "9999999999",
  "secondary_phone": "8888888888"
}
```

Minimum response contract:

```json
{
  "duplicate_found": true,
  "matches": [
    {
      "candidate_id": 88,
      "full_name": "Asha Verma",
      "primary_email": "asha@example.com",
      "primary_phone": "9999999999",
      "comparison_summary": {
        "email_match": true,
        "phone_match": true
      }
    }
  ],
  "next_action": "compare_before_override"
}
```

Access enforcement:

- `candidate.read` plus duplicate-check permission if separated

Validation checkpoints:

- company duplicate rules must be applied
- duplicate search must be global across company data
- same candidate id should not be returned as its own duplicate

Completion proof:

- user cannot silently continue when duplicate risk is found

### UC-16 Compare And Resolve Duplicate

Goal:

- allow only trusted users to approve an override or cleanup after comparison

Endpoint sequence:

1. `POST /api/v1/candidates/duplicate-review/{review_id}/decision`

Minimum request contract:

```json
{
  "decision": "override",
  "reason": "Candidate is distinct after manual comparison"
}
```

Minimum response contract:

- review id
- decision
- decided by
- decision time
- resulting candidate status

Access enforcement:

- Admin plus selected senior roles only

Validation checkpoints:

- duplicate review record must exist
- actor must hold override authority
- decision must be in allowed set
- reason required for override or deletion-style action

Completion proof:

- duplicate warning can be resolved only through a controlled auditable action

### UC-17 Link Candidate To Requisition

Goal:

- create a requisition-specific application from a reusable candidate profile

Endpoint sequence:

1. `POST /api/v1/candidates/{candidate_id}/applications`
2. `GET /api/v1/pipeline/board?requisition_id={id}`
3. `GET /api/v1/pipeline/applications/{application_id}`

Minimum request contract:

```json
{
  "requisition_id": 55,
  "submitted_by_user_id": 18,
  "initial_stage_code": "sourced",
  "notes": "Strong profile for first shortlist"
}
```

Minimum response contract:

- application id
- candidate id
- requisition id
- current stage
- submitted by
- owner summary
- created at

Access enforcement:

- `candidate.link_requisition`
- requisition must be in visible location scope

Validation checkpoints:

- candidate must exist
- requisition must exist
- duplicate same-candidate same-requisition link must be blocked or controlled
- initial stage must be valid for the requisition pipeline

Completion proof:

- application appears in the requisition pipeline immediately

## Group 4. Pipeline Operations

### UC-18 View Candidate Pipeline

Goal:

- show live candidate progress for a requisition or work scope

Endpoint sequence:

1. `GET /api/v1/pipeline/board`
2. `GET /api/v1/pipeline/applications/{application_id}`

Minimum request contract:

Query examples:

- `requisition_id`
- `location_id`
- `owner_user_id`
- `submitted_by_user_id`
- `stage_code`
- `aging_bucket`

Minimum response contract:

- requisition summary
- stage columns or grouped stage payload
- application cards or rows
- counts by stage
- aging information
- owner, source, and submitter references

Access enforcement:

- `pipeline.read.summary`
- server-side scope enforcement

Validation checkpoints:

- non-admin users must not pull another location’s board unless explicitly allowed
- upward visibility can allow read without edit
- recruiter should still see sourced or submitted pipeline progress where permitted

Completion proof:

- recruiter can see their sourced or submitted candidates
- senior users can see operational progress appropriate to their scope

### UC-19 Move Candidate To Next Stage

Goal:

- change the live candidate workflow stage safely

Endpoint sequence:

1. `POST /api/v1/pipeline/applications/{application_id}/move-stage`
2. `GET /api/v1/pipeline/applications/{application_id}`
3. `GET /api/v1/pipeline/applications/{application_id}/history`

Minimum request contract:

```json
{
  "to_stage_code": "submitted_to_client",
  "reason": "Profile qualified and reviewed",
  "note": "Sent to client at 4 PM"
}
```

Minimum response contract:

- application id
- previous stage
- new stage
- moved by
- moved at
- current stage counters if returned

Access enforcement:

- `pipeline.stage.move`
- read access alone is not enough

Validation checkpoints:

- application must exist
- target stage must be part of the requisition pipeline
- inconsistent transitions must be blocked
- reason required when client policy or stage policy requires it

Completion proof:

- current application row changes
- stage history is appended
- board counts update correctly

### UC-20 View Pipeline History

Goal:

- make every stage transition explainable

Endpoint sequence:

1. `GET /api/v1/pipeline/applications/{application_id}/history`

Minimum response contract:

- ordered stage timeline
- from stage
- to stage
- moved by
- moved at
- reason
- note

Access enforcement:

- `pipeline.stage.history.read`
- same scope as application read

Validation checkpoints:

- application must exist
- history must be immutable after write

Completion proof:

- every successful stage move creates a visible history event

### UC-21 Track Recruiter-Owned Progress

Goal:

- make sure recruiters can track candidates they sourced or submitted

Endpoint sequence:

1. `GET /api/v1/pipeline/board?owner_user_id={actor}`
2. `GET /api/v1/pipeline/board?submitted_by_user_id={actor}`
3. `GET /api/v1/dashboard/my-work`

Minimum response contract:

- active requisitions
- recruiter-linked applications
- stage counts
- pending follow-up items

Access enforcement:

- `pipeline.read.summary`
- server-side ownership or source-linked visibility where configured

Validation checkpoints:

- recruiter read visibility must not disappear only because another user became the later-stage owner

Completion proof:

- recruiter can still track candidate status after submission when policy allows it

## Group 5. Daily Updates And Reporting

### UC-22 Submit Daily Update

Goal:

- capture execution output and blockers for a requisition and date

Endpoint sequence:

1. `POST /api/v1/daily-updates`
2. `GET /api/v1/daily-updates/{update_id}`
3. `GET /api/v1/daily-updates?requisition_id={id}&date={yyyy-mm-dd}`

Minimum request contract:

```json
{
  "requisition_id": 55,
  "update_date": "2026-08-19",
  "sourced_count": 10,
  "screened_count": 5,
  "submitted_count": 2,
  "interview_count": 1,
  "closure_count": 0,
  "blockers": "Waiting for client feedback on earlier submissions",
  "next_action": "Follow up with client at 3 PM"
}
```

Minimum response contract:

- update id
- requisition id
- submitted by
- update date
- count summary
- blockers
- next action

Access enforcement:

- `daily_update.create`
- requisition must be in the actor’s visible scope

Validation checkpoints:

- requisition must exist
- date required
- count fields must be non-negative
- duplicate same-user same-requisition same-date behavior must follow company configuration

Completion proof:

- update becomes visible in requisition progress review and reporting views

### UC-23 Review Team Progress

Goal:

- let senior users review delivery progress without giving broad edit rights

Endpoint sequence:

1. `GET /api/v1/dashboard/pipeline-summary`
2. `GET /api/v1/dashboard/my-work`
3. `GET /api/v1/daily-updates`
4. `GET /api/v1/requisitions/{requisition_id}`

Minimum response contract:

- open requisition counts
- stage distribution
- aging indicators
- daily update coverage
- blocked requisitions
- owner-wise or team-wise grouping

Access enforcement:

- dashboard read permissions only
- no write implied

Validation checkpoints:

- reporting read should respect configured scope
- combined read should not imply cross-location edit access

Completion proof:

- senior users can identify stalled or under-serviced requisitions from dashboard data alone

### UC-24 View Location Performance

Goal:

- provide operational visibility for one location

Endpoint sequence:

1. `GET /api/v1/dashboard/location-summary`

Minimum request contract:

- `location_id`
- `from_date`
- `to_date`

Minimum response contract:

- requisition volume
- candidate pipeline counts
- submission and interview counts
- join and closure counts
- daily update compliance indicators

Access enforcement:

- reporting permission
- location scope enforced

Validation checkpoints:

- date range must be valid
- requested location must be visible to actor

Completion proof:

- users with reporting rights can monitor a single location without needing raw table access

### UC-25 View Combined Company Reporting

Goal:

- give Admin and selected report roles a full company view

Endpoint sequence:

1. `GET /api/v1/dashboard/company-summary`

Minimum request contract:

- `from_date`
- `to_date`
- optional grouped filters

Minimum response contract:

- location-wise breakdown
- total requisitions
- total active applications
- total submissions
- total interviews
- total joins or closures

Access enforcement:

- Admin plus configured report roles

Validation checkpoints:

- combined reporting permission must be explicit

Completion proof:

- company summary shows all locations in one report while edit rights remain separate

## MVP Completion Standard For API Work

A use case should not be called API-ready unless all of these are true:

1. Every endpoint in the use-case flow exists.
2. Request fields match the use-case business requirements.
3. Response fields are enough for the frontend page or workflow.
4. Permission checks are enforced server-side.
5. Scope checks are enforced server-side.
6. Validation blocks invalid business states.
7. The exception path is handled through block, review, or audit.

If one of these is missing, the use case is only partially implemented.
