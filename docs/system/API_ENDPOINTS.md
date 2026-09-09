# API Endpoints

## Important Note

This document contains legacy endpoint planning that was originally organized around the prototype role set `Admin`, `Manager`, `HR`, and `Recruiter`.

For execution planning going forward, interpret those role names as example customer mappings only.

Validated implementation note as of Tuesday, August 18, 2026:

- use `clients` instead of `client_companies`
- use `daily_updates` instead of `recruiter_daily_updates`
- use `primary_role_id` as the active user role field
- use `location_head_user_id`, `meeting_owner_user_id`, and `lead_user_id` for neutral owner references where applicable

The product API should now be designed around the universal architecture in `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md`, especially:

- permission roles
- business titles
- visibility scopes
- workflow ownership
- configurable operating templates

## Purpose

This document lists the recommended backend API endpoints for the recruitment system based on:

- the current live frontend in `frontend/`
- the universal permission and ownership model
- the updated database design in `DATABASE_DESIGN.md`

This is an endpoint list and scope guide, not a final OpenAPI contract.

## API Conventions

- Base path: `/api/v1`
- Auth: bearer token or secure session cookie
- Design principle:
  - automate high-confidence tasks in the background
  - ask users only for review, approval, or exception handling
  - keep lightweight convenience helpers in frontend JS where backend audit is not required
- Response format:
  - `success`
  - `message`
  - `data`
  - `meta` for pagination, counts, filters
- Pagination for list endpoints:
  - `page`
  - `limit`
  - `sort_by`
  - `sort_order`
- Standard filters where useful:
  - `location_id`
  - `status`
  - `role`
  - `from_date`
  - `to_date`
  - `search`

## Frontend JS Automation Scope

The current frontend already handles some low-risk convenience behavior in shared JS so we do not overload the API layer with avoidable helper calls.

These can stay in JS:

- temporary password generation for create-user and reset-user flows
- employee code suggestion
- requisition priority recommendation from date and workload hints
- structured JD preview rendering
- local draft persistence for selected forms
- daily update draft narrative generation from entered fields
- local notification generation for prototype reminders and UI feedback
- local notification counters and live activity rendering

For the current MVP frontend handoff, the frontend team should also keep these in JS:

- drawer open and close state
- dialog open and close state
- local form step transitions
- filter chip rendering
- optimistic success toasts
- local draft state before final API submit
- board drag preview before stage confirmation

These still require backend APIs as the source of truth:

- authentication and password storage
- invitation acceptance and first-login activation
- persistent notifications
- official reports and locked reporting periods
- resume parsing
- duplicate candidate detection across the full database
- approvals, audit logs, and location-wide performance metrics

## Frontend Handoff Rule

When frontend teams are working in parallel:

- JS should handle interaction state and presentation
- APIs should handle persistence and business truth
- local helpers must never replace backend validation for saved actions
- any action that affects another user, another location, or a dashboard metric must go through the backend

## Access Model Summary

The API should not assume one global customer hierarchy.

Access should be determined by a combination of:

- `permission_role`
- `business_title`
- `visibility_scope`
- `primary_owner_user_id`
- `assigned_team_id`
- `location_id`
- workflow assignment and approval context

Example permission-role templates:

- `platform_admin`
- `operations_admin`
- `business_lead`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`

Example business-title mappings:

- Director
- BDM
- Account Manager
- Lead Recruiter
- Assistant Recruiter
- Recruiter
- Talent Acquisition Manager
- Hiring Manager

Implementation rule:

- product permissions must be enforced from permission roles and scopes
- customer titles must remain configurable labels
- dashboards may still expose customer-friendly labels, but APIs should prefer stable product codes

## Working Model First

For implementation, split the API plan into:

- working model now
- extensions later

The working model should support this core operating chain:

`Director / BDM -> Account Manager -> Lead Recruiter -> Recruiter / Assistant Recruiter -> Profiles`

In product terms, that should be implemented with these permission roles:

- `platform_admin`
- `business_development`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`

Titles remain configurable labels. APIs should still enforce stable permission-role codes.

## Working Model API Set

The first release only needs the APIs required to run daily recruitment operations.

### Must-Have APIs

- authentication
- current user and permission payload
- location management
- user management
- client registry management
- client contact management
- BDM source mapping
- requisition management
- requisition assignment
- candidate management
- candidate stage movement
- daily updates
- simple dashboard summaries

### Extension APIs For Later

- invitation orchestration and setup-link flows
- advanced password recovery variants
- approvals
- notifications
- audit center
- parser and duplicate review workflows
- interview scheduling engine
- report locks and finalized reporting
- forecasting and automation
- external client portal APIs

## Working Model Endpoint Map

These are the endpoints we should actually plan to build first.

### Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Access

- `GET /api/v1/permissions/me`

### Locations

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `GET /api/v1/locations/:id`
- `PUT /api/v1/locations/:id`

### Users

- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/:id`
- `PUT /api/v1/users/:id`
- `PATCH /api/v1/users/:id/status`

### Clients

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/:id`
- `PUT /api/v1/clients/:id`

Working model note:

- BDM is the business source for the client
- client records exist so requisitions can be created and tracked
- Account Manager should not be treated as the general client owner in the MVP API

### Client Contacts

- `GET /api/v1/clients/:client_id/contacts`
- `POST /api/v1/clients/:client_id/contacts`
- `PUT /api/v1/client-contacts/:id`

### Requisitions

- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/:id`
- `PUT /api/v1/requisitions/:id`
- `PATCH /api/v1/requisitions/:id/status`

Working model note:

- BDM may be the originating business source through the client
- Account Manager is the requisition-side owner from the client coordination side
- Lead Recruiter or Delivery Lead is the delivery owner
- requisition payloads should expose `primary_owner_user_id` and `delivery_owner_user_id`

### Requisition Assignment

- `POST /api/v1/requisitions/:id/assignments`
- `GET /api/v1/requisitions/:id/assignments`
- `DELETE /api/v1/requisition-assignments/:id`

### Candidates

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/:id`
- `PUT /api/v1/candidates/:id`
- `GET /api/v1/candidates/duplicate-check`
- `GET /api/v1/candidates/pipeline`

