# MVP Component And State Contract

## Purpose

This document defines the reusable component structure and required UI states for the MVP frontend.

It is the build contract for:

- page composition
- reusable section planning
- role-gated UI behavior
- loading, empty, error, restricted, and success states
- consistent UX across modules

Use this together with:

- `docs/system/BUILD_PACK_FRONTEND_ARCHITECTURE.md`
- `docs/system/BUILD_PACK_FRONTEND_PAGE_MODULE_PLAN.md`
- `docs/system/MVP_USE_CASE_PAGE_EXECUTION_MAP.md`
- `docs/system/MVP_PAGE_API_PAYLOAD_MAP.md`

## Core Rule

Every MVP page must be built from reusable layout and component blocks wherever possible.

A page is not considered complete unless it defines:

- layout wrapper
- core sections
- role-gated actions
- loading state
- empty state if applicable
- error state
- restricted state if access can be denied
- success or completion state where relevant

## Shared Layout Contracts

### `AuthLayout`

Use for:

- `Login`

Must provide:

- centered content container
- brand area
- form area
- error banner slot

### `AppShellLayout`

Use for most authenticated pages.

Must provide:

- sidebar navigation
- top bar
- notification entry point
- page title zone
- breadcrumb zone
- page action zone

### `ManagementLayout`

Use for:

- `Location Management`
- `User Management`
- `Role Management`
- `Client Directory`
- `Requisition List`
- `Candidate Profiles`

Must provide:

- filter bar zone
- table or grid content zone
- bulk or page action zone
- drawer anchor area
- dialog trigger area

### `DetailLayout`

Use for:

- `Client Detail`
- `Requisition Detail`
- `Candidate Duplicate Review`

Must provide:

- detail header
- summary card zone
- secondary information zone
- related records zone
- right-side action area if the design uses one

### `DashboardLayout`

Use for:

- `Role Dashboard`
- `My Work Dashboard`
- `Location Dashboard`
- `Company Dashboard`

Must provide:

- KPI strip zone
- widget grid zone
- alert or risk strip
- quick action area if applicable

## Shared Reusable Components

These components should be available before most page work starts:

- `PageHeader`
- `Breadcrumbs`
- `ActionBar`
- `FilterBar`
- `SearchInput`
- `StatusBadge`
- `EmptyState`
- `ErrorState`
- `RestrictedState`
- `LoadingSkeleton`
- `TableShell`
- `DetailCard`
- `KpiCard`
- `FormSection`
- `FormGrid`
- `DialogShell`
- `DrawerShell`
- `ConfirmationDialog`
- `Timeline`
- `InlineBanner`
- `PermissionAwareAction`

## Shared State Contracts

Every page should implement only the states that make sense for its behavior, but these definitions should stay consistent:

### `Loading`

Use when page data or action response is in progress.

Must show:

- skeleton or spinner
- disabled destructive or submit actions
- stable page frame if possible

### `Empty`

Use when a list, table, board, or dashboard widget has no records.

Must show:

- clear explanation
- next useful action if permitted
- no fake placeholder data

### `Error`

Use when page data fails to load or an action fails unexpectedly.

Must show:

- plain-language problem message
- retry action if safe
- preserved form data where possible

### `Restricted`

Use when a user lacks permission or scope.

Must show:

- access denied or restricted message
- safe way back
- no hidden action escape route

### `Success`

Use after major writes like create, update, submit, assign, resolve, or move stage.

May show:

- toast
- inline confirmation banner
- updated card or row state
- redirect to detail page when that is the defined flow

### `Review Required`

Use when business logic blocks direct completion and requires explicit review.

Examples:

- duplicate candidate found
- active work reassignment needed
- deactivation with linked ownership

Must show:

- why the action cannot continue normally
- what review path the user must enter
- protected decision action if the user is authorized

## Role-Gated Action Rule

Frontend may hide or disable actions for clarity, but backend remains the real authority.

Frontend should still model these action states:

- `visible and enabled`
- `visible but disabled with reason`
- `hidden because not relevant to the page role experience`

Use disabled-with-reason for important actions a user may expect, such as:

- `Move Stage`
- `Resolve Duplicate`
- `Deactivate User`
- `View Company Dashboard`

## Page-Level Contracts

## 1. `Login`

### Layout

- `AuthLayout`

### Core Components

- brand panel
- login form
- forgot password link
- error banner

### Role-Gated Actions

- none before login

### Required States

- `Loading`
  during sign-in
- `Error`
  invalid credentials or auth failure
- `Success`
  redirect to authenticated landing page

## 2. `Location Management`

### Layout

- `ManagementLayout`

### Core Components

- page header
- filter bar
- location table
- create location dialog
- edit location drawer
- status badge

### Role-Gated Actions

- `Create Location`
  Admin only
- `Edit Location`
  Admin only
- `Activate Or Deactivate`
  Admin only

