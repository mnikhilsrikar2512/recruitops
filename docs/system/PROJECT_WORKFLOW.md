# RecruitOps — Project Workflow Document

> Comprehensive guide to every module, data flow, and business process in the recruitment system.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Module Workflows](#3-module-workflows)
   - 3.0 [End-to-End Candidate Journey](#30-end-to-end-candidate-journey)
   - 3.1 [Candidates](#31-candidates)
   - 3.2 [Requisitions](#32-requisitions)
   - 3.3 [Pipelines](#33-pipelines)
   - 3.4 [Interviews](#34-interviews)
   - 3.5 [Offers](#35-offers)
   - 3.6 [Daily Updates](#36-daily-updates)
   - 3.7 [Users & Roles](#37-users--roles)
   - 3.8 [Clients & Contacts](#38-clients--contacts)
   - 3.9 [Locations](#39-locations)
   - 3.10 [Analytics & Reports](#310-analytics--reports)
   - 3.11 [Notifications](#311-notifications)
   - 3.12 [Meetings](#312-meetings)
   - 3.13 [Approvals](#313-approvals)
   - 3.14 [Workflow Actions](#314-workflow-actions)
   - 3.15 [Onboarding](#315-onboarding)
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)
5. [Data Model Summary](#5-data-model-summary)
6. [Permission Model](#6-permission-model)

---

## 1. Project Overview

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Static HTML)                │
│  100 pages (74 primary + 26 overlays)                   │
│  Tailwind CSS · CDN · No build step                     │
├─────────────────────────────────────────────────────────┤
│                    REST API (FastAPI)                    │
│  15 modules · 70+ endpoints · /api/v1 prefix            │
│  Pydantic v2 schemas · Bearer token auth                │
├─────────────────────────────────────────────────────────┤
│                 Data Access Layer                        │
│  Raw SQL (sqlalchemy.text) · No ORM · No migrations     │
│  MSSQL / Azure SQL                                      │
├─────────────────────────────────────────────────────────┤
│                 Database (40+ tables)                    │
│  Candidates · Requisitions · Pipelines · Users · ...    │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, Pydantic v2 |
| Database | Microsoft SQL Server / Azure SQL |
| ORM | None — raw SQL via `sqlalchemy.text()` |
| Schema Changes | ⚠️ No migration tool today — see note below |
| Auth | Bearer token (session-based), SHA-256 password hashing |
| Frontend | Static HTML, Tailwind CSS (CDN), no JS framework |
| File Storage | Local filesystem (`uploads/` directory) |
| Email | aiosmtplib (async, disabled by default) |

> **Fix — flagged risk:** "no ORM, no migrations" was stated as a neutral fact, but
> for a 40+ table schema that's an operational hazard: there's no record of which
> schema version a given environment is on, no repeatable way to apply a change to
> staging then prod in the same order, and no rollback path if a raw `ALTER TABLE`
> partially fails. Recommendation: keep raw SQL for queries (that's a legitimate
> choice), but add a lightweight, ordered migrations folder
> (`scripts/migrations/0001_*.sql`, `0002_*.sql`, ...) with a `schema_migrations`
> tracking table, applied by a small runner script — this doesn't require adopting
> an ORM, just version control for DDL.

### Directory Structure

```
recruitment system/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (15 modules)
│   │   ├── core/            # Config, security, email, storage
│   │   ├── db/              # Session, SQL runner, bootstrap
│   │   ├── repositories/    # Data access (SQL queries)
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # Business logic
│   │   └── main.py          # App factory, middleware
│   ├── tests/               # 173 unit + E2E tests
│   └── uploads/             # File upload storage
├── frontend/
│   ├── partials/            # NEW — shared fragments (nav, drawers, overlays)
│   ├── pages-src/           # NEW — source pages, {% include %} shared partials
│   ├── pages/               # 100 HTML pages — BUILD OUTPUT, still what's served
│   ├── shared/              # global.css, app.js, api-client.js
│   ├── build.py             # NEW — Jinja2 generator: pages-src + partials → pages
│   └── route-manifest.json  # Route metadata
├── scripts/                 # SQL schemas, seeds, scripts
└── docs/system/             # Documentation
```

### Frontend Build Step (Partial Templating)

**Decision (Aug 31, 2026):** the 100 static HTML pages had no shared component
system, so any change to a common element (nav, notification bell, an
approval/overlay drawer) required hand-editing every page that used it. The team
agreed to accept a small build step to fix this rather than stay pure zero-tooling.

**Approach:** Jinja2 (already available via the FastAPI/Python stack — no new
dependency) renders each page in `pages-src/` against shared fragments in
`partials/`, and writes plain static HTML into `pages/`. Deployment is unchanged:
`pages/` still holds ordinary static files served exactly as before. Only the
*authoring* step changes — pages are written once with `{% include %}` tags
instead of copy-pasted markup, and `build.py` expands them.

```
frontend/build.py:
  Environment(loader=FileSystemLoader("frontend/pages-src"))
  for each *.html in pages-src/:
    render template (expanding {% include "../partials/*.html" %})
    write output to frontend/pages/{name}.html
```

Example source page (`pages-src/candidate-detail.html`):
```html
{% include "../partials/nav.html" %}
<main>
  ... page-specific content ...
</main>
{% include "../partials/approval-drawer.html" %}
```

**Migration plan (incremental, not a rewrite):**
1. Extract the highest-pain shared fragment first (nav or the drawer pattern) into `partials/`.
2. Move only the pages using that fragment into `pages-src/`; swap duplicated markup for `{% include %}`.
3. Run `build.py`, diff output against the previous `pages/` files to confirm parity.
4. Repeat fragment-by-fragment. Unmigrated pages continue to live directly in `pages/` untouched in the meantime — nothing breaks mid-migration.

**Operational requirement:** `build.py` must run as part of the deploy step (CI job, pre-push hook, or Makefile target) — not be a manual step someone has to remember. A generated page silently drifting out of sync with its source is a worse failure mode than the duplication this replaces.

---

## 2. Authentication & Authorization

### Login Flow

```
1. User submits email + password
   → POST /api/v1/auth/login

2. Backend finds user by email
   → SELECT * FROM users WHERE email = ?

3. Password verified (SHA-256 hash comparison)
   → verify_password(plain, stored_hash)

4. Session created
   → INSERT INTO user_sessions (user_id, token_hash, ip_address, user_agent, expires_at)
   → Token generated: generate_session_token()
   → Token hashed: hash_session_token(token)

5. Response returned
   → { token, user, primary_role, primary_location, session }
```

### Session Validation (Every Request)

```
1. Bearer token extracted from Authorization header

2. Token hashed → looked up in user_sessions
   → SELECT * FROM user_sessions WHERE token_hash = ?

3. Session validated:
   - Not revoked (revoked_at IS NULL)
   - Not expired (expires_at > NOW)
   - User status = 'active'

4. Session touched (last_activity_at updated)

5. AuthContext returned:
   → { session_id, session_token_hash, user }
```

### Permission Resolution

```
1. AuthContext extracted from session

2. If user.role_code = 'admin' → bypass all checks, return immediately

3. Otherwise:
   → SELECT p.code FROM permissions p
     JOIN role_permissions rp ON rp.permission_id = p.id
     WHERE rp.role_id = user.role_id

4. Check if required permission code (or alias) is in resolved set

5. Missing permission → 403 Forbidden
```

### Password Flows

| Flow | Endpoint | Trigger |
|------|----------|---------|
| First-time setup | `POST /auth/password/setup` | New user clicks setup link |
| Forgot password | `POST /auth/password/forgot` | User forgets password |
| Reset password | `POST /auth/password/reset` | User clicks reset link |
| Change password | `POST /auth/password/change` | Authenticated user changes |

**Token Lifecycle:**
```
1. Token created → password_reset_tokens table
2. Token sent via email (or console log if email disabled)
3. User submits token + new password
4. Token validated (not expired, not used, correct purpose)
5. Password updated → password_hash column in users
6. Token marked as used → used_at set
7. All other active user_sessions for this user are revoked (revoked_at set),
   except the session that just performed the change (if any) — forces
   re-login everywhere else the account was signed in
```
> **Fix:** step 7 was missing entirely. Without it, if a password is changed because
> an account was compromised, whoever holds the old session token keeps full access
> indefinitely — the reset accomplishes nothing from a security standpoint. This
> applies to all four password flows in the table above, not just reset.

---

## 3. Module Workflows

> **Fix — added missing overview:** every module below (§3.1–§3.15) was documented
> as an island, each with its own data flow diagram. Nothing tied them together, so
> a reader had to mentally stitch nine modules into one hire funnel. §3.0 below does
> that stitching once, up front.

### 3.0 End-to-End Candidate Journey

This is how the modules in §3.1–§3.5 actually chain together for a single hire,
start to finish. Each module's own section still has the full detail — this is the
connective tissue between them.

```
1. REQUISITION OPENS (§3.2)
   requisitions.status = 'open', pipeline_template_id assigned
                    │
2. CANDIDATE ENTERS SYSTEM (§3.1)
   Sourced manually or via resume upload → parsed → dedup-checked → finalized
                    │
3. CANDIDATE LINKED TO REQUISITION (§3.1 → §3.3)
   candidate_applications row created, inherits requisition's pipeline_template
   → current_stage = template's first stage
                    │
4. SCREENING (§3.1)
   candidate_screening_checks run against requisition_screening_rules
   → pass/fail feeds the recruiter's decision to advance or reject
                    │
5. PIPELINE MOVEMENT (§3.3)
   PATCH .../stage moves candidate through template stages
   → every move recorded in candidate_stage_history (source_type shows *why*
     it moved: manual | screening | interview | client-feedback)
                    │
6. INTERVIEWS (§3.4)   ── optional loop, can repeat across multiple rounds
   interview_rounds created per stage; feedback recorded
   → feedback decision can itself trigger the next stage move (step 5),
     forming a screening ⇄ interview ⇄ pipeline-move loop until a
     rejection or offer stage is reached
                    │
7. OFFER (§3.5)
   offer-create-dialog → approval_requests (source_type: 'offer', see §3.13)
   → approved offer → candidate_applications reflects offer terms
                    │
8. ACCEPTANCE & JOINING (§3.5)
   application_status = 'joined', expected_joining_date set
   → join-tracker.html monitors the gap between offer acceptance and Day 1
                    │
9. THROUGHOUT: reporting & visibility (§3.6, §3.10, §3.11, §3.14)
   Every recruiter action above is summarized in that day's daily_update,
   rolled into weekly/monthly reports, and any stall at any step (no stage
   movement in 7+ days, missing feedback, SLA breach) spawns a
   workflow_action_item so it surfaces in the action queue even if no one
   is actively watching that requisition.
```

**Where a candidate can exit the funnel early:** duplicate resolved as
`cancelled` (step 2), screening `failed` with no override (step 4), pipeline moved
to a `rejection`-type stage (step 5, either `internal` or `client` side), or an
offer `rejected` at approval (step 7). Each exit is still tracked in
`candidate_stage_history` / `candidate_applications` rather than deleted, so the
funnel's conversion rate at each step is queryable for §3.10 analytics.

---

### 3.1 Candidates

**Purpose:** Manage the full candidate lifecycle from sourcing to pipeline placement.

**Key Tables:** `candidates`, `candidate_skills`, `candidate_documents`, `candidate_resume_parse_logs`, `candidate_duplicate_checks`, `duplicate_review_cases`, `candidate_applications`, `candidate_stage_history`, `candidate_screening_checks`

#### Data Flow

```
SOURCING
│
├─ Manual Creation
│  → POST /api/v1/candidates/
│  → candidates.status = 'active'
│  → candidates.intake_stage = 'created'
│
├─ Resume Upload
│  → POST /api/v1/candidates/{id}/upload
│  → File saved to uploads/candidates/{id}/
│  → candidate_documents record created
│  → candidates.intake_stage = 'uploaded'
│
RESUME PARSING
│
├─ System triggers automation_job (type: 'resume-parse')
│  → candidate_resume_parse_logs created
│  → candidates.intake_stage: uploaded → parsed → needs-review
│  → candidate_skills populated from parsed JSON
│
DUPLICATE DETECTION
│
├─ System triggers automation_job (type: 'duplicate-check')
│  → candidate_duplicate_checks records created
│  → Candidates with matches: intake_stage = 'duplicate-review'
│  → GET /api/v1/candidates/{id}/duplicate-check
│
DUPLICATE RESOLUTION
│
├─ Recruiter reviews matches
│  → POST /api/v1/candidates/{id}/duplicate-check/decision
│  → Decision: continue-as-new | merge-into-existing | cancelled
│  → If override needed: duplicate_review_cases created
│
│  Decision semantics (previously undefined — clarified here):
│  • continue-as-new    → new candidate record kept as-is; matches dismissed
│  • merge-into-existing → new record's documents, skills, and any
│    candidate_applications are re-parented onto the existing candidate_id;
│    the new (duplicate) candidate row is soft-deleted (status = 'merged',
│    merged_into_candidate_id set) rather than hard-deleted, so audit history
│    and any in-flight application on the duplicate is preserved
│  • cancelled          → intake abandoned; candidate.status = 'cancelled',
│    no further processing occurs
│
PROFILE FINALIZATION
│
├─ → POST /api/v1/candidates/{id}/finalize-profile
│  → candidates.intake_stage = 'finalized'
│  → candidates.finalized_at set
│
LINK TO REQUISITION
│
├─ → POST /api/v1/candidates/{id}/applications
│  → candidate_applications record created
│  → Linked to specific requisition with initial pipeline stage
│
SCREENING
│
├─ candidate_screening_checks created
│  → Check types: must-have-skill, experience, employment-gap,
│     document, compensation, notice-period
│  → Status: pending → in-progress → passed | failed
│
PIPELINE PLACEMENT
│
└─ → PATCH /api/v1/pipeline/applications/{id}/stage
   → candidate_stage_history recorded
   → candidate_applications.current_stage updated
```

**Frontend Pages:** candidate-profiles, candidate-detail, resume-upload-and-review, candidate-duplicate-review, candidate-screening, review-matches-workspace, application-history

---

### 3.2 Requisitions

**Purpose:** Create, manage, and track job openings through their lifecycle.

**Key Tables:** `requisitions`, `requisition_end_clients`, `requisition_assignments`, `requisition_skill_requirements`, `requisition_screening_rules`, `requisition_documents_required`

#### Data Flow

```
INTAKE
│
├─ Account Manager or Admin creates
│  → POST /api/v1/requisitions/
│  → requisitions.status = 'draft'
│  → Requisition code auto-generated (RQ-HYD-0001 format)
│
INTAKE DETAILS
│
├─ Structured intake captures:
│  • Client, department, title, hiring_type (internal/external)
│  • Priority (low/medium/high/critical)
│  • Target close date, SLA
│  • Job description, budget range, currency
│  • Employment type, work mode
│
├─ Skill Requirements
│  → requisition_skill_requirements
│  → Type: must-have | good-to-have
│
├─ Screening Rules
│  → requisition_screening_rules
│  → Gap limits, notice period, document requirements
│
STATUS TRANSITIONS
│
├─ draft → open → (on-hold | closed | cancelled)
│  → PATCH /api/v1/requisitions/{id}/status
│  → Creates workflow_action_items for downstream effects
│
ASSIGNMENTS
│
├─ → POST /api/v1/requisitions/{id}/assignments
│  → Types: primary_owner, delivery_owner, contributor, support
│  → Unique active constraint per requisition+user+type
│
OWNER REASSIGNMENT
│
└─ → POST /api/v1/requisitions/{id}/reassign-owners
   → Creates approval_requests for sensitive reassignments
   → Reassignment history tracked
```

**Status Flow:**
```
draft ──→ open ──⇄ on-hold   (on-hold is temporary; PATCH …/status can move it back to open)
             ──→ closed
             ──→ cancelled
```
> **Fix:** `on-hold` was previously a dead end in this document — there was no
> documented way back to `open`. Since on-hold is meant to be a pause (client budget
> freeze, headcount review, etc.) rather than a terminal state, the status endpoint
> must accept `on-hold → open` as a valid transition. `closed` and `cancelled` remain
> terminal; reopening a closed/cancelled requisition should require creating a new one.

**Frontend Pages:** requisition-list, requisition-intake, requisition-intake-edit, requisition-detail, delivery-work-queue, work-assignment, reassign-owner-dialog, assignment-history-drawer

---

### 3.3 Pipelines

**Purpose:** Visualize and manage candidates moving through hiring stages.

**Key Tables:** `pipeline_templates`, `pipeline_template_stages`, `candidate_applications`, `candidate_stage_history`

#### Data Flow

```
PIPELINE TEMPLATE
│
├─ Templates define ordered stages
│  → pipeline_templates (scoped by client/company/location)
│  → pipeline_template_stages (ordered stages with type)
│  → Stage types: normal, rejection, joining, hold
│
TEMPLATE ASSIGNMENT
│
├─ requisitions.pipeline_template_id linked
│  → Candidate applications inherit template
│
PIPELINE BOARD VIEW
│
├─ → GET /api/v1/pipeline/board
│  → Grouped by requisition
│  → Shows candidates per stage
│  → Filters: requisition_id, owner, sourced_by, stage
│
STAGE TRANSITION
│
├─ → PATCH /api/v1/pipeline/applications/{id}/stage
│  → Payload: to_stage, reason, source_type
│  → candidate_stage_history recorded
│  → source_type: manual | automation | client-feedback |
│     screening | interview
│
REJECTION FLOW
│
├─ Rejection side: internal | client | none
│  → Rejection stage and reason recorded
│  → client_feedback_status tracks client response
│
JOINING FLOW
│
└─ application_status = 'joined'
   → expected_joining_date tracked
   → Triggers join-tracker workflow
```

**Frontend Pages:** pipeline-board, stage-history-audit-log, stage-move-dialog, pipeline-history-drawer

---

### 3.4 Interviews

**Purpose:** Schedule interviews, collect feedback, and integrate with pipeline movement.

**Key Tables:** `interview_rounds`

#### Data Flow

```
SCHEDULING
│
├─ → interview_rounds created for candidate_applications
│  → Round types: internal, manager, client
│  → Interviewer: system user or external name
│  → scheduled_at, status set
│
FEEDBACK
│
├─ → Interview feedback via interview-feedback-dialog
│  → feedback_status, decision, feedback_notes recorded
│  → Status: scheduled → completed | rescheduled | cancelled | no-show
│
PIPELINE INTEGRATION
│
└─ Interview completion can trigger stage movement
   → pipeline.stage.move with source_type = 'interview'
```

**Frontend Pages:** interview-scheduler, interview-detail, interview-feedback-dialog

---

### 3.5 Offers

**Purpose:** Create offers, manage approval workflows, and track candidate acceptance.

**Key Tables:** `candidate_applications` (offer fields), `approval_requests`

#### Data Flow

```
OFFER CREATION
│
├─ → offer-create-dialog
│  → Linked to candidate_applications
│  → Offer details: CTC, benefits, start date
│
APPROVAL
│
├─ → approval_requests created (source_type: 'offer')
│  → Routed to appropriate approvers
│  → Status: pending → in-review → approved | rejected
│
CANDIDATE ACCEPTANCE
│
├─ → application_status = 'joined'
│  → expected_joining_date recorded
│  → Triggers join-tracker workflow
│
JOIN TRACKING
│
└─ → join-tracker.html monitors onboarding progress
```

**Frontend Pages:** offer-management, offer-create-dialog, join-tracker

---

### 3.6 Daily Updates

**Purpose:** Track recruiter daily activity and feed into reporting.

**Key Tables:** `daily_updates`

#### Data Flow

```
SUBMISSION
│
├─ Recruiter submits daily update
│  → POST /api/v1/daily-updates/
│  → Fields:
│    • summary (narrative)
│    • profiles_sourced_count
│    • profiles_screened_count
│    • profiles_submitted_count
│    • interviews_scheduled_count
│    • offers_closed_count
│    • blockers
│    • planned_next_actions
│    • portal_usage_summary
│  → submission_status = 'submitted'
│
REVIEW
│
├─ Manager/HR reviews
│  → GET /api/v1/daily-updates/ (location-scoped)
│  → submission_status = 'reviewed'
│  → reviewed_by_user_id, reviewed_at set
│
CLARIFICATION
│
├─ → clarification-request-dialog for manager queries
│  → Back-and-forth until satisfactory
│
REPORT GENERATION
│
└─ Daily updates feed into reports table
   → automation_jobs (type: 'report-generation')
   → Aggregates into weekly/monthly reports
```

**Frontend Pages:** daily-updates-workspace, daily-updates-submission, daily-updates-review, daily-update-detail-panel, clarification-request-dialog

---

### 3.7 Users & Roles

**Purpose:** Manage user accounts, role assignments, and permission configuration.

**Key Tables:** `users`, `roles`, `role_permissions`, `role_scope_rules`, `role_templates`, `role_template_permissions`, `user_extra_permissions`, `user_location_roles`, `user_sessions`, `password_reset_tokens`, `user_notification_preferences`

#### Data Flow

```
USER CREATION
│
├─ Admin creates user
│  → POST /api/v1/users/
│  → Employee code, name, email, phone
│  → Primary role assigned
│  → password_setup_status = 'pending-setup'
│  → user_invitations created
│
PASSWORD SETUP
│
├─ → POST /api/v1/auth/password/setup (with token)
│  → password_setup_status = 'active'
│  → force_password_change_on_first_login can trigger reset
│
LOCATION ROLE ASSIGNMENT
│
├─ → user_location_roles: user + location + role + is_primary
│  → Supports multi-location users
│  → start_date / end_date for temporal assignments
│
ROLE CONFIGURATION
│
├─ → POST /api/v1/roles/ to create custom roles
│  → PUT /api/v1/roles/{id}/permissions to assign permissions
│  → Permission aliases resolve multiple acceptable codes
│
PERMISSION RESOLUTION
│
├─ → GET /api/v1/permissions/me
│  → Combines: role_permissions + user_extra_permissions
│  → Admin bypasses all permission checks
│
DEACTIVATION
│
├─ → POST /api/v1/users/{id}/deactivate
│  → Reassignment of owned work (candidates, requisitions)
│  → reassignment-review-drawer for bulk reassignment
│  → User status → 'inactive'
│
LOCATION TRANSFER
│
└─ → POST /api/v1/users/{id}/move
   → Updates user_location_roles
   → Creates new location assignment
```

**Seeded Roles:** admin (system), manager, hr, recruiter

**Role Templates (6):** director, bdm, account_manager, lead_recruiter, recruiter, assistant_recruiter

**Frontend Pages:** user-management, user-detail, role-management, role-permissions-editor, deactivate-user-dialog, reassignment-review-drawer

---

### 3.8 Clients & Contacts

**Purpose:** Manage client accounts, contacts, and cross-location access.

**Key Tables:** `clients`, `client_contacts`, `client_access_requests`

#### Data Flow

```
CLIENT CREATION
│
├─ BDM or Admin creates client
│  → POST /api/v1/clients/
│  → Types: direct-client | end-client
│  → Parent-child hierarchy (end-client under direct-client)
│  → Status: active | inactive | prospect
│  → Client owner and business source owner assigned
│
CONTACT MANAGEMENT
│
├─ → POST /api/v1/clients/{id}/contacts
│  → is_primary / is_secondary flags
│  → Status: active | inactive
│
CROSS-LOCATION ACCESS
│
├─ → client_access_requests for cross-location visibility
│  → Approval workflow: pending → approved | rejected
│
CLIENT-REQUISITION LINK
│
└─ → requisitions.client_id links to client
   → requisition_end_clients for end-client mapping
```

**Frontend Pages:** client-directory, client-detail, contact-form-dialog

---

### 3.9 Locations

**Purpose:** Manage office locations and enforce data scoping.

**Key Tables:** `locations`, `master_data_values`

#### Data Flow

```
LOCATION CREATION
│
├─ Admin creates location
│  → POST /api/v1/locations/
│  → Fields: name, code, city, state, country
│  → location_mapping_type: legal-entity | operational-team | both
│  → Monthly/weekly targets for hiring
│
LOCATION HEAD
│
├─ → locations.location_head_user_id assigned
│  → Drives reporting hierarchy
│
SCOPE ENFORCEMENT
│
├─ → require_location_scope dependency
│  → Users see only their location's data
│  → Admin bypasses scope
│
PERFORMANCE TRACKING
│
└─ → vw_location_performance_summary view
   → Open requisitions, daily updates, closures, risk status
```

**Seeded Locations (3):** Hyderabad (HYD01), Vijayawada (VJW01), Vizag (VZG01)

**Frontend Pages:** location-management, location-dashboard

---

### 3.10 Analytics & Reports

**Purpose:** Generate, review, and distribute hiring reports and analytics.

**Key Tables:** `reports`, `report_rows`, `report_locks`, `automation_jobs`, database views

#### Data Flow

```
DAILY UPDATE INPUT
│
├─ Daily updates feed raw data
│  → Sourced/screened/submitted/interview/offer counts per recruiter
│
REPORT GENERATION
│
├─ → automation_jobs (type: 'report-generation')
│  → Aggregates daily updates into weekly/monthly reports
│  → Reports have scope: admin | manager | hr | recruiter | location
│
REPORT LIFECYCLE
│
├─ draft → generated → in-review → published → locked
│  → report_locks prevent data changes for closed periods
│  → Lock/unlock with audit trail
│
DASHBOARD VIEWS
│
├─ /api/v1/dashboards/role: role-specific pipeline summary
├─ /api/v1/dashboards/my-work: personal assignment queue
├─ /api/v1/dashboards/location-summary: location KPIs
└─ /api/v1/dashboards/company-summary: organization-wide metrics
```

**Frontend Pages:** analytics-dashboard, reports, company-dashboard, pipeline-analytics, time-to-fill-report, source-effectiveness, custom-report-builder, user-performance-reports, sla-tracker, team-workload

---

### 3.11 Notifications

**Purpose:** Notify users of important events via in-app and email channels.

**Key Tables:** `notifications`, `user_notification_preferences`

#### Data Flow

```
NOTIFICATION CREATION
│
├─ System generates on events:
│  • approval_pending
│  • requisition_assigned
│  • interview_scheduled
│  • feedback_pending
│  • portal_slot_reminder
│  • candidate_expiry_warning
│  • report_submission_reminder
│  • meeting_follow_up_reminder
│  • duplicate_warning
│  • profile_escalation_update
│
DELIVERY
│
├─ In-app: notifications table
│  → Status: unread → read → archived
│
├─ Email: via aiosmtplib (if email_enabled)
│  → Per-user preferences control channels
│
NOTIFICATION CENTER
│
└─ → GET /api/v1/notifications/ with filters
   → PATCH /api/v1/notifications/{id}/read
   → Priority: low, normal, high, critical
```

**Frontend Pages:** notifications-center, notification-detail-panel

---

### 3.12 Meetings

**Purpose:** Schedule client/internal meetings and track outcomes.

**Key Tables:** `meetings`, `meeting_attendees`

#### Data Flow

```
MEETING CREATION
│
├─ → meeting-form-dialog
│  → Types: client_introduction, requirement_discussion,
│     follow_up, review_meeting, escalation_meeting,
│     internal_review
│  → Linked to client, location, owner
│
ATTENDEE MANAGEMENT
│
├─ → meeting_attendees
│  → Internal users + client contacts
│  → Attendee type: internal-user | client-contact
│
OUTCOME TRACKING
│
├─ attendance_status: pending | attended | partially-attended |
│  no-show | cancelled
├─ outcome_status: pending | accepted | rejected |
│  follow-up-required | rescheduled | closed
├─ minutes_of_meeting, decision_summary, next_steps
│
FOLLOW-UP
│
└─ → follow_up_owner_user_id, follow_up_due_date
   → Creates workflow_action_items for reminders
```

**Frontend Pages:** meetings, meeting-form-dialog, follow-ups, follow-up-form-dialog

---

### 3.13 Approvals

**Purpose:** Route approval requests (offers, exceptions, reassignments) to appropriate reviewers.

**Key Tables:** `approval_requests`

> **Fix — module boundary clarified:** this section previously documented
> `approval_requests` as its own module but pointed every endpoint at
> `/api/v1/workflow-actions/...`, the same endpoints owned by §3.14. That made it
> impossible to tell whether Approvals is a distinct module or just a filtered view.
> It is the latter, and the doc now says so explicitly: **Approvals is a
> specialized, permission-scoped view over the Workflow Actions queue**, filtered to
> `source_type IN ('offer','exception','reassignment','access-request')`. It uses the
> same `workflow_action_items` / `workflow_action_events` tables and the same
> `/api/v1/workflow-actions/*` endpoints as §3.14, but is gated by the separate
> `approval.request` / `approval.decide` permissions instead of `workflow_action.run`,
> so that a user can be granted "approve offers" rights without also getting generic
> "run any workflow action" rights. Frontend surfaces this filtered view under its own
> `approvals-inbox` page rather than the general action queue page.

#### Data Flow

```
APPROVAL REQUEST CREATION
│
├─ System creates on events:
│  • Offer approval (source_type: 'offer')
│  • Budget exception (source_type: 'exception')
│  • Owner reassignment (source_type: 'reassignment')
│  • Cross-location access (source_type: 'access-request')
│  → Each creates an approval_requests row AND a linked workflow_action_items
│    row (source_type matches) so it surfaces in both the Approvals inbox and
│    the general action queue
│
APPROVAL QUEUE
│
├─ → GET /api/v1/workflow-actions/queue?source=offer,exception,reassignment,access-request
│  → Requires approval.request (view) permission
│  → Filters: status, source, location
│  → Each item: priority, assigned_user, due_at
│
REVIEW
│
├─ → approval-review-drawer
│  → Reviewer sees request details and context
│
DECISION
│
├─ → POST /api/v1/workflow-actions/{id}/run
│  → Requires approval.decide permission (checked in addition to the
│    generic workflow_action.run check when source_type is approval-related)
│  → Decision: approve | reject
│  → downstream_effects triggered
│
AUDIT
│
└─ → workflow_action_events records execution
```

**Frontend Pages:** approvals-inbox, approval-review-drawer, exception-request-dialog

---

### 3.14 Workflow Actions

**Purpose:** Cross-cutting action queue for stalled items, reminders, and system-generated tasks.

**Key Tables:** `workflow_action_items`, `workflow_action_events`

#### Data Flow

```
ACTION ITEM CREATION
│
├─ System creates based on events:
│  • Stalled candidates (age > 7 days in stage)
│  • Pending approvals
│  • Missing daily updates
│  • Overdue follow-ups
│  • SLA breach warnings
│
ACTION QUEUE
│
├─ → GET /api/v1/workflow-actions/queue
│  → Filters: status, source, location
│  → Each item: priority, assigned_user, due_at,
│     route_href, overlay_key
│
ACTION EXECUTION
│
├─ → POST /api/v1/workflow-actions/{id}/run
│  → Execute primary action (move candidate, approve request)
│  → workflow_action_events audit trail
│
OVERLAY SUBMISSIONS
│
├─ → POST /api/v1/workflow-actions/overlay-submissions
│  → Submit data from routed overlay forms/drawers
│  → Connects UI actions to backend state changes
│
RESOLUTION & NUDGES
│
├─ → POST /api/v1/workflow-actions/{id}/resolve
│  → Mark as resolved
│
└─ → POST /api/v1/workflow-actions/{id}/nudge
   → Send reminder to assignee
```

**Frontend Pages:** dashboard-actions-overlay, approvals-inbox, approval-review-drawer, exception-request-dialog

---

### 3.15 Onboarding

**Purpose:** Guided setup wizard for new tenant configuration.

#### Flow (8 Steps)

```
1. WELCOME
   → onboarding-welcome.html
   → Introduction and getting started

2. COMPANY PROFILE
   → onboarding-company-profile.html
   → Company entity details, branding

3. HIRING TEAMS
   → onboarding-hiring-teams.html
   → Team structure, reporting lines

4. LOCATIONS
   → onboarding-locations.html
   → Operating locations setup

5. ROLE SETUP
   → onboarding-role-setup.html
   → Permissions and role templates

6. PIPELINE STAGES
   → onboarding-pipeline-stage-builder.html
   → Default hiring pipeline stages
   → Add custom stages overlay

7. INTEGRATIONS
   → onboarding-integrations.html
   → Connect external tools

8. LAUNCH
   → onboarding-success-launch.html
   → Workspace ready confirmation
```

---

## 4. Cross-Cutting Concerns

### 4.1 Notification Triggers

Notifications are created by services when specific events occur.

> **Fix:** this table previously listed only 7 triggers while §3.11 separately listed
> 10 notification types, and the two lists didn't match (e.g. `approval_pending`,
> `feedback_pending`, `duplicate_warning` appeared only in §3.11). Consolidated here
> as the single source of truth — §3.11 should be read as referring back to this table.

| Trigger | Notification Type | Recipients |
|---------|------------------|------------|
| Pipeline stage change | `stage_moved` | Candidate owner |
| Requisition created | `requisition_assigned` | Assigned owners |
| Requisition status changed | `requisition_status_changed` | Owners, managers |
| Interview scheduled | `interview_scheduled` | Interviewer, candidate owner |
| Daily update submitted | `daily_update_submitted` | Manager |
| User deactivated | `user_deactivated` | User, admin |
| Candidate owner reassigned | `candidate_owner_changed` | Old owner, new owner |
| Approval request created | `approval_pending` | Assigned approver(s) |
| Interview completed, feedback missing | `feedback_pending` | Interviewer |
| Client portal slot approaching | `portal_slot_reminder` | Recruiter, account manager |
| Candidate profile nearing staleness | `candidate_expiry_warning` | Candidate owner |
| Daily update not yet submitted | `report_submission_reminder` | Recruiter |
| Meeting follow-up due | `meeting_follow_up_reminder` | Follow-up owner |
| Possible duplicate candidate found | `duplicate_warning` | Candidate owner, HR |
| Duplicate review case escalated | `profile_escalation_update` | HR, location head |

### 4.2 Audit Logging

Every significant state change is recorded in `audit_logs`:

```
audit_logs:
  - actor_user_id (who performed the action)
  - action_type (create, update, delete, status_change, reassign)
  - entity_type (candidate, requisition, user, etc.)
  - entity_id
  - old_value (JSON)
  - new_value (JSON)
  - ip_address
  - user_agent
  - created_at
```

### 4.3 File Upload Flow

```
1. File received via POST /api/v1/candidates/{id}/upload
2. Extension validated against allowed_upload_extensions
3. Size validated against max_upload_size_bytes
4. UUID filename generated
5. Saved to uploads/candidates/{id}/{uuid}.{ext}
6. candidate_documents record created
7. File served via GET /api/v1/files/{path}
   → AuthContext required (Bearer token) AND caller must pass
     require_location_scope for the owning candidate's location, OR hold
     candidate.read, before the file is streamed
```

> **Fix — access control gap:** as previously written, step 7 had no permission
> check described at all — any authenticated user with a valid bearer token could
> request any `{path}` and receive resumes/documents belonging to candidates outside
> their location or role scope, since UUID filenames are not a substitute for
> authorization. The file-serving endpoint must resolve `{path}` back to its
> `candidate_documents` row and re-run the same location-scope / permission check
> used to read that candidate, not just verify the token is valid.

### 4.4 Email Delivery

```
1. System event triggers email
2. Template selected based on event type
3. Email rendered with context variables
4. aiosmtplib sends via configured SMTP server
5. Delivery status logged
6. Per-user preferences checked before sending
```

### 4.5 Automation Jobs

Background jobs tracked in `automation_jobs`:

| Job Type | Purpose |
|----------|---------|
| `resume-parse` | Extract structured data from uploaded resumes |
| `duplicate-check` | Scan for matching candidate profiles |
| `report-generation` | Aggregate daily updates into reports |
| `notification-dispatch` | Send pending notifications |

---

## 5. Data Model Summary

### Entity Relationship Overview

```
                    ┌──────────────┐
                    │   locations  │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
    │   users   │   │  clients  │   │requisitions│
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │                │                │
          │                │          ┌─────┴─────┐
          │                │          │candidate_ │
          │                │          │applications│
          │                │          └─────┬─────┘
          │                │                │
          │          ┌─────┴─────┐   ┌─────┴─────┐
          │          │client_    │   │candidates │
          │          │contacts   │   └─────┬─────┘
          │          └───────────┘         │
          │                          ┌─────┴─────┐
          │                          │candidate_ │
          │                          │skills     │
          │                          └───────────┘
          │
    ┌─────┴─────┐
    │   roles   │
    └─────┬─────┘
          │
    ┌─────┴─────┐
    │role_      │
    │permissions│
    └─────┬─────┘
          │
    ┌─────┴─────┐
    │permissions│
    └───────────┘
```

> **Fix — ERD was incomplete:** the diagram above only traced the org/hiring-structure
> side of the schema (locations → users/clients/requisitions → candidates). It
> omitted every entity from §3.4, §3.11, §3.13, and §3.14 even though those are
> full modules with their own tables. The relationship table below now covers them;
> redrawing the ASCII diagram itself would make it unreadable, so those four
> modules are called out here as **satellite entities that all hang off
> `candidate_applications`, `users`, or system events** rather than off `locations`.

### Key Relationships

| Parent | Child | Relationship |
|--------|-------|-------------|
| locations | users | One-to-many (via user_location_roles) |
| locations | requisitions | One-to-many |
| clients | client_contacts | One-to-many |
| clients | requisitions | One-to-many |
| requisitions | candidate_applications | One-to-many |
| requisitions | requisition_assignments | One-to-many |
| requisitions | requisition_skill_requirements | One-to-many |
| candidates | candidate_applications | One-to-many |
| candidates | candidate_documents | One-to-many |
| candidates | candidate_skills | One-to-many |
| candidate_applications | candidate_stage_history | One-to-many |
| candidate_applications | interview_rounds | One-to-many |
| candidate_applications | candidate_screening_checks | One-to-many |
| candidate_applications | approval_requests | One-to-many (source_type: 'offer') |
| users | user_sessions | One-to-many |
| users | daily_updates | One-to-many |
| users | notifications | One-to-many (recipient) |
| users | workflow_action_items | One-to-many (assigned_user) |
| roles | role_permissions | One-to-many |
| workflow_action_items | workflow_action_events | One-to-many (execution audit trail) |
| meetings | meeting_attendees | One-to-many |

---

## 6. Permission Model

### Code Convention

```
{module}.{action}                    # Simple permission
{module}.{sub-module}.{action}       # Nested permission
```

### Permission Modules

| Module | Count | Key Permissions |
|--------|-------|----------------|
| auth | 2 | `auth.session.manage_own` |
| role | 8 | `role.create`, `role.permissions.assign` |
| location | 8 | `location.read`, `location.create` |
| user | 13 | `user.create`, `user.credentials.manage` |
| client | 10 | `client.create`, `client.contact.read` |
| requisition | 11 | `requisition.create`, `requisition.status.update` |
| assignment | 5 | `assignment.create`, `assignment.reassign` |
| candidate | 17 | `candidate.create`, `candidate.duplicate.check` |
| pipeline | 11 | `pipeline.stage.move`, `pipeline.read.summary` |
| daily_update | 5 | `daily_update.create_main`, `daily_update.review` |
| dashboard | 5 | `dashboard.read_my_work`, `dashboard.read_pipeline_summary` |
| report | 10 | `report.generate_weekly`, `report.lock_monthly` |
| audit | 6 | `audit.read`, `audit.read_global` |
| approval | 5 | `approval.request`, `approval.decide` |
| workflow | 5 | `workflow_action.run`, `workflow_overlay.submit` |
| notification | 1 | `notification.mark_read` |
| settings | 3 | `settings.read`, `settings.update_system` |

### Permission Aliases

Some permissions have backward-compatible aliases defined in `deps.py`:

```python
PERMISSION_ALIASES = {
    "location.read": ("location.read", "branch.read"),
    "candidate.resume.upload": ("candidate.resume.upload", "candidate.upload_resume"),
    "pipeline.read.summary": ("pipeline.read.summary", "requisition.read", "candidate.read"),
    # ... 30+ alias mappings
}
```

### Scope Enforcement

- **Admin**: Bypasses all permission and scope checks
- **Non-admin**: Data filtered by `location_id` via `require_location_scope` dependency
- **Cross-location**: Requires explicit `client_access_requests` approval

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| API Route Modules | 15 |
| API Endpoints | 70+ |
| Database Tables | 40+ |
| Database Views | 5 |
| Frontend Primary Pages | 74 |
| Frontend Overlay Pages | 26 |
| Total Frontend Pages | 100 |
| Permission Codes | 130+ |
| Seeded Role Templates | 6 |
| Master Data Categories | 32 |
| Master Data Values | 100+ |
| Unit + E2E Tests | 173 |

---

## Change Log — Review Pass (Aug 31, 2026)

This pass read the full document end-to-end and fixed the following hiccups
in place (each is also marked inline with a `> **Fix**` callout at its location):

| # | Issue | Section | Fix |
|---|-------|---------|-----|
| 1 | Onboarding said "7 Steps" but listed 8 | §3.15 | Corrected header to "8 Steps" |
| 2 | Requisition `on-hold` had no path back to `open` | §3.2 | Added `open ⇄ on-hold` transition |
| 3 | "merge-into-existing" duplicate decision was undefined | §3.1 | Specified re-parenting + soft-delete behavior |
| 4 | Approvals and Workflow Actions shared identical endpoints with no explanation | §3.13 | Documented Approvals as a permission-scoped view over Workflow Actions |
| 5 | Notification trigger table (4.1) didn't match the fuller list in §3.11 | §4.1 | Consolidated to one complete, authoritative table |
| 6 | File-serving endpoint had no documented access control | §4.3 | Required location-scope/permission check before streaming a file |
| 7 | Password change didn't revoke other active sessions | §2 | Added session revocation step to all password flows |
| 8 | "No migrations" on a 40+ table schema was stated with no risk/mitigation | §1 | Flagged risk, proposed lightweight versioned-SQL migration runner |
| 9 | No single view connected the 5 core hiring modules into one funnel | §3 | Added new §3.0 End-to-End Candidate Journey |
| 10 | ERD and relationship table omitted interviews, approvals, notifications, workflow actions | §5 | Extended relationship table to cover all four |
| 11 | 100 static pages had no shared component system, forcing hand-edits across pages for any common element | §1 | Team accepted a small build step; added Jinja2 partial-templating plan with incremental migration path |

**Resolved (Aug 31, 2026):** the 100 static HTML pages with no shared
component/templating system meant any change to a common element (nav, header, a
drawer pattern) had to be hand-edited across pages. The team decided to accept a
small build step to fix this — see new §1 subsection **"Frontend Build Step
(Partial Templating)"** for the chosen approach and migration plan.
