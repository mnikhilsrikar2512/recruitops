# MVP Use Case Actor Matrix

## Purpose

This document converts MVP use cases into a delivery-ready actor matrix.

It is meant to help:

- frontend teams know which pages each actor needs
- backend teams know which APIs support each actor action
- QA teams know which permission and exception paths to verify
- product teams confirm that business use is covered without hard-coding roles

This document should be read together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/MVP_USE_CASE_IMPLEMENTATION_MATRIX.md`
- `docs/system/BUILD_PACK_PERMISSION_ACTION_MATRIX.md`

## Important Product Rule

- `Admin` is the only fixed product role
- all other actors below are operating-role examples
- Admin can rename roles, combine responsibilities, or split responsibilities by company
- use cases stay stable even if business titles vary by company

## How To Read This Matrix

Each row answers:

- which actor usually performs the action
- which module owns the action
- which page or screen must exist
- which API group must support it
- which permission style is normally needed
- which exception or risk must be handled

## Actor Key Used In This Document

- `Admin`
  Fixed product governance role
- `Permitted Business User`
  A configurable role allowed to manage client-side or intake-side work
- `Permitted Senior User`
  A configurable lead, manager, or controller role with wider operational authority
- `Recruiter Or Sourcing User`
  A configurable execution user who creates candidates and works live pipeline
- `Permitted Reporting User`
  A configurable read-heavy or governance-heavy reporting role
- `Any Authenticated User`
  Any active logged-in user with access to the product

## MVP Actor Matrix

| Use Case | Primary Actor | Supporting Actors | Module | Main Pages Or Screens | API Surface | Typical Permission Need | Key Exception Or Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `UC-01 User Login` | `Any Authenticated User` | `Admin` for resets | Authentication And Session Control | Login, Logout, Session Expiry, Password Reset | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Public login, authenticated session read | Invalid credentials, inactive user, expired session |
| `UC-02 View Current Access Context` | `Any Authenticated User` | None | Authentication And Access | My Profile, My Access Summary | `GET /auth/me`, `GET /permissions/me` | Self-access read | Permission payload mismatch, stale role mapping |
| `UC-03 Create Custom Role` | `Admin` | None | Roles, Permissions, And Access Configuration | Role List, Create Role, Edit Role, Permission Matrix | `GET /roles`, `POST /roles`, `GET /roles/{id}`, `PUT /roles/{id}`, `PUT /roles/{id}/permissions` | Role configuration create and edit | Overly broad permissions, breaking live access unexpectedly |
| `UC-04 Assign Role To User` | `Admin` | None | Roles, Permissions, And User Administration | User Create, User Edit, Access Assignment Panel | `POST /users`, `PUT /users/{id}` | User create and access assignment | User mapped to inactive location or invalid role |
| `UC-05 Create Location` | `Admin` | None | Location Administration | Location List, Create Location, Edit Location | `GET /locations`, `POST /locations`, `GET /locations/{id}`, `PUT /locations/{id}` | Location governance create and edit | Duplicate or deactivated location used operationally |
| `UC-06 Create User` | `Admin` | None | User Administration | User List, Create User, User Detail, User Edit | `POST /users`, `GET /users`, `GET /users/{id}` | User create and read | Duplicate email, phone, employee ID, self-manager mapping |
| `UC-07 Deactivate User With Active Work` | `Admin` | `Permitted Senior User` if company allows | User Administration | User Detail, Deactivate Review, Reassignment Review | `POST /users/{id}/deactivate`, `GET /requisitions`, `GET /candidates`, `GET /daily-updates` | User deactivate and work review | Live work orphaning, incomplete reassignment |
| `UC-08 Create Client Under A Location` | `Permitted Business User` | `Admin` | Client Directory | Client List, Create Client, Client Detail, Edit Client | `GET /clients`, `POST /clients`, `GET /clients/{id}`, `PUT /clients/{id}` | Client create and edit within allowed scope | Wrong location mapping, duplicate client, cross-location access |
| `UC-09 Add Client Contact` | `Permitted Business User` | `Admin` | Client Directory | Client Detail, Add Contact, Edit Contact | `GET /clients/{client_id}/contacts`, `POST /clients/{client_id}/contacts`, `PUT /client-contacts/{id}` | Client contact create and edit | Contact linked to wrong client |
| `UC-10 Create Requisition` | `Permitted Business User` | `Permitted Senior User`, `Admin` | Requisition Management | Requisition List, Create Requisition, Requisition Detail, Requisition Edit | `GET /requisitions`, `POST /requisitions`, `GET /requisitions/{id}`, `PUT /requisitions/{id}` | Requisition create and edit | Inactive client, wrong contact, wrong location inheritance |
| `UC-11 Update Requisition Status` | `Permitted Business User` | `Permitted Senior User`, `Admin` | Requisition Management | Requisition Detail, Status Update Drawer, Status History | `PATCH /requisitions/{id}/status` | Requisition status update | Invalid status move, reopening without reason |
| `UC-12 Assign Requisition To Delivery Team` | `Permitted Senior User` | `Admin`, `Permitted Business User` with company approval | Work Allocation And Assignment | Requisition Detail, Assignment Panel, Assignment History | `GET /requisitions/{id}/assignments`, `POST /requisitions/{id}/assignments`, `DELETE /requisition-assignments/{id}`, `POST /requisitions/{id}/reassign` | Assignment create, remove, reassign | Wrong-location assignee, reassignment during active work |
| `UC-13 Create Candidate Profile` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Candidate Management | Candidate List, Create Candidate, Candidate Detail, Edit Candidate | `GET /candidates`, `POST /candidates`, `GET /candidates/{id}`, `PUT /candidates/{id}` | Candidate create and edit | Duplicate identity, incomplete profile finalized |
| `UC-14 Upload Resume Or Candidate Document` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Candidate Management | Candidate Detail, Document Upload Modal, Document List | `POST /candidates/{id}/documents`, `GET /candidates/{id}` | Candidate document upload | Invalid file metadata, missing uploader traceability |
| `UC-15 Detect Candidate Duplicate` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Candidate Management | Candidate Create, Candidate Edit, Duplicate Warning Modal | `POST /candidates/duplicate-check` | Candidate create or finalize with duplicate check | Same person entered twice, same candidate for same requisition |
| `UC-16 Compare And Resolve Duplicate` | `Admin` | `Permitted Senior User` if explicitly allowed | Candidate Governance | Duplicate Review Queue, Compare Candidate View, Resolution Action Modal | `GET /candidates/duplicate-cases`, `GET /candidates/duplicate-cases/{id}`, `POST /candidates/duplicate-cases/{id}/decision` | Duplicate review and override authority | Wrong merge, silent delete, missing audit history |
| `UC-17 Link Candidate To Requisition` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Candidate Management And Pipeline | Candidate Detail, Link To Requisition Modal, Requisition Candidate View | `POST /candidates/{id}/applications`, `GET /requisitions/{id}` | Candidate-to-requisition link create | Same candidate linked twice, wrong requisition selection |
| `UC-18 View Candidate Pipeline` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Permitted Business User`, `Permitted Reporting User`, `Admin` | Pipeline Tracking | Pipeline Board, Pipeline List, Application Detail | `GET /pipeline/board`, `GET /pipeline/applications/{id}` | Pipeline read with scope control | Visibility beyond scope, edit rights confused with read rights |
| `UC-19 Move Candidate To Next Stage` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Pipeline Tracking | Pipeline Board, Move Stage Modal, Application Detail | `POST /pipeline/applications/{id}/move-stage` | Pipeline stage update | Invalid stage, backward move without reason, joined candidate moved again |
| `UC-20 View Pipeline History` | `Permitted Senior User` | `Recruiter Or Sourcing User`, `Permitted Business User`, `Admin` | Pipeline Tracking | Application Detail, Stage History Timeline | `GET /pipeline/applications/{id}/history` | Pipeline history read | Missing timeline accuracy, hidden critical movement |
| `UC-21 Track Recruiter-Owned Progress` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Pipeline And Personal Work Tracking | My Pipeline, My Candidates, My Work Dashboard | `GET /pipeline/board`, `GET /candidates`, `GET /dashboard/my-work` | Personal pipeline and work summary read | Recruiter cannot see sourced candidate progress after submission |
| `UC-22 Submit Daily Update` | `Recruiter Or Sourcing User` | `Permitted Senior User`, `Admin` | Daily Updates And Execution Tracking | Daily Update List, Submit Daily Update, Daily Update Detail | `GET /daily-updates`, `POST /daily-updates`, `GET /daily-updates/{id}` | Daily update create and self-read | Multiple same-day updates, unlinked requisition update |
| `UC-23 Review Team Progress` | `Permitted Senior User` | `Permitted Business User`, `Permitted Reporting User`, `Admin` | Dashboards, Reports, And Governance | Team Dashboard, Requisition Progress View, Update Review View | `GET /dashboard/pipeline-summary`, `GET /dashboard/my-work`, `GET /daily-updates` | Team summary read | Visibility without proper scope, managers editing instead of reviewing |
| `UC-24 View Location Performance` | `Permitted Reporting User` | `Admin`, `Permitted Senior User` if company allows | Dashboards, Reports, And Governance | Location Dashboard, Location Summary Report | `GET /dashboard/location-summary`, `GET /reports/location-performance` | Location report read | Unauthorized cross-location reporting |
| `UC-25 View Combined Company Reporting` | `Admin` | `Permitted Reporting User` if allowed | Dashboards, Reports, And Governance | Company Dashboard, Combined Performance Report | `GET /dashboard/company-summary`, `GET /reports/company-performance` | Company-wide reporting read | Combined visibility accidentally enabling operational edits |
| `UC-26 Reassign Ownership On Active Work` | `Permitted Senior User` | `Admin` | Governance And Work Continuity | Reassignment Review, User Move Review, Requisition Ownership Change | `POST /requisitions/{id}/reassign`, `POST /candidates/{id}/reassign`, `POST /users/{id}/move` | Reassignment and controlled ownership change | Active work continuity breaks if review is skipped |
| `UC-27 Handle Access Denial` | `Any Authenticated User` | `Admin` for audit follow-up | Access Control | Access Denied State, Restricted Modal, Audit Trail View | All protected endpoints | Server-side permission and scope enforcement | UI-only restriction, unclear denial reason, missing logs |
| `UC-28 Audit Sensitive Changes` | `Admin` | `Permitted Reporting User` or auditors if company allows | Governance And Audit | Audit Log List, Audit Detail, Filtered Change History | Audit-enabled create, update, override, status, and reassignment endpoints | Audit read and governance oversight | Missing evidence for critical actions |

