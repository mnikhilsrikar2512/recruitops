# API Validation Rules

## Purpose

This document converts the product use cases, exceptions, and system rules into API-facing validation behavior.

It is intended for:

- backend implementation
- request validation design
- service-layer rule enforcement
- exception handling design
- QA API test design

This is not a full OpenAPI file.

It is the rulebook for:

- what the API must validate
- when the API must reject a request
- when the API may allow draft/save behavior
- when the API must require approval, review, or exception workflow

## Source Documents

This document is aligned to:

- [MODULE_WISE_USE_CASES_AND_EXCEPTIONS.md](/Users/bhargavnikhil/Desktop/recrutment system/docs/system/MODULE_WISE_USE_CASES_AND_EXCEPTIONS.md)
- [SYSTEM_RULES_AND_VALIDATIONS.md](/Users/bhargavnikhil/Desktop/recrutment system/docs/system/SYSTEM_RULES_AND_VALIDATIONS.md)
- [API_ENDPOINTS.md](/Users/bhargavnikhil/Desktop/recrutment system/docs/system/API_ENDPOINTS.md)
- [DATABASE_DESIGN.md](/Users/bhargavnikhil/Desktop/recrutment system/docs/system/DATABASE_DESIGN.md)

## Validation Layers

Every important API should validate across these layers:

- request shape validation
  - required fields
  - type checks
  - enum checks
  - length checks
- reference validation
  - foreign key existence
  - status of referenced records
  - same-location or same-scope rules
- business rule validation
  - allowed workflow transitions
  - ownership rules
  - uniqueness rules
  - duplicate rules
- permission validation
  - module access
  - action access
  - scope access
- exception routing
  - reject immediately
  - save as draft
  - create review request
  - require approval

## Error Handling Standard

The API should return clear and stable validation responses.

Recommended response categories:

- `400 Bad Request`
  - malformed or logically invalid payload
- `401 Unauthorized`
  - missing or invalid authentication
- `403 Forbidden`
  - valid user but action or scope not allowed
- `404 Not Found`
  - referenced entity does not exist
- `409 Conflict`
  - duplicate, conflicting state, or uniqueness failure
- `422 Unprocessable Entity`
  - semantically valid JSON but business validation failed

## Draft Versus Final Rule

Where draft workflow exists:

- draft save may allow partial completeness
- final save must enforce all required business rules

If a request attempts final submission without mandatory completion:

- API should reject final submit
- API may optionally suggest draft fallback in client behavior

## Module 1. Authentication And Session Control

### Endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/permissions/me`

### Request Validation Rules

- login requires:
  - email
  - password
- email must be normalized to lowercase and trimmed
- password must not be empty
- bearer token must be present for authenticated endpoints

### Business Validation Rules

- user must exist for login
- password must match stored password hash
- user status must allow access
- session must not be expired
- session must not be revoked

### Exception Handling

- invalid credentials:
  - return `401`
- revoked or expired session:
  - return `401`
- inactive or suspended user:
  - return `403`
- permission payload request without valid session:
  - return `401`

## Module 2. Roles, Permissions, And Access Configuration

### Endpoints

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`

### Request Validation Rules

- role create requires:
  - role name
  - role code
  - status
- role update must include at least one editable field
- permission assignment requires:
  - target role
  - permission identifiers list

### Reference Validation Rules

- target role must exist
- assigned permissions must exist
- role code should be unique where product rules require uniqueness

### Business Validation Rules

- sensitive permission combinations should be reviewable
- deactivated roles should not be assignable to new users
- permission updates should replace or reconcile prior mapping deterministically

### Exception Handling

- role not found:
  - return `404`
- invalid permission id in assignment:
  - return `404` or `422`
- duplicate role code:
  - return `409`
- dangerous access combination:
  - allow save only if policy allows or flag for review workflow

## Module 3. Location And User Administration

### Endpoints

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`

### Location Validation Rules

- location create requires:
  - location name
  - location code
  - status
- location code should be unique if used as a business identifier
- deactivated locations should not receive new operational users unless explicitly allowed

### User Validation Rules

- user create requires:
  - full name
  - email
  - phone number if company policy requires it
  - employee code if company uses employee ids
  - primary location
  - primary role
  - reporting manager if policy requires it
