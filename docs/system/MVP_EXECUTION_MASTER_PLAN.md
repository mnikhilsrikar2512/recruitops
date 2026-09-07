# MVP Execution Master Plan

## Purpose

This document is the top-level coordinated delivery plan for the MVP.

It combines:

- frontend execution sequencing
- backend execution sequencing
- QA checkpoints
- dependency gates
- milestone definitions
- readiness movement rules

It is the main document to use when the team wants one shared answer to:

- what we build first
- what can run in parallel
- what blocks the next stage
- when a stage is really done

Use this together with:

- `docs/system/MVP_FRONTEND_BUILD_SEQUENCE_PACK.md`
- `docs/system/MVP_BACKEND_BUILD_SEQUENCE_PACK.md`
- `docs/system/MVP_LIVE_IMPLEMENTATION_TRACKER.md`
- `docs/system/MVP_MODULE_DELIVERY_CHECKLIST.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`

## Date Locked

- Wednesday, August 19, 2026

## Master Delivery Rule

The MVP must be delivered in business slices, not isolated technical parts.

A milestone is complete only when:

- the backend slice is usable
- the frontend slice is usable
- permissions and scope rules are respected
- the core QA scenarios for that slice pass

If one of those is missing, the slice is still in progress.

## Current Delivery Position

Based on current project evidence as of Wednesday, August 19, 2026:

- planning depth is strong
- backend is ahead of frontend implementation
- frontend execution planning is now strong
- the product is not yet end-to-end complete
- the next major transition is from planning depth to coordinated build execution

## Delivery Streams

This MVP should be managed through four coordinated streams:

### 1. Product And Planning Stream

Owns:

- business rules
- use cases
- module scope
- execution sequencing
- planning updates

### 2. Backend Stream

Owns:

- schema
- routes
- services
- validation rules
- permission and scope enforcement
- tests

### 3. Frontend Stream

Owns:

- layouts
- pages
- routing
- dialogs and drawers
- shared components
- hooks and adapters
- UI state behavior

### 4. QA And Readiness Stream

Owns:

- scenario verification
- regression checks
- status evidence
- tracker updates
- go or no-go quality judgment

## Coordinated Delivery Milestones

1. Foundation Ready
2. Admin Setup Ready
3. Client And Requisition Ready
4. Candidate And Pipeline Ready
5. Daily Updates And Reporting Ready
6. MVP Integration Ready
7. MVP Done

## Milestone 1. Foundation Ready

### Business Goal

Make the product structurally usable as a secure application shell.

### Backend Scope

- auth routes
- permission context routes
- auth dependency
- permission dependency
- scope dependency base

### Frontend Scope

- login page
- access denied page
- app shell
- route guards
- base layouts
- shared state components

### QA Scope

- login
- logout
- expired-session redirect
- protected route denial

### Parallel Work Allowed

- backend auth and permission work
- frontend shell and route guard work
- shared UI primitives

### Milestone Exit Criteria

- user can sign in
- protected route gating works
- app shell loads with current user context
- access denied route works

## Milestone 2. Admin Setup Ready

### Business Goal

Allow initial company configuration before operations begin.

### Backend Scope

- locations
- roles
- permissions assignment
- users
- user detail
- user move review
- user deactivation review

### Frontend Scope

- location management
- role management
- user management
- user detail

### QA Scope

- admin-only access
- create and edit flows
- deactivation review
- move-review handling

### Dependency Gate

- Milestone 1 must be stable first

### Milestone Exit Criteria

- Admin can create location
- Admin can create role and assign access
- Admin can create user
- Admin can open user detail
- deactivation and move review flows are present and testable

## Milestone 3. Client And Requisition Ready

### Business Goal

Enable demand intake and preparation for delivery execution.

### Backend Scope

- clients
- client contacts
- requisitions
- requisition status changes
- requisition assignments
- owner reassignment

### Frontend Scope

- client directory
- client detail
- requisition list
- requisition intake
- requisition detail

### QA Scope

- client creation under location
- contact integrity
- requisition create and edit
- assignment and reassignment
- invalid ownership and location checks

### Dependency Gate

- Milestone 2 must be stable because roles, users, and locations are required

### Milestone Exit Criteria

- permitted user can create client and contact
- permitted user can create requisition
- permitted senior user can assign delivery work
- requisition detail shows ownership and assignment correctly

## Milestone 4. Candidate And Pipeline Ready

### Business Goal

Enable the core recruitment execution flow.

### Backend Scope

- candidates
- duplicate detection
- duplicate review decision
- candidate application creation
- pipeline board
- pipeline application detail
- stage movement
- stage history

### Frontend Scope

- candidate profiles
- resume upload and review
- duplicate review page
- link candidate to requisition flow
- pipeline board
- stage move dialog
- history drawer

### QA Scope

