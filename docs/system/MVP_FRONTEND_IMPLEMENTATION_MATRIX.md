# MVP Frontend Implementation Matrix

## Purpose

This document maps each MVP frontend page to its recommended implementation location.

It is the practical handoff for:

- page file creation
- module ownership
- shared component reuse
- route container setup
- API hook planning

Use this together with:

- `docs/system/BUILD_PACK_FRONTEND_ARCHITECTURE.md`
- `docs/system/MVP_ROUTE_AND_NAVIGATION_CONTRACT.md`
- `docs/system/MVP_COMPONENT_AND_STATE_CONTRACT.md`
- `docs/system/MVP_PAGE_API_PAYLOAD_MAP.md`

## Core Rule

Each page should have:

- a route-aware page container in `frontend/pages/`
- module-level business components in `frontend/modules/`
- shared reusable UI in `frontend/components/`
- data hooks or services in `frontend/data/`

Do not place all logic directly inside the page file.

## Suggested Folder Strategy

### Route Containers

Use `frontend/pages/` for:

- route registration targets
- page-level composition
- layout selection
- route param handling
- high-level guard-aware rendering

### Module Features

Use `frontend/modules/` for:

- business sections
- page-specific forms
- tables
- drawers
- dialogs
- widgets
- local business state

### Shared UI

Use `frontend/components/` for:

- generic table shell
- generic form shell
- status badge
- dialogs
- drawers
- banners
- reusable cards
- reusable timeline

### Data Hooks And APIs

Use `frontend/data/` for:

- API clients
- auth session helpers
- page query hooks
- mutation hooks
- response adapters

## Naming Convention Recommendation

### Page Files

- `LoginPage.tsx`
- `RoleDashboardPage.tsx`
- `MyWorkDashboardPage.tsx`
- `LocationManagementPage.tsx`
- `UserManagementPage.tsx`
- `UserDetailPage.tsx`
- `RoleManagementPage.tsx`
- `ClientDirectoryPage.tsx`
- `ClientDetailPage.tsx`
- `RequisitionListPage.tsx`
- `RequisitionIntakePage.tsx`
- `RequisitionDetailPage.tsx`
- `CandidateProfilesPage.tsx`
- `CandidateDuplicateReviewPage.tsx`
- `ResumeUploadReviewPage.tsx`
- `PipelineBoardPage.tsx`
- `DailyUpdatesSubmissionPage.tsx`
- `DailyUpdatesReviewPage.tsx`
- `NotificationsCenterPage.tsx`
- `LocationDashboardPage.tsx`
- `CompanyDashboardPage.tsx`
- `AccessDeniedPage.tsx`

### Hook Names

Prefer clear query and mutation naming:

- `useAuthSession`
- `usePermissionContext`
- `useLocationsQuery`
- `useCreateLocationMutation`
- `useUsersQuery`
- `useCreateUserMutation`
- `useClientsQuery`
- `useCreateClientMutation`
- `useRequisitionDetailQuery`
- `useCreateCandidateMutation`
- `usePipelineBoardQuery`
- `useMovePipelineStageMutation`

## Page Implementation Matrix

