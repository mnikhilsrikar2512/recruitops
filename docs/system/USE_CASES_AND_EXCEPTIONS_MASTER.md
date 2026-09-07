# Use Cases And Exceptions Master

## Purpose

This document converts the MVP working model into one execution-ready reference that can be used by product, backend, frontend, QA, and implementation teams.

It combines three layers for each module:

- normal use cases
- operational exceptions
- system contract expectations

This is the simplest document to use when the team wants to understand:

- what the user is trying to do
- what can go wrong
- what the system must enforce

## How To Use This Document

For every module below, read in this order:

1. Use cases
2. Exceptions
3. System contract

The rule is:

- use cases define the normal business flow
- exceptions define validations, warnings, approvals, and edge conditions
- system contract defines the implementation expectation across UI, API, DB, permissions, and audit

## Product Model Assumptions

- `Admin` is the only fixed product role
- all other working roles are created by Admin
- operational users belong to a location
- one client belongs to one operating location in MVP
- candidates are global at company level for duplicate detection
- operational access remains controlled by location, ownership, and permissions
- visibility can move upward, while edit rights can remain restricted
- reporting must support both location-level and combined company views

## Module 1. Authentication And Session Control

### Use Cases

- A user logs in with valid credentials and enters the product with the correct role, title, permission set, and location context.
- A user logs out and their active session is ended.
- A logged-in user reopens the system and continues only if the session is still valid.
- A user opens their own profile context and sees effective access information.
- An admin resets a user password and may force first-login password change.

### Exceptions

- Invalid credentials are entered:
  System rejects access and records the failed attempt.
- Inactive or suspended user tries to log in:
  System blocks access and returns a restricted response.
- Session token is expired, revoked, or invalid:
  System forces re-authentication.
- Credentials are reset while the user is active:
  System may revoke live sessions depending on company policy.

### System Contract

- UI:
  Login, logout, session expiry, reset-password, and current-access screens must exist.
- API:
  Authentication endpoints must support login, logout, self-profile, and credential reset.
- DB:
  User status, password state, session metadata, and audit trail fields are required.
- Permissions:
  Only permitted users can reset another user’s credentials.
- Audit:
  Login, reset, lock, revoke, and suspicious access events should be traceable.

## Module 2. Roles, Permissions, And Access Configuration

### Use Cases

- Admin creates a custom role for a company-specific operating model.
- Admin assigns modules, pages, features, actions, and visibility scope to a role.
- Admin updates a role later without breaking historical records.
- Admin assigns a role to a user.
- A user sees only the modules and actions allowed by effective access.

### Exceptions

- Admin creates a role with risky permission combinations:
  System should flag sensitive access for review.
- A role change removes access from active users:
  System should apply the change immediately and log it.
- A user tries to perform an action outside allowed scope:
  System must deny the action clearly.
- Direct grants or exceptions exist beyond the base role:
  System must resolve the final effective permission set correctly.

### System Contract

- UI:
  Role list, role create, role edit, permission matrix, and user-role assignment screens are required.
- API:
  Role CRUD, permission read, permission assignment, and access-summary endpoints are required.
- DB:
  Role master, permission mappings, module mappings, page mappings, and action mappings are required.
- Permissions:
  Only Admin or explicitly authorized governance users can manage access configuration.
- Audit:
  Every role change and user-access change must be logged.

## Module 3. Location And User Administration

### Use Cases

- Admin creates, activates, or deactivates a location.
- Admin creates a user with identity, contact, employee ID, title, manager, role, and location.
- Admin edits a user’s profile, manager, status, role, or contact information.
- Admin reviews a user detail page with access, reporting, and work-assignment context.
- Admin deactivates a user safely.
- Admin moves a user to another location or operating role through a controlled workflow.

### Exceptions

- User is assigned to a deactivated location:
  System should block operational use until corrected.
- User is mapped to themselves as manager:
  System must reject the update.
- Duplicate email, phone, or employee ID is detected:
  System must apply the configured company rule.
- User is moved while owning live requisitions, candidates, or pipeline records:
  System should require reassignment review before completion.
- User is deactivated while still owning active work:
  System should force review and transfer handling instead of silent orphaning.

### System Contract

- UI:
  Location list, location create, user list, user create, user detail, user edit, user move, and user deactivation review pages are required.
- API:
  Location CRUD, user CRUD, user detail, credential reset, move-review, and deactivate-review endpoints are required.
- DB:
  User master, location master, reporting relationship, status flags, and assignment references are required.
- Permissions:
  User lifecycle actions must be limited to governance-enabled users.
- Audit:
  User creation, edit, move, deactivate, reassign, and credential actions must be traceable.

