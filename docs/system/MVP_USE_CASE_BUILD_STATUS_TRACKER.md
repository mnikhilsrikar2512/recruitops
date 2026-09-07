# MVP Use Case Build Status Tracker

## Purpose

This file tracks actual implementation coverage for the current MVP use cases.

It answers:

- which use cases already have a mapped frontend page
- which use cases already have backend routes
- which use cases are only partially covered
- which use cases still need real implementation work

Use this file during:

- sprint planning
- backend slice planning
- frontend integration planning
- QA readiness review

Read together with:

- `docs/system/MVP_USE_CASE_EXECUTION_MATRIX.md`
- `docs/system/MVP_USE_CASE_PAGE_EXECUTION_MAP.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`

## Status Meaning

- `Ready`
  Frontend page exists and backend API surface exists for the MVP flow.
- `Partial`
  Major pieces exist, but one or more important gaps still block true end-to-end completion.
- `Planned`
  The use case is clearly designed in docs, but current implementation is still missing important runtime pieces.

## Current Evidence Source

Frontend evidence checked from:

- `frontend-mvp/app/pages`
- `frontend-mvp/app/components`

Backend evidence checked from:

- `backend/app/api/v1`

Audit date:

- Wednesday, August 19, 2026

## MVP Use Case Status

| Use Case | Main MVP Page | Frontend Page Status | Backend API Status | Overall Status | Main Gaps Or Notes |
| --- | --- | --- | --- | --- | --- |
| `UC-01 Login` | `Login` | `Ready` | `Ready` | `Ready` | Login, logout, `me`, and permission context routes exist. |
| `UC-02 Access Summary` | `Role Dashboard` | `Partial` | `Ready` | `Partial` | Backend context exists, but a dedicated access-summary UI is still implied rather than clearly separated. |
| `UC-03 Create Location` | `Location Management` | `Ready` | `Ready` | `Ready` | Page exists and list plus create or update routes exist. |
| `UC-04 Create Role` | `Role Management` | `Ready` | `Partial` | `Partial` | Role list, create, update, and permission routes exist, but a dedicated role detail read route is not visible in current API files. |
| `UC-05 Create User` | `User Management` | `Ready` | `Ready` | `Ready` | Core user lifecycle routes exist, including reset, deactivate, and move. |
| `UC-06 Create Client` | `Client Directory` | `Ready` | `Ready` | `Ready` | Core CRUD surface exists for MVP create and update flow. |
| `UC-07 Add Client Contact` | `Client Detail` | `Ready` | `Ready` | `Ready` | Detail page and contact dialog exist, with list, create, and update routes. |
| `UC-08 Create Requisition` | `Requisition Intake` | `Ready` | `Ready` | `Ready` | Page and create flow APIs exist. |
| `UC-09 View Requisition Backlog` | `Requisition List` | `Ready` | `Ready` | `Ready` | List page and list route exist. |
| `UC-10 Assign Delivery Ownership` | `Requisition Detail` | `Ready` | `Ready` | `Ready` | Detail page, assignment list, create assignment, and owner reassignment routes exist. |
| `UC-11 Work Queue Review` | `Delivery Work Queue` | `Ready` | `Partial` | `Partial` | Page exists, but queue behavior still depends on generic requisition and dashboard routes instead of a dedicated work queue contract. |
| `UC-12 Create Candidate` | `Candidate Profiles` | `Ready` | `Ready` | `Ready` | Core candidate list, create, detail, and update routes exist. |
| `UC-13 Upload Resume` | `Resume Upload And Review` | `Ready` | `Ready` | `Ready` | Upload route exists; parsing and richer document workflow may still evolve later. |
| `UC-14 Detect Duplicate Candidate` | `Candidate Profiles` | `Ready` | `Partial` | `Partial` | Duplicate-check behavior exists, but current route shape is candidate-specific and may differ from planning docs. |
| `UC-15 Resolve Duplicate` | `Candidate Duplicate Review` | `Ready` | `Partial` | `Partial` | Review decision route exists, but current backend appears tied to candidate review flow rather than a fuller duplicate-case work queue. |
| `UC-16 Link Candidate To Requisition` | `Candidate Profiles` | `Partial` | `Planned` | `Planned` | Current page exists, but no application-create route is visible in the current API files. |
| `UC-17 Screen Candidate` | `Candidate Screening` | `Ready` | `Partial` | `Partial` | Page exists, but a clearly separated screening-specific endpoint is not visible; likely still handled through candidate update flow. |
| `UC-18 View Pipeline` | `Pipeline Board` | `Ready` | `Ready` | `Ready` | Board, application detail, and history routes exist. |
| `UC-19 Move Pipeline Stage` | `Pipeline Board` | `Ready` | `Ready` | `Ready` | Stage move route exists along with dedicated stage-move dialog. |
| `UC-20 Recruiter Progress Tracking` | `My Work Dashboard` | `Ready` | `Ready` | `Ready` | My-work dashboard route exists and page is present. |
| `UC-21 Submit Daily Update` | `Daily Updates Submission` | `Ready` | `Ready` | `Ready` | Daily update list, create, and detail routes exist. |
| `UC-22 Review Daily Updates` | `Daily Updates Review` | `Ready` | `Ready` | `Ready` | Review page exists and backend data is available from daily-updates plus dashboard summary routes. |
| `UC-23 Notifications Review` | `Notifications Center` | `Ready` | `Ready` | `Ready` | List and mark-read routes exist, plus notification detail panel page. |
| `UC-24 Location Reporting` | `Location Dashboard` | `Ready` | `Ready` | `Ready` | Location summary route exists. |
| `UC-25 Company Reporting` | `Company Dashboard` | `Ready` | `Ready` | `Ready` | Company summary route exists. |
| `UC-26 Access Denial` | `Access Denied` | `Ready` | `Ready` | `Ready` | Page exists; protected APIs are present across modules. |