| Page | Route | Suggested Page File | Owning Module Folder | Likely Module Components | Shared Components Needed | Data Hooks Or Services |
| --- | --- | --- | --- | --- | --- | --- |
| `Login` | `/login` | `frontend/pages/auth/LoginPage.tsx` | `frontend/modules/auth/` | `LoginForm`, `AuthErrorBanner` | `FormSection`, `InlineBanner`, `LoadingSkeleton` | `useLoginMutation`, `useAuthSession`, `usePermissionContext` |
| `Access Denied` | `/access-denied` | `frontend/pages/auth/AccessDeniedPage.tsx` | `frontend/modules/auth/` | `AccessDeniedView` | `PageHeader`, `RestrictedState` | none beyond route helper |
| `Role Dashboard` | `/dashboard` | `frontend/pages/dashboard/RoleDashboardPage.tsx` | `frontend/modules/dashboard/` | `RoleKpiStrip`, `UrgentWorkWidget`, `DuplicateReviewWidget`, `UpdatesPendingWidget` | `KpiCard`, `DetailCard`, `EmptyState`, `ErrorState` | `useRoleDashboardQuery`, `useNotificationSummaryQuery` |
| `My Work Dashboard` | `/dashboard/my-work` | `frontend/pages/dashboard/MyWorkDashboardPage.tsx` | `frontend/modules/dashboard/` | `MyWorkKpiStrip`, `MyPipelineWidget`, `PendingActionsWidget`, `DailyReminderWidget` | `KpiCard`, `DetailCard`, `EmptyState` | `useMyWorkDashboardQuery`, `useMyPipelineSummaryQuery` |
| `Location Management` | `/admin/locations` | `frontend/pages/admin/LocationManagementPage.tsx` | `frontend/modules/admin/locations/` | `LocationsTable`, `CreateLocationDialog`, `EditLocationDrawer` | `PageHeader`, `FilterBar`, `TableShell`, `DialogShell`, `DrawerShell`, `StatusBadge` | `useLocationsQuery`, `useCreateLocationMutation`, `useUpdateLocationMutation` |
| `User Management` | `/admin/users` | `frontend/pages/admin/UserManagementPage.tsx` | `frontend/modules/admin/users/` | `UsersTable`, `CreateUserDrawer`, `EditUserDrawer`, `UserAccessPreview` | `PageHeader`, `FilterBar`, `TableShell`, `DrawerShell`, `StatusBadge` | `useUsersQuery`, `useCreateUserMutation`, `useUpdateUserMutation` |
| `User Detail` | `/admin/users/:userId` | `frontend/pages/admin/UserDetailPage.tsx` | `frontend/modules/admin/users/` | `UserSummaryCard`, `UserActiveWorkSummary`, `DeactivateUserDialog`, `ReassignmentReviewDrawer` | `DetailCard`, `ConfirmationDialog`, `DrawerShell`, `Timeline` | `useUserDetailQuery`, `useDeactivateUserMutation`, `useUserOwnershipImpactQuery` |
| `Role Management` | `/admin/roles` | `frontend/pages/admin/RoleManagementPage.tsx` | `frontend/modules/admin/roles/` | `RolesTable`, `CreateRoleDrawer`, `EditRoleDrawer`, `PermissionMatrix`, `ScopeMatrix` | `PageHeader`, `FilterBar`, `TableShell`, `DrawerShell`, `PermissionAwareAction` | `useRolesQuery`, `useCreateRoleMutation`, `useUpdateRoleMutation`, `useAssignRolePermissionsMutation` |
| `Client Directory` | `/clients` | `frontend/pages/clients/ClientDirectoryPage.tsx` | `frontend/modules/clients/` | `ClientsTable`, `CreateClientDrawer`, `EditClientDrawer` | `PageHeader`, `FilterBar`, `TableShell`, `StatusBadge` | `useClientsQuery`, `useCreateClientMutation`, `useUpdateClientMutation` |
| `Client Detail` | `/clients/:clientId` | `frontend/pages/clients/ClientDetailPage.tsx` | `frontend/modules/clients/` | `ClientSummaryCard`, `ClientContactsTable`, `ContactFormDialog`, `LinkedRequisitionsList` | `DetailCard`, `TableShell`, `DialogShell`, `StatusBadge` | `useClientDetailQuery`, `useClientContactsQuery`, `useCreateClientContactMutation`, `useUpdateClientContactMutation` |
| `Requisition List` | `/requisitions` | `frontend/pages/requisitions/RequisitionListPage.tsx` | `frontend/modules/requisitions/` | `RequisitionsTable`, `RequisitionFilterBar`, `QuickStatusChips` | `PageHeader`, `FilterBar`, `TableShell`, `StatusBadge` | `useRequisitionsQuery` |
| `Requisition Intake` | `/requisitions/new`, `/requisitions/:requisitionId/edit` | `frontend/pages/requisitions/RequisitionIntakePage.tsx` | `frontend/modules/requisitions/` | `RequisitionForm`, `ClientContactSelector`, `SkillsSection`, `OwnerSection`, `PipelineTemplateSection` | `FormSection`, `FormGrid`, `ActionBar`, `InlineBanner` | `useRequisitionFormBootstrapQuery`, `useCreateRequisitionMutation`, `useUpdateRequisitionMutation`, `useClientContactsQuery` |
| `Requisition Detail` | `/requisitions/:requisitionId` | `frontend/pages/requisitions/RequisitionDetailPage.tsx` | `frontend/modules/requisitions/` | `RequisitionSummaryCard`, `OwnerSummaryCard`, `AssignmentPanel`, `StatusUpdateDialog`, `AssignmentHistoryDrawer`, `ReassignOwnerDialog` | `DetailCard`, `DialogShell`, `DrawerShell`, `Timeline`, `StatusBadge` | `useRequisitionDetailQuery`, `useRequisitionAssignmentsQuery`, `useUpdateRequisitionStatusMutation`, `useAddAssignmentMutation`, `useRemoveAssignmentMutation`, `useReassignRequisitionOwnerMutation` |
| `Candidate Profiles` | `/candidates` | `frontend/pages/candidates/CandidateProfilesPage.tsx` | `frontend/modules/candidates/` | `CandidatesTable`, `CandidateForm`, `DuplicateWarningModal`, `LinkToRequisitionDialog`, `SocialProfilesSection` | `PageHeader`, `FilterBar`, `TableShell`, `DialogShell`, `FormSection` | `useCandidatesQuery`, `useCreateCandidateMutation`, `useUpdateCandidateMutation`, `useCandidateDuplicateCheckMutation`, `useLinkCandidateToRequisitionMutation` |
| `Resume Upload And Review` | `/candidates/upload/:candidateId` | `frontend/pages/candidates/ResumeUploadReviewPage.tsx` | `frontend/modules/candidates/` | `ResumeUploadZone`, `ParsedResumeReview`, `DocumentMetadataForm` | `FormSection`, `InlineBanner`, `ActionBar` | `useCandidateDetailQuery`, `useUploadCandidateDocumentMutation` |
| `Candidate Duplicate Review` | `/candidates/duplicate-review/:caseId` | `frontend/pages/candidates/CandidateDuplicateReviewPage.tsx` | `frontend/modules/candidates/` | `DuplicateCaseSummary`, `CandidateCompareView`, `DuplicateDecisionFooter` | `DetailCard`, `Timeline`, `PermissionAwareAction`, `InlineBanner` | `useDuplicateCaseDetailQuery`, `useResolveDuplicateCaseMutation` |
| `Pipeline Board` | `/pipeline` | `frontend/pages/pipeline/PipelineBoardPage.tsx` | `frontend/modules/pipeline/` | `PipelineFilters`, `PipelineColumns`, `ApplicationDetailDrawer`, `StageMoveDialog`, `PipelineHistoryDrawer` | `FilterBar`, `DrawerShell`, `DialogShell`, `StatusBadge`, `Timeline` | `usePipelineBoardQuery`, `usePipelineApplicationDetailQuery`, `useMovePipelineStageMutation`, `usePipelineHistoryQuery` |
| `Daily Updates Submission` | `/daily-updates/submit` | `frontend/pages/daily-updates/DailyUpdatesSubmissionPage.tsx` | `frontend/modules/daily-updates/` | `DailyUpdateForm`, `LinkedRequisitionSelector`, `SubmissionHistoryStrip` | `FormSection`, `ActionBar`, `InlineBanner` | `useMyDailyUpdatesQuery`, `useLinkedRequisitionsQuery`, `useSubmitDailyUpdateMutation` |
| `Daily Updates Review` | `/daily-updates/review` | `frontend/pages/daily-updates/DailyUpdatesReviewPage.tsx` | `frontend/modules/daily-updates/` | `DailyUpdatesTable`, `BlockerHighlightCards`, `UpdateDetailPanel` | `PageHeader`, `FilterBar`, `TableShell`, `DrawerShell` | `useTeamDailyUpdatesQuery`, `usePipelineSummaryQuery` |
| `Notifications Center` | `/notifications` | `frontend/pages/notifications/NotificationsCenterPage.tsx` | `frontend/modules/notifications/` | `NotificationsList`, `NotificationDetailPanel` | `PageHeader`, `TableShell`, `DrawerShell`, `StatusBadge` | `useNotificationsQuery`, `useMarkNotificationReadMutation` |
| `Location Dashboard` | `/reports/location` | `frontend/pages/dashboard/LocationDashboardPage.tsx` | `frontend/modules/dashboard/` | `LocationKpiStrip`, `PipelineVolumeChart`, `ClosureStatsWidget`, `UpdateComplianceWidget` | `KpiCard`, `DetailCard`, `EmptyState`, `ErrorState` | `useLocationDashboardQuery` |
| `Company Dashboard` | `/reports/company` | `frontend/pages/dashboard/CompanyDashboardPage.tsx` | `frontend/modules/dashboard/` | `CompanyKpiStrip`, `LocationComparisonGrid`, `TrendCharts`, `TopRiskTable` | `KpiCard`, `DetailCard`, `TableShell`, `ErrorState` | `useCompanyDashboardQuery` |

