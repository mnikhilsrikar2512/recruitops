# MVP Use Case Page Execution Map

## Purpose

This document converts MVP use cases into page-by-page execution guidance.

It is the practical handoff file for:

- frontend page creation
- backend endpoint wiring
- JS-managed interaction planning
- validation implementation
- QA scenario coverage

It should be used with:

- `docs/system/MVP_USE_CASE_ACTOR_MATRIX.md`
- `docs/system/BUILD_PACK_FRONTEND_PAGE_MODULE_PLAN.md`
- `docs/system/BUILD_PACK_SCREEN_FIELD_SPEC.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md`

## Reading Rule

Each row below explains:

- which use case is being supported
- which exact page or UI container handles it
- which major page sections are required
- which API calls are needed
- which interactions can stay in frontend JS
- which validations must be enforced

## UI Container Types Used Here

- `Page`
  A full route-level page
- `Dialog`
  A modal used for short structured actions
- `Drawer`
  A side panel used for detail, edit, or history actions
- `Inline State`
  A tab, section, table state, or form state inside an existing page

## JS Versus API Rule

Use frontend JS for:

- form state
- inline filters and sort behavior
- client-side field formatting
- controlled dialogs, drawers, and view switching
- draft unsaved warnings
- optimistic UI only where business safety is not affected

Use APIs for:

- authentication
- permission checks
- location scope checks
- duplicate checks
- create, edit, delete, deactivate, reassign, and status changes
- pipeline movement
- daily update persistence
- dashboards and reporting metrics

## Page Execution Matrix