### Candidate Requisition Workflow

- `POST /api/v1/requisitions/:id/candidates`
- `GET /api/v1/requisitions/:id/candidates`
- `PATCH /api/v1/candidate-links/:id/stage`
- `GET /api/v1/candidates/:id/stage-history`

### Daily Updates

- `GET /api/v1/daily-updates`
- `POST /api/v1/daily-updates`
- `GET /api/v1/daily-updates/:id`

### Dashboards

- `GET /api/v1/dashboards/admin`
- `GET /api/v1/dashboards/client-manager`
- `GET /api/v1/dashboards/delivery`
- `GET /api/v1/dashboards/recruiter`
- `GET /api/v1/dashboards/my-work`

## Working Model Response Expectations

The first-release APIs should prefer operational payloads over heavy analytics payloads.

Examples:

- dashboard APIs should return counts, status buckets, overdue items, and assigned-work summaries
- requisition list APIs should return assignment and pipeline counters
- requisition detail APIs should return `business_source_owner_user_id`, `primary_owner_user_id`, and `delivery_owner_user_id` where relevant
- candidate APIs should return current stage, owner, and linked requisitions
- daily update APIs should return blockers and next actions clearly

## Working Model Rules

- do not build role-specific APIs for every customer title
- do not split APIs by hierarchy label like Director, BDM, or Lead Recruiter
- keep one capability-based API and use permissions plus filters for access
- avoid advanced workflow APIs until the base requisition-to-candidate flow is stable

## Working Model Pipeline Access

- recruiters should be able to view pipeline status for candidates they sourced, submitted, or currently own
- sourcing support can view candidates they created plus candidates explicitly assigned to them
- delivery leads can view location and team pipeline within location scope
- client managers can view pipeline summaries tied to their assigned requisitions where allowed
- business development users can view client origination visibility where allowed by location rules
- admin can view pipeline across one location or all locations combined

## Pipeline Visibility Hierarchy

- recruiter: full profile-level pipeline for sourced, submitted, or owned candidates
- sourcing support: profile-level pipeline for created or assigned support records
- lead recruiter or delivery lead: full team pipeline with action control inside location scope
- account manager or client manager: requisition-wise pipeline plus shortlist, blockers, delays, and progress follow-up
- BDM or business development: account and requisition summary visibility for originated business
- director or admin: location-wise and all-location rollup visibility with optional drill-down

## Working Model Ownership Rules

- `business_source_owner_user_id` identifies who originated the business through the client relationship
- `primary_owner_user_id` identifies who owns requisition intake and follow-up from the client side
- `delivery_owner_user_id` identifies who owns recruitment execution
- APIs should return these roles separately instead of collapsing them into one generic owner field

## 1. Authentication And Session APIs

## `POST /api/v1/auth/login`

Purpose:

- authenticate user
- return token or session details
- return effective primary role, business title, scopes, and landing context

Body:

- `email`
- `password`
- `login_context` optional

## `POST /api/v1/auth/logout`

Purpose:

- invalidate current session or token

## `GET /api/v1/auth/me`

Purpose:

- return logged-in user
- return primary role
- return business title
- return location and team assignments
- return visibility scopes
- return ownership context where relevant
- return permissions summary

## `POST /api/v1/auth/refresh`

Purpose:

- refresh access token if token-based auth is used

## `POST /api/v1/auth/forgot-password`

Purpose:

- trigger password reset flow

## `POST /api/v1/auth/reset-password`

Purpose:

- reset password using token or OTP

## `POST /api/v1/auth/invitations/accept`

Purpose:

- allow invited user to accept invite
- set first password if invite was setup-link based
- activate first-login session

## `POST /api/v1/auth/password/setup-link`

Purpose:

- generate one-time password setup link
- used by admin invite flow or manual resend flow

## 2. Role And Permission APIs

## `GET /api/v1/roles`

Purpose:

- list permission-role templates

Access:

- `Admin`

Recommended future shape:

- `GET /api/v1/permission-roles`
- `GET /api/v1/business-titles`

## `GET /api/v1/permissions/me`

Purpose:

- return current user feature permissions
- useful for frontend RBAC rendering

Implementation note:

- current frontend JS can hide sidebar items and actions from the authenticated role payload
- if needed, permissions can also be bundled into `GET /api/v1/auth/me` instead of requiring a second helper endpoint

## 3. Dashboard APIs

Dashboard APIs should be capability-based, not hard-coded to one company hierarchy.

Recommended patterns:

- `GET /api/v1/dashboards/executive`
- `GET /api/v1/dashboards/business`
- `GET /api/v1/dashboards/client-accounts`
- `GET /api/v1/dashboards/delivery`
- `GET /api/v1/dashboards/recruiter`
- `GET /api/v1/dashboards/my-work`

Access should depend on permission role and visibility scope, not only a role name in the path.

Legacy role-specific dashboards can still be supported as compatibility routes during migration from the prototype.

## 4. User Management APIs

## `GET /api/v1/users`

Purpose:

- list users
- support search, role, location, status filters

Access:

- `Admin`
- `Manager` with restricted location scope if needed

## `POST /api/v1/users`

Purpose:

- create user
- support direct user creation with first-login credentials

Implementation note:

- low-priority convenience helpers such as temporary password generation can be handled in frontend JS
- backend should still store only the final submitted credential state and never rely on plain-text password persistence

Important request fields:

- `full_name`
- `email`
- `mobile_number` optional
- `employee_code` optional
- `permission_role_code`
- `business_title_id` optional
- `primary_location_id`
- `primary_team_id` optional
- `reporting_manager_user_id` optional
- `visibility_scope_code` optional
- `credential_setup_method`
  - `temporary_password`
  - `system_generated_password`
  - `setup_link`
- `temporary_password` required when method is manual temporary password
- `credential_delivery_method`
  - `email_credentials`
  - `manual_share`
  - `setup_instructions_only`
- `password_validity_hours` optional
- `force_password_change_on_first_login` optional

Access:

- `Admin`

## `POST /api/v1/users/invitations`

Purpose:

- create invited user in pending state
- assign role, location, manager, and login credential method
- send invite email or credential communication

Access:

- `Admin`

## `GET /api/v1/users/{user_id}`

Purpose:

- get user profile
- role assignments
- location assignments
- reporting manager

## `PATCH /api/v1/users/{user_id}`

Purpose:

- update user identity, status, phone, manager, etc.
- update credential delivery preference if needed

Access:

- `Admin`

## `POST /api/v1/users/{user_id}/credentials/reset`

Purpose:

- reset password for an existing user
- support manual temporary password, system-generated password, or setup link
- optionally trigger resend of credentials

Access:

- `Admin`

## `POST /api/v1/users/{user_id}/credentials/resend`

Purpose:

- resend existing invite or first-login instructions
- resend temporary password notification or setup link

Access:

- `Admin`

## `PATCH /api/v1/users/{user_id}/status`

Purpose:

- activate or deactivate user

Access:

- `Admin`

## `GET /api/v1/users/{user_id}/performance-summary`

Purpose:

- recruiter or manager performance summary
- closures
- open work
- update completion
- portal usage summary
- internal hiring call activity where applicable
- profiles escalated count

Access:

- `Admin`
- `Manager` within scope

## `GET /api/v1/users/{user_id}/reporting-line`

Purpose:

- return hierarchical reporting chain
- support `Admin -> Manager -> HR -> Recruiter` visibility and audit screens

## MVP API Contract

The first backend release should implement a focused API surface instead of the full long-term endpoint list.

### MVP Identity And Access APIs

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `GET /api/v1/permission-roles`
- `GET /api/v1/business-titles`
- `GET /api/v1/permissions/me`

### MVP Organization APIs

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`
- `GET /api/v1/teams`
- `POST /api/v1/teams`
- `PATCH /api/v1/teams/{team_id}`

### MVP User APIs

- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}/status`
- `POST /api/v1/users/{user_id}/credentials/reset`
- `GET /api/v1/users/{user_id}/reporting-line`

### MVP Client APIs

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`

### MVP Requisition APIs

- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}`
- `POST /api/v1/requisitions/{requisition_id}/assignments`
- `GET /api/v1/requisitions/{requisition_id}/candidates`

