# MVP Frontend Hook And Adapter Contract

## Purpose

This document defines the recommended contract for frontend data hooks and API response adapters in the MVP.

It is the build reference for:

- query hook shape
- mutation hook shape
- parameter naming
- returned loading and error state
- response normalization
- adapter responsibilities

Use this together with:

- `docs/system/MVP_FRONTEND_IMPLEMENTATION_MATRIX.md`
- `docs/system/MVP_PAGE_API_PAYLOAD_MAP.md`
- `docs/system/BUILD_PACK_API_IMPLEMENTATION_CONTRACT.md`
- `docs/system/BUILD_PACK_FRONTEND_ARCHITECTURE.md`

## Core Rule

Frontend pages and module components should not consume raw backend responses directly unless the response is already clean and final for UI use.

Prefer this pattern:

1. API client fetches server response
2. adapter normalizes server payload
3. hook exposes stable UI-friendly state
4. page consumes the hook, not the raw API client

## Recommended Data Layer Shape

```text
frontend/data/
  api/
    auth.ts
    locations.ts
    users.ts
    roles.ts
    clients.ts
    requisitions.ts
    candidates.ts
    pipeline.ts
    daily-updates.ts
    notifications.ts
    reports.ts
  adapters/
    auth.ts
    locations.ts
    users.ts
    roles.ts
    clients.ts
    requisitions.ts
    candidates.ts
    pipeline.ts
    daily-updates.ts
    notifications.ts
    reports.ts
  auth/
    session.ts
```

## Standard Query Hook Contract

Every query hook should aim to return:

```ts
type QueryHookResult<TData, TFilters = unknown> = {
  data: TData
  rawData?: unknown
  filters?: TFilters
  isLoading: boolean
  isFetching: boolean
  isError: boolean
  error: UiError | null
  refetch: () => Promise<unknown>
}
```

## Standard Mutation Hook Contract

Every mutation hook should aim to return:

```ts
type MutationHookResult<TPayload, TResult> = {
  mutate: (payload: TPayload) => Promise<TResult>
  isPending: boolean
  isSuccess: boolean
  isError: boolean
  error: UiError | null
  reset: () => void
}
```

## Standard UI Error Shape

Prefer one UI error model:

```ts
type UiError = {
  code: string
  message: string
  fieldErrors?: Record<string, string>
  details?: string[]
  severity?: "info" | "warning" | "error"
}
```

## Adapter Responsibility Rules

Adapters should do these jobs:

- unwrap `success`, `data`, and `meta`
- rename backend fields only when the UI needs simpler naming
- normalize missing arrays to empty arrays
- normalize missing counts to `0`
- flatten nested values that are awkward for page components
- convert server error shapes into `UiError`

Adapters should not do these jobs:

- trigger navigation
- open dialogs
- perform permission decisions
- own page-specific presentation text

## Query Hook Responsibility Rules

Query hooks should:

- call one or more APIs as needed
- pass results through adapters
- expose stable loading and error flags
- expose filter state only when the hook owns server query filters
- expose `refetch`

Query hooks should not:

- embed page JSX
- own dialog state
- know page layout decisions

## Mutation Hook Responsibility Rules

Mutation hooks should:

- accept a typed payload
- call one API action
- adapt the success result
- adapt the error result
- expose predictable pending and error state

Mutation hooks should not:

- hard-code toast messages
- perform route navigation
- mutate unrelated page state directly

## Authentication Hooks

### `useAuthSession`

Purpose:

- expose current authenticated session state to route guards and app shell

Input params:

- none or optional bootstrap options

Return shape:

```ts
type AuthSessionState = {
  isAuthenticated: boolean
  token: string | null
  user: {
    id: number
    fullName: string
    email: string
    businessTitle?: string
  } | null
  primaryRole: {
    id: number
    code: string
    name: string
  } | null
  primaryLocation: {
    id: number
    code: string
    name: string
  } | null
  isBootstrapping: boolean
}
```

Adapter responsibility:

- normalize login response into session model
- normalize `auth/me` response into the same session model

### `usePermissionContext`

Purpose:

- expose allowed pages, permissions, and scope summary to guards and page actions

Input params:

- none

Return shape:

```ts
type PermissionContextState = {
  permissions: string[]
  allowedPages: string[]
  scopes: Record<string, string>
  isLoading: boolean
  error: UiError | null
}
```