### Required States

- `Loading`
  table load and save actions
- `Empty`
  no locations yet
- `Error`
  list fetch or save failure
- `Restricted`
  non-admin user access
- `Success`
  create or update completed

## 3. `User Management`

### Layout

- `ManagementLayout`

### Core Components

- page header
- filter bar
- users table
- create user drawer
- edit user drawer
- reset credential action
- access preview panel

### Role-Gated Actions

- `Create User`
  Admin only
- `Edit User`
  Admin only
- `Deactivate User`
  Admin or configured senior role if allowed later

### Required States

- `Loading`
- `Empty`
  no users for filter result
- `Error`
- `Restricted`
- `Success`
  create, update, reset, deactivate
- `Review Required`
  deactivation with active work

## 4. `Role Management`

### Layout

- `ManagementLayout`

### Core Components

- role list table
- create role drawer
- edit role drawer
- permission matrix
- scope matrix
- assigned users count

### Role-Gated Actions

- all create and edit actions
  Admin only

### Required States

- `Loading`
- `Empty`
- `Error`
- `Restricted`
- `Success`
  role saved or permissions saved

## 5. `Client Directory`

### Layout

- `ManagementLayout`

### Core Components

- page header
- filter bar
- client table
- create client drawer
- edit client drawer
- status badge

### Role-Gated Actions

- `Create Client`
  permitted business users and Admin
- `Edit Client`
  permitted business users and Admin

### Required States

- `Loading`
- `Empty`
  no clients
- `Error`
- `Restricted`
  wrong permission or location scope
- `Success`
  client created or updated

## 6. `Client Detail`

### Layout

- `DetailLayout`

### Core Components

- client summary card
- contacts table
- linked requisitions section
- contact form dialog
- detail header actions

### Role-Gated Actions

- `Add Contact`
  permitted business users and Admin
- `Edit Contact`
  permitted business users and Admin

### Required States

- `Loading`
- `Empty`
  no contacts or no linked requisitions
- `Error`
- `Restricted`
- `Success`
  contact added or updated

## 7. `Requisition List`

### Layout

- `ManagementLayout`

### Core Components

- requisition table
- filter bar
- quick status chips
- create requisition action

### Role-Gated Actions

- `Create Requisition`
  permitted business users and Admin

### Required States

- `Loading`
- `Empty`
- `Error`
- `Restricted`

## 8. `Requisition Intake`

### Layout

- `DetailLayout` or dedicated form layout

### Core Components

- requisition header section
- client and contact section
- requirement details section
- skills section
- owner section
- update availability section
- pipeline template section
- sticky action bar

### Role-Gated Actions

- `Create`
  permitted business users and Admin
- `Save Changes`
  permitted business users and Admin

### Required States

- `Loading`
  form bootstrap or save
- `Error`
  form load or save failure
- `Restricted`
- `Success`
  redirect to detail or show saved state

## 9. `Requisition Detail`

### Layout

- `DetailLayout`

### Core Components

- requisition summary card
- owner summary
- assignment panel
- pipeline summary
- status history drawer
- assignment history drawer
- reassign owner dialog

### Role-Gated Actions

- `Update Status`
  permitted business users, permitted senior users, Admin
- `Add Assignment`
  permitted senior users, Admin
- `Remove Assignment`
  permitted senior users, Admin
- `Reassign Owner`
  permitted senior users, Admin

### Required States

- `Loading`
- `Empty`
  only for related subsections like no assignments
- `Error`
- `Restricted`
- `Success`
  status updated, assignment changed
- `Review Required`
  owner reassignment affecting active work

## 10. `Candidate Profiles`

### Layout

- `ManagementLayout`

### Core Components

- candidate list
- candidate create or edit inline state
- identity section
- contact section
- source section
- skills section
- social profiles section
- duplicate warning modal
- link to requisition dialog

### Role-Gated Actions

- `Create Candidate`
  recruiter or sourcing users, permitted senior users, Admin
- `Edit Candidate`
  owner or permitted user
- `Link To Requisition`
  recruiter or sourcing users, permitted senior users, Admin

### Required States

- `Loading`
- `Empty`
- `Error`
- `Restricted`
- `Success`
  candidate saved or linked
- `Review Required`
  duplicate found before finalization

## 11. `Resume Upload And Review`

### Layout

- `DetailLayout` or focused upload layout

### Core Components

- upload drop zone
- parsed field review
- document metadata section
- replace file action
- confirm attach action

### Role-Gated Actions

- `Upload`
  recruiter or sourcing users, permitted senior users, Admin

### Required States

- `Loading`
  upload and attach
- `Error`
  upload failure or invalid parse
- `Restricted`
- `Success`
  document linked

## 12. `Candidate Duplicate Review`

### Layout

- `DetailLayout`

### Core Components

- case summary
- submitted candidate card
- possible match cards
- side-by-side compare section
- decision footer
- audit note field