### MVP Candidate APIs

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`
- `POST /api/v1/candidates/{candidate_id}/documents`
- `POST /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/stage-transitions`

### MVP Work And Dashboard APIs

- `GET /api/v1/dashboards/my-work`
- `GET /api/v1/dashboards/delivery`
- `GET /api/v1/dashboards/business`
- `GET /api/v1/dashboards/executive`

### Deferred APIs

These can wait until after the MVP:

- approvals inbox APIs
- audit center APIs
- report locking APIs
- resume parsing APIs
- automation job APIs
- external client portal APIs

### MVP Access Enforcement Rules

The backend must enforce access using:

- permission role
- scope assignment
- location and team membership
- ownership fields
- contextual assignment such as reviewer access

The backend must not enforce access using only:

- visible frontend navigation
- business title labels
- one hard-coded hierarchy chain

## 5. User Location Role APIs

## `GET /api/v1/user-location-roles`

Purpose:

- list location-role assignments

## `POST /api/v1/user-location-roles`

Purpose:

- assign user to location and role

Access:

- `Admin`

## `PATCH /api/v1/user-location-roles/{assignment_id}`

Purpose:

- update assignment status
- change primary flag
- change date range

Access:

- `Admin`

## `DELETE /api/v1/user-location-roles/{assignment_id}`

Purpose:

- end or remove assignment

Access:

- `Admin`

## 6. Location APIs

## `GET /api/v1/locations`

Purpose:

- list locations
- show manager and target details

## `POST /api/v1/locations`

Purpose:

- create location

Access:

- `Admin`

## `GET /api/v1/locations/{location_id}`

Purpose:

- location detail
- team
- targets
- operational status

## `PATCH /api/v1/locations/{location_id}`

Purpose:

- update location details

Access:

- `Admin`

## `GET /api/v1/locations/{location_id}/team`

Purpose:

- list manager and HR team members for a location

## `GET /api/v1/locations/{location_id}/performance`

Purpose:

- location-level performance rollup
- weekly and monthly metrics

Access:

- `Admin`
- `Manager`

## 7. Client Company APIs

## `GET /api/v1/clients`

Purpose:

- list client registry records used for requisition operations
- filter by relationship type, location, status, and BDM source where needed

## `POST /api/v1/clients`

Purpose:

- create client company or end client
- store business-source context for downstream requisitions

Access:

- `Admin`
- `Manager`

## `GET /api/v1/clients/{client_id}`

Purpose:

- client detail
- BDM source details
- contact summary
- related requisitions
- meeting summary

## `PATCH /api/v1/clients/{client_id}`

Purpose:

- update client profile

Access:

- `Admin`
- `Manager`

## `GET /api/v1/clients/{client_id}/contacts`

Purpose:

- list contacts for a client

## `POST /api/v1/clients/{client_id}/contacts`

Purpose:

- add client contact

Access:

- `Admin`
- `Manager`

## `PATCH /api/v1/clients/{client_id}/contacts/{contact_id}`

Purpose:

- update client contact

## `GET /api/v1/clients/{client_id}/meetings`

Purpose:

- list client meetings

## `GET /api/v1/clients/{client_id}/requisitions`

Purpose:

- list client-linked requisitions

## `GET /api/v1/clients/{client_id}/end-clients`

Purpose:

- list optional end clients mapped under a direct client

## `POST /api/v1/clients/{client_id}/end-clients`

Purpose:

- create end client under a direct client when required

Access:

- `Admin`
- `Manager`

## 8. Requisition APIs

## `GET /api/v1/requisitions`

Purpose:

- list requisitions
- filter by location, hiring type, status, priority, due date, primary owner, and delivery owner

## `POST /api/v1/requisitions`

Purpose:

- create requisition from structured intake
- support one direct client with zero, one, or many optional end-client mappings
- capture the handoff between Account Manager and Lead Recruiter

Access:

- `Admin`
- `Client Manager`
- `Business Development` only if business rules allow assisted intake creation

Important request fields:

- `location_id`
- `hiring_type`
- `client_id` optional
- `end_client_ids` optional array
- `department_name` optional
- `title`
- `primary_owner_user_id`
- `delivery_owner_user_id`
- `priority` optional
- `target_close_date`
- `open_positions`
- `client_round_required`
- `structured_jd_json`

## `GET /api/v1/requisitions/{requisition_id}`

Purpose:

- requisition detail
- requisition ownership split by business source, account manager, and delivery owner
- structured JD
- skills
- screening rules
- direct client and optional end-client mappings

## `PATCH /api/v1/requisitions/{requisition_id}`

Purpose:

- update requisition
- update requisition ownership, delivery ownership, and optional end-client mappings

## `PATCH /api/v1/requisitions/{requisition_id}/status`

Purpose:

- update requisition lifecycle state

## `POST /api/v1/requisitions/{requisition_id}/assign-owner`

Purpose:

- assign or reassign HR owner

Access:

- `Admin`
- `Manager`

## `GET /api/v1/requisitions/priorities/queue`

Purpose:

- return the role-prioritized requisition work queue
- sort using close date, SLA pressure, aging, and workload balancing

Access:

- `Admin`
- `Manager`
- `HR`
- `Recruiter`

## `GET /api/v1/requisitions/{requisition_id}/priority`

Purpose:

- get computed priority details
- show why role is high priority

## `GET /api/v1/workflow-actions/queue`

Purpose:

- return the shared role dashboard, daily review, and work queue action list
- include visible action labels, route targets, overlay keys, priority, status, age, and entity context
- support location-scoped and role-aware filtering

Access:

- `workflow_action.read`

## `POST /api/v1/workflow-actions/{action_item_id}/run`

Purpose:

- record a visible UI action such as View, Review, Schedule, or Do Now
- move open Do Now items to in-progress
- return the next route or overlay target for the frontend

Access:

- `workflow_action.run`

## `POST /api/v1/workflow-actions/{action_item_id}/resolve`

Purpose:

- resolve a queue item from dashboard/list actions
- write workflow event and audit history

Access:

- `workflow_action.resolve`

## `POST /api/v1/workflow-actions/{action_item_id}/nudge`

Purpose:

- send a reminder notification for an action item
- write workflow event and audit history

Access:

- `workflow_action.nudge`

## `POST /api/v1/workflow-actions/overlay-submissions`

Purpose:

- persist routed overlay, drawer, and dialog submissions
- retain parent route, overlay key, entity context, submitted payload, and audit trail

Access:

- `workflow_overlay.submit`

## `GET /api/v1/requisitions/{requisition_id}/skills`

Purpose:

- list structured skill requirements

## `POST /api/v1/requisitions/{requisition_id}/skills`

Purpose:

- add skill requirement rows

## `PATCH /api/v1/requisitions/{requisition_id}/skills/{skill_id}`

Purpose:

- update skill requirement

## `DELETE /api/v1/requisitions/{requisition_id}/skills/{skill_id}`

Purpose:

- remove skill requirement

## `GET /api/v1/requisitions/{requisition_id}/screening-rules`

Purpose:

- get JD-based screening rules

## `PUT /api/v1/requisitions/{requisition_id}/screening-rules`

Purpose:

- create or replace screening rules

## `GET /api/v1/requisitions/{requisition_id}/required-documents`

Purpose:

- list required document rules

## `PUT /api/v1/requisitions/{requisition_id}/required-documents`

Purpose:

- upsert document requirement list

## `GET /api/v1/requisitions/{requisition_id}/end-clients`

Purpose:

- list end clients attached to a requisition
- support downstream client visibility for external hiring

## `PUT /api/v1/requisitions/{requisition_id}/end-clients`

Purpose:

- replace requisition end-client mappings
- mark one mapping as primary when needed

Access:

- `Admin`
- `Manager`
- `HR`

## `GET /api/v1/requisitions/{requisition_id}/candidates`

Purpose:

- list candidates attached to a requisition

## 9. Candidate APIs

## `GET /api/v1/candidates`

Purpose:

- list candidates
- filter by source, status, portal, location-linked work
- filter by expiry status and duplicate acknowledgement status

## `POST /api/v1/candidates`

Purpose:

- create candidate profile
- optionally create candidate from parsed resume output
- support save-draft or final-save behavior from HR candidate add flow

Important request fields:

- `full_name`
- `email` optional
- `phone` optional
- `source_type`
- `source_platform` optional
- `resume_document_id` optional
- `primary_requisition_id` optional
- `primary_owner_user_id` optional
- `initial_pipeline_stage` optional
- `save_mode`
  - `draft`
  - `final`

## `GET /api/v1/candidates/{candidate_id}`

Purpose:

- candidate detail
- core profile
- experience
- compensation
- documents summary
- profile life and expiry status

## `PATCH /api/v1/candidates/{candidate_id}`

Purpose:

- update candidate profile

## `POST /api/v1/candidates/resume-upload`

Purpose:

- upload resume file
- create draft candidate parsing job
- extract candidate fields automatically
- trigger background duplicate analysis automatically

Response should include:

- `candidate_id` if a draft candidate record is created
- `parse_job_id`
- `resume_parsing_status`
- duplicate match summary if a likely existing candidate is found

## `GET /api/v1/candidates/resume-parse-jobs/{parse_job_id}`

Purpose:

- check parsing job status
- return extracted candidate fields
- return confidence by field
- return duplicate warnings

## `POST /api/v1/candidates/{candidate_id}/resume-parse-review`

Purpose:

- confirm or correct parsed resume fields
- save reviewed values into draft candidate fields before duplicate check and final save
- allow recruiter to accept system-suggested values with minimal changes

Important behavior:

- parser output should not be treated as final until HR reviews or confirms it
- low-confidence fields should remain editable

## `GET /api/v1/candidates/{candidate_id}/duplicate-check`

Purpose:

- fetch duplicate analysis after parsing or manual candidate entry
- return likely, possible, and archived matches
- return match reasons like email, phone, employer overlap, or name similarity

## `POST /api/v1/candidates/{candidate_id}/duplicate-check/decision`

Purpose:

- store HR-side decision after duplicate review
- continue as new candidate, merge into existing, or stop creation

Important request fields:

- `decision`
  - `continue_as_new`
  - `merge_into_existing`
  - `cancel_creation`
- `existing_candidate_id` required when merging
- `decision_notes` optional

## `POST /api/v1/candidates/{candidate_id}/finalize-profile`

Purpose:

- finalize candidate after parse review and duplicate review
- assign source, owner, requisition, and initial pipeline stage
- create the active candidate profile used by downstream screening and pipeline flows
- start profile life timer for 1 month unless refreshed

Important request fields:

- `source_platform`
- `primary_requisition_id` optional
- `primary_owner_user_id`
- `initial_pipeline_stage`
- `profile_status`
- `recruiter_notes` optional

## `POST /api/v1/candidates/{candidate_id}/refresh-profile-life`

Purpose:

- extend candidate profile life when the profile is reactivated or reused within business rules

Access:

- `HR`
- `Manager`

## `POST /api/v1/candidates/{candidate_id}/save-draft`

Purpose:

- save parsed or manually reviewed candidate profile without finalizing
- allow HR to return later before pushing candidate into the active queue

## `POST /api/v1/candidates/{candidate_id}/reparse-resume`

Purpose:

- rerun parser after replacing resume or improving extraction rules

## `GET /api/v1/candidates/{candidate_id}/skills`

Purpose:

- list candidate skills

## `PUT /api/v1/candidates/{candidate_id}/skills`

Purpose:

- replace or upsert candidate skills

## `GET /api/v1/candidates/{candidate_id}/documents`

Purpose:

- list uploaded documents

## `POST /api/v1/candidates/{candidate_id}/documents`

Purpose:

- upload candidate document metadata

Important note:

- when `document_type = resume`, system should support automatic parsing flow

## `PATCH /api/v1/candidates/{candidate_id}/documents/{document_id}`

Purpose:

- update verification status or metadata

## `DELETE /api/v1/candidates/{candidate_id}/documents/{document_id}`

Purpose:

- remove document link or record

## 10. Candidate Application APIs

## `GET /api/v1/candidate-applications`

Purpose:

- list candidate applications
- support pipeline filters

## `POST /api/v1/candidate-applications`

Purpose:

- attach candidate to requisition

## `GET /api/v1/candidate-applications/{application_id}`

Purpose:

- application detail
- stage
- screening
- rejection state
- client feedback state
- duplicate acknowledgement from client if any

## `PATCH /api/v1/candidate-applications/{application_id}`

Purpose:

- update generic application fields

## `PATCH /api/v1/candidate-applications/{application_id}/stage`

Purpose:

- move candidate to next stage

Important rule:

- profile escalation should depend on valid client feedback or prior HR approval according to workflow

## `PATCH /api/v1/candidate-applications/{application_id}/screening-status`

Purpose:

- update screening pass, fail, pending

## `POST /api/v1/candidate-applications/{application_id}/reject`

Purpose:

- reject candidate
- requires `rejection_side`, `rejection_reason`, `rejection_stage`

Important rule:

- use `internal` rejection before client round
- use `client` rejection only after client-side round or client review

## `POST /api/v1/candidate-applications/{application_id}/restore`

Purpose:

- reopen or restore mistakenly rejected application

Access:

- `Admin`
- `Manager`

## `POST /api/v1/candidate-applications/{application_id}/client-feedback`

Purpose:

- capture structured client feedback received and processed by HR or Manager
- update progression, hold, rejection, duplicate acknowledgement, or escalation readiness

Important request fields:

- `feedback_status`
  - `positive`
  - `negative`
  - `hold`
  - `needs-more-profiles`
  - `duplicate-acknowledged`
- `feedback_notes` optional
- `received_from_client_contact_id` optional
- `processed_by_user_id`

Access:

- `HR`
- `Manager`

## `GET /api/v1/candidate-applications/{application_id}/client-feedback`

Purpose:

- list structured client feedback events for one application
- show progression, hold, rejection, and duplicate acknowledgement history

## `POST /api/v1/candidate-applications/{application_id}/escalate`

Purpose:

- escalate candidate profile to the next client-facing step only when workflow conditions are satisfied

Important rule:

- external hiring escalation should depend on accepted client feedback state
- internal hiring escalation can proceed based on HR or Manager approval without client dependency

## `POST /api/v1/candidate-applications/{application_id}/acknowledge-client-duplicate`

Purpose:

- record that a client marked the submitted profile as duplicate
- preserve duplicate reason and reporting attribution without losing the application record

Access:

- `HR`
- `Manager`

## `GET /api/v1/candidate-applications/{application_id}/timeline`

Purpose:

- stage history and activity log

## 11. Screening APIs

## `GET /api/v1/screening/queue`

Purpose:

- list candidate applications awaiting screening

Access:

- `HR`
- `Manager`

## `GET /api/v1/candidate-applications/{application_id}/screening-checks`

Purpose:

- list structured screening checks

## `POST /api/v1/candidate-applications/{application_id}/screening-checks`

Purpose:

- create screening check

## `PATCH /api/v1/candidate-applications/{application_id}/screening-checks/{check_id}`

Purpose:

- update screening result, notes, actual value

## `POST /api/v1/candidate-applications/{application_id}/complete-screening`

Purpose:

- finalize screening summary
- update application screening status

## 12. Pipeline APIs

## `GET /api/v1/pipeline/board`

Purpose:

- return pipeline board grouped by stage
- filter by location, owner, requisition, hiring type

## `GET /api/v1/pipeline/summary`

Purpose:

- return KPIs for sourced, screened, client rounds, offers

## `GET /api/v1/pipeline/stalled`

Purpose:

- list stalled applications and aging reasons

## 13. Interview APIs

## `GET /api/v1/interviews`

Purpose:

- list interview rounds
- filter by date, location, round type, status

## `POST /api/v1/interviews`

Purpose:

- schedule interview round

## `GET /api/v1/interviews/{interview_id}`

Purpose:

- interview round detail

## `PATCH /api/v1/interviews/{interview_id}`

Purpose:

- update schedule or interviewer details

## `PATCH /api/v1/interviews/{interview_id}/status`

Purpose:

- mark completed, rescheduled, cancelled, no-show

## `POST /api/v1/interviews/{interview_id}/feedback`

Purpose:

- store interview decision and notes handled by HR or Manager

Access:

- `HR`
- `Manager`

## 14. Meeting And Follow-up APIs

## `GET /api/v1/meetings`

Purpose:

- list meetings
- filter by client, location, date, outcome, attendance

## `POST /api/v1/meetings`

Purpose:

- schedule meeting

## `GET /api/v1/meetings/{meeting_id}`

Purpose:

- meeting detail
- agenda
- minutes
- next steps

## `PATCH /api/v1/meetings/{meeting_id}`

Purpose:

- update meeting metadata

## `PATCH /api/v1/meetings/{meeting_id}/attendance`

Purpose:

- mark attended, partially attended, no-show

## `PATCH /api/v1/meetings/{meeting_id}/outcome`

Purpose:

- record accepted, pending, rejected, reschedule-needed

## `POST /api/v1/meetings/{meeting_id}/attendees`

Purpose:

- add internal or client attendee rows

## `PATCH /api/v1/meetings/{meeting_id}/follow-up`

Purpose:

- assign follow-up owner and due date

## 15. Portal Account APIs

## `GET /api/v1/portal-accounts`

Purpose:

- list sourcing accounts
- filter by platform, location, status, full access, shared access

## `POST /api/v1/portal-accounts`

Purpose:

- create portal account

Access:

- `Admin`
- `Manager`

## `GET /api/v1/portal-accounts/{portal_account_id}`

Purpose:

- portal account detail

## `PATCH /api/v1/portal-accounts/{portal_account_id}`

Purpose:

- update account details

## `GET /api/v1/portal-accounts/{portal_account_id}/slots`

Purpose:

- list scheduled usage slots

## `POST /api/v1/portal-accounts/{portal_account_id}/slots`

Purpose:

- create usage slot

## `PATCH /api/v1/portal-accounts/{portal_account_id}/slots/{slot_id}`

Purpose:

- update slot schedule or approval state

## `DELETE /api/v1/portal-accounts/{portal_account_id}/slots/{slot_id}`

Purpose:

- cancel slot

## `GET /api/v1/portal-usage/summary`

Purpose:

- usage summary for reports and utilization pages

## `GET /api/v1/portal-accounts/availability`

Purpose:

- return shared portal availability by platform, location, and date
- help optional slot scheduling without blocking users who have full access

## 16. Daily Update APIs

## `GET /api/v1/daily-updates`

Purpose:

- list recruiter daily updates

## `POST /api/v1/daily-updates`

Purpose:

- submit daily update input
- support recruiter, HR, or manager update submission depending on role
- support manual submission or reviewed system-generated draft

Access:

- `Recruiter`
- `HR`
- `Manager` if manager-level note entry is allowed

## `GET /api/v1/daily-updates/{update_id}`

Purpose:

- get submitted daily update detail

## `PATCH /api/v1/daily-updates/{update_id}`

Purpose:

- edit daily update before reporting lock

## `GET /api/v1/daily-updates/mine/today`

Purpose:

- return current user draft or submitted update for today

## 16A. Automation And Background Processing APIs

## `GET /api/v1/automation/jobs`

Purpose:

- list background jobs triggered by parsing, reporting, notifications, and queue rebuilds

Access:

- `Admin`
- `Manager` within scope where relevant

## `GET /api/v1/automation/jobs/{job_id}`

Purpose:

- return automation job status, progress, summary, warnings, and failures

## `POST /api/v1/automation/report-jobs`

Purpose:

- trigger weekly, monthly, or daily summary generation manually when needed

Implementation note:

- lightweight visual report shaping can happen in frontend JS
- this endpoint is for official, auditable report generation from SQL data

Important request fields:

- `report_type`
  - `weekly`
  - `monthly`
  - `daily-summary`
- `scope_type`
  - `admin`
  - `manager`
  - `hr`
  - `location`
- `scope_id` optional
- `from_date`
- `to_date`
- `auto_publish` optional

## `POST /api/v1/automation/priority-queues/rebuild`

Purpose:

- rebuild requisition and recruiter priority queues from close dates, SLA, stage aging, and workload data

Access:

- `Admin`
- `Manager`

## 17. Report APIs

## `GET /api/v1/reports`

Purpose:

- list weekly and monthly reports
- include manually compiled and auto-generated reports
- include reporting lock status for the requested period when applicable

## `GET /api/v1/reports/{report_id}/rows`

Purpose:

- return structured tabular rows for a generated report
- support weekly and monthly drill-down screens and exports

## `POST /api/v1/reports/generate`

Purpose:

- generate report from daily update and operational data
- support backend-driven weekly and monthly generation without requiring users to compile everything manually

Important request fields:

- `report_scope`
- `report_type`
- `location_id` optional
- `period_start`
- `period_end`
- `generated_from_daily_inputs`
- `force_regenerate` optional

Access:

- `Admin`
- `Manager`
- `HR` for own scope if required

## `GET /api/v1/reports/{report_id}`

Purpose:

- report detail with summary data
- generation source details
- linked lock status for the report period

## `PATCH /api/v1/reports/{report_id}/review`

Purpose:

- mark report reviewed
- attach review note

Access:

- `Admin`
- `Manager`

## `POST /api/v1/reports/{report_id}/publish`

Purpose:

- publish approved report snapshot for final visibility
- keep generated report output stable after review when required

## `GET /api/v1/reports/export`

Purpose:

- export reports as CSV, XLSX, or PDF

## `GET /api/v1/report-locks`

Purpose:

- list weekly and monthly reporting lock records
- filter by scope, location, period, and lock status

Access:

- `Admin`
- `Manager` for location-scoped visibility if needed

## `POST /api/v1/report-locks`

Purpose:

- create or apply a reporting period lock
- prevent edits or regeneration for finalized report windows

Access:

- `Admin`

## `PATCH /api/v1/report-locks/{lock_id}`

Purpose:

- reopen or update a locked reporting period
- capture reopen reason or lock note updates

Access:

- `Admin`

## `GET /api/v1/reports/templates/weekly`

Purpose:

- return weekly tabular report column definition and display rules

## `GET /api/v1/reports/templates/monthly`

Purpose:

- return monthly tabular report column definition and display rules

## `GET /api/v1/reports/summary/admin`

Purpose:

- admin reporting summary API

## `GET /api/v1/reports/summary/manager`

Purpose:

- manager reporting summary API

## `GET /api/v1/reports/summary/hr`

Purpose:

- HR reporting summary API

## `GET /api/v1/reports/summary/recruiter`

Purpose:

- recruiter reporting summary API
- highlight sourcing output, internal call count where relevant, profiles escalated, blockers, and portal usage

## 18. Approval APIs

## `GET /api/v1/approvals`

Purpose:

- list approval requests
- filter by status, priority, request type, location

## `POST /api/v1/approvals`

Purpose:

- create approval request

Examples:

- portal slot extension
- rejection override
- target update
- requisition exception

## `GET /api/v1/approvals/{approval_id}`

Purpose:

- approval detail

## `PATCH /api/v1/approvals/{approval_id}`

Purpose:

- update assignment or notes

## `POST /api/v1/approvals/{approval_id}/approve`

Purpose:

- approve request

## `POST /api/v1/approvals/{approval_id}/reject`

Purpose:

- reject request

## 19. Notification APIs

## `GET /api/v1/notifications`

Purpose:

- list notifications for current user
- return delivery status and optional action URL

Implementation note:

- frontend JS currently supports prototype-only local notifications
- this endpoint will replace local-only storage for production behavior

## `PATCH /api/v1/notifications/{notification_id}/read`

Purpose:

- mark one notification as read

## `PATCH /api/v1/notifications/read-all`

## `GET /api/v1/notification-preferences/me`

Purpose:

- return current user notification settings

## `PATCH /api/v1/notification-preferences/me`

Purpose:

- update current user notification settings

Purpose:

- mark all current user notifications as read

## `POST /api/v1/notifications/{notification_id}/deliver`

Purpose:

- mark notification as delivered for in-app or secondary-channel processing
- useful for backend notification worker acknowledgements

Access:

- internal service or backend job only

## 20. Audit And Activity APIs

## `GET /api/v1/audit-logs`

Purpose:

- list audit logs for sensitive actions

Access:

- `Admin`

## `GET /api/v1/activity/recent`

Purpose:

- recent cross-module activity feed for dashboards if needed

## 21. Search And Lookup APIs

## `GET /api/v1/lookups/locations`

Purpose:

- dropdown location values

## `GET /api/v1/lookups/users`

Purpose:

- dropdown user values

## `GET /api/v1/lookups/clients`

Purpose:

- dropdown client values

## `GET /api/v1/lookups/requisitions`

Purpose:

- dropdown requisition values

## `GET /api/v1/lookups/skills`

Purpose:

- reusable skills list

## `GET /api/v1/search/global`

Purpose:

- quick search across users, clients, requisitions, candidates

## `GET /api/v1/lookups/report-columns`

Purpose:

- return reporting column metadata for frontend table builders and exports

## Frontend Page To API Mapping

Page names below are the live routed pages under `frontend/pages/` (see
`frontend/route-manifest.json`).

## Login

- Login (`login.html`)
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`

