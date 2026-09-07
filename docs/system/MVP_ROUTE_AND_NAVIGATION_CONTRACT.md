# MVP Route And Navigation Contract

## Purpose

This document defines the route structure and navigation behavior for the MVP frontend.

It is the source of truth for:

- route paths
- layout selection
- route guards
- page entry points
- page exit flows
- reachable dialogs, drawers, and panels

Use this together with:

- `docs/system/BUILD_PACK_FRONTEND_PAGE_MODULE_PLAN.md`
- `docs/system/MVP_USE_CASE_PAGE_EXECUTION_MAP.md`
- `docs/system/MVP_COMPONENT_AND_STATE_CONTRACT.md`
- `docs/system/MVP_PAGE_API_PAYLOAD_MAP.md`

## Core Rule

Every user-visible transition in the MVP must be one of these:

- route navigation to a full page
- in-page dialog open
- in-page drawer or panel open

No hidden redirect or undocumented destination should exist.

## Route Design Principles

- route names must use stable product language
- route paths should be simple and readable
- details should use entity ids in path segments
- create and edit flows should reuse existing pages where practical
- duplicate review and access denial should stay as dedicated pages
- dialogs and drawers should not become separate routes unless the workflow clearly needs shareable deep links later

## Guard Types

### `PublicOnlyGuard`

Use for:

- routes that should not be opened by authenticated users during normal operation

Behavior:

- unauthenticated user may enter
- authenticated user is redirected to landing page

### `AuthenticatedGuard`

Use for:

- any route that requires a valid session

Behavior:

- valid session may enter
- missing or expired session redirects to `Login`

### `PermissionGuard`

Use for:

- routes that require specific page or module permission

Behavior:

- if authenticated but not permitted, redirect to `Access Denied`

### `ScopeGuard`

Use for:

- entity detail routes where location or ownership scope matters

Behavior:

- access is allowed only when backend and route context both permit it
- if route is readable but the record is outside scope, show restricted state or redirect to `Access Denied`

## Recommended Route Tree

```text
/
  /login
  /access-denied
  /dashboard
  /dashboard/my-work
  /admin/locations
  /admin/users
  /admin/users/:userId
  /admin/roles
  /clients
  /clients/:clientId
  /requisitions
  /requisitions/new
  /requisitions/:requisitionId
  /requisitions/:requisitionId/edit
  /candidates
  /candidates/duplicate-review/:caseId
  /candidates/upload/:candidateId
  /pipeline
  /daily-updates/submit
  /daily-updates/review
  /notifications
  /reports/location
  /reports/company
```

## Route-Level Contract