## Suggested Module Folder Expansion

Recommended deeper module structure:

```text
frontend/modules/
  auth/
    components/
    hooks/
  dashboard/
    components/
    widgets/
    hooks/
  admin/
    locations/
      components/
      hooks/
    users/
      components/
      hooks/
    roles/
      components/
      hooks/
  clients/
    components/
    hooks/
  requisitions/
    components/
    hooks/
  candidates/
    components/
    hooks/
  pipeline/
    components/
    hooks/
  daily-updates/
    components/
    hooks/
  notifications/
    components/
    hooks/
```

## Suggested Shared Component Placement

Examples:

- `frontend/components/data-display/TableShell.tsx`
- `frontend/components/data-display/DetailCard.tsx`
- `frontend/components/data-display/KpiCard.tsx`
- `frontend/components/forms/FormSection.tsx`
- `frontend/components/forms/FormGrid.tsx`
- `frontend/components/navigation/Breadcrumbs.tsx`
- `frontend/components/feedback/EmptyState.tsx`
- `frontend/components/feedback/ErrorState.tsx`
- `frontend/components/feedback/RestrictedState.tsx`
- `frontend/components/overlays/DialogShell.tsx`
- `frontend/components/overlays/DrawerShell.tsx`
- `frontend/components/actions/PermissionAwareAction.tsx`

