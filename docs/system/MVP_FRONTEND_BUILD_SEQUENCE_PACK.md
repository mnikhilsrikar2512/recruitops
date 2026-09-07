# MVP Frontend Build Sequence Pack

## Purpose

This document converts the MVP frontend planning pack into an execution sequence the team can build in batches.

It is meant to answer:

- what should be built first
- what each build batch depends on
- what pages and components belong in each batch
- what must be true before the next batch begins

Use this together with:

- `docs/system/MVP_FRONTEND_IMPLEMENTATION_MATRIX.md`
- `docs/system/MVP_FRONTEND_HOOK_AND_ADAPTER_CONTRACT.md`
- `docs/system/MVP_ROUTE_AND_NAVIGATION_CONTRACT.md`
- `docs/system/MVP_COMPONENT_AND_STATE_CONTRACT.md`
- `docs/system/MVP_PAGE_API_PAYLOAD_MAP.md`

## Core Rule

Frontend work should not start page by page in random order.

The team should build in layered batches so that:

- layouts are ready before pages multiply
- shared components are reusable before duplication spreads
- route guards exist before protected pages go live
- hooks and adapters are consistent before deeper integrations begin

## Recommended Frontend Build Batches

1. Foundation
2. Admin Setup
3. Client And Requisition Operations
4. Candidate And Pipeline Operations
5. Daily Updates And Reporting
6. Hardening And Final Integration

## Batch 1. Foundation

### Goal

Create the reusable frontend base so later pages are built on stable structure.

### Must Be Built In This Batch

- route bootstrapping
- app shell
- auth layout
- dashboard layout
- management layout
- detail layout
- route guards
- navigation config
- shared state components
- shared overlays
- base data layer pattern

### Main Deliverables

- `frontend/app/router/`
- `frontend/app/guards/`
- `frontend/layouts/auth/`
- `frontend/layouts/app-shell/`
- `frontend/layouts/dashboard/`
- `frontend/layouts/management/`
- `frontend/layouts/detail/`
- reusable shared components:
  - `PageHeader`
  - `Breadcrumbs`
  - `FilterBar`
  - `TableShell`
  - `DetailCard`
  - `KpiCard`
  - `DialogShell`
  - `DrawerShell`
  - `EmptyState`
  - `ErrorState`
  - `RestrictedState`
  - `LoadingSkeleton`
  - `PermissionAwareAction`
- data layer base:
  - API client wrapper
  - error adapter base
  - auth session store or session helper
  - hook contract pattern

### Pages In Scope

- `Login`
- `Access Denied`

### Required Hooks In Scope

- `useAuthSession`
- `usePermissionContext`
- `useLoginMutation`

### Entry Criteria

- planning docs approved enough for frontend start

### Exit Criteria

- login route works
- protected route redirect works
- access denied route works
- authenticated shell can render
- one management page and one dashboard page can be mounted inside shared layouts without structural rework

### QA Focus

- login flow
- expired session redirect
- guard behavior
- shared loading, error, and restricted states

## Batch 2. Admin Setup

### Goal

Enable the system setup workflows required before recruitment operations begin.

### Must Be Built In This Batch

- location management
- role management
- user management
- user detail with deactivation review

### Pages In Scope

- `Location Management`
- `Role Management`
- `User Management`
- `User Detail`

### Reusable Components To Finish In This Batch

- status badge patterns
- form section patterns
- confirmation dialog pattern
- timeline component for audit or review

### Required Hooks In Scope

- `useLocationsQuery`
- `useCreateLocationMutation`
- `useUpdateLocationMutation`
- `useRolesQuery`
- `useCreateRoleMutation`
- `useUpdateRoleMutation`
- `useAssignRolePermissionsMutation`
- `useUsersQuery`
- `useCreateUserMutation`
- `useUpdateUserMutation`
- `useUserDetailQuery`
- `useDeactivateUserMutation`

### Dependencies

- Batch 1 complete

### Exit Criteria

- Admin can create location
- Admin can create role and assign permissions
- Admin can create user
- Admin can open user detail
- deactivation review UI exists for active-work scenario

### QA Focus

- admin-only route protection
- create and edit flows
- field validation mapping
- review-required deactivation path

## Batch 3. Client And Requisition Operations

### Goal

Enable the intake and delivery-start workflow from client to requisition ownership.

### Must Be Built In This Batch

- client directory
- client detail and contact flow
- requisition list
- requisition create and edit
- requisition detail
- assignment and owner reassignment flows

### Pages In Scope

- `Client Directory`
- `Client Detail`
- `Requisition List`
- `Requisition Intake`
- `Requisition Detail`

### Reusable Components To Finish In This Batch

- linked-record list patterns
- owner summary cards
- assignment panel pattern
- history drawer pattern

### Required Hooks In Scope

- `useClientsQuery`
- `useCreateClientMutation`
- `useUpdateClientMutation`
- `useClientDetailQuery`
- `useClientContactsQuery`
- `useCreateClientContactMutation`
- `useUpdateClientContactMutation`
- `useRequisitionsQuery`
- `useRequisitionFormBootstrapQuery`
- `useCreateRequisitionMutation`
- `useUpdateRequisitionMutation`
- `useRequisitionDetailQuery`
- `useRequisitionAssignmentsQuery`
- `useUpdateRequisitionStatusMutation`
- `useAddAssignmentMutation`
- `useRemoveAssignmentMutation`
- `useReassignRequisitionOwnerMutation`

### Dependencies

- Batch 2 complete enough for users, roles, and permissions to exist in UI

### Exit Criteria

- permitted user can create client
- permitted user can add contact
- permitted user can create requisition
- permitted user can edit requisition
- permitted senior user can assign and reassign delivery work