Adapter responsibility:

- normalize permission and scope payload
- ensure arrays always return arrays

### `useLoginMutation`

Purpose:

- submit login credentials

Payload:

```ts
type LoginPayload = {
  email: string
  password: string
}
```

Success result:

- normalized auth session data

Error shape:

- invalid credentials
- inactive user
- generic auth failure

## Admin Hooks

### `useLocationsQuery`

Purpose:

- load location list with server-side filters

Input params:

```ts
type LocationListFilters = {
  page?: number
  pageSize?: number
  search?: string
  status?: "active" | "inactive"
}
```

Return `data` shape:

```ts
type LocationListData = {
  items: Array<{
    id: number
    code: string
    name: string
    status: string
    locationHeadName?: string
  }>
  total: number
}
```

Adapter responsibility:

- map `location_code` to `code`
- map `location_name` to `name`
- flatten `location_head.full_name` into `locationHeadName`

### `useCreateLocationMutation`

Payload:

```ts
type CreateLocationPayload = {
  locationName: string
  locationCode: string
  address?: string
  status: "active" | "inactive"
  locationHeadUserId?: number
}
```

Mutation must transform payload to backend names:

- `locationName` -> `location_name`
- `locationCode` -> `location_code`
- `locationHeadUserId` -> `location_head_user_id`

Success result:

- new location summary

### `useUpdateLocationMutation`

Purpose:

- update existing location

Same adapter rules as create.

### `useUsersQuery`

Input params:

```ts
type UserListFilters = {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  locationId?: number
}
```

Return `data` shape:

```ts
type UserListData = {
  items: Array<{
    id: number
    employeeCode: string
    fullName: string
    email: string
    phone: string
    status: string
    primaryRoleName?: string
    primaryLocationName?: string
  }>
  total: number
}
```

Adapter responsibility:

- flatten nested role and location names
- preserve id references for row actions

### `useCreateUserMutation`

Payload:

```ts
type CreateUserPayload = {
  fullName: string
  email: string
  phone: string
  employeeCode: string
  primaryLocationId: number
  primaryRoleId: number
  reportingManagerUserId?: number
  businessTitle?: string
  secondaryContact?: string
  status: string
}
```

Mutation transform:

- camelCase form payload to backend snake_case

Error adapter must support field errors for:

- email
- phone
- employeeCode
- reportingManagerUserId

### `useUpdateUserMutation`

Same payload shape as create, usually without immutable identity fields if the UI locks them.

### `useUserDetailQuery`

Purpose:

- load one user detail and active work impact summary if needed

Return `data` shape:

```ts
type UserDetailData = {
  id: number
  fullName: string
  status: string
  businessTitle?: string
  roleName?: string
  locationName?: string
  activeWorkCounts?: {
    requisitions: number
    candidates: number
    dailyUpdates: number
  }
}
```

### `useDeactivateUserMutation`

Payload:

```ts
type DeactivateUserPayload = {
  replacementUserId?: number
  reviewNote?: string
}
```

Adapter responsibility:

- normalize `APPROVAL_REQUIRED` or review-required errors into a warning-style `UiError`

### `useRolesQuery`

Return `data` shape:

```ts
type RoleListData = {
  items: Array<{
    id: number
    code: string
    name: string
    status: string
    assignedUsersCount: number
  }>
  total: number
}
```

### `useCreateRoleMutation`

Payload:

```ts
type CreateRolePayload = {
  name: string
  code: string
  description?: string
  status: string
}
```

### `useAssignRolePermissionsMutation`

Payload:

```ts
type AssignRolePermissionsPayload = {
  roleId: number
  permissionCodes: string[]
  scopeRules: Record<string, string>
  allowedPages?: string[]
}
```

Error adapter must normalize:

- invalid permission code
- invalid scope value
- forbidden error

## Client Hooks

### `useClientsQuery`

Input params:

```ts
type ClientListFilters = {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  locationId?: number
}
```

Return `data` shape:

```ts
type ClientListData = {
  items: Array<{
    id: number
    clientCode: string
    clientName: string
    status: string
    locationName?: string
    clientOwnerName?: string
    businessSourceOwnerName?: string
  }>
  total: number
}
```

### `useCreateClientMutation`

Payload must map:

- `clientName` -> `client_name`
- `clientCode` -> `client_code`
- `locationId` -> `location_id`
- `clientOwnerUserId` -> `client_owner_user_id`
- `businessSourceOwnerUserId` -> `business_source_owner_user_id`

### `useUpdateClientMutation`

Use same payload shape as create.

### `useClientDetailQuery`

Return `data` shape:

```ts
type ClientDetailData = {
  id: number
  clientCode: string
  clientName: string
  status: string
  locationName?: string
  activeRequisitionsCount: number
  contacts: Array<unknown>
}
```

### `useClientContactsQuery`

Purpose:

- load contacts for selected client

Adapter must ensure:

- empty contact list returns `[]`

### `useCreateClientContactMutation`

Payload must map UI booleans to backend fields:

- `isPrimary` -> `is_primary`
- `isSecondary` -> `is_secondary`

### `useUpdateClientContactMutation`

Use same payload shape as create.

## Requisition Hooks

### `useRequisitionsQuery`

Input params:

```ts
type RequisitionListFilters = {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  clientId?: number
  locationId?: number
}
```

Return `data` shape:

```ts
type RequisitionListData = {
  items: Array<{
    id: number
    requisitionCode: string
    title: string
    status: string
    priority?: string
    clientName?: string
  }>
  total: number
}
```

### `useRequisitionFormBootstrapQuery`

Purpose:

- load dropdown dependencies required by `Requisition Intake`

Return `data` shape:

```ts
type RequisitionFormBootstrapData = {
  clients: Array<{ id: number; name: string }>
  contacts: Array<{ id: number; name: string }>
  owners: Array<{ id: number; name: string }>
  pipelineTemplates: Array<{ id: number; name: string }>
}
```

Adapter responsibility:

- aggregate multiple list sources if needed

### `useCreateRequisitionMutation`

Payload must map:

- `clientId` -> `client_id`
- `clientContactId` -> `client_contact_id`
- `locationId` -> `location_id`
- `targetClosureDate` -> `target_closure_date`
- `profileUpdateAvailabilityTime` -> `profile_update_availability_time`
- `primaryOwnerUserId` -> `primary_owner_user_id`
- `deliveryOwnerUserId` -> `delivery_owner_user_id`
- `pipelineTemplateId` -> `pipeline_template_id`

### `useUpdateRequisitionMutation`

Use the same adapter mapping as create.

### `useRequisitionDetailQuery`

Return `data` shape:

```ts
type RequisitionDetailData = {
  id: number
  requisitionCode: string
  title: string
  status: string
  priority?: string
  clientName?: string
  primaryOwnerName?: string
  deliveryOwnerName?: string
}
```

### `useRequisitionAssignmentsQuery`

Return `data` shape:

```ts
type RequisitionAssignmentsData = {
  items: Array<{
    assignmentId: number
    userId: number
    userName: string
    assignmentRole: string
    status: string
  }>
}
```

### `useUpdateRequisitionStatusMutation`

Payload:

```ts
type UpdateRequisitionStatusPayload = {
  status: string
  reason?: string
}
```

### `useAddAssignmentMutation`

Payload:

```ts
type AddAssignmentPayload = {
  requisitionId: number
  userId: number
  assignmentRole: string
  note?: string
}
```

### `useRemoveAssignmentMutation`

Payload:

```ts
type RemoveAssignmentPayload = {
  assignmentId: number
  reviewNote?: string
}
```

### `useReassignRequisitionOwnerMutation`

Payload:

```ts
type ReassignRequisitionOwnerPayload = {
  requisitionId: number
  fromUserId: number
  toUserId: number
  reason: string
}
```

Adapter must normalize review-required responses clearly.

## Candidate Hooks

### `useCandidatesQuery`

Input params:

```ts
type CandidateListFilters = {
  page?: number
  pageSize?: number
  search?: string
  ownerId?: number
  duplicateState?: string
}
```

Return `data` shape:

```ts
type CandidateListData = {
  items: Array<{
    id: number
    fullName: string
    primaryPhone?: string
    primaryEmail?: string
    ownerName?: string
    duplicateState?: string
  }>
  total: number
}
```

### `useCreateCandidateMutation`

Payload must map:

- `fullName` -> `full_name`
- `primaryPhone` -> `primary_phone`
- `primaryEmail` -> `primary_email`
- `secondaryContact` -> `secondary_contact`
- `sourceOwnerUserId` -> `source_owner_user_id`
- `candidateOwnerUserId` -> `candidate_owner_user_id`
- `socialProfiles` -> `social_profiles`