| Use Case | Main Page Or Container | Type | Required Sections Or Components | Primary APIs | JS-Handled Behavior | Required Validations |
| --- | --- | --- | --- | --- | --- | --- |
| `UC-01 User Login` | `Login` | `Page` | brand panel, login form, forgot password link, auth error state | `POST /api/v1/auth/login` | password show or hide, submit loading state, enter-to-submit, redirect after success | valid email format, required password, inactive user blocked by API |
| `UC-02 View Current Access Context` | `My Profile`, `My Access Summary` | `Page` or `Inline State` | user card, role card, location card, permission summary, session info | `GET /api/v1/auth/me`, `GET /api/v1/permissions/me` | collapse or expand permission groups, copy access summary, local tab switch | self-only access unless elevated permission exists |
| `UC-03 Create Custom Role` | `Role Management`, `Create Role Drawer`, `Edit Role Drawer` | `Page`, `Drawer` | role table, status chips, role form, module matrix, page matrix, action matrix, scope matrix | `GET /api/v1/roles`, `POST /api/v1/roles`, `GET /api/v1/roles/{id}`, `PUT /api/v1/roles/{id}`, `PUT /api/v1/roles/{id}/permissions` | permission toggles, grouped checkboxes, unsaved-change warning, matrix search | role name required, at least one valid permission set, sensitive combinations flagged |
| `UC-04 Assign Role To User` | `User Management`, `Create User Drawer`, `Edit User Drawer` | `Page`, `Drawer` | user table, identity form, contact form, role assignment, location assignment, manager assignment | `POST /api/v1/users`, `PUT /api/v1/users/{id}` | dependent dropdown reset, manager autocomplete, role-to-scope preview | active location required, role required, invalid self-manager blocked |
| `UC-05 Create Location` | `Location Management`, `Create Location Dialog`, `Edit Location Drawer` | `Page`, `Dialog`, `Drawer` | location table, location form, status control, location head assignment | `GET /api/v1/locations`, `POST /api/v1/locations`, `GET /api/v1/locations/{id}`, `PUT /api/v1/locations/{id}` | filter by status, inline search, confirm deactivate | unique code, name required, status required |
| `UC-06 Create User` | `User Management`, `Create User Drawer` | `Page`, `Drawer` | user list filters, create user form, invite status, access preview | `GET /api/v1/users`, `POST /api/v1/users`, `GET /api/v1/users/{id}` | phone formatting, employee ID formatting, local dirty-state warning | duplicate email, phone, employee ID rules from company config |
| `UC-07 Deactivate User With Active Work` | `User Detail`, `Deactivate User Dialog`, `Reassignment Review Drawer` | `Page`, `Dialog`, `Drawer` | user summary, linked active work summary, impact warning, reassignment actions, audit notes | `GET /api/v1/users/{id}`, `POST /api/v1/users/{id}/deactivate`, supporting list APIs for linked work | impact counts preview, select replacement user, confirm modal flow | active work review mandatory, cannot silently orphan linked work |
| `UC-08 Create Client Under A Location` | `Client Directory`, `Create Client Drawer`, `Edit Client Drawer` | `Page`, `Drawer` | client table, filter bar, client form, location ownership, source owner section | `GET /api/v1/clients`, `POST /api/v1/clients`, `GET /api/v1/clients/{id}`, `PUT /api/v1/clients/{id}` | local duplicate hint on typed name or code, chip filters, inline status badges | one location only, duplicate warning, required ownership fields |
| `UC-09 Add Client Contact` | `Client Detail`, `Contact Form Dialog` | `Page`, `Dialog` | client summary, contacts table, contact form, primary and secondary markers | `GET /api/v1/clients/{client_id}/contacts`, `POST /api/v1/clients/{client_id}/contacts`, `PUT /api/v1/client-contacts/{id}` | inline contact search, primary toggle behavior, contact row expansion | contact must belong to selected client, distinguish primary and secondary roles |
| `UC-10 Create Requisition` | `Requisition Intake` | `Page` | requisition header, client selection, contact selection, skill section, ownership section, update availability section, pipeline template section | `POST /api/v1/requisitions`, `GET /api/v1/clients`, `GET /api/v1/clients/{id}/contacts`, `GET /api/v1/pipeline-templates` if separate | dynamic contact loading by client, conditional sections, draft autosave only if enabled later | required fields, client must be active, location inherited from client, invalid contact blocked |
| `UC-11 Update Requisition Status` | `Requisition Detail`, `Status Update Dialog`, `Status History Drawer` | `Page`, `Dialog`, `Drawer` | requisition summary, status chip, status history, reason field when required | `GET /api/v1/requisitions/{id}`, `PATCH /api/v1/requisitions/{id}/status` | status option enable or disable hints, confirm dialog, local success update | valid transition only, mandatory reason for configured statuses |
| `UC-12 Assign Requisition To Delivery Team` | `Requisition Detail`, `Assignment Panel`, `Assignment History Drawer`, `Reassign Owner Dialog` | `Page`, `Inline State`, `Drawer`, `Dialog` | active assignees table, add assignee action, contributor list, owner summary, history timeline | `GET /api/v1/requisitions/{id}/assignments`, `POST /api/v1/requisitions/{id}/assignments`, `DELETE /api/v1/requisition-assignments/{id}`, `POST /api/v1/requisitions/{id}/reassign` | user picker search, workload preview if available, inline remove confirmation | same-location rule, live-work reassignment confirmation, history preserved |
| `UC-13 Create Candidate Profile` | `Candidate Profiles`, `Candidate Create Inline State`, `Candidate Edit Inline State` | `Page`, `Inline State` | candidate table, candidate form, identity section, contact section, source section, skills section, ownership section, social profiles section | `GET /api/v1/candidates`, `POST /api/v1/candidates`, `GET /api/v1/candidates/{id}`, `PUT /api/v1/candidates/{id}` | local format normalization, section stepper, unsaved changes warning | required identity fields, company duplicate rules, no finalization with incomplete mandatory data |
| `UC-14 Upload Resume Or Candidate Document` | `Resume Upload And Review` | `Page` | upload zone, parsed field review, document metadata, confirm attach action | `POST /api/v1/candidates/{id}/documents`, `GET /api/v1/candidates/{id}` | drag and drop, file preview, replace before submit, progress state | allowed file type and size, metadata required by company if configured |
| `UC-15 Detect Candidate Duplicate` | `Candidate Profiles`, `Duplicate Warning Modal` | `Page`, `Dialog` | duplicate warning banner, probable matches table, compare action, hold finalization state | `POST /api/v1/candidates/duplicate-check` | pre-submit duplicate trigger, match highlighting, local suspend submit state | compare-first mandatory before override or discard decision |
| `UC-16 Compare And Resolve Duplicate` | `Candidate Duplicate Review` | `Page` | side-by-side comparison, field conflict markers, audit note, decision footer, protected actions | `GET /api/v1/candidates/duplicate-cases`, `GET /api/v1/candidates/duplicate-cases/{id}`, `POST /api/v1/candidates/duplicate-cases/{id}/decision` | expand conflict fields, preview selected winning values, local action confirmation | Admin or selected senior role only, audit reason required, destructive cleanup controlled |
| `UC-17 Link Candidate To Requisition` | `Candidate Profiles`, `Link To Requisition Dialog` | `Page`, `Dialog` | requisition search, requisition summary, duplicate submission warning, confirm link action | `POST /api/v1/candidates/{id}/applications`, `GET /api/v1/requisitions` | requisition search, filter by active only, local summary preview | same candidate for same requisition blocked or warned per rule |
| `UC-18 View Candidate Pipeline` | `Pipeline Board`, `Application Detail Drawer` | `Page`, `Drawer` | kanban board or staged list, filters, requisition selector, aging badges, application drawer | `GET /api/v1/pipeline/board`, `GET /api/v1/pipeline/applications/{id}` | board drag preview without commit, local filters, saved column visibility | data visibility by permission and scope only |
| `UC-19 Move Candidate To Next Stage` | `Pipeline Board`, `Stage Move Dialog` | `Page`, `Dialog` | stage selector, note field, rejection reason field, joining date field, stage impact preview | `POST /api/v1/pipeline/applications/{id}/move-stage` | disable invalid target stages, conditional field rendering, submit spinner | stage must belong to template, backward move reason if configured, rejection reason and joining date rules |
| `UC-20 View Pipeline History` | `Pipeline History Drawer Or Panel` | `Drawer` | timeline, actor name, date and time, stage notes, stage badges | `GET /api/v1/pipeline/applications/{id}/history` | local timeline grouping, expand notes, quick jump from current card | append-only history expectation |
| `UC-21 Track Recruiter-Owned Progress` | `My Work Dashboard`, `My Pipeline`, `Candidate Profiles` | `Page`, `Inline State` | sourced candidates widget, submitted candidates widget, pending action list, quick filters | `GET /api/v1/dashboard/my-work`, `GET /api/v1/pipeline/board`, `GET /api/v1/candidates` | local scope toggles like sourced by me or submitted by me, saved filter state | recruiter must see owned progress without broader edit rights |
| `UC-22 Submit Daily Update` | `Daily Updates Submission` | `Page` | requisition selector, activity counts, blockers, notes, next steps, submit history strip | `GET /api/v1/daily-updates`, `POST /api/v1/daily-updates`, `GET /api/v1/requisitions` | draft retention before submit, character count, date defaulting, inline confirmation | linked requisition required, duplicate same-day behavior follows company rule |
| `UC-23 Review Team Progress` | `Daily Updates Review`, `Team Dashboard`, `Requisition Progress View` | `Page`, `Inline State` | summary cards, updates table, delayed work flags, pipeline counts, blocker highlight section | `GET /api/v1/dashboard/pipeline-summary`, `GET /api/v1/dashboard/my-work`, `GET /api/v1/daily-updates` | filter by user, location, requisition, status; expand row panels | visibility-only roles should not receive hidden edit actions |
| `UC-24 View Location Performance` | `Location Dashboard` | `Page` | KPI strip, pipeline volume charts, closure stats, update compliance, location comparison cards | `GET /api/v1/dashboard/location-summary`, `GET /api/v1/reports/location-performance` | date-range switch, chart toggles, export trigger UI if added later | location access must stay within granted reporting scope |
| `UC-25 View Combined Company Reporting` | `Company Dashboard` | `Page` | overall KPI strip, multi-location comparison, trend charts, top risk tables | `GET /api/v1/dashboard/company-summary`, `GET /api/v1/reports/company-performance` | cross-filter charts, compare locations, export or print preparation | company-wide visibility must not imply edit authority |
| `UC-26 Reassign Ownership On Active Work` | `Reassignment Review`, `User Move Review`, `Ownership Change Dialog` | `Page`, `Dialog` | impacted records table, before and after owner summary, approval note, confirmation state | `POST /api/v1/requisitions/{id}/reassign`, `POST /api/v1/candidates/{id}/reassign`, `POST /api/v1/users/{id}/move` | impact preview, replacement search, warning banners, final double-confirm | manual review required for active work, audit capture mandatory |
| `UC-27 Handle Access Denial` | `Access Denied`, `Restricted Action Modal` | `Page`, `Dialog` | denial message, context hint, back navigation, request-help action if enabled later | protected API responses across modules | redirect from guard, modal fallback for in-page denied action | server-side denial only, no UI-only protection |
| `UC-28 Audit Sensitive Changes` | `Audit Log`, `Audit Detail Drawer`, `History Tabs On Detail Pages` | `Page`, `Drawer`, `Inline State` | audit table, filters, entity link, actor info, before and after summary, timestamp | audit-enabled endpoints and `GET /api/v1/audit-logs` later if exposed separately | filter state persistence, compare view expand or collapse | sensitive actions must be traceable with actor, time, and reason where required |