- candidate creation
- duplicate compare-first flow
- same-candidate same-requisition protection
- pipeline movement validations
- recruiter visibility continuity

### Dependency Gate

- Milestone 3 must be stable because live requisitions must already exist

### Milestone Exit Criteria

- recruiter can create candidate
- duplicate detection and duplicate review route work
- candidate can enter pipeline
- permitted users can move candidate through valid stages

## Milestone 5. Daily Updates And Reporting Ready

### Business Goal

Enable operational progress tracking and management visibility.

### Backend Scope

- daily updates
- my-work dashboard
- role summary or team summary
- location summary
- company summary
- notifications

### Frontend Scope

- daily updates submission
- daily updates review
- role dashboard
- my work dashboard
- location dashboard
- company dashboard
- notifications center

### QA Scope

- daily update submission
- update review
- dashboard routing
- reporting visibility by permission
- notification linked-record flow

### Dependency Gate

- Milestone 4 must be stable because live candidate and pipeline data must exist

### Milestone Exit Criteria

- recruiters can submit updates
- managers can review execution progress
- reporting pages load with correct access control
- notifications can open linked work items

## Milestone 6. MVP Integration Ready

### Business Goal

Ensure every MVP slice works together as one integrated product.

### End-To-End Chain That Must Work

1. Admin creates location
2. Admin creates role and permissions
3. Admin creates user
4. user logs in
5. permitted user creates client and contact
6. permitted user creates requisition
7. permitted senior user assigns delivery work
8. recruiter creates candidate
9. duplicate check runs
10. candidate enters pipeline
11. pipeline stages move
12. daily update is submitted
13. management views reporting

### Cross-Team Focus

- route-to-API integration
- permission-aware UI behavior
- scope-safe data access
- success and review-required state handling
- end-to-end regression

### Milestone Exit Criteria

- the full business chain above is manually testable from UI to backend
- no critical planning-to-implementation mismatch blocks the chain
- live tracker status can be advanced with evidence

## Milestone 7. MVP Done

### Business Goal

Reach a defensible first usable end-to-end product.

### Requirements

- all MVP modules are at least `QA Ready`
- core chain is fully testable
- no critical module remains only planning-stage
- permissions and scope behavior are proven in integrated scenarios
- major dialogs, drawers, and routes are all present
- known blockers are documented and acceptable for MVP

### Exit Criteria

- the live implementation tracker can justify `Done` or equivalent complete readiness for the MVP chain
- delivery checklist expectations are satisfied across modules

## Cross-Team Dependency Map

### Frontend Depends On Backend For

- auth context
- role and permission data
- list and detail APIs
- mutation responses
- review-required error codes
- dashboard and reporting metrics

### Backend Depends On Product And Planning For

- final field rules
- status transition rules
- duplicate handling rules
- review-required flows
- reporting scope rules

### QA Depends On Frontend And Backend For

- real routes and pages
- real APIs and validations
- stable test data setup
- clear expected outcomes

## Recommended Working Rhythm

### Daily

- update implementation tracker when real evidence changes
- surface blockers between frontend and backend early

### Per Milestone

- review exit criteria
- verify QA focus areas
- confirm dependency gates are truly satisfied

### Weekly

- review the full master plan
- confirm whether milestone order still matches real progress
- adjust only with evidence, not optimism

## Suggested Ownership Model

If the team assigns owners, use these categories:

- product owner
- frontend owner
- backend owner
- QA owner
- integration owner

Do not let milestone ownership become unclear across streams.

## Suggested Tracking Columns For A Sheet

- milestone
- module
- backend owner
- frontend owner
- QA owner
- current status
- dependency gate
- blocker
- next action
- target date
- evidence link

## Relationship To Live Tracker

This master plan is not a replacement for the live tracker.

Use them differently:

- `MVP_EXECUTION_MASTER_PLAN.md`
  for coordinated delivery structure
- `MVP_LIVE_IMPLEMENTATION_TRACKER.md`
  for current evidence-based status

## Escalation Rules

Escalate immediately if:

- frontend build is blocked by undefined API behavior
- backend build is blocked by unclear business rule
- QA cannot determine expected result for a critical scenario
- one stream claims readiness but another stream lacks supporting evidence

Do not hide these gaps inside optimistic status updates.

## Current Best Next Actions

1. Start real frontend implementation using the frontend build sequence pack.
2. Continue backend hardening only where tracker evidence still shows partial or in-progress status.
3. Update the live tracker from implementation evidence, not planning docs.
4. Begin milestone-based QA checklists as soon as the first integrated UI flows exist.

## Final Delivery Rule

The MVP is not execution-ready in practice unless this master plan can answer:

- what milestone the team is in now
- what each stream is doing now
- what blocks the next milestone
- what evidence proves the milestone is complete

If any of those are unclear, coordination risk is still high.