- user update must include at least one editable field
- reset credentials requires reset mode

### Reference Validation Rules

- primary location must exist
- primary location must be active for operational users
- primary role must exist and be active
- reporting manager must exist
- reporting manager cannot be the same as the target user

### Business Validation Rules

- email must be unique
- employee code must be unique where enabled
- status changes should not silently strand active assignments
- moving a user to another location should trigger reassignment review when active owned work exists

### Exception Handling

- duplicate email:
  - return `409`
- duplicate employee code:
  - return `409`
- invalid location or role:
  - return `404`
- self-reporting manager:
  - return `400` or `422`
- location transfer with active work:
  - return `409` or create reassignment exception workflow

## Module 4. Client Directory

### Endpoints

- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`
- `PATCH /api/v1/clients/contacts/{contact_id}`

### Client Validation Rules

- client create requires:
  - client name
  - client code if code-based tracking is used
  - location
  - business source owner
  - client status
- client update must include at least one field

### Contact Validation Rules

- contact create requires:
  - contact name
  - client link
- at least one usable contact method is recommended
- contact update must include at least one editable field

### Reference Validation Rules

- client location must exist and be active
- business source owner must exist
- business source owner must belong to the same location unless cross-location policy permits otherwise
- client owner, if used, must exist and be location-compatible
- contact update target must exist

### Business Validation Rules

- client code should be unique
- client should remain location-bound
- same location should not create duplicate client entries without review
- primary and secondary contacts should not accidentally point to invalid records

### Exception Handling

- duplicate client code:
  - return `409`
- likely duplicate client by name:
  - return `409` or warning-plus-review flow depending on product policy
- cross-location client ownership attempt:
  - return `403` or route to exception request
- contact mapped outside the client:
  - return `422`

## Module 5. Requisition Management

### Endpoints

- `GET /api/v1/requisitions`
- `POST /api/v1/requisitions`
- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `GET /api/v1/requisitions/{requisition_id}/assignments`
- `POST /api/v1/requisitions/{requisition_id}/assignments`
- `DELETE /api/v1/requisitions/assignments/{assignment_id}`

### Request Validation Rules

- requisition create requires:
  - client
  - location
  - title
  - primary owner
  - openings
  - target closure date
  - job description
- must-have and good-to-have skills must be structured lists
- openings must be greater than zero
- status update requires:
  - target status
  - reason

### Reference Validation Rules

- client must exist
- client must belong to the same location as requisition
- primary owner must exist
- primary owner must belong to requisition location
- delivery owner, if present, must belong to requisition location
- selected client contacts must belong to the same client

### Business Validation Rules

- inactive client should not be used for normal requisition creation
- stage template must exist if provided
- status transition must be valid for current state
- reopening or reactivating closed work should capture reason

### Assignment Validation Rules

- assignee must exist
- assignee must belong to requisition location unless explicit exception path is used
- assignment type must be valid

### Exception Handling

- wrong-location owner:
  - return `422`
- closed requisition reopened:
  - require reason and audit trail
- inactive client:
  - return `409` or require controlled override
- reassignment after work starts:
  - require confirmation, audit, or approval flow

## Module 6. Candidate Management

### Endpoints

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`
- `POST /api/v1/candidates/{candidate_id}/documents`
- `GET /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/duplicate-check/decision`
- `POST /api/v1/candidates/{candidate_id}/finalize-profile`

### Request Validation Rules

- candidate create requires for normal final creation:
  - full name
  - source type
  - primary owner
- recommended business completeness for final flow:
  - email
  - phone
  - current company
  - resume
  - social profiles
- candidate update must include at least one field
- document create requires:
  - document type
  - file name
  - file path
  - uploaded by user
- duplicate decision requires:
  - decision
  - requested by user
- finalize requires:
  - requisition
  - initial stage
  - owner user

### Reference Validation Rules

- primary owner must exist
- sourced by user, if provided, must exist
- uploaded by user must exist
- requisition for finalize must exist
- application owner for finalize must exist
- application owner must belong to requisition location

### Business Validation Rules

- candidate should have at least one usable contact method for active workflow
- duplicate check should run before finalization where policy requires it
- finalization should not silently create conflicting active applications if duplicate restrictions exist
- duplicate review decisions must update duplicate state predictably

### Exception Handling