### QA Focus

- location-safe visibility
- client detail navigation
- requisition create and edit validations
- review-required assignment changes

## Batch 4. Candidate And Pipeline Operations

### Goal

Enable recruitment execution from candidate creation to pipeline movement.

### Must Be Built In This Batch

- candidate profiles
- resume upload and review
- duplicate warning flow
- duplicate review page
- link candidate to requisition
- pipeline board
- application detail drawer
- stage move flow
- pipeline history

### Pages In Scope

- `Candidate Profiles`
- `Resume Upload And Review`
- `Candidate Duplicate Review`
- `Pipeline Board`

### Reusable Components To Finish In This Batch

- compare view pattern
- pipeline card pattern
- history timeline refinement
- dialog-driven stage move pattern

### Required Hooks In Scope

- `useCandidatesQuery`
- `useCreateCandidateMutation`
- `useUpdateCandidateMutation`
- `useCandidateDetailQuery`
- `useCandidateDuplicateCheckMutation`
- `useLinkCandidateToRequisitionMutation`
- `useUploadCandidateDocumentMutation`
- `useDuplicateCaseDetailQuery`
- `useResolveDuplicateCaseMutation`
- `usePipelineBoardQuery`
- `usePipelineApplicationDetailQuery`
- `useMovePipelineStageMutation`
- `usePipelineHistoryQuery`

### Dependencies

- Batch 3 complete because requisitions and assignments must already exist

### Exit Criteria

- recruiter can create candidate
- recruiter can trigger duplicate check
- reviewer can resolve duplicate case
- candidate can be linked to requisition
- permitted user can move candidate through valid pipeline stages

### QA Focus

- duplicate review routing
- same-candidate same-requisition protection
- stage validation errors
- recruiter visibility versus edit authority

## Batch 5. Daily Updates And Reporting

### Goal

Enable daily execution tracking and management visibility.

### Must Be Built In This Batch

- daily update submission
- daily updates review
- role dashboard
- my work dashboard
- location dashboard
- company dashboard
- notifications center

### Pages In Scope

- `Daily Updates Submission`
- `Daily Updates Review`
- `Role Dashboard`
- `My Work Dashboard`
- `Location Dashboard`
- `Company Dashboard`
- `Notifications Center`

### Reusable Components To Finish In This Batch

- dashboard KPI strip patterns
- widget grid patterns
- notification list and detail panel
- reporting summary card patterns

### Required Hooks In Scope

- `useMyDailyUpdatesQuery`
- `useLinkedRequisitionsQuery`
- `useSubmitDailyUpdateMutation`
- `useTeamDailyUpdatesQuery`
- `usePipelineSummaryQuery`
- `useRoleDashboardQuery`
- `useMyWorkDashboardQuery`
- `useNotificationSummaryQuery`
- `useLocationDashboardQuery`
- `useCompanyDashboardQuery`
- `useNotificationsQuery`
- `useMarkNotificationReadMutation`

### Dependencies

- Batch 4 complete enough for live candidate and pipeline data to exist

### Exit Criteria

- recruiter can submit daily update
- managers can review updates and progress
- role dashboard widgets route correctly
- location and company reporting routes work with permission-aware access
- notifications center opens linked records

### QA Focus

- role-sensitive widget visibility
- dashboard loading and empty states
- reporting permission restrictions
- notification linked-route behavior

## Batch 6. Hardening And Final Integration

### Goal

Stabilize the MVP frontend for team handoff and integrated testing.

### Must Be Built In This Batch

- consistent empty, error, and restricted states on all pages
- final breadcrumb consistency
- unsaved-change prompts
- responsive polish
- permission-aware action cleanup
- cross-page navigation cleanup
- adapter and hook naming cleanup

### Work In Scope

- remove duplicated page-local UI that should be shared
- align table, drawer, and dialog behavior
- verify all documented dialogs and drawers are reachable
- verify all route guards behave as planned
- verify all success and review-required states exist

### Dependencies

- Batches 1 through 5 functionally complete

### Exit Criteria

- every MVP route renders inside intended layout
- every documented page action has a working hook path
- every page has its required states
- every guarded page and action shows correct restricted behavior
- no critical route or dialog path is undocumented

### QA Focus

- end-to-end route coverage
- page-state coverage
- regression across shared components
- responsive behavior on common screen sizes

## Suggested Sprint Grouping

If the team wants sprint-style packaging:

### Sprint 1

- Batch 1 Foundation

### Sprint 2

- Batch 2 Admin Setup

### Sprint 3

- Batch 3 Client And Requisition Operations

### Sprint 4

- Batch 4 Candidate And Pipeline Operations

### Sprint 5

- Batch 5 Daily Updates And Reporting

### Sprint 6

- Batch 6 Hardening And Final Integration

This can be compressed if more than one frontend developer works in parallel.

## Parallel Work Guidance

These workstreams can overlap once the earlier dependency is stable:

- shared component creation
- page container setup
- module hook creation
- adapter creation

Good safe parallel split:

- Developer A:
  layouts, route guards, app shell
- Developer B:
  shared components and overlays
- Developer C:
  admin and client management pages
- Developer D:
  candidate and pipeline pages after Batch 3 readiness

## Handoff Checklist Per Batch

Before a batch is called done, confirm:

- routes exist
- page files exist
- module components exist
- shared components are reused
- hooks and adapters exist
- loading, error, empty, and restricted states are present
- primary success flows are testable

## Final Delivery Rule

Frontend execution planning is incomplete if the team cannot answer, for each batch:

- what gets built
- what it depends on
- what done means

If one of those is unclear, the build sequence is not yet safe for execution.