## Module 4. Client Directory

### Use Cases

- A permitted user creates a client and assigns it to one location.
- A permitted user adds primary and secondary client contacts.
- A user edits client profile, notes, status, industry, and tags.
- A user searches and views clients by location, owner, industry, or status.
- A user reviews linked contacts and requisitions from client detail.

### Exceptions

- Same client is created again in the same location:
  System should warn and require review.
- Wrong location is assigned during client creation:
  System should require correction before live work begins.
- A requisition contact does not belong to the selected client:
  System must reject the mapping.
- A different location tries to operate on the client:
  System must block by default in MVP.

### System Contract

- UI:
  Client list, client create, client detail, client edit, contact create, and contact edit pages are required.
- API:
  Client CRUD, contact CRUD, client search, and client detail endpoints are required.
- DB:
  Client master, client contact, location ownership, ownership user references, and client status fields are required.
- Permissions:
  Access depends on module permission plus location scope.
- Audit:
  Client ownership, status changes, and contact edits should be logged.

## Module 5. Requisition Management

### Use Cases

- A permitted user creates a requisition from a client requirement.
- A user captures title, openings, priority, skills, acceptable career gap, target date, and client update availability time.
- A user assigns the business-side owner and operational owner set.
- A user updates requisition status and tracks intake to execution movement.
- A user reviews requisition detail, including linked pipeline and ownership.

### Exceptions

- Requisition is created against an inactive client:
  System should reject or require a controlled override.
- Assigned owners belong to the wrong location:
  System must reject the mapping.
- Closed requisition needs reopening:
  System should require a reason and preserve history.
- Requisition owner becomes unavailable:
  System should trigger reassignment workflow.
- Pipeline template needs to change mid-process:
  System should support controlled update without corrupting active applications.

### System Contract

- UI:
  Requisition list, requisition create, requisition detail, requisition edit, ownership assignment, and status-history sections are required.
- API:
  Requisition CRUD, detail, list filters, owner reassignment, status update, and history endpoints are required.
- DB:
  Requisition master, ownership references, status history, client mapping, and pipeline-template reference are required.
- Permissions:
  Edit rights should remain limited even when visibility moves upward.
- Audit:
  Status changes, assignment changes, and reopening actions must be recorded.

## Module 6. Work Allocation And Assignment

### Use Cases

- A permitted user assigns recruiters or contributors to a requisition.
- A lead user reviews workload and adjusts distribution.
- A user sees current assignment ownership and contribution structure.
- A senior user reassigns work because of leave, performance, or workload balancing.

### Exceptions

- Assignee belongs to another location:
  System should block unless future exception support is enabled.
- Reassignment happens while active candidate work exists:
  System should require review and preserve history.
- A user is deactivated while still assigned:
  System should force reassignment handling.

### System Contract

- UI:
  Assignment panel, reassignment modal, workload view, and assignment history section are required.
- API:
  Assignment create, list, update, remove, and reassignment-review endpoints are required.
- DB:
  Requisition assignment records, contributor mappings, reassignment history, and active flags are required.
- Permissions:
  Only permitted senior users can reassign ownership.
- Audit:
  Assignment creation, replacement, and removal must be logged.

## Module 7. Candidate Management

### Use Cases

- A recruiter creates a candidate profile manually.
- A recruiter enters contact, skills, source, social profiles, documents, and ownership details.
- A recruiter edits a candidate before final pipeline submission.
- A user searches candidates across the company for duplicate-aware intelligence.
- A user reviews candidate detail, linked requisitions, and ownership context.
- A user finalizes a candidate into a requisition pipeline.

### Exceptions

- A duplicate candidate is detected:
  System must force compare-first handling before override or discard.
- Duplicate merge, delete, or override is needed:
  Only Admin and selected senior roles should be able to complete the change.
- Candidate profile is incomplete at final submission:
  System should block or keep it in draft.
- Candidate is linked to the wrong owner:
  System should support controlled correction with audit.

### System Contract

- UI:
  Candidate list, candidate create, duplicate compare, candidate detail, document section, and finalize-to-pipeline flow are required.
- API:
  Candidate CRUD, duplicate detection, duplicate review decision, owner reassignment, document handling, and finalize endpoints are required.
- DB:
  Candidate master, contact fields, source metadata, document metadata, duplicate flags, and ownership links are required.
- Permissions:
  Candidate visibility may be broad, but destructive duplicate actions must remain limited.
- Audit:
  Duplicate handling, owner changes, and finalization events must be logged.

## Module 8. Pipeline Tracking

### Use Cases