### `useUpdateCandidateMutation`

Use same mapping as create where applicable.

### `useCandidateDetailQuery`

Return `data` shape:

```ts
type CandidateDetailData = {
  id: number
  fullName: string
  status: string
  skills: string[]
  duplicateState?: string
  applications?: Array<unknown>
}
```

### `useCandidateDuplicateCheckMutation`

Payload:

```ts
type CandidateDuplicateCheckPayload = {
  fullName: string
  primaryPhone?: string
  primaryEmail?: string
}
```

Success result:

```ts
type CandidateDuplicateCheckResult = {
  duplicateState: string
  matches: Array<{
    candidateId: number
    fullName: string
    primaryPhone?: string
    primaryEmail?: string
  }>
}
```

### `useLinkCandidateToRequisitionMutation`

Payload:

```ts
type LinkCandidateToRequisitionPayload = {
  candidateId: number
  requisitionId: number
  submittedByUserId: number
  initialStageCode: string
  note?: string
}
```

### `useUploadCandidateDocumentMutation`

Payload:

```ts
type UploadCandidateDocumentPayload = {
  candidateId: number
  file: File
  documentType?: string
  note?: string
}
```

Adapter should normalize upload result into a minimal document summary.

### `useDuplicateCaseDetailQuery`

Return `data` shape:

```ts
type DuplicateCaseDetailData = {
  caseId: number
  reviewStatus: string
  submittedCandidate: unknown
  possibleMatches: unknown[]
}
```

### `useResolveDuplicateCaseMutation`

Payload:

```ts
type ResolveDuplicateCasePayload = {
  caseId: number
  decision: string
  approvedByUserId: number
  note: string
}
```

## Pipeline Hooks

### `usePipelineBoardQuery`

Input params:

```ts
type PipelineBoardFilters = {
  requisitionId?: number
  ownerId?: number
  stageCode?: string
}
```

Return `data` shape:

```ts
type PipelineBoardData = {
  stages: Array<{
    stageCode: string
    stageName: string
    count: number
    applications: Array<{
      applicationId: number
      candidateName: string
      ownerName?: string
      agingDays?: number
    }>
  }>
}
```

Adapter responsibility:

- convert snake_case stage payload to camelCase
- flatten nested candidate and owner display values

### `usePipelineApplicationDetailQuery`

Return `data` shape:

```ts
type PipelineApplicationDetailData = {
  applicationId: number
  candidateId: number
  candidateName: string
  requisitionId: number
  requisitionTitle: string
  currentStageCode: string
  historyCount: number
}
```

### `useMovePipelineStageMutation`

Payload:

```ts
type MovePipelineStagePayload = {
  applicationId: number
  targetStageCode: string
  note?: string
  rejectionReason?: string | null
  joiningDate?: string | null
}
```

Error adapter must support:

- invalid stage
- backward move restriction
- missing rejection reason
- missing joining date

### `usePipelineHistoryQuery`

Return `data` shape:

```ts
type PipelineHistoryData = {
  items: Array<{
    stageCode: string
    stageName: string
    movedByName?: string
    movedAt: string
    note?: string
  }>
}
```

## Daily Update Hooks

### `useMyDailyUpdatesQuery`

Input params:

```ts
type MyDailyUpdatesFilters = {
  userId?: number
  date?: string
}
```

Return `data` shape:

```ts
type MyDailyUpdatesData = {
  items: Array<{
    id: number
    requisitionId: number
    requisitionTitle: string
    status: string
    submittedAt?: string
  }>
}
```

### `useLinkedRequisitionsQuery`

Purpose:

- load requisitions the current user can submit updates for

Return `data` shape:

```ts
type LinkedRequisitionsData = {
  items: Array<{
    id: number
    title: string
  }>
}
```

### `useSubmitDailyUpdateMutation`

Payload:

```ts
type SubmitDailyUpdatePayload = {
  requisitionId: number
  updateDate: string
  submittedByUserId: number
  profilesSourcedCount?: number
  profilesSubmittedCount?: number
  interviewsScheduledCount?: number
  blockers?: string
  nextSteps?: string
  note?: string
}
```

Error adapter must support:

- duplicate same-day update
- unlinked requisition
- forbidden error

