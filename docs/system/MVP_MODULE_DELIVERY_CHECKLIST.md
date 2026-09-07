# MVP Module Delivery Checklist

## Purpose

This document turns the MVP core use cases into a module-by-module delivery checklist.

It should be used by:

- product for delivery tracking
- frontend for page coverage
- backend for endpoint completion
- database work for schema validation
- QA for test-case coverage

This is not a strategy document.

This is a completion checklist.

A module should not be called done unless its required pages, APIs, DB structures, permission rules, and test coverage are all complete enough for the MVP flow.

## How To Use This Checklist

For each module:

1. Confirm page coverage
2. Confirm API coverage
3. Confirm DB support
4. Confirm permission and scope behavior
5. Confirm test coverage
6. Confirm module-level done criteria

Use this document together with:

- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/USE_CASE_PRIORITY_EXECUTION_LIST.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`
- `docs/system/BUILD_PACK_FRONTEND_PAGE_MODULE_PLAN.md`

## Global MVP Completion Rule

The system is not MVP-ready unless all P0 modules support the full working flow:

1. Admin creates location.
2. Admin creates role and permissions.
3. Admin creates user.
4. User logs in.
5. User creates client and contact.
6. User creates requisition.
7. User assigns delivery work.
8. Recruiter creates candidate.
9. Duplicate check happens.
10. Candidate enters pipeline.
11. Pipeline progresses through valid stages.
12. Daily updates are posted.
13. Dashboard users can review location and company summaries.

## Module 1. Authentication And Session Control

### Required Pages And UI Flows

- `Login`
- `First Login Password Setup` if enabled in MVP flow
- `Access Denied`
- current access summary area inside profile or dashboard

### Required APIs

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`
- user credential reset endpoint for admin recovery flow

### Required DB Support

- user identity and authentication fields
- password hash storage
- active or inactive status
- role and location linkage
- session or token revocation support if used

### Required Permission And Scope Behavior

- inactive users cannot log in
- authenticated context must load user, role, and location
- protected modules must rely on authenticated context
- only authorized users can reset another user’s credentials

### Required Tests

- valid login succeeds
- invalid login fails with predictable error
- inactive user cannot log in
- auth context returns expected user and permission payload
- logout or revoke behavior blocks reuse of invalid token if revoke model is used

### Done When

- frontend can log in safely
- protected pages can load user context
- permission-aware navigation can be rendered from actual API data

## Module 2. Roles, Permissions, And Access Configuration

### Required Pages And UI Flows

- `Role Management`
- role create flow
- role edit flow
- permission matrix or permission assignment flow
- user-role assignment flow inside user management

### Required APIs

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- role permission assignment endpoint
- permission summary endpoint for current user

### Required DB Support

- role master table
- role-to-module mapping
- role-to-page mapping
- role-to-action mapping
- optional scope configuration storage

### Required Permission And Scope Behavior

- only Admin or equivalent governance permission can manage roles
- users only see modules and actions allowed by effective access
- permission updates must affect runtime access correctly

### Required Tests

- create role succeeds with valid fields
- duplicate or invalid role code fails
- permission assignment saves valid combinations
- unauthorized role update is rejected
- permission summary reflects assigned access

### Done When

- Admin can configure working roles without code change
- frontend navigation and API enforcement use the same access model

## Module 3. Location And User Administration

### Required Pages And UI Flows

- `Location Management`
- `User Management`
- user create flow
- user edit flow
- user deactivate review flow
- user list filters

### Required APIs

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`
- `POST /api/v1/users/{user_id}/deactivate`

### Required DB Support

- location master
- user master
- employee ID storage
- contact fields
- reporting manager reference
- user-to-location mapping
- user-to-role mapping
- active-work relationship references for review workflows

### Required Permission And Scope Behavior

- users cannot be operationally active under invalid setup state
- manager self-mapping must be blocked
- duplicate email, phone, or employee ID must follow company rule
- deactivation with active work must require review handling

### Required Tests

- create location succeeds
- duplicate location code fails
- create user succeeds with valid role and location
- duplicate identity fields are handled correctly
- invalid manager mapping fails
- deactivation with active work requires review and transfer behavior

### Done When

- Admin can create locations and users safely
- the system can prevent orphaned active work during user exit

## Module 4. Client Directory

### Required Pages And UI Flows

- `Client Directory`
- `Client Detail`
- client create flow
- client edit flow
- contact create dialog
- contact edit dialog

### Required APIs

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`
- `PATCH /api/v1/client-contacts/{contact_id}`