## Actor-Wise Working View

### Admin

Admin must be able to:

- manage locations
- manage users
- create and edit custom roles
- assign permissions, pages, modules, and scope
- review duplicate resolution cases if the company wants strict control
- review company-wide dashboards and governance trails
- intervene in reassignment and deactivation workflows

Admin is not required to perform daily recruitment work, but Admin must be able to govern and recover any blocked business flow.

### Permitted Business User

This actor usually covers intake-side or client-side operations.

Typical responsibilities:

- create and maintain clients
- manage client contacts
- create requisitions
- update requisition status
- review pipeline progress where visibility is allowed

This actor should not automatically gain unrestricted edit access to candidate records just because they can see progress.

### Permitted Senior User

This actor usually covers operational control.

Typical responsibilities:

- assign requisitions
- reassign live work
- review team progress
- monitor candidate pipeline
- handle execution continuity when a user moves or becomes inactive

This actor often needs broader visibility than recruiters, but still should remain inside configured scope rules.

### Recruiter Or Sourcing User

This actor usually covers execution work.

Typical responsibilities:

- create candidates
- maintain candidate records before finalization
- run duplicate checks
- link candidates to requisitions
- move candidates through pipeline stages where allowed
- submit daily updates
- track sourced candidate progress

This actor must always be able to see the pipeline progress of candidates they sourced or submitted, even if broader leadership users also see the same pipeline.