## Admin pages

- Role Dashboard (`role-dashboard.html`)
  - `GET /api/v1/dashboards/admin`
- Location Management (`location-management.html`)
  - `GET /api/v1/locations`
  - `POST /api/v1/locations`
  - `PATCH /api/v1/locations/{location_id}`
- User Management (`user-management.html`)
  - `GET /api/v1/users`
  - `POST /api/v1/users`
  - `POST /api/v1/users/invitations`
  - `PATCH /api/v1/users/{user_id}`
  - `POST /api/v1/users/{user_id}/credentials/reset`
  - `POST /api/v1/users/{user_id}/credentials/resend`
  - `GET /api/v1/user-location-roles`
- Client Directory (`client-directory.html`)
  - `GET /api/v1/clients`
  - `POST /api/v1/clients`
  - `GET /api/v1/clients/{client_id}/contacts`
- Reports (`reports.html`)
  - `GET /api/v1/reports`
  - `GET /api/v1/reports/summary/admin`
  - `GET /api/v1/reports/export`
  - `GET /api/v1/report-locks`
  - `POST /api/v1/report-locks`
  - `PATCH /api/v1/report-locks/{lock_id}`
  - `POST /api/v1/automation/report-jobs`
  - `POST /api/v1/reports/{report_id}/publish`