| Route Path | Screen Name | Layout | Guards | Main Entry Points | Main Exit Flows | Reachable Dialogs, Drawers, Or Panels |
| --- | --- | --- | --- | --- | --- | --- |
| `/login` | `Login` | `AuthLayout` | `PublicOnlyGuard` | direct URL, session expiry redirect, logout redirect | success to `/dashboard`, forgot password to future flow | none |
| `/access-denied` | `Access Denied` | `AuthLayout` or minimal shell | `AuthenticatedGuard` optional | permission denial redirect, scope denial redirect | back to previous safe page, dashboard redirect | none |
| `/dashboard` | `Role Dashboard` | `DashboardLayout` | `AuthenticatedGuard`, `PermissionGuard` | login success, top-level navigation | to detail pages from widgets | notification panel if global shell uses one |
| `/dashboard/my-work` | `My Work Dashboard` | `DashboardLayout` | `AuthenticatedGuard`, `PermissionGuard` | role dashboard widget, sidebar navigation | to pipeline, candidate list, daily updates | none |
| `/admin/locations` | `Location Management` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation | back through sidebar or to entity flows if later expanded | `Create Location Dialog`, `Edit Location Drawer` |
| `/admin/users` | `User Management` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation | to user detail, back through sidebar | `Create User Drawer`, `Edit User Drawer` |
| `/admin/users/:userId` | `User Detail` | `DetailLayout` | `AuthenticatedGuard`, `PermissionGuard`, `ScopeGuard` | click row in `User Management`, notifications if later used | back to `/admin/users` | `Deactivate User Dialog`, `Reassignment Review Drawer` |
| `/admin/roles` | `Role Management` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation | back through sidebar | `Create Role Drawer`, `Edit Role Drawer` |
| `/clients` | `Client Directory` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, role dashboard widget if later used | to client detail | `Create Client Drawer`, `Edit Client Drawer` |
| `/clients/:clientId` | `Client Detail` | `DetailLayout` | `AuthenticatedGuard`, `PermissionGuard`, `ScopeGuard` | click row in `Client Directory`, linked notification | to requisition detail, back to `/clients` | `Contact Form Dialog` |
| `/requisitions` | `Requisition List` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, dashboard widgets | to new requisition, requisition detail | none |
| `/requisitions/new` | `Requisition Intake` | `DetailLayout` or form layout | `AuthenticatedGuard`, `PermissionGuard` | create action from `Requisition List`, linked client flow | on save to `/requisitions/:requisitionId`, cancel to `/requisitions` | none |
| `/requisitions/:requisitionId` | `Requisition Detail` | `DetailLayout` | `AuthenticatedGuard`, `PermissionGuard`, `ScopeGuard` | requisition list row, linked client detail, dashboard widget | to edit route, pipeline route, back to `/requisitions` | `Status Update Dialog`, `Assignment History Drawer`, `Reassign Owner Dialog` |
| `/requisitions/:requisitionId/edit` | `Requisition Intake` edit mode | `DetailLayout` or form layout | `AuthenticatedGuard`, `PermissionGuard`, `ScopeGuard` | edit action from `Requisition Detail` | save to `/requisitions/:requisitionId`, cancel back to detail | none |
| `/candidates` | `Candidate Profiles` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, pipeline link back, upload flow return | to duplicate review, upload route, linked requisition dialog flows | `Duplicate Warning Modal`, `Link To Requisition Dialog` |
| `/candidates/duplicate-review/:caseId` | `Candidate Duplicate Review` | `DetailLayout` | `AuthenticatedGuard`, `PermissionGuard` | duplicate warning flow, role dashboard widget, notification link | resolved flow to candidate list or kept candidate context | none |
| `/candidates/upload/:candidateId` | `Resume Upload And Review` | `DetailLayout` or focused upload layout | `AuthenticatedGuard`, `PermissionGuard`, `ScopeGuard` | upload action from candidate list or detail state | continue back to `/candidates` | none |
| `/pipeline` | `Pipeline Board` | `ManagementLayout` or board layout | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, requisition detail, my work dashboard | to candidate list, back to requisition detail if query context exists | `Application Detail Drawer`, `Stage Move Dialog`, `Pipeline History Drawer Or Panel` |
| `/daily-updates/submit` | `Daily Updates Submission` | `DetailLayout` or form layout | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, my work dashboard, role dashboard pending updates widget | success state stays on page or routes to `/dashboard/my-work` | none |
| `/daily-updates/review` | `Daily Updates Review` | `ManagementLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, role dashboard widget, notification link | back through sidebar or to linked requisition detail | `Update Detail Panel` |
| `/notifications` | `Notifications Center` | `ManagementLayout` or shell utility page | `AuthenticatedGuard`, `PermissionGuard` | top bar notification entry, sidebar if included | to linked target route from selected item | `Notification Detail Panel` |
| `/reports/location` | `Location Dashboard` | `DashboardLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, reporting widget links | to filtered detail pages later if added | none |
| `/reports/company` | `Company Dashboard` | `DashboardLayout` | `AuthenticatedGuard`, `PermissionGuard` | sidebar navigation, Admin navigation | to filtered location dashboard later if added | none |

## Default Landing Rule

After successful login:

- route to `/dashboard`
- if the company later wants role-specific landing overrides, they can still start from `/dashboard` and route by widget or quick action

This keeps the MVP navigation predictable.

## Route Parameter Rules

Use route params for:

- `:userId`
- `:clientId`
- `:requisitionId`
- `:candidateId`
- `:caseId`

Use query params for view state, not identity:

- filters
- sort order
- selected location in reporting
- selected requisition in pipeline
- selected owner in my work views

Examples:

- `/pipeline?requisitionId=18`
- `/clients?status=active&search=tech`
- `/daily-updates/review?date=2026-08-19&locationId=1`

## Entry And Exit Flow Rules

### Auth Flow

- unauthenticated access to protected route
  redirect to `/login`
- authenticated login success
  route to `/dashboard`
- explicit logout
  route to `/login`
- expired session during action
  show message and route to `/login`

### Dashboard Flow

- `Role Dashboard` widget to personal work
  route to `/dashboard/my-work`
- urgent requisition widget
  route to `/requisitions/:requisitionId`
- pending duplicate review widget
  route to `/candidates/duplicate-review/:caseId`
- updates pending widget
  route to `/daily-updates/review` or `/daily-updates/submit`

### Client Flow

- client row click
  route to `/clients/:clientId`
- linked requisition click from client detail
  route to `/requisitions/:requisitionId`
- create client success
  either stay on `/clients` with refresh or route to `/clients/:clientId`

### Requisition Flow

- create click from list
  route to `/requisitions/new`
- save success from new requisition
  route to `/requisitions/:requisitionId`
- edit click from detail
  route to `/requisitions/:requisitionId/edit`
- save success from edit
  route to `/requisitions/:requisitionId`
- open pipeline from detail
  route to `/pipeline?requisitionId=:requisitionId`

### Candidate Flow

- upload resume from candidate list
  route to `/candidates/upload/:candidateId`
