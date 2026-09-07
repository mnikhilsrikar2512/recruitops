# Phased Implementation Backlog

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document converts the MVP plan into an execution sequence.

It is the working backlog for:

- backend development
- frontend integration
- QA
- seeded demo validation

## Phase 0. Technical Foundation

### Goal

Create a stable backend skeleton and development workflow.

### Deliverables

- backend project bootstrap
- environment configuration
- database connectivity
- migration runner
- seed runner
- common error handler
- request logging
- health endpoint

### Exit Criteria

- app boots locally
- database connection succeeds
- migration and seed flows are repeatable

## Phase 1. Authentication And Permission Core

### Goal

Make users, roles, and scope enforcement real.

### Stories

- implement login
- implement logout
- implement current user endpoint
- implement permission summary endpoint
- implement permission middleware
- implement scope middleware
- seed Admin and starter roles

### Exit Criteria

- Admin can log in
- protected routes reject unauthorized access
- permission payload is returned correctly

## Phase 2. Admin Setup Core

### Goal

Allow Admin to configure the operating structure.

### Stories

- create locations
- edit locations
- activate and deactivate locations
- create users
- edit users
- activate and deactivate users
- create roles
- edit roles
- assign permissions to roles
- assign scope to roles
- assign primary role to user

### Exit Criteria

- Admin can configure locations, users, and roles end to end

## Phase 3. Client Management

### Goal

Enable live client records with location-safe ownership.

### Stories

- create client
- edit client
- list clients
- view client detail
- create client contact
- edit client contact

### Exit Criteria

- permitted users can manage clients in allowed location scope

## Phase 4. Requisition Management

### Goal

Enable structured hiring demand intake and assignment.

### Stories

- create requisition
- edit requisition
- list requisitions
- view requisition detail
- assign primary owner
- assign delivery owner
- assign support users
- update requisition status

### Exit Criteria

- permitted users can create and manage requisitions with correct ownership

## Phase 5. Candidate Intake And Duplicate Review

### Goal

Enable candidate creation and protect against duplicate records.

### Stories

- create candidate draft
- upload resume
- edit candidate draft
- run duplicate check
- review duplicate matches
- request duplicate override
- finalize candidate

### Exit Criteria

- candidate intake works end to end
- duplicate review is enforced before final save

## Phase 6. Pipeline Execution

### Goal

Enable live candidate movement against requisitions.

### Stories

- attach candidate to requisition
- view pipeline board
- move stage
- store stage history
- reject candidate
- mark joined

### Exit Criteria

- requisition pipeline is operational and auditable

## Phase 7. Daily Updates And Dashboards

### Goal

Enable operational execution visibility.

### Stories

- submit daily update
- list daily updates
- review daily updates
- role dashboard
- my work dashboard
- location summary

### Exit Criteria

- dashboards show live operational data
- daily updates are usable in live workflow

## Phase 8. Notifications And Audit

### Goal

Add minimum governance and follow-up support.

### Stories

- create workflow notifications
- list notifications
- mark notifications read
- persist critical audit logs

### Exit Criteria

- important actions generate notifications and audit trails

## Phase 9. Frontend Integration

### Goal

Connect real APIs to the MVP pages only.

### Stories

- connect login
- connect Admin setup pages
- connect client pages
- connect requisition pages
- connect candidate pages
- connect pipeline board
- connect daily updates pages
- connect dashboards

### Exit Criteria

- core MVP screens no longer rely on mock data

## Cross-Phase QA Track

This track runs in parallel after Phase 2 begins.

### Required QA Scenarios

- invalid login
- unauthorized route access
- location access denial
- duplicate candidate detection
- requisition ownership reassignment
- stage movement validation
- required field validation
- daily update submission validation

## Suggested Sprint Grouping

### Sprint 1

- Phase 0
- Phase 1

### Sprint 2

- Phase 2
- Phase 3

### Sprint 3

- Phase 4
- Phase 5

### Sprint 4

- Phase 6
- Phase 7

### Sprint 5

- Phase 8
- Phase 9

## Build Order Rule

No frontend page should be treated as complete until:

- its API exists
- its permissions are enforced
- its validations are implemented
- its data persists in the database