### Role-Gated Actions

- `Resolve Duplicate`
  Admin and selected senior roles only

### Required States

- `Loading`
- `Empty`
  no active cases or no matches returned
- `Error`
- `Restricted`
  unauthorized reviewer
- `Success`
  case resolved
- `Review Required`
  pending decision remains

## 13. `Pipeline Board`

### Layout

- `ManagementLayout` or board-focused layout

### Core Components

- requisition selector
- board columns
- stage cards
- filter bar
- application detail drawer
- stage move dialog
- pipeline history drawer

### Role-Gated Actions

- `Move Stage`
  recruiter or sourcing users with permission, permitted senior users, Admin
- `View History`
  permitted readers

### Required States

- `Loading`
- `Empty`
  no applications in current filter
- `Error`
- `Restricted`
- `Success`
  stage moved

## 14. `Daily Updates Submission`

### Layout

- `DetailLayout` or focused form layout

### Core Components

- requisition selector
- activity count inputs
- blockers section
- next steps section
- submission history strip
- sticky submit bar

### Role-Gated Actions

- `Submit Daily Update`
  recruiter or sourcing users, permitted users linked to requisition, Admin if needed

### Required States

- `Loading`
- `Empty`
  no linked requisitions
- `Error`
- `Restricted`
- `Success`
  update submitted
- `Review Required`
  duplicate same-day rule blocks direct submit

## 15. `Daily Updates Review`

### Layout

- `ManagementLayout`

### Core Components

- updates table
- filter bar
- blocker highlight cards
- row detail panel

### Role-Gated Actions

- `View Team Updates`
  permitted senior users, reporting users, Admin

### Required States

- `Loading`
- `Empty`
- `Error`
- `Restricted`

## 16. `My Work Dashboard`

### Layout

- `DashboardLayout`

### Core Components

- KPI cards
- pending actions widget
- sourced candidates widget
- my pipeline widget
- daily update reminders

### Role-Gated Actions

- `Open My Pipeline`
  any permitted operational user
- `Open Pending Update`
  any permitted operational user

### Required States

- `Loading`
- `Empty`
  no active work
- `Error`
- `Restricted`

## 17. `Role Dashboard`

### Layout

- `DashboardLayout`

### Core Components

- role-aware KPI strip
- urgent work widget
- pending duplicate review widget
- updates pending widget
- quick navigation cards

### Role-Gated Actions

- widget actions depend on role permissions and allowed pages

### Required States

- `Loading`
- `Empty`
  no actionable data
- `Error`
- `Restricted`

## 18. `Location Dashboard`

### Layout

- `DashboardLayout`

### Core Components

- location KPI strip
- pipeline volume charts
- closure stats widget
- update compliance widget
- risk summary table

### Role-Gated Actions

- `View Location Performance`
  reporting users, permitted senior users if allowed, Admin

### Required States

- `Loading`
- `Empty`
  no reporting data
- `Error`
- `Restricted`

## 19. `Company Dashboard`

### Layout

- `DashboardLayout`

### Core Components

- company KPI strip
- multi-location comparison cards
- trend charts
- top-risk tables

### Role-Gated Actions

- `View Company Reporting`
  Admin and selected reporting roles only

### Required States

- `Loading`
- `Empty`
  no reporting data
- `Error`
- `Restricted`

## 20. `Notifications Center`

### Layout

- `ManagementLayout` or utility panel page

### Core Components

- notifications list
- unread filter
- notification detail panel
- linked record shortcut

### Role-Gated Actions

- `Mark Read`
  authenticated user for own notifications

### Required States

- `Loading`
- `Empty`
  no notifications
- `Error`
- `Restricted`
- `Success`
  mark-read reflected immediately

## Support Container Contracts

These reusable containers must behave consistently:

### Dialogs

Examples:

- `Create Location Dialog`
- `Contact Form Dialog`
- `Status Update Dialog`
- `Stage Move Dialog`
- `Deactivate User Dialog`

Rules:

- must trap focus
- must support cancel and confirm
- must show form or action errors clearly
- must not hide critical validation below the fold

### Drawers

Examples:

- `Edit Location Drawer`
- `Edit User Drawer`
- `Assignment History Drawer`
- `Pipeline History Drawer`

Rules:

- must preserve parent-page context
- must support close without data loss warning when needed
- must handle its own loading and error state

## Reusability Guidance

Prefer one reusable section when the same structure appears in multiple pages:

- summary cards
- owner cards
- filter bars
- tables
- history timelines
- audit note blocks
- empty and restricted states

Do not create separate one-off components if a reusable version will clearly support:

- clients
- requisitions
- candidates
- pipeline
- daily updates

## Final Delivery Rule

Frontend work is not ready for handoff unless each MVP page has:

- named layout
- named core components
- defined role-gated actions
- defined required states

If one of these is missing, the page contract is incomplete.
