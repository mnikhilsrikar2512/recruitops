# MVP Live Implementation Tracker

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document is the live execution tracker for the MVP.

It is meant to sit between planning and implementation.

Use it to answer:

- what is only planned
- what is currently in progress
- what is backend-ready
- what is frontend-ready
- what is QA-ready
- what is fully done

This document should be updated as work changes.

It should not stay frozen like a requirements document.

## Status Legend

- `Planned`
  Scope is defined, but delivery work has not materially started.
- `In Progress`
  Active implementation is happening, but the module is not yet ready for handoff.
- `Backend Ready`
  APIs, validations, and backend rules are materially usable for MVP.
- `Frontend Ready`
  Required pages and integrations are materially usable for MVP.
- `QA Ready`
  The module is stable enough for structured end-to-end verification.
- `Done`
  The module satisfies MVP checklist expectations across backend, frontend, permissions, and tests.

## Evidence Rule

Do not move a module to a higher status unless there is evidence for it.

Evidence may include:

- existing routes
- existing frontend pages
- test coverage
- schema support
- implementation notes
- current integration behavior

Do not mark something `Done` because:

- a page mockup exists
- an endpoint returns sample data
- a table exists without enforced behavior

## How To Update This Tracker

For each module:

1. update overall status
2. update backend status
3. update frontend status
4. update QA status
5. add current evidence
6. add next blocking gap

## Global MVP End-To-End Flow

The MVP is not complete until this full chain is working:

1. Admin creates location.
2. Admin creates role and permissions.
3. Admin creates user.
4. User logs in.
5. User creates client and contact.
6. User creates requisition.
7. User assigns delivery work.
8. Recruiter creates candidate.
9. Duplicate check runs.
10. Candidate enters pipeline.
11. Pipeline stages are updated.
12. Daily updates are posted.
13. Dashboard users can review location and company summaries.

## Current Overall MVP Position

Based on the current project evidence on Wednesday, August 19, 2026:

- planning depth is strong
- backend is materially ahead of frontend
- frontend planning is strong, but the old static page artifacts should not be treated as MVP frontend implementation evidence for the target product
- the product is not yet end-to-end MVP complete

## Module Tracker

| Module | Overall Status | Backend Status | Frontend Status | QA Status | Current Evidence | Next Blocking Gap |
| --- | --- | --- | --- | --- | --- | --- |
| Authentication And Session Control | `Backend Ready` | `Backend Ready` | `Planned` | `In Progress` | auth routes exist, permission self-summary exists, auth guard tests exist | real frontend integration and end-to-end auth flow verification |
| Roles, Permissions, And Access Configuration | `Backend Ready` | `Backend Ready` | `Planned` | `In Progress` | role routes exist, permission dependencies exist across core modules | actual role-management UI and end-to-end permission matrix verification |
| Location And User Administration | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | location routes exist, user detail route exists, deactivation review flow exists, move-review workflow exists, user lifecycle tests cover deactivation and move handling | frontend coverage and integrated UI-to-backend lifecycle verification |
| Client Directory | `Backend Ready` | `Backend Ready` | `Planned` | `In Progress` | client and contact routes exist, location-bound rules are documented and partly enforced | frontend client pages wired to live APIs and fuller QA scenarios |
| Requisition Management | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | requisition routes exist, active-client validation now exists, owner reassignment support exists, requisition workflow tests cover create, status, and assignment rules | full frontend flow and end-to-end requisition lifecycle QA |
| Work Allocation And Assignment | `In Progress` | `In Progress` | `Planned` | `Planned` | reassignment workflows exist in backend, requisition ownership support exists | dedicated frontend assignment experience and assignment-specific QA coverage |
| Candidate Management | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | candidate routes exist, duplicate handling exists, duplicate-decision audit coverage exists, finalize flow now blocks uncleared duplicates and same-requisition relinking, access-scope tests exist | richer duplicate review UX and integrated frontend/end-to-end QA |
| Pipeline Tracking | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | pipeline routes exist, scoped access tests exist, stage-template validation now exists, backward and post-joined invalid moves are blocked, rejection and joining stage field requirements are enforced | frontend pipeline board integration and E2E movement QA |
| Daily Updates And Execution Tracking | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | daily update routes exist and are protected, duplicate same-date blocking now exists, submitter-to-requisition linkage is enforced, daily update workflow tests now cover core validation paths | integrated UI, summary verification, and workflow-level QA |
| Dashboards, Reports, And Governance | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | dashboard routes exist, role and my-work service coverage exists, location and company summary endpoints exist, admin and location scope behavior are tested | integrated dashboards, richer reporting scope verification, and user-facing QA |
| Notifications | `In Progress` | `Backend Ready` | `Planned` | `In Progress` | notification routes exist, explicit notification permissions are now enforced, ownership checks exist, and notification workflow tests cover list scope and mark-read behavior | usable frontend and workflow-level integration coverage |

