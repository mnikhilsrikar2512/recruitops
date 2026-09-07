# MVP Use Case Implementation Matrix

## Purpose

This document converts MVP use cases into implementation guidance.

It connects:

- business use cases
- backend APIs
- core database tables
- major validation and access rules

Use this document during:

- API implementation
- database migration planning
- permission and scope enforcement
- frontend page integration
- QA coverage planning

Read this together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/BUILD_PACK_API_CONTRACT_BASELINE.md`
- `docs/system/DATABASE_DESIGN.md`
- `docs/system/API_VALIDATION_RULES.md`

## How To Read It

Each row answers:

- what business action must be supported
- which APIs are required
- which tables are required
- what business rules must be enforced

## MVP Use Case To API And DB Mapping

| Use Case | Core Business Action | Required API Surface | Core Tables | Critical Rules |
| --- | --- | --- | --- | --- |
| `UC-01` | User login | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, `GET /api/v1/permissions/me` | `users`, `permission_roles`, `permissions`, `permission_role_permissions`, `user_sessions` or session store | Active user only, valid credential only, permission payload must load with location context |
| `UC-02` | View current access context | `GET /api/v1/auth/me`, `GET /api/v1/permissions/me` | `users`, `permission_roles`, `business_titles`, `user_location_roles`, `permissions`, `permission_role_permissions` | Effective access must reflect active role and allowed scope |
| `UC-03` | Create custom role | `GET /api/v1/roles`, `POST /api/v1/roles`, `GET /api/v1/roles/{id}`, `PUT /api/v1/roles/{id}`, `PUT /api/v1/roles/{id}/permissions` | `permission_roles`, `permissions`, `permission_role_permissions` | Admin-only for MVP, permission assignment must be auditable |
| `UC-04` | Assign role to user | `POST /api/v1/users`, `PUT /api/v1/users/{id}` | `users`, `permission_roles`, `business_titles`, `locations`, `user_location_roles` | User must have valid active location and role mapping |
| `UC-05` | Create location | `GET /api/v1/locations`, `POST /api/v1/locations`, `GET /api/v1/locations/{id}`, `PUT /api/v1/locations/{id}` | `locations` | Location identity must be unique enough for operations and reporting |
| `UC-06` | Create user | `POST /api/v1/users`, `GET /api/v1/users`, `GET /api/v1/users/{id}` | `users`, `business_titles`, `permission_roles`, `locations`, `user_location_roles` | Duplicate checks for configured identity fields such as email, phone, employee ID |
| `UC-07` | Deactivate user with active work | `PATCH /api/v1/users/{id}/status`, `GET /api/v1/requisitions`, `GET /api/v1/candidates`, `GET /api/v1/daily-updates` | `users`, `requisitions`, `requisition_assignments`, `candidates`, `candidate_applications`, `daily_updates` | Deactivation should trigger active-work review and reassignment handling |
| `UC-08` | Create client under a location | `GET /api/v1/clients`, `POST /api/v1/clients`, `GET /api/v1/clients/{id}`, `PUT /api/v1/clients/{id}` | `clients`, `locations`, `users` | One client belongs to one location for MVP operations |
| `UC-09` | Add client contact | `GET /api/v1/clients/{client_id}/contacts`, `POST /api/v1/clients/{client_id}/contacts`, `PUT /api/v1/client-contacts/{id}` | `client_contacts`, `clients` | Contact must belong to the same client |
| `UC-10` | Create requisition | `GET /api/v1/requisitions`, `POST /api/v1/requisitions`, `GET /api/v1/requisitions/{id}`, `PUT /api/v1/requisitions/{id}` | `requisitions`, `clients`, `client_contacts`, `locations`, `users` | Requisition location must align to client location, required fields include skills and update availability window |
| `UC-11` | Update requisition status | `PATCH /api/v1/requisitions/{id}/status` | `requisitions` | Status transitions must be valid and auditable |
| `UC-12` | Assign requisition to delivery team | `GET /api/v1/requisitions/{id}/assignments`, `POST /api/v1/requisitions/{id}/assignments`, `PUT /api/v1/requisition-assignments/{id}` | `requisition_assignments`, `requisitions`, `users`, `locations` | Assignment remains location-safe by default, reassignment review required on live work |
| `UC-13` | Create candidate profile | `GET /api/v1/candidates`, `POST /api/v1/candidates`, `GET /api/v1/candidates/{id}`, `PUT /api/v1/candidates/{id}` | `candidates`, `users`, `locations` | Candidate is global for duplicate detection but access must still be permission-controlled |
| `UC-14` | Upload resume or document | `POST /api/v1/candidates/{id}/documents`, `GET /api/v1/candidates/{id}` | `candidate_documents`, `candidates`, file storage | Upload metadata must be tracked with uploader context |
| `UC-15` | Detect candidate duplicate | `POST /api/v1/candidates/duplicate-check` | `candidates`, optional `duplicate_review_cases` later | Duplicate check should use global candidate search and configured company fields |
| `UC-16` | Compare and resolve duplicate | `POST /api/v1/candidates/duplicate-review/{id}/decision` or equivalent review endpoint | `candidates`, `duplicate_review_cases`, `audit_logs` | Only Admin and selected senior roles can override or clean up after comparison |
| `UC-17` | Link candidate to requisition | `POST /api/v1/candidates/{id}/applications`, `GET /api/v1/requisitions/{id}`, `GET /api/v1/pipeline/board` | `candidate_applications`, `candidates`, `requisitions`, `users`, `locations` | Prevent same candidate from being linked twice to the same requisition without explicit controlled behavior |
| `UC-18` | View candidate pipeline | `GET /api/v1/pipeline/board`, `GET /api/v1/pipeline/applications/{id}` | `candidate_applications`, `candidate_stage_history`, `requisitions`, `candidates`, `users`, `locations` | Visibility can move upward, but access scope must still be enforced |
| `UC-19` | Move candidate to next stage | `POST /api/v1/pipeline/applications/{id}/move-stage` | `candidate_applications`, `candidate_stage_history`, `requisitions` | Stage must belong to active client or requisition pipeline template |
| `UC-20` | View pipeline history | `GET /api/v1/pipeline/applications/{id}/history` | `candidate_stage_history`, `candidate_applications` | History must be append-only and auditable |
| `UC-21` | Track recruiter-owned progress | `GET /api/v1/pipeline/board`, `GET /api/v1/candidates`, `GET /api/v1/dashboard/my-work` | `candidate_applications`, `candidates`, `requisitions`, `users` | Recruiter should be able to see sourced, owned, or submitted candidate progress without needing broader edit rights |
| `UC-22` | Submit daily update | `GET /api/v1/daily-updates`, `POST /api/v1/daily-updates`, `GET /api/v1/daily-updates/{id}` | `daily_updates`, `requisitions`, `users`, `locations` | Behavior for multiple same-day updates follows company configuration |
| `UC-23` | Review team progress | `GET /api/v1/dashboard/pipeline-summary`, `GET /api/v1/dashboard/my-work`, `GET /api/v1/daily-updates` | `requisitions`, `candidate_applications`, `daily_updates`, `users`, `locations` | Visibility-first access, edit rights remain separate |
| `UC-24` | View location performance | `GET /api/v1/dashboard/location-summary`, `GET /api/v1/reports/location-performance` later | `requisitions`, `candidate_applications`, `daily_updates`, `locations`, reporting snapshots later | Admin and selected report roles can see location summaries |
| `UC-25` | View combined company reporting | `GET /api/v1/dashboard/company-summary`, `GET /api/v1/reports/company-performance` later | `requisitions`, `candidate_applications`, `daily_updates`, `locations`, reporting snapshots later | Combined reporting must not automatically grant edit authority everywhere |
| `UC-26` | Reassign ownership on active work | `POST /api/v1/requisitions/{id}/reassign`, `POST /api/v1/candidates/{id}/reassign`, or equivalent controlled update endpoints | `requisitions`, `requisition_assignments`, `candidates`, `candidate_applications`, `audit_logs` | Manual reassignment review required when active workflow impact exists |
| `UC-27` | Handle access denial | All protected APIs | All operational tables plus permission tables | Server-side denial only, never UI-only hiding as the only control |
| `UC-28` | Audit sensitive changes | Audit-aware versions of create, update, reassign, override, and status-change APIs | `audit_logs` later or equivalent audit store | Duplicate decisions, permission changes, ownership changes, and major status changes must be traceable |

## Minimum End-To-End MVP Loop

The first working product is successful only if this loop works fully:

1. Admin creates location
2. Admin creates role
3. Admin creates user and assigns role and location
4. Permitted user creates client under that location
5. Permitted user creates requisition under that client
6. Permitted senior user assigns the requisition
7. Recruiter creates or selects candidate
8. System checks duplicate risk
9. Recruiter links candidate to requisition
10. Recruiter and seniors can track candidate in pipeline
11. Permitted user moves candidate through stages
12. Recruiter submits daily update
13. Senior users review pipeline and delivery progress
14. Admin and reporting roles review location and combined reporting

## Core Access Enforcement Expectations

These rules apply across the matrix:

- authentication is required for all non-login APIs
- permission checks are server-side only
- location scope checks are server-side only
- upward visibility should not automatically imply edit access
- client ownership is location-bound in MVP
- candidate duplicate detection is global at company level
- candidate operational access is still controlled
- reassignment on live work should be reviewable

## Core Data Design Expectations

These design rules should remain true even when table names evolve:

- client records must carry `location_id`
- requisitions must carry `client_id` and `location_id`
- assignments must link requisitions to working users
- candidate records must remain globally reusable
- candidate application records must track requisition-specific workflow
- stage history must be separate from the current application row
- daily updates must link user, requisition, date, and execution details
- auditability should exist for sensitive actions, even if the final audit-center module comes later

## Gaps To Watch During Build

When implementation says a use case is done, verify all four layers:

- page or user trigger exists
- API exists and enforces permissions
- data model supports the workflow cleanly
- exception path is either blocked, logged, or routed for review

If one of those layers is missing, the use case is not fully done.