## Page Build Order Recommendation

Build these pages first because they unlock the MVP journey:

1. `Login`
2. `Location Management`
3. `Role Management`
4. `User Management`
5. `Client Directory`
6. `Client Detail`
7. `Requisition List`
8. `Requisition Intake`
9. `Requisition Detail`
10. `Candidate Profiles`
11. `Candidate Duplicate Review`
12. `Pipeline Board`
13. `Daily Updates Submission`
14. `My Work Dashboard`
15. `Location Dashboard`
16. `Company Dashboard`

Build these support containers alongside them:

1. `Create Role Drawer`
2. `Create User Drawer`
3. `Create Client Drawer`
4. `Contact Form Dialog`
5. `Status Update Dialog`
6. `Assignment History Drawer`
7. `Reassign Owner Dialog`
8. `Duplicate Warning Modal`
9. `Link To Requisition Dialog`
10. `Stage Move Dialog`
11. `Pipeline History Drawer Or Panel`
12. `Deactivate User Dialog`

## Shared Component Requirements

These shared components should exist before page implementation moves too far:

- app shell with sidebar and top bar
- management table layout
- detail header with action slots
- filter bar with chips and saved-state support
- reusable form section block
- dialog shell
- drawer shell
- status badge system
- audit timeline component
- empty state and error state components
- permission-aware action button wrapper

## JS-Handled Behaviors That Should Stay Consistent

Across pages, frontend JS should consistently handle:

- route guard redirection
- unsaved form warning
- dialog and drawer open state
- inline table filters and sorting
- local pagination state
- staged form sections
- field masking and formatting
- conditional field rendering
- confirmation prompts before risky actions

These should not replace backend enforcement.

## Backend-Enforced Rules That Must Never Depend On JS Alone

- role permission checks
- location visibility rules
- duplicate decision authority
- client and requisition ownership rules
- candidate-to-requisition duplicate blocking
- pipeline stage validity
- daily update submission ownership checks
- reassignment approval rules
- reporting scope restrictions

## QA Execution Guidance

For each mapped page, QA should verify:

- the page loads for the correct actor
- the page is hidden or blocked for the wrong actor
- every primary action calls the expected API
- JS-only behavior improves UX but does not create security gaps
- validation messages appear clearly
- exception paths route to the correct dialog, drawer, or page

## Final Build Rule

If a page exists without:

- a mapped use case
- a defined API contract
- known JS-managed behavior
- explicit validation rules

then that page is not ready for implementation.