## Highest-Priority Gaps

These are the most important remaining gaps before we can confidently say the MVP use cases are fully buildable end to end:

1. `UC-16 Link Candidate To Requisition`
   The planning expects a candidate-to-application creation flow, but a visible application-create endpoint is not present in current API routes.
2. `UC-11 Work Queue Review`
   The page exists, but the backend contract still looks assembled from generic dashboard and requisition data instead of one explicit work-queue response.
3. `UC-14 Detect Duplicate Candidate`
   Duplicate detection exists, but the current route shape should be aligned with the planning contract before frontend integration begins.
4. `UC-15 Resolve Duplicate`
   The decision route exists, but the duplicate review lifecycle may need a fuller case-list model if senior users are expected to review queued cases.
5. `UC-17 Screen Candidate`
   Candidate screening needs a clearer API contract if the screen is meant to persist structured screening outcomes rather than general profile edits.

## Best Next Backend Slice

If we want the next implementation slice to unlock the most frontend value, build in this order:

1. candidate-to-requisition application create flow
2. dedicated work-queue response contract
3. duplicate review contract alignment
4. structured screening save contract

## Best Next Frontend Integration Slice

Once the backend gaps above are closed, the best integration order is:

1. `Candidate Profiles` -> link candidate to requisition
2. `Delivery Work Queue` -> live workload and next-action data
3. `Candidate Duplicate Review` -> real compare and decision flow
4. `Candidate Screening` -> real saved screening outcomes

## Current Readiness Summary

- Strongest completed area:
  auth, administration, client, requisition, pipeline, daily updates, notifications, and reporting all have real page and route coverage.
- Most important incomplete area:
  candidate execution still needs one more pass to fully close the application, duplicate-case, and screening workflows.
- Product implication:
  the MVP is already structurally strong, but candidate execution is the most important remaining business slice before full end-to-end confidence.