- Approvals Inbox (`approvals-inbox.html`)
  - `GET /api/v1/approvals`
  - `POST /api/v1/approvals/{approval_id}/approve`
  - `POST /api/v1/approvals/{approval_id}/reject`
- Notifications Center (`notifications-center.html`)
  - `GET /api/v1/notifications`

## Manager pages

- Role Dashboard (`role-dashboard.html`)
  - `GET /api/v1/dashboards/manager`
- Client Directory (`client-directory.html`), Client Detail (`client-detail.html`)
  - `GET /api/v1/clients`
  - `GET /api/v1/clients/{client_id}`
- Meetings (`meetings.html`)
  - `GET /api/v1/meetings`
  - `POST /api/v1/meetings`
  - `PATCH /api/v1/meetings/{meeting_id}/outcome`
- Requisition List (`requisition-list.html`), Requisition Detail (`requisition-detail.html`)
  - `GET /api/v1/requisitions`
  - `GET /api/v1/requisitions/{requisition_id}`
- Reports (`reports.html`)
  - `GET /api/v1/reports`
  - `GET /api/v1/reports/summary/manager`
  - `GET /api/v1/report-locks`
  - `POST /api/v1/automation/report-jobs`
- Notifications Center (`notifications-center.html`)
  - `GET /api/v1/notifications`