### Required DB Support

- client master
- client code
- client status
- location ownership
- business source owner reference
- client contact table
- primary and secondary contact capability

### Required Permission And Scope Behavior

- one client belongs to one location for operations
- cross-location operational access is blocked by default
- contact must always belong to selected client
- client access must follow location scope and assigned permissions

### Required Tests

- create client succeeds with valid location
- cross-location client access is blocked
- create contact under client succeeds
- contact-to-wrong-client mapping fails
- client detail returns linked contact and requisition context correctly

### Done When

- users can manage clients and contacts without location ambiguity
- requisition creation can rely on clean client ownership

## Module 5. Requisition Management

### Required Pages And UI Flows

- `Requisition List`
- `Requisition Intake`
- `Requisition Detail`
- status update flow
- owner assignment flow
- requisition filters

### Required APIs

- requisition list endpoint
- requisition create endpoint
- requisition detail endpoint
- requisition update endpoint
- requisition status update endpoint
- requisition owner assignment or reassignment endpoint
- requisition history endpoint if used by detail screen

### Required DB Support

- requisition master
- client reference
- contact reference
- location ownership
- business-side ownership reference
- delivery ownership reference
- priority and openings fields
- skills and acceptable career gap fields
- target date
- client update availability time
- requisition status history

### Required Permission And Scope Behavior

- requisition must inherit valid location ownership from client
- invalid owner location mapping must be blocked
- only permitted users can create or change requisitions
- upward visibility must not imply edit access

### Required Tests

- create requisition succeeds with valid client
- create requisition against inactive or invalid client fails according to rule
- invalid contact mapping fails
- invalid owner mapping fails
- requisition status update works with history
- requisition detail returns ownership and linked context correctly

### Done When

- client demand can be captured and assigned safely
- downstream work allocation and pipeline flows can depend on requisition records

## Module 6. Work Allocation And Assignment

### Required Pages And UI Flows

- assignment section inside `Requisition Detail`
- `Delivery Work Queue`
- assign recruiter flow
- contributor add flow if included in MVP
- reassignment dialog
- assignment history view

### Required APIs

- assignment create endpoint
- assignment list endpoint
- assignment update or remove endpoint
- reassignment-review endpoint
- workload listing endpoint if `Delivery Work Queue` depends on separate aggregation

### Required DB Support

- requisition assignment table
- assigned owner references
- contributor support if included
- active flags
- reassignment history

### Required Permission And Scope Behavior

- assignment must stay within allowed location scope
- only permitted senior users can reassign live work
- reassignment with active candidate work must preserve history

### Required Tests

- assign recruiter succeeds
- invalid cross-location assignment fails
- active-work reassignment requires review confirmation
- assignment history is preserved after reassignment

### Done When

- live requisitions can be distributed and transferred safely
- recruiters can receive clear work ownership from the system

## Module 7. Candidate Management

### Required Pages And UI Flows

- `Candidate Profiles`
- candidate create flow
- candidate edit flow
- `Resume Upload And Review` if part of MVP foundation
- `Candidate Duplicate Review`
- candidate detail state with linked applications

### Required APIs

- candidate list endpoint
- candidate create endpoint
- candidate detail endpoint
- candidate update endpoint
- candidate duplicate detection endpoint
- duplicate decision endpoint
- candidate finalize-to-pipeline endpoint
- candidate owner reassignment endpoint if part of current MVP backend behavior

### Required DB Support

- candidate master
- candidate contact fields
- source details
- owner references
- social profile fields
- document metadata
- duplicate state fields
- links to applications

### Required Permission And Scope Behavior