## Module-Level Tracking Notes

### 1. Authentication And Session Control

- Overall status:
  `Backend Ready`
- Why:
  core backend auth surfaces exist and current-user loading is present
- To move higher:
  connect live frontend flows and verify end-to-end behavior through UI

### 2. Roles, Permissions, And Access Configuration

- Overall status:
  `Backend Ready`
- Why:
  role and permission route surfaces are implemented and actively used by permission dependencies
- To move higher:
  prove UI management flow and confirm permission behavior through integrated scenarios

### 3. Location And User Administration

- Overall status:
  `In Progress`
- Why:
  backend lifecycle coverage is now materially present, but frontend evidence is still missing
- To move higher:
  confirm frontend screens and integrated lifecycle flows

### 4. Client Directory

- Overall status:
  `Backend Ready`
- Why:
  backend client and contact operations exist with location-aware structure
- To move higher:
  connect real UI and verify location-safe client operations end to end

### 5. Requisition Management

- Overall status:
  `In Progress`
- Why:
  backend lifecycle coverage is now materially present, but frontend and integrated QA evidence are still missing
- To move higher:
  confirm real UI flow and full integrated requisition lifecycle behavior

### 6. Work Allocation And Assignment

- Overall status:
  `In Progress`
- Why:
  backend reassignment support exists, but assignment handling is not yet fully proven as a complete module
- To move higher:
  finish dedicated assignment flow coverage and attach UI evidence

### 7. Candidate Management

- Overall status:
  `In Progress`
- Why:
  backend workflow coverage is now materially present, but frontend and integrated QA evidence are still missing
- To move higher:
  complete duplicate review UX and verify candidate-to-pipeline behavior end to end

### 8. Pipeline Tracking

- Overall status:
  `In Progress`
- Why:
  backend workflow coverage is now materially present, but frontend and integrated QA evidence are still missing
- To move higher:
  integrate the actual board workflow and prove valid stage movement through end-to-end tests

### 9. Daily Updates And Execution Tracking

- Overall status:
  `In Progress`
- Why:
  backend workflow coverage is now materially present, but frontend and integrated QA evidence are still missing
- To move higher:
  validate the UI workflow and reporting behavior with real scenarios

### 10. Dashboards, Reports, And Governance

- Overall status:
  `In Progress`
- Why:
  backend reporting coverage is now materially present, but frontend and integrated QA evidence are still missing
- To move higher:
  connect dashboards to real data and verify reporting access rules

### 11. Notifications

- Overall status:
  `In Progress`
- Why:
  backend notification coverage is now materially present, but frontend and integrated QA evidence are still missing
- To move higher:
  integrate notification usage in live workflows and prove the user-facing experience

## Suggested Working Columns For Daily Use

If this tracker is copied into a sheet later, use these columns:

- module
- owner
- overall status
- backend status
- frontend status
- QA status
- current blocker
- next action
- evidence link
- target date

## Recommended Update Rhythm

- update after each meaningful backend milestone
- update after each frontend integration milestone
- update after each QA pass
- review the full tracker at the end of every build phase

## Current Best Next Actions

1. Start marking frontend modules against actual built pages for the target MVP frontend, not legacy or discarded static artifacts.
2. Update module statuses again only after route-level frontend integration evidence exists in the real frontend codebase.
3. Add end-to-end QA evidence module by module using the delivery checklist.
3. Reassess requisition, candidate, and pipeline modules next, since they still carry the highest operational depth risk.
4. Reassess the tracker after each P0 module reaches at least `Backend Ready` and `Frontend Ready`.
