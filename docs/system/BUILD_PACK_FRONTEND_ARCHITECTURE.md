# MVP Frontend Architecture

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document defines the proper frontend structure for the current MVP.

It is the source of truth for:

- frontend folder layering
- global layouts
- shared UI
- module boundaries
- route organization
- page creation rules

The goal is to make creation of new pages easy, consistent, and properly layered.

## Core Rule

The MVP frontend must not be built as isolated pages only.

Every page should be created inside a clear frontend architecture with:

- app-level layouts
- shared global UI
- module-level features
- page-level route containers
- reusable dialogs and panels

## Frontend Layering Model

The MVP frontend should be organized into these layers:

### 1. App Layer

This layer owns:

- app bootstrap
- routing
- route guards
- top-level layouts
- session bootstrap
- global navigation

### 2. Layout Layer

This layer owns:

- authentication layout
- app shell layout
- detail layout
- dashboard layout
- management layout

### 3. Module Layer

This layer owns:

- business features grouped by module
- page-specific state
- module-specific components
- page actions and local flows

### 4. Shared UI Layer

This layer owns:

- buttons
- form fields
- chips
- tables
- cards
- empty states
- loading states
- drawers
- dialogs
- panels

### 5. Theme And Global Layer

This layer owns:

- design tokens
- color system
- typography
- spacing scale
- shadows
- status colors
- global CSS utilities

### 6. Data Layer

This layer owns:

- API clients
- request helpers
- response adapters
- auth token handling
- module data hooks or services

## Recommended MVP Frontend Structure

```text
frontend/
  app/
    router/
    guards/
    shell/
    boot/
  layouts/
    auth/
    app-shell/
    dashboard/
    management/
    detail/
  modules/
    auth/
    dashboard/
    admin/
    clients/
    requisitions/
    candidates/
    pipeline/
    daily-updates/
    notifications/
  components/
    data-display/
    forms/
    navigation/
    feedback/
    overlays/
    actions/
  theme/
    tokens.css
    globals.css
    components.css
  data/
    api/
    auth/
    adapters/
    mocks/
  pages/
    auth/
    dashboard/
    admin/
    clients/
    requisitions/
    candidates/
    pipeline/
    daily-updates/
    notifications/
  shared/
    assets/
    icons/
    brand/
```

## Folder Responsibilities

## `frontend/app/`

Use this for:

- app startup
- route registration
- auth boot
- navigation boot
- protected route logic

Do not put page-specific UI here.

## `frontend/layouts/`

Use this for structural wrappers only.

Examples:

- `AuthLayout`
- `AppShellLayout`
- `DashboardLayout`
- `ManagementLayout`
- `DetailLayout`

Layouts should define:

- sidebar presence
- top bar behavior
- content width rules
- action bar position
- breadcrumb behavior

## `frontend/modules/`

Use this for business logic and module-specific components.

Example module breakdown:

### `modules/auth/`

- login form logic
- first login setup logic
- auth error states

### `modules/dashboard/`

- KPI cards
- alerts widgets
- personal work widgets

### `modules/admin/`

- locations table
- users table
- roles permissions section

### `modules/clients/`

- clients table
- client summary
- client contacts section

### `modules/requisitions/`

- requisition filters
- requisition form sections
- ownership summary
- work queue cards

### `modules/candidates/`

- candidate table
- candidate form
- duplicate review section
- resume review section

### `modules/pipeline/`

- kanban board
- stage cards
- stage history drawer
- move-stage flow

### `modules/daily-updates/`

- update form
- updates table
- review detail panel

### `modules/notifications/`

- notifications list
- notification detail panel

## `frontend/components/`

Use this only for truly reusable UI.

### `components/data-display/`

- table shell
- KPI card
- summary card
- detail block
- timeline row

### `components/forms/`

- text field
- select field
- textarea field
- inline field hint
- field error
- form section wrapper

### `components/navigation/`

- sidebar item
- breadcrumb
- tab switcher
- filter bar

### `components/feedback/`

- empty state
- loading skeleton
- inline alert
- confirmation banner
- status chip

### `components/overlays/`

- dialog shell
- drawer shell
- side panel shell

### `components/actions/`

- primary action bar
- split action button
- row actions

## `frontend/theme/`

This layer should define the visual system before page creation grows too much.

### Required theme files

- `tokens.css`
  color, spacing, radius, shadow, typography variables
- `globals.css`
  body, headings, input, table, button base behavior
- `components.css`
  reusable component appearance rules

### Theme rules

- use one consistent enterprise visual language
- keep status colors standardized
- use one spacing scale
- avoid page-specific color invention