- A recruiter views the candidate pipeline for the requisitions they are connected to.
- A lead user reviews location-level pipeline progress.
- An account-facing user reviews requisition-level pipeline progress.
- A user opens pipeline application detail and stage history.
- A permitted user moves a candidate through stages.
- A user tracks stalled, rejected, offered, or joined profiles.

### Exceptions

- Candidate is moved to a stage that is not part of the active requisition pipeline:
  System must reject the change.
- Candidate is moved backward:
  System should preserve stage history and optionally require a reason.
- An invalid transition is attempted, such as joined to rejected:
  System should block inconsistent movement.
- Unauthorized user tries to update pipeline outside their scope:
  System must deny the action.

### System Contract

- UI:
  Pipeline board, application detail page, stage-change modal, activity history, and stage aging view are required.
- API:
  Pipeline list, application detail, stage transition, history, and pipeline summary endpoints are required.
- DB:
  Application records, stage history, stage template mapping, requisition link, and ownership references are required.
- Permissions:
  Visibility can extend from recruiter upward to account-facing users; edit rights stay limited to permitted delivery operators.
- Audit:
  Stage transitions and reversals must be recorded.

## Module 9. Daily Updates And Execution Tracking

### Use Cases

- A user posts a daily update for their active work.
- A lead user reviews team updates and blockers.
- A manager checks execution summaries linked to requisitions or assignees.
- A user updates progress notes for the day or configured reporting cycle.

### Exceptions

- A user tries to submit an update for work they are not linked to:
  System must deny the action.
- Update is missed within the expected window:
  System should surface reminders or reporting gaps.
- Update is changed after review lock:
  System should block direct edit or require override depending on policy.

### System Contract

- UI:
  Daily update form, daily update list, blocker summary, and execution rollup views are required.
- API:
  Daily update create, list, filter, and summary endpoints are required.
- DB:
  Daily update records, linkage to user and requisition, timestamps, and status fields are required.
- Permissions:
  Submission rights depend on assignment and access; review rights depend on configured oversight scope.
- Audit:
  Post-lock edits or overrides must be logged.

## Module 10. Dashboards, Reports, And Governance

### Use Cases

- Admin views company-wide summary across all locations.
- A permitted reporting user views a location summary.
- A user reviews requisition, candidate, and pipeline trends based on their allowed scope.
- A reporting user exports governed reports where allowed.
- A reviewer accesses historical reporting snapshots if the company enables locked reporting periods.

### Exceptions

- A user tries to see data outside their allowed reporting scope:
  System must restrict the output.
- Report period is locked:
  System should prevent retroactive operational edits from changing the locked snapshot.
- Combined reporting is requested across locations:
  Only Admin or selected reporting roles should be allowed.

### System Contract

- UI:
  Dashboard, location summary, company summary, report filters, and export actions are required.
- API:
  Dashboard summary, location summary, company summary, and governed report endpoints are required.
- DB:
  Reporting queries must be supportable from live operational tables and optional snapshot tables.
- Permissions:
  Reporting access must be configurable by company, with combined visibility limited to authorized roles.
- Audit:
  Sensitive export actions and locked-period overrides should be visible in logs.

## Cross-Module Use Cases

### 1. Controlled Visibility Model

- A recruiter should see candidate and pipeline progress for the work they sourced or are linked to.
- A lead or account-facing user should see progress upward without automatically gaining edit rights.
- A business-side or oversight user should see summaries based on configured scope.

System expectation:

- visibility and edit rights must be modeled separately
- upward visibility should be easier to grant than upward edit rights

### 2. Controlled Ownership Transfer

- When a user becomes unavailable, active requisitions, candidates, assignments, and pipeline work must move through a tracked review flow.

System expectation:

- transfer should not silently rewrite history
- audit and reassignment reasoning must be preserved

### 3. Duplicate-Safe Global Candidate Intelligence

- Candidate records should remain global for duplicate detection across the company.
- Operational access should still remain controlled by permission and location-linked work context.

System expectation:

- the system must allow compare-first duplicate review
- destructive duplicate resolution should stay restricted

### 4. Configurable Client-Driven Pipeline Design

- Different clients may require different stage names or stage orders.

System expectation:

- the pipeline template should be configurable by company or requisition rule
- active applications must not be corrupted when templates change

## What This Means For Build Execution

Every module should be built and reviewed in five layers:

1. Pages and user flows
2. API routes and request-response contracts
3. DB schema and relational rules
4. Permission and scope enforcement
5. Audit and exception handling

If one of those five layers is missing, the module is only partially done.

## Recommended Document Order

Use this document first for business understanding, then move to:

1. `docs/system/MVP_USE_CASE_CATALOG.md`
2. `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`
3. `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
4. `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`
5. `docs/system/API_VALIDATION_RULES.md`
