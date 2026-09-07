# MVP Use Case Execution Matrix

## Purpose

This document is the build-ready use case reference for the current RecruitOps MVP.

It consolidates:

- business use cases
- actual MVP frontend pages
- required overlays or supporting containers
- primary APIs
- core database entities
- permission and scope rules
- JS-managed UX behavior
- exception hooks

Use this as the first execution document when a team member asks:

- which page supports this business flow
- which API is required for this page
- which data entities are involved
- which interactions stay in frontend JS
- which validations and exceptions must be enforced by backend

Read together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/MVP_USE_CASE_PAGE_EXECUTION_MAP.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`
- `docs/system/API_VALIDATION_RULES.md`

## MVP Frontend Pages In Scope

These are the current MVP route-level pages:

- `Login`
- `Access Denied`
- `Role Dashboard`
- `My Work Dashboard`
- `Location Management`
- `User Management`
- `Role Management`
- `Client Directory`
- `Client Detail`
- `Requisition List`
- `Requisition Intake`
- `Requisition Detail`
- `Delivery Work Queue`
- `Candidate Profiles`
- `Resume Upload And Review`
- `Candidate Duplicate Review`
- `Candidate Screening`
- `Pipeline Board`
- `Daily Updates Submission`
- `Daily Updates Review`
- `Notifications Center`
- `Location Dashboard`
- `Company Dashboard`

These are the current shared overlay or component pages:

- `Reassign Owner Dialog`
- `Stage Move Dialog`
- `Pipeline History Drawer`
- `Contact Form Dialog`
- `Notification Detail Panel`

## Execution Rules

### Frontend JS Should Handle

- form state
- drawer and dialog state
- drag-and-drop preview behavior
- local sorting and filtering
- staged form transitions
- unsaved-change prompts
- success, loading, and empty-state behavior
- animation, emphasis, and micro-interaction polish

### APIs Must Handle

- authentication truth
- permission truth
- location-safe access enforcement
- duplicate checks
- persistent create and update actions
- pipeline stage changes
- dashboard metrics
- notification persistence
- audit-sensitive actions

### DB Must Guarantee

- referential integrity
- unique identity rules
- location ownership rules
- candidate reusability for duplicate detection
- application-level pipeline history
- reassignment traceability
- status and audit history preservation

## Top MVP Use Cases

These are the highest-priority use cases that prove the product works end to end:

1. User login with effective access context
2. Admin creates location
3. Admin creates custom role and assigns permissions
4. Admin creates user and assigns location plus role
5. Permitted user creates client under one location
6. Permitted user adds client contacts
7. Permitted user creates requisition from client requirement
8. Permitted senior user assigns requisition to delivery team
9. Recruiter creates candidate profile
10. Recruiter uploads resume and reviews parsed data
11. System checks duplicate candidate risk globally
12. Senior user resolves duplicate case when required
13. Recruiter links candidate to requisition
14. Recruiter screens candidate for fit
15. Recruiter and seniors track candidate pipeline
16. Permitted user moves candidate through pipeline stages
17. Recruiter submits daily updates
18. Seniors review delivery progress
19. Reporting users review location dashboard
20. Reporting users review combined company dashboard

## Build Matrix

| Use Case | Business Outcome | Main MVP Page | Supporting Container | Primary APIs | Core DB Entities | Permission And Scope Rule | JS / UX Responsibility | Exception Hooks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `UC-01 Login` | User enters product with correct access context | `Login` | none | `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `GET /api/v1/permissions/me` | `users`, `roles`, `permissions`, `role_permissions`, `user_sessions` | active user only, valid role and location context required | password toggle, loading state, redirect, auth error display | invalid credentials, inactive user, expired session |
| `UC-02 Access Summary` | User understands allowed modules and actions | `Role Dashboard` | inline access summary card or future profile state | `GET /api/v1/auth/me`, `GET /api/v1/permissions/me` | `users`, `roles`, `permissions`, `user_role_assignments` | self-view allowed, broader access requires permission | reveal grouped permissions, contextual hints, read-only summaries | mismatch between role and direct grants |
| `UC-03 Create Location` | New operating location becomes usable in system | `Location Management` | create or edit drawer in page flow | `GET /api/v1/locations`, `POST /api/v1/locations`, `PUT /api/v1/locations/{id}` | `locations`, `users` | governance users only | inline create flow, local validation hints, status chips, confirmation motion | duplicate code, invalid location head, deactivate with active work |
| `UC-04 Create Role` | Company-specific role becomes reusable | `Role Management` | permission editor sections inside page | `GET /api/v1/roles`, `POST /api/v1/roles`, `PUT /api/v1/roles/{id}`, `PUT /api/v1/roles/{id}/permissions` | `roles`, `permissions`, `role_permissions` | Admin only for MVP | grouped permission toggles, matrix search, sticky review bar, smooth accordion transitions | risky permission combinations, invalid scope combinations |
| `UC-05 Create User` | Operational user is onboarded with valid access | `User Management` | create or edit drawer in page flow | `GET /api/v1/users`, `POST /api/v1/users`, `PUT /api/v1/users/{id}`, `POST /api/v1/users/{id}/credentials/reset` | `users`, `locations`, `roles`, `user_role_assignments` | governance users only, active location required | field formatting, unsaved warning, manager lookup UX, role preview | duplicate email, duplicate phone, duplicate employee ID, self-manager |
| `UC-06 Create Client` | Client is added under one location | `Client Directory` | create drawer in page flow | `GET /api/v1/clients`, `POST /api/v1/clients`, `PUT /api/v1/clients/{id}` | `clients`, `locations`, `users` | client belongs to one location in MVP | filter chips, duplicate hints, quick-create flow, concise section descriptions | wrong location, likely duplicate client, inactive status risk |
| `UC-07 Add Client Contact` | Requisition-ready contact is stored under client | `Client Detail` | `Contact Form Dialog` | `GET /api/v1/clients/{id}`, `GET /api/v1/clients/{id}/contacts`, `POST /api/v1/clients/{id}/contacts`, `PUT /api/v1/client-contacts/{id}` | `clients`, `client_contacts` | same-client mapping only | quick add contact modal, inline primary marker, secondary contact badge | contact linked to wrong client, missing required contact fields |
| `UC-08 Create Requisition` | Hiring requirement is captured cleanly | `Requisition Intake` | none | `POST /api/v1/requisitions`, `GET /api/v1/clients`, `GET /api/v1/clients/{id}/contacts` | `requisitions`, `clients`, `client_contacts`, `locations`, `users` | requisition inherits client location | dynamic form sections, progressive disclosure, sticky save bar, concise helper text | inactive client, wrong contact, missing skills, missing update availability |
| `UC-09 View Requisition Backlog` | Team can search and prioritize open requisitions | `Requisition List` | filters and quick actions inline | `GET /api/v1/requisitions` | `requisitions`, `clients`, `users`, `locations` | visibility by location and permission | sort by urgency, status chips, saved filters, compact row actions | unauthorized cross-location visibility |
| `UC-10 Assign Delivery Ownership` | Requisition reaches the right working team | `Requisition Detail` | `Reassign Owner Dialog` | `GET /api/v1/requisitions/{id}`, `GET /api/v1/requisitions/{id}/assignments`, `POST /api/v1/requisitions/{id}/assignments`, `POST /api/v1/requisitions/{id}/reassign` | `requisitions`, `requisition_assignments`, `users`, `locations` | edit rights limited, same-location assignment by default | assignment panel, impact preview, replacement search, motion-rich confirmation | wrong location assignee, active work reassignment review |
| `UC-11 Work Queue Review` | Delivery users know what to act on next | `Delivery Work Queue` | inline quick-action panels | `GET /api/v1/requisitions`, `GET /api/v1/dashboard/my-work` or queue endpoint | `requisitions`, `requisition_assignments`, `candidate_applications`, `users` | queue visibility follows assignment and role scope | drag-priority feel, urgency grouping, next-step labels, fast action bar | overdue work, SLA pressure, orphaned assignment |
| `UC-12 Create Candidate` | Recruiter captures a reusable candidate profile | `Candidate Profiles` | inline create and edit states | `GET /api/v1/candidates`, `POST /api/v1/candidates`, `GET /api/v1/candidates/{id}`, `PUT /api/v1/candidates/{id}` | `candidates`, `users`, `locations` | access controlled by permission and scoped visibility | staged form sections, source tags, social profile blocks, sticky action footer | incomplete profile, wrong owner mapping |
| `UC-13 Upload Resume` | Candidate data can be added from document workflow | `Resume Upload And Review` | none | `POST /api/v1/candidates/{id}/documents`, resume-parse service later, `GET /api/v1/candidates/{id}` | `candidate_documents`, `candidates` | create or edit candidate permission required | drag-and-drop upload, parse preview, field review animation, replace-before-save flow | invalid file type, parse mismatch, missing mandatory metadata |
| `UC-14 Detect Duplicate Candidate` | System prevents accidental duplicate records | `Candidate Profiles` | duplicate warning state leading to review flow | `POST /api/v1/candidates/duplicate-check` | `candidates`, `duplicate_review_cases` | duplicate detection is global, decision authority is restricted | compare-first warning, highlighted match cards, blocked final submit state | same candidate same requisition risk, fuzzy-match conflict |
| `UC-15 Resolve Duplicate` | Authorized user compares and decides safe outcome | `Candidate Duplicate Review` | none | `GET /api/v1/candidates/duplicate-cases`, `GET /api/v1/candidates/duplicate-cases/{id}`, `POST /api/v1/candidates/duplicate-cases/{id}/decision` | `duplicate_review_cases`, `candidates`, `audit_logs` | Admin plus selected senior roles only | side-by-side compare, conflict highlighting, guarded confirm actions | override or delete requires reason and audit |
| `UC-16 Link Candidate To Requisition` | Candidate becomes an application in active pipeline | `Candidate Profiles` | inline link action or future dialog | `POST /api/v1/candidates/{id}/applications`, `GET /api/v1/requisitions` | `candidate_applications`, `candidates`, `requisitions` | same-location operational rule, same candidate same requisition control | requisition picker, summary preview, duplicate warning banner | duplicate application for same requisition, requisition not active |
| `UC-17 Screen Candidate` | Recruiter confirms candidate fit before movement | `Candidate Screening` | none | `GET /api/v1/candidates/{id}`, `GET /api/v1/requisitions/{id}`, `PATCH /api/v1/candidates/{id}` or screening endpoint later | `candidates`, `requisitions`, `candidate_documents`, `candidate_applications` | screening access follows requisition and candidate scope | checklist UX, pass-fail markers, document-fit summary, smooth reveal per section | gap rule mismatch, missing documents, comp or notice mismatch |
| `UC-18 View Pipeline` | Recruiter and seniors track active applications | `Pipeline Board` | `Pipeline History Drawer` | `GET /api/v1/pipeline/board`, `GET /api/v1/pipeline/applications/{id}`, `GET /api/v1/pipeline/applications/{id}/history` | `candidate_applications`, `candidate_stage_history`, `requisitions`, `candidates` | upward visibility allowed, edit rights still restricted | draggable card preview, swimlane filters, aging badges, drawer detail | cross-location access block, stale application state |
| `UC-19 Move Pipeline Stage` | Candidate progresses through client-specific stages | `Pipeline Board` | `Stage Move Dialog` | `POST /api/v1/pipeline/applications/{id}/move-stage` | `candidate_applications`, `candidate_stage_history`, `requisitions`, `pipeline_templates` | valid stage only, move authority required | drag-and-drop preview with backend commit, stage confirmation dialog, contextual notes | invalid stage, backward move reason, reject or join consistency |
| `UC-20 Recruiter Progress Tracking` | Recruiter sees sourced and submitted pipeline progress | `My Work Dashboard` | inline widgets and quick filters | `GET /api/v1/dashboard/my-work`, `GET /api/v1/pipeline/board`, `GET /api/v1/candidates` | `candidate_applications`, `candidates`, `requisitions`, `users` | recruiter visibility without broader management edit rights | personal KPI cards, sourced-by-me filter, action reminders, lightweight animations | hidden work due to scope mismatch |
| `UC-21 Submit Daily Update` | Recruiter or operator logs execution progress | `Daily Updates Submission` | none | `GET /api/v1/daily-updates`, `POST /api/v1/daily-updates`, `GET /api/v1/requisitions` | `daily_updates`, `requisitions`, `users`, `locations` | linked requisition access required | autosave feel in JS only until submit, counters, blocker chips, concise writing prompts | duplicate same-day rule, closed requisition update block |
| `UC-22 Review Daily Updates` | Lead or manager reviews work progress and blockers | `Daily Updates Review` | inline expandable rows | `GET /api/v1/daily-updates`, `GET /api/v1/dashboard/pipeline-summary` | `daily_updates`, `requisitions`, `candidate_applications`, `users` | visibility-first review access | row expansion, trend grouping, blocker emphasis, review filters | no edit rights for read-only reviewers |
| `UC-23 Notifications Review` | User responds to alerts and reminders | `Notifications Center` | `Notification Detail Panel` | `GET /api/v1/notifications`, `PATCH /api/v1/notifications/{id}/read` | `notifications`, `users`, linked business entities | user sees only eligible notifications | optimistic read state, unread badge animation, detail slide-in panel | stale notification target, revoked access to linked record |
| `UC-24 Location Reporting` | Location-safe reporting supports operations oversight | `Location Dashboard` | none | `GET /api/v1/dashboard/location-summary`, `GET /api/v1/reports/location-performance` later | reporting views or derived data from `requisitions`, `candidate_applications`, `daily_updates`, `locations` | Admin and selected report roles only | chart toggles, comparison cards, date-range switch, export trigger shell | access outside allowed reporting scope |
| `UC-25 Company Reporting` | Combined company view supports leadership review | `Company Dashboard` | none | `GET /api/v1/dashboard/company-summary`, `GET /api/v1/reports/company-performance` later | reporting views or derived data from `requisitions`, `candidate_applications`, `daily_updates`, `locations` | visibility across locations without edit expansion | compare-mode widgets, ranking tables, trend transitions, compact annotations | company-wide visibility must not leak edit permissions |
| `UC-26 Access Denial` | Unauthorized users are blocked clearly | `Access Denied` | restricted-action state where needed | protected endpoints across modules | permission and business entities across modules | backend decision only, never UI-only hiding | redirect, context messaging, safe return navigation | permission removed while page is open |