## `frontend/data/`

Use this for all data access.

### `data/api/`

- endpoint wrappers
- request builders
- pagination helpers

### `data/auth/`

- session storage
- current user loading
- permission payload loading

### `data/adapters/`

- map backend responses to page-ready shapes

### `data/mocks/`

- temporary fallback data only while backend is not integrated

## `frontend/pages/`

This layer should contain route-level page containers only.

Pages should:

- compose layouts
- compose module components
- wire route params
- call module data hooks

Pages should not:

- own global styles
- duplicate shared components
- hardcode repeated table patterns

## MVP Layout Set

These layouts should exist before mass page generation.

### 1. Auth Layout

Used by:

- Login
- First Login Password Setup
- Access Denied

Includes:

- centered content zone
- clean background
- minimal header

### 2. App Shell Layout

Used by most authenticated pages.

Includes:

- left sidebar
- top header
- page title zone
- page actions zone
- main content area

### 3. Dashboard Layout

Used by:

- Role Dashboard
- My Work Dashboard

Includes:

- KPI strip
- widget grid
- activity region

### 4. Management Layout

Used by:

- Location Management
- User Management
- Role Management
- Client Directory
- Requisition List
- Daily Updates Review

Includes:

- page header
- filter bar
- table region
- secondary drawer support

### 5. Detail Layout

Used by:

- Client Detail
- Requisition Detail
- Candidate Profiles detail state

Includes:

- sticky summary header
- main detail column
- side info column
- action row

## MVP Global UI Set

These global items should be created before later pages:

### Navigation

- sidebar
- top header
- breadcrumb
- page title block

### Data Display

- KPI card
- summary stat strip
- enterprise table shell
- section card
- detail summary panel

### Feedback

- loading skeleton
- empty state
- error state
- success banner
- validation message

### Form System

- field label pattern
- required field marker
- inline error pattern
- section divider
- sticky footer action bar

### Overlays

- dialog shell
- drawer shell
- right-side panel shell

## MVP Route Structure

Recommended route grouping:

```text
/login
/access-denied
/dashboard
/my-work
/admin/locations
/admin/users
/admin/roles
/clients
/clients/:clientId
/requisitions
/requisitions/new
/requisitions/:requisitionId
/requisitions/:requisitionId/edit
/delivery/work-queue
/candidates
/candidates/duplicate-review/:candidateId
/candidates/resume-review/:candidateId
/screening/:candidateId
/pipeline/:requisitionId
/daily-updates/new
/daily-updates/review
/notifications
```

## Page Creation Rules

When creating a new page:

1. choose the page layout first
2. identify reusable shared UI before creating page-specific UI
3. identify module ownership
4. define linked dialogs and panels
5. define loading, empty, validation, and error states

No page should be created as a one-off isolated screen.

## Page To Layout Mapping

### Auth

- Login -> `AuthLayout`
- First Login Password Setup -> `AuthLayout`
- Access Denied -> `AuthLayout`

### Dashboard

- Role Dashboard -> `DashboardLayout`
- My Work Dashboard -> `DashboardLayout`

### Management

- Location Management -> `ManagementLayout`
- User Management -> `ManagementLayout`
- Role Management -> `ManagementLayout`
- Client Directory -> `ManagementLayout`
- Requisition List -> `ManagementLayout`
- Daily Updates Review -> `ManagementLayout`

### Detail

- Client Detail -> `DetailLayout`
- Requisition Detail -> `DetailLayout`

### Form-Heavy Operational

- Requisition Intake -> `AppShellLayout` with form page pattern
- Candidate Screening -> `AppShellLayout` with review page pattern
- Daily Updates Submission -> `AppShellLayout` with compact form pattern

### Board

- Pipeline Board -> `AppShellLayout` with board page pattern

## Shared Workflow Components

These must be built as reusable overlay components, not page-specific custom markup:

- Reassign Owner Dialog
- Stage Move Dialog
- Contact Form Dialog
- Notification Detail Panel
- Pipeline History Drawer

## MVP Build Sequence For Frontend Foundation

Before generating many pages, first build:

1. theme tokens
2. global styles
3. app shell layout
4. auth layout
5. dashboard layout
6. management layout
7. detail layout
8. enterprise table shell
9. form field system
10. dialog, drawer, and side panel shells

Only after that should page generation continue at scale.

## Practical Rule For Stitch

When using Stitch, do not generate pages as unrelated standalone designs.

Generate in this order:

1. layouts
2. global UI patterns
3. page screens
4. shared overlays
5. page refinements

This will make the MVP frontend much easier to assemble and keep consistent.