### `useTeamDailyUpdatesQuery`

Input params:

```ts
type TeamDailyUpdatesFilters = {
  locationId?: number
  date?: string
  status?: string
}
```

### `usePipelineSummaryQuery`

Purpose:

- load management-level pipeline and progress summary widgets

## Dashboard And Reporting Hooks

### `useRoleDashboardQuery`

Return `data` shape:

```ts
type RoleDashboardData = {
  kpis: Array<{ label: string; value: number }>
  urgentItems: unknown[]
  pendingDuplicateCases: unknown[]
  pendingUpdates: unknown[]
}
```

### `useMyWorkDashboardQuery`

Return `data` shape:

```ts
type MyWorkDashboardData = {
  openRequisitionsCount: number
  myPipelineCount: number
  dailyUpdatePendingCount: number
  stalledCandidatesCount: number
}
```

### `useNotificationSummaryQuery`

Purpose:

- load top-bar notification counters if needed

### `useLocationDashboardQuery`

Input params:

```ts
type LocationDashboardFilters = {
  locationId?: number
  dateFrom?: string
  dateTo?: string
}
```

Return `data` shape:

```ts
type LocationDashboardData = {
  locationName?: string
  openRequisitionsCount: number
  activePipelineCount: number
  submittedUpdatesCount: number
}
```

### `useCompanyDashboardQuery`

Input params:

```ts
type CompanyDashboardFilters = {
  dateFrom?: string
  dateTo?: string
}
```

Return `data` shape:

```ts
type CompanyDashboardData = {
  totalLocationsCount: number
  openRequisitionsCount: number
  activePipelineCount: number
  submittedUpdatesCount: number
}
```

## Notification Hooks

### `useNotificationsQuery`

Input params:

```ts
type NotificationListFilters = {
  page?: number
  pageSize?: number
  status?: "unread" | "read"
}
```

Return `data` shape:

```ts
type NotificationListData = {
  items: Array<{
    id: number
    type: string
    title: string
    isRead: boolean
    linkedEntityType?: string
    linkedEntityId?: number
  }>
  total: number
}
```

### `useMarkNotificationReadMutation`

Payload:

```ts
type MarkNotificationReadPayload = {
  notificationId: number
}
```

## Adapter Error Mapping Guide

Map backend error codes into consistent frontend handling:

- `AUTH_REQUIRED`
  route guard or session refresh logic
- `AUTH_INVALID`
  login error banner
- `FORBIDDEN`
  restricted state or disabled action explanation
- `VALIDATION_ERROR`
  field errors and form banner
- `NOT_FOUND`
  detail page not-found or record-missing state
- `CONFLICT`
  business conflict banner
- `DUPLICATE_DETECTED`
  duplicate review path
- `APPROVAL_REQUIRED`
  review-required state
- `LOCATION_ACCESS_DENIED`
  restricted scope state

## Response Adapter Examples

### Example: location list adapter

Input:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "location_code": "HYD",
        "location_name": "Hyderabad",
        "status": "active",
        "location_head": {
          "full_name": "Alex Rao"
        }
      }
    ]
  },
  "meta": {
    "total": 1
  }
}
```

Output:

```ts
{
  items: [
    {
      id: 1,
      code: "HYD",
      name: "Hyderabad",
      status: "active",
      locationHeadName: "Alex Rao"
    }
  ],
  total: 1
}
```

### Example: pipeline board adapter

Input:

```json
{
  "success": true,
  "data": {
    "stages": [
      {
        "stage_code": "sourced",
        "stage_name": "Sourced",
        "count": 4,
        "applications": [
          {
            "application_id": 400,
            "candidate": {
              "full_name": "Priya Rao"
            },
            "owner": {
              "full_name": "Neha"
            },
            "aging_days": 2
          }
        ]
      }
    ]
  }
}
```

Output:

```ts
{
  stages: [
    {
      stageCode: "sourced",
      stageName: "Sourced",
      count: 4,
      applications: [
        {
          applicationId: 400,
          candidateName: "Priya Rao",
          ownerName: "Neha",
          agingDays: 2
        }
      ]
    }
  ]
}
```

## Final Delivery Rule

Frontend data-layer planning is incomplete if a hook is missing:

- its input params
- its return shape
- its loading and error contract
- its adapter responsibility

If those are missing, implementation consistency will drift across the team.