## Recommended Build Sequence By Use Case

Build in this order so the MVP becomes testable early:

1. `UC-01 Login`
2. `UC-03 Create Location`
3. `UC-04 Create Role`
4. `UC-05 Create User`
5. `UC-06 Create Client`
6. `UC-07 Add Client Contact`
7. `UC-08 Create Requisition`
8. `UC-10 Assign Delivery Ownership`
9. `UC-12 Create Candidate`
10. `UC-13 Upload Resume`
11. `UC-14 Detect Duplicate Candidate`
12. `UC-16 Link Candidate To Requisition`
13. `UC-18 View Pipeline`
14. `UC-19 Move Pipeline Stage`
15. `UC-21 Submit Daily Update`
16. `UC-22 Review Daily Updates`
17. `UC-24 Location Reporting`
18. `UC-25 Company Reporting`

## Frontend UX Patterns That Should Be Reused Across Use Cases

These patterns are especially important for this MVP and should not be redesigned page by page:

- drag-and-drop upload for resume handling
- drag-preview plus confirm-dialog flow for pipeline stage changes
- sticky form action bar for long create and edit flows
- side-by-side comparison layout for duplicate resolution
- compact detail drawer for history and quick review
- saved-filter style management tables
- concise section helper text capped at one or two lines
- subtle motion for open, close, submit, success, and emphasis states

## Completion Rule

A use case is not complete just because the page exists.

It is complete only when all of the following are true:

- the correct MVP page or container exists
- the mapped API exists and is connected
- the data entities support the flow cleanly
- permission and location rules are enforced by backend
- the user can complete the normal flow
- the main exception path is handled intentionally

If one of these is missing, the use case is still in progress.