- candidate records remain global for duplicate detection
- operational access remains controlled by permission and linked work context
- duplicate handling must use compare-first behavior
- destructive duplicate actions remain limited to Admin and selected senior roles

### Required Tests

- create candidate succeeds
- candidate update succeeds within allowed scope
- duplicate detection returns expected warning cases
- duplicate review decision is auditable
- unauthorized candidate access is blocked
- finalize-to-pipeline creates correct application record

### Done When

- recruiters can create and manage candidates safely
- the system can stop duplicate pollution before pipeline entry

## Module 8. Pipeline Tracking

### Required Pages And UI Flows

- `Pipeline Board`
- pipeline application detail
- `Stage Move Dialog`
- `Pipeline History Drawer Or Panel`
- requisition-linked pipeline view

### Required APIs

- pipeline list or board endpoint
- pipeline application detail endpoint
- stage transition endpoint
- pipeline history endpoint
- requisition pipeline summary endpoint

### Required DB Support

- candidate application table
- requisition link
- candidate link
- current stage field
- stage history records
- stage template or allowed-stage structure
- ownership and visibility references

### Required Permission And Scope Behavior

- recruiter must be able to view candidates they sourced or are linked to
- visibility should move upward to lead and account-facing users where allowed
- stage changes must be limited to permitted delivery operators
- invalid transitions must be blocked

### Required Tests

- pipeline list returns correct scoped applications
- pipeline detail returns stage history
- valid stage move succeeds
- invalid stage move fails
- unauthorized stage update fails

### Done When

- the team can track live candidate progress after submission
- the system can enforce valid pipeline movement rules

## Module 9. Daily Updates And Execution Tracking

### Required Pages And UI Flows

- `Daily Updates Submission`
- `Daily Updates Review`
- daily update detail or expanded row state
- user-linked update history view if used in MVP

### Required APIs

- daily update create endpoint
- daily update list endpoint
- daily update filter endpoint
- daily update summary endpoint

### Required DB Support

- daily update table
- user reference
- requisition reference
- status or progress fields
- blocker or note fields
- timestamps

### Required Permission And Scope Behavior

- users can submit updates only for linked work
- reviewers can see updates only within their allowed oversight scope
- location and assignment rules must be respected

### Required Tests

- create daily update succeeds for linked work
- create daily update fails for unauthorized work
- daily update list respects scope
- summary endpoint returns expected aggregates

### Done When

- execution progress can be captured daily
- leads and oversight users can monitor activity and blockers

## Module 10. Dashboards, Reports, And Governance

### Required Pages And UI Flows

- `Role Dashboard`
- `My Work Dashboard`
- location summary dashboard
- company summary dashboard
- core report filters

### Required APIs

- dashboard summary endpoint
- location summary endpoint
- company summary endpoint
- requisition metrics endpoint if separate
- candidate or pipeline metrics endpoint if separate

### Required DB Support

- reporting queries over live requisitions
- reporting queries over candidates and applications
- location aggregation support
- company-wide aggregation support
- optional export or snapshot support only if included in MVP

### Required Permission And Scope Behavior

- Admin can see company-wide combined reporting
- selected reporting users can see allowed location summaries
- users must not see data outside allowed reporting scope

### Required Tests

- location summary returns correct scoped metrics
- company summary returns combined metrics only for authorized user
- unauthorized reporting access fails
- dashboard aggregates match underlying test data scenarios

### Done When

- leaders and managers can monitor operational progress from system-generated summaries
- the MVP provides both local execution visibility and top-level oversight

## Module Dependency Order

Build and verify in this order:

1. Authentication And Session Control
2. Roles, Permissions, And Access Configuration
3. Location And User Administration
4. Client Directory
5. Requisition Management
6. Work Allocation And Assignment
7. Candidate Management
8. Pipeline Tracking
9. Daily Updates And Execution Tracking
10. Dashboards, Reports, And Governance

## Evidence Rule

Do not mark a module complete because:

- the page exists visually
- one endpoint returns a 200 response
- a table exists in the schema

Mark a module complete only when:

- pages are usable
- APIs enforce rules
- DB supports the flow
- permissions are correct
- tests prove the intended behavior