- continue after upload
  route to `/candidates`
- duplicate issue after candidate finalization attempt
  route to `/candidates/duplicate-review/:caseId`
- successful duplicate resolution
  route back to `/candidates` or to the surviving candidate context later if that page exists

### Pipeline Flow

- open candidate from board
  route to `/candidates`
  note:
  preserve filter or selection context in JS if possible
- open history from board
  drawer or panel, not route navigation
- move stage
  dialog, not route navigation

### Daily Update Flow

- submit success
  show success state in place or route to `/dashboard/my-work`
- review row to linked requisition
  route to `/requisitions/:requisitionId`

### Notification Flow

- open notifications center
  route to `/notifications`
- click linked record from notification detail
  route to the linked entity route based on type

## Reachable Container Contract

These containers should never be opened from undefined pages:

### Dialogs

- `Create Location Dialog`
  from `/admin/locations`
- `Create User Drawer`
  from `/admin/users`
- `Create Role Drawer`
  from `/admin/roles`
- `Contact Form Dialog`
  from `/clients/:clientId`
- `Status Update Dialog`
  from `/requisitions/:requisitionId`
- `Reassign Owner Dialog`
  from `/requisitions/:requisitionId`
- `Duplicate Warning Modal`
  from `/candidates`
- `Link To Requisition Dialog`
  from `/candidates`
- `Stage Move Dialog`
  from `/pipeline`
- `Deactivate User Dialog`
  from `/admin/users/:userId`

### Drawers And Panels

- `Edit Location Drawer`
  from `/admin/locations`
- `Edit User Drawer`
  from `/admin/users`
- `Reassignment Review Drawer`
  from `/admin/users/:userId`
- `Assignment History Drawer`
  from `/requisitions/:requisitionId`
- `Application Detail Drawer`
  from `/pipeline`
- `Pipeline History Drawer Or Panel`
  from `/pipeline`
- `Update Detail Panel`
  from `/daily-updates/review`
- `Notification Detail Panel`
  from `/notifications`

## Breadcrumb Contract

Use breadcrumbs on all authenticated pages except dashboards when unnecessary.

Recommended examples:

- `Admin / Locations`
- `Admin / Users / User Detail`
- `Clients / Client Detail`
- `Requisitions / Requisition Detail`
- `Candidates / Duplicate Review`
- `Reports / Location Dashboard`
- `Reports / Company Dashboard`

## Navigation Visibility Rules

Sidebar and top-level navigation should be permission-aware.

Examples:

- a user without location admin permission should not see `Location Management`
- a user with read-only reporting permission may see `Location Dashboard` but not `Company Dashboard`
- a recruiter may see `Candidate Profiles`, `Pipeline Board`, and `Daily Updates Submission`, but not Admin pages

This improves UX, but backend permission and scope checks still remain mandatory.

## Deep Link Rules

The MVP should support direct opening of full pages when the user has valid access:

- `/clients/:clientId`
- `/requisitions/:requisitionId`
- `/candidates/duplicate-review/:caseId`
- `/pipeline`
- `/daily-updates/review`

Dialogs and drawers do not require standalone deep links in MVP.

## Unsaved Navigation Rules

If the user tries to leave a form route or close a form-heavy container with unsaved changes:

- show a confirmation prompt
- offer `stay` and `leave`
- do not silently drop entered data

Apply this especially to:

- `/requisitions/new`
- `/requisitions/:requisitionId/edit`
- candidate create or edit inline state
- `Create User Drawer`
- `Create Role Drawer`

## Error Navigation Rules

- `404` on route record load
  show page-level not-found or error state inside the current layout
- permission failure
  redirect to `/access-denied` or show restricted page state
- scope failure on detail route
  prefer restricted state or `/access-denied`
- unexpected server error
  keep user in current route with retry option when safe

## Frontend Implementation Notes

Recommended folders:

- route definitions in `frontend/app/router/`
- guard logic in `frontend/app/guards/`
- navigation config in `frontend/app/shell/` or `frontend/shared/navigation/`
- route-aware page containers in `frontend/pages/`

Recommended route config fields:

- `path`
- `pageName`
- `layout`
- `guardTypes`
- `requiredPermissions`
- `breadcrumb`
- `supportsQueryFilters`

## QA Verification Checklist

QA should verify:

- every route opens the intended page
- unauthorized users are redirected or restricted correctly
- entity detail routes enforce scope correctly
- login and logout redirects are correct
- route transitions match the documented destination
- dialogs and drawers open only from allowed pages
- unsaved-change prompts appear where required

## Final Delivery Rule

Routing is not MVP-ready unless every build-pack page has:

- a named route path or an explicit statement that it is container-only
- a named layout
- a named guard model
- defined entry and exit flows
- defined reachable dialogs or drawers

If one of these is missing, navigation planning is incomplete.