## Suggested Data Folder Placement

Examples:

- `frontend/data/api/client.ts`
- `frontend/data/auth/session.ts`
- `frontend/data/adapters/requisition.ts`
- `frontend/data/api/locations.ts`
- `frontend/data/api/users.ts`
- `frontend/data/api/clients.ts`
- `frontend/data/api/requisitions.ts`
- `frontend/data/api/candidates.ts`
- `frontend/data/api/pipeline.ts`
- `frontend/data/api/daily-updates.ts`
- `frontend/data/api/notifications.ts`
- `frontend/data/api/reports.ts`

## Implementation Order Guidance

Build in this order for best momentum:

1. `Login`
2. `Access Denied`
3. `Location Management`
4. `Role Management`
5. `User Management`
6. `Client Directory`
7. `Client Detail`
8. `Requisition List`
9. `Requisition Intake`
10. `Requisition Detail`
11. `Candidate Profiles`
12. `Candidate Duplicate Review`
13. `Pipeline Board`
14. `Daily Updates Submission`
15. `Daily Updates Review`
16. `My Work Dashboard`
17. `Role Dashboard`
18. `Location Dashboard`
19. `Company Dashboard`
20. `Notifications Center`

## QA And Review Use

This matrix should also help QA and review teams check:

- page file exists where expected
- route points to the correct page file
- business UI lives inside module folders, not random shared folders
- reusable UI is actually shared
- page actions have matching data hooks

## Final Delivery Rule

Frontend implementation planning is incomplete if a page is missing:

- route path
- page file suggestion
- module ownership
- shared component list
- hook or service plan

If one of these is missing, the page is not ready for engineering handoff.
