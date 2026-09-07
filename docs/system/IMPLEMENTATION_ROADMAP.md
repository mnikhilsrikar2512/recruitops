# Recruitment System Execution Plan

This roadmap resets the project around what is actually present in the repository on August 13, 2026.

## Important Note

This roadmap now assumes the universal architecture described in `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md`.

That means implementation should not hard-code one fixed hierarchy such as `Admin -> Manager -> HR -> Recruiter`.

Execution should instead be based on:

- permission roles
- business titles
- reporting relationships
- visibility scopes
- workflow ownership

## Current State

The repository already has strong planning assets:

- product and system documentation in `docs/system/`
- a broad API scope in `docs/system/API_ENDPOINTS.md`
- a detailed SQL-first schema draft in `scripts/001_recruitment_system_mssql_schema.sql`
- seed data scripts in `scripts/002_*`, `003_*`, and `004_*`
- a large stitched frontend prototype in `frontend/`

The repository does not yet have a real application backend, running API server, migrations framework, authentication implementation, or persistent integration between the frontend and backend.

## Planning Reset

Frontend expansion should pause until the operational backend exists.

The next goal is not "finish more screens." The next goal is:

Build the smallest backend slice that can support real login, real users, real requisitions, real candidates, and real daily updates.

The detailed scope for that slice now lives in `docs/system/WORKING_MODEL.md`.

## Execution Principles

- Build backend-first from the existing docs and schema
- Treat the frontend as a consumer, not the source of truth
- Ship one usable vertical slice before touching advanced reporting or approvals
- Keep Phase 1 limited to operational workflows that unblock daily usage
- Delay automation, exports, and advanced analytics until data capture is stable

## Immediate Decisions To Lock

These decisions should be confirmed before implementation starts because they affect every backend task:

1. Backend framework
2. Database engine
3. Migration strategy
4. Authentication approach
5. File storage approach for resumes and documents

## Recommended Assumptions

Unless there is an external constraint, use these assumptions to move quickly:

1. Use the existing MSSQL-oriented schema as the baseline, because the current SQL scripts are already written in that style.
2. Keep the API under `/api/v1` exactly as described in `docs/system/API_ENDPOINTS.md`.
3. Start with session or bearer-token auth only; do not build SSO or multi-factor flows in the first slice.
4. Store uploaded files in a simple local or single-bucket strategy first; avoid complex document workflows in the MVP.

## What "Phase 1" Means Now

Phase 1 should be reduced to the minimum operational core.

For execution, treat this as the working model:

- `platform_admin`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`

### In Scope

- authentication
- RBAC and location scoping
- user management
- location management
- client companies
- requisitions
- candidates
- daily updates
- basic dashboards needed to prove data flow

Working-model business title examples:

- Director
- BDM
- Account Manager
- Lead Recruiter
- Assistant Recruiter
- Recruiter

### Out Of Scope For The First Delivery Slice

- weekly and monthly finalized report generation
- approvals
- audit center workflows
- advanced notification engine
- resume parsing integration
- duplicate candidate intelligence beyond simple checks
- PDF and Excel exports
- forecasting and automation jobs

## Delivery Sequence

## Stage 0: Foundation And Backend Bootstrap

Objective:

Create the application skeleton and lock the technical direction.

Tasks:

- choose and document backend stack
- create backend project structure
- add environment configuration
- add migration runner
- add database connection setup
- define common API response format
- define error handling and request logging
- add basic health endpoint

Exit criteria:

- backend app starts locally
- database connection works
- migration workflow is repeatable

## Stage 1: Auth, Roles, And User Access

Objective:

Make login and access control real.

Tasks:

- implement permission-role and permissions bootstrap
- implement business-title bootstrap
- implement `POST /api/v1/auth/login`
- implement `POST /api/v1/auth/logout`
- implement `GET /api/v1/auth/me`
- implement password hashing and session/token persistence
- implement scope-aware permission checks
- implement `GET /api/v1/permissions/me`
- implement minimal seeded users for each core permission role

Exit criteria:

- core permission-role templates can log in
- each user receives the correct permission payload and scope summary
- unauthorized routes are blocked server-side

## Stage 2: Organization Setup

Objective:

Support core master data needed by every other workflow.

Tasks:

- implement locations CRUD
- implement teams CRUD
- implement users CRUD
- implement user activation and deactivation
- implement reporting-manager assignment
- implement business title assignment
- implement user scope assignment
- implement client companies CRUD
- implement client contacts if needed for meetings and requisitions

Exit criteria:

- admins can create locations and users
- reporting relationships and scope assignments are stored correctly
- clients can be created and listed with location-safe visibility

## Stage 3: Requisition Workflow

Objective:

Enable structured hiring demand intake.

Tasks:

- implement requisition create, list, detail, update
- persist internal vs external requisitions
- persist direct client and optional end-client relationships
- persist structured JD fields
- persist assignment to delivery owner
- persist priority, due date, openings, and status
- implement minimal validation rules

Exit criteria:

- client-side and delivery-side users can create and view requisitions according to scope
- requisitions are filterable by location, status, and owner
- structured JD data is stored cleanly

## Stage 4: Candidate Workflow

Objective:

Support the first end-to-end recruiting execution flow.

Tasks:

- implement candidate create, list, detail, update
- attach candidate to requisition
- store source, documents, and screening fields
- implement stage movement and stage history
- implement simple duplicate checks using email and phone
- implement rejection classification fields

Exit criteria:

- assigned delivery users can add candidates against requisitions
- candidate stage changes are auditable
- duplicate prevention exists at a basic operational level

## Stage 5: Daily Updates And Basic Dashboards

Objective:

Prove that structured operational data can drive role-specific visibility.

Tasks:

- implement daily update submission APIs
- store blockers, movements, sourcing activity, and next actions
- implement minimal dashboard summary endpoints for executive, business, and delivery views
- expose simple KPI counts from live tables

Exit criteria:

- daily updates are submitted and stored
- dashboards return real counts
- location-level operational reporting starts to work

## Stage 6: Frontend Integration Pass

Objective:

Connect the stitched frontend only after the backend slice is stable.

Tasks:

- connect login flow
- connect authenticated session bootstrap
- connect users, locations, clients, requisitions, candidates, and daily updates
- replace local mock behavior where backend truth is now available
- leave unfinished screens in fallback mode rather than forcing fake completeness

Exit criteria:

- core role journeys use live APIs
- frontend can operate in `live` mode for the implemented modules

## Milestone View

## Milestone A

Backend foundation plus auth.

Includes:

- Stage 0
- Stage 1

Result:

- real login
- real access control

## Milestone B

Operational setup modules.

Includes:

- Stage 2
- Stage 3

Result:

- users, locations, clients, and requisitions become usable

## Milestone C

Core recruiting execution.

Includes:

- Stage 4
- Stage 5

Result:

- candidates and daily updates create the first real operating loop

## Milestone D

Frontend integration for the implemented slice.

Includes:

- Stage 6

Result:

- the prototype starts behaving like an application

## Recommended Work Queue Right Now

If work resumes immediately, this should be the exact order:

1. create the backend app skeleton
2. adopt the schema into a real migration workflow
3. implement auth and permission middleware
4. seed roles, permissions, locations, and sample users
5. build users and locations APIs
6. build clients and requisitions APIs
7. build candidates APIs
8. build daily updates APIs
9. expose dashboard summary endpoints
10. connect the frontend only for completed modules

## Risks To Watch Early

### Database direction mismatch

The roadmap originally aimed to stay vendor-neutral, but the repository already contains MSSQL-specific schema work. That mismatch should be resolved before implementation starts.

### Over-scoping from the frontend

The frontend contains many screens for approvals, reports, audit, notifications, and settings. Those screens should not be treated as a promise that all backend modules must be built at once.

### Reporting before clean operational data

Weekly, monthly, and executive reporting should wait until requisitions, candidates, and daily updates are being captured reliably.

### Automation too early

Resume parsing, smart duplicate handling, and advanced alerts are useful, but they should not block the first working backend release.

## Definition Of Success For The Next Build Cycle

The next build cycle is successful when:

- a backend app exists in the repository
- the database schema is executable through migrations
- all four roles can log in
- location-safe access is enforced
- users, clients, requisitions, candidates, and daily updates are persisted
- the frontend can consume live APIs for those modules

At that point, planning can move to reporting, approvals, and automation with much lower risk.