- duplicate detected:
  - return review payload instead of allowing silent final continuation
- duplicate override requested:
  - create review case and set blocked or in-review state
- invalid finalize target:
  - return `404` or `422`
- attempt to finalize incomplete profile:
  - return `422`
- wrong-location application owner:
  - return `422`

## Module 7. Pipeline Management

### Endpoints

- `GET /api/v1/pipeline/board`
- `GET /api/v1/pipeline/applications/{application_id}`
- `PATCH /api/v1/pipeline/applications/{application_id}/stage`
- `GET /api/v1/pipeline/applications/{application_id}/history`

### Request Validation Rules

- stage move requires:
  - target stage
- stage move may additionally require:
  - notes
  - rejection reason
  - joining date
  depending on stage type and company policy

### Reference Validation Rules

- target application must exist
- changed-by user, if passed, must exist
- target stage should belong to the requisition’s active pipeline template when template enforcement is enabled

### Business Validation Rules

- invalid forward or backward transitions must be blocked unless exception path exists
- joined status should not later move into incompatible rejection state
- rejection transitions should include rejection reason where required
- stage history must always be preserved for stage changes

### Exception Handling

- stage not in active template:
  - return `422`
- unauthorized scope access:
  - return `403`
- invalid post-joined transition:
  - return `409`
- forced stage skip:
  - require approval path or exception logging based on policy

## Module 8. Daily Updates

### Endpoints

- `GET /api/v1/daily-updates`
- `POST /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`

### Request Validation Rules

- create requires:
  - update date
  - requisition
  - submitted by user
  - summary
- counters must be zero or positive integers

### Reference Validation Rules

- submitting user must exist
- requisition must exist
- submitting user must belong to the same location as requisition

### Business Validation Rules

- draft versus submitted behavior should be explicit
- multiple final updates for same date and requisition should follow company policy
- counts should not silently violate impossible state rules if deeper reconciliation is later implemented

### Exception Handling

- wrong-location submitter:
  - return `422`
- duplicate final update for same date and requisition:
  - return `409` or merge by configured policy
- missed period backfill:
  - allow only through approved catch-up flow if reporting rules require it

## Module 9. Dashboards

### Endpoints

- `GET /api/v1/dashboards/role`
- `GET /api/v1/dashboards/my-work`

### Validation Rules

- authentication is mandatory
- dashboard aggregation must always respect:
  - role
  - location
  - ownership scope

### Business Validation Rules

- role dashboard must not expose records outside access boundary
- my-work dashboard should reflect only the current authenticated user context

### Exception Handling

- stale or delayed summary data:
  - return available data but system should support freshness indicators later
- access scope mismatch:
  - return filtered response, never over-broad response

## Module 10. Notifications

### Endpoints

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

### Request Validation Rules

- list filters may include:
  - status
  - priority
- mark-read requires:
  - valid target notification

### Reference Validation Rules

- notification must exist
- notification must belong to the authenticated user

### Business Validation Rules

- only the owning user should update read status
- read operation should be idempotent where possible

### Exception Handling

- notification belongs to another user:
  - return `403`
- notification not found:
  - return `404`
- already read notification:
  - API may still return success with unchanged read timestamp depending on implementation policy

## Cross-Module Validation Rules

### Location Safety

- no normal operational API should permit silent cross-location work leakage
- when a location-based restriction is violated:
  - reject
  - or route to controlled exception workflow

### Ownership Safety

- ownership changes must preserve history
- reassignment after work begins must not silently overwrite responsibility trails

### Duplicate Safety

- duplicate handling must use structured states
- review-required situations must not be downgraded into simple warnings

### Permission Safety

- visibility and edit rights must be enforced separately
- upward visibility should not imply edit permission

## Approval-Sensitive API Actions

These actions should either:

- be blocked in MVP
- or create explicit approval/exception records

Examples:

- duplicate override
- candidate transfer between locations
- forced cross-location client or requisition access
- reassignment after work is already in progress
- reopening locked or finalized reporting periods
- invalid stage skip outside standard pipeline rules

## Recommended QA Conversion

From this document, QA should derive:

- valid request tests
- missing field tests
- wrong reference tests
- permission denial tests
- cross-location denial tests
- duplicate conflict tests
- state transition conflict tests
- approval-sensitive exception tests