## HR pages

- Role Dashboard (`role-dashboard.html`)
  - `GET /api/v1/dashboards/hr`
- Requisition Intake (`requisition-intake.html`)
  - `POST /api/v1/requisitions`
  - `PUT /api/v1/requisitions/{requisition_id}/end-clients`
  - `PUT /api/v1/requisitions/{requisition_id}/screening-rules`
  - `PUT /api/v1/requisitions/{requisition_id}/required-documents`
- Candidate Profiles (`candidate-profiles.html`)
  - `GET /api/v1/candidates`
  - `POST /api/v1/candidates`
  - `POST /api/v1/candidates/resume-upload`
  - `GET /api/v1/candidates/resume-parse-jobs/{parse_job_id}`
  - `POST /api/v1/candidates/{candidate_id}/resume-parse-review`
  - `GET /api/v1/candidates/{candidate_id}/duplicate-check`
  - `POST /api/v1/candidates/{candidate_id}/duplicate-check/decision`
  - `POST /api/v1/candidates/{candidate_id}/save-draft`
  - `POST /api/v1/candidates/{candidate_id}/finalize-profile`
  - `POST /api/v1/candidates/{candidate_id}/refresh-profile-life`
  - `GET /api/v1/candidate-applications`
  - `POST /api/v1/candidate-applications/{application_id}/client-feedback`
  - `POST /api/v1/candidate-applications/{application_id}/escalate`