### Permitted Reporting User

This actor is mainly read-focused.

Typical responsibilities:

- review location dashboards
- review combined reporting if granted
- inspect productivity and execution summaries
- support governance and reporting needs without changing operations

This actor should usually receive visibility without operational edit authority.

## Role Assignment Clarification

Because the system is configurable, the product should not assume:

- one company uses `BDM`
- another company uses `Account Manager`
- another company uses `Lead Recruiter`

Instead, Admin maps those real-world titles onto permissions and scope.

Example configuration:

- Company A may give `Account Manager` client and requisition visibility but no candidate edit rights
- Company B may allow `Lead Recruiter` to assign work and move late-stage pipeline
- Company C may create a `Delivery Manager` role with the same system permissions as a `Lead Recruiter`

The stable product rule is:

- use cases are fixed
- permissions are configurable
- titles are business-specific

## Recommended QA Focus From This Matrix

For each use case, QA should verify:

- correct actor can access the intended page
- wrong actor cannot access the page or action
- correct API permission passes
- wrong API permission fails
- location scope is enforced correctly
- upward visibility does not automatically create edit rights
- exceptions are blocked, warned, or routed for review as expected

## Minimum End-To-End Actor Journey

The MVP is operational only if this journey works fully:

1. `Admin` creates location, role, and user
2. `Permitted Business User` creates client and requisition
3. `Permitted Senior User` assigns the requisition
4. `Recruiter Or Sourcing User` creates candidate and clears duplicate check
5. `Recruiter Or Sourcing User` links candidate to requisition
6. `Recruiter Or Sourcing User` and seniors track pipeline progress
7. `Recruiter Or Sourcing User` submits daily update
8. `Permitted Senior User` reviews team execution
9. `Permitted Reporting User` or `Admin` reviews location and company reporting

If any of these actor journeys is missing page, API, permission, or exception handling support, the MVP is not fully execution-ready.