- Candidate Screening (`candidate-screening.html`)
  - `GET /api/v1/screening/queue`
  - `POST /api/v1/candidate-applications/{application_id}/screening-checks`
  - `POST /api/v1/candidate-applications/{application_id}/complete-screening`
  - `POST /api/v1/candidate-applications/{application_id}/reject`
- Pipeline Board (`pipeline-board.html`)
  - `GET /api/v1/pipeline/board`
  - `GET /api/v1/pipeline/summary`
- Interview Scheduler (`interview-scheduler.html`)
  - `GET /api/v1/interviews`
  - `POST /api/v1/interviews`
  - `POST /api/v1/interviews/{interview_id}/feedback`
- Delivery Reports (`reports.html`)
  - `GET /api/v1/reports`
  - `GET /api/v1/reports/summary/hr`
  - `GET /api/v1/daily-updates/mine/today`
  - `POST /api/v1/daily-updates`
- Notifications Center (`notifications-center.html`)
  - `GET /api/v1/notifications`
  - `PATCH /api/v1/notifications/read-all`

## Recruiter pages

- Role Dashboard (`role-dashboard.html`)
  - `GET /api/v1/dashboards/hr`
- Candidate Profiles (`candidate-profiles.html`)
  - `GET /api/v1/candidates`
  - `POST /api/v1/candidates/resume-upload`
  - `GET /api/v1/candidates/resume-parse-jobs/{parse_job_id}`
  - `POST /api/v1/candidates/{candidate_id}/save-draft`
- Recruiter Productivity Reports (`user-performance-reports.html`)
  - `GET /api/v1/reports/summary/recruiter`
  - `GET /api/v1/daily-updates/mine/today`
  - `POST /api/v1/daily-updates`
  - `GET /api/v1/reports`

## Suggested Build Priority

## Phase 1

- auth
- roles and permissions
- dashboards
- locations
- users

## Phase 2

- clients
- requisitions
- candidates
- candidate applications
- screening

## Phase 3

- interviews
- meetings
- portal accounts
- daily updates
- reports

## Phase 4

- approvals
- notifications
- audit logs
- global search

## Notes

- Keep list endpoints filterable because the frontend is dashboard-heavy
- Keep summary endpoints separate from raw list endpoints for performance
- Enforce role and location scope in backend, not only in frontend
- Validate business rules at API level:
  - client rejection should not be accepted before client round exists
  - optional end-client fields must stay nullable
  - portal slot scheduling must stay optional when account has full access
  - parsed resume fields should be reviewable before becoming trusted candidate data
