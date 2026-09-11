# Product Requirements Document

Project: RecruitOps — configurable recruitment operating system
Status: Living document. Update a requirement here before (or while) changing code; this is the single source of truth for what the product must do.
Date: September 11, 2026

Requirement keywords: **MUST**, **SHOULD**, **MAY** are used in the RFC 2119 sense. Status markers: **Shipped** (built and verified), **Partial** (built, gaps noted), **Planned** (required for MVP, not built), **Deferred** (explicitly out of MVP).

---

## 1. Product Vision

When a company wants a recruitment system, they use RecruitOps because the system adapts to *their* structure — not the other way around:

1. They create their own **designations** (job titles).
2. They create their own **locations** (branches the org operates from).
3. They create their own **roles** with explicit permissions — the product ships with no fixed business roles.
4. They create **users** and assign them those roles.
5. They then run recruitment end to end: clients → requisitions → candidates → pipeline → daily updates → approvals.

`Admin` is the only fixed system role. Every other role, designation, pipeline stage, and visibility scope is defined by the Admin during and after onboarding.

The person who completes setup **becomes the Admin** and owns the workspace from then on.

---

## 2. Target Users

| Actor | Who they are | What they do |
|---|---|---|
| Workspace Admin | The person who set the company up | Configures designations, locations, pipeline stages, roles, permissions, users; oversees everything |
| Configured business role (e.g., Recruiter, BDM, Account Manager) | Named roles the Admin creates — names are examples, not product constants | Works within the permissions their role grants: own requisitions, pipeline moves, daily updates, approvals when granted |
| Limited-permission user | A user whose role grants only view-level permissions | Sees data they are permitted to see; actions their role lacks are hidden or read-only, never error-prone |

Location scoping is a first-class concept: operational data is location-bound by default, and a user's access is scoped by the locations they can operate in.

---

## 3. Product Principles

1. **No hard-coded business roles.** The product must not depend on BDM/Recruiter/Lead Recruiter constants. Roles, their names, and their permissions are data, not code.
2. **Permission-checked everything.** Every mutating and sensitive read endpoint enforces an action-level permission code. The frontend hides what the role lacks; the backend is the real gate.
3. **One owner per state.** Session, permissions, and page state have single owners in the frontend; a behavior change lands in one place.
4. **Real data only.** Pages render live API data. Static mockup content is scaffolding to be replaced, never the end state.
5. **Fail safe.** A denied permission is a clean 403 with an understandable UI state (read-only mode, hidden buttons, access-denied page) — not a raw error.

---

## 4. MVP Scope

### In scope

- Authentication and session (JWT, bcrypt hashing, password setup/reset flows)
- Tenant onboarding (7 steps → company profile, locations, pipeline stages, designations, roles, users, launch)
- Admin configuration: locations, designations (master data), pipeline stage templates, roles, permissions, users
- Client management (clients + contacts, location-bound)
- Requisition management (intake, primary/delivery ownership, assignment, status)
- Candidate management (profiles, duplicate detection flow, resume upload, screening)
- Pipeline (configurable stages, stage moves, history/audit)
- Interviews and offers
- Daily updates (submission, review) and meetings
- Approvals (request → inbox → decide)
- Notifications (in-app; generated on key actions; badge counts; mark-as-read)
- Portal accounts (job-portal account registry + usage-slot booking + weekly usage reporting)
- Dashboards and reports (role dashboards, my-work, analytics)
- Files (resume/document uploads)
- Workflow actions (nudges/reminders on stalled work)

### Explicitly out of scope (Deferred)

- Payments, subscription billing, plan tiers
- Email/SMS delivery of notifications (in-app only for MVP)
- Third-party ATS/job-board integrations (portal accounts are a manual registry, not live integrations)
- AI resume parsing/ranking
- Multi-tenancy beyond one workspace per deployment (a fresh deployment is a fresh tenant)
- Mobile native apps

---

## 5. Functional Requirements

### 5.1 Authentication & session — Shipped

- **FR-1.1** The system MUST authenticate users with email + password and issue a JWT session.
- **FR-1.2** Passwords MUST be hashed with bcrypt. Legacy unsalted SHA-256 hashes MUST migrate transparently on successful login.
- **FR-1.3** A user created by Admin without a password MUST receive a setup link; setting a password activates login.
- **FR-1.4** Session MUST expose the current user, their role(s), permission codes, and location scope to the frontend.
- **FR-1.5** Login MUST redirect to the dashboard; failed login MUST show a clear error without leaking whether the email exists.

### 5.2 Onboarding — Shipped (E2E verification pending)

- **FR-2.1** A fresh deployment MUST present a start-free-trial onboarding flow, not marketing pages, before login exists.
- **FR-2.2** The 7 onboarding steps MUST persist real data via API: company profile, locations, pipeline stages, designations, roles, users, and launch confirmation.
- **FR-2.3** The completing user MUST become the workspace Admin.
- **FR-2.4** Onboarding MUST be skippable per step (steps can be completed later in Admin settings) except company profile and Admin account.
- **FR-2.5** After launch, the Admin MUST land on a working dashboard with their created data visible.

### 5.3 Locations — Shipped

- **FR-3.1** Admin MUST create, edit, list, and deactivate locations.
- **FR-3.2** Each location MUST have a unique name and code, an optional head of location, and an address.
- **FR-3.3** Operational records (clients, requisitions, users) MUST be bound to a location.

### 5.4 Designations (master data) — Shipped

- **FR-4.1** Admin MUST create, edit, and list designations (the company's own job titles) via the master-data module.
- **FR-4.2** Designation codes MUST be unique and auto-generated slugs (editable).
- **FR-4.3** Requisitions MUST reference designations; the designation list MUST be maintained independently of requisitions.
- **FR-4.4** The master-data model MUST be generic (category → values) so Admin-defined categories beyond "designation" can be added later.

### 5.5 Roles & permissions — Shipped

- **FR-5.1** Admin MUST create roles and assign permission codes to them (module/action granularity).
- **FR-5.2** The permission catalog MUST cover: read/create/update on each module, approval.decide, requisition.assign, pipeline.stage.move, report.*, dashboard.view_*, notification.*, candidate duplicate handling, and settings management.
- **FR-5.3** Every protected endpoint MUST enforce its permission code server-side; the frontend MUST additionally hide actions the session's permission set lacks.
- **FR-5.4** A user with read-only permissions MUST get a read-only experience (no action buttons, read-only banners) — never broken buttons or silent failures.
- **FR-5.5** Role → permission → user chains MUST be covered by integration tests so bypasses cannot regress.

### 5.6 Users — Shipped

- **FR-6.1** Admin MUST create users (name, email, role, location) and trigger credential setup.
- **FR-6.2** Admin MUST deactivate users; deactivated users MUST fail login and lose API access.
- **FR-6.3** Admin MUST reset a user's password and move a user between locations.

### 5.7 Clients — Shipped

- **FR-7.1** Authorized users MUST create, edit, and list clients; a client belongs to one location.
- **FR-7.2** Clients MUST support multiple contacts (create/edit).

### 5.8 Requisitions — Shipped

- **FR-8.1** Authorized users MUST create requisitions referencing a client, designation, location, and pipeline template.
- **FR-8.2** A requisition MUST have exactly one primary owner and MAY have one delivery owner.
- **FR-8.3** Authorized users MUST assign contributors to a requisition and remove assignments.
- **FR-8.4** Requisition status changes MUST be permission-gated (`requisition.status.update`).

### 5.9 Candidates — Shipped

- **FR-9.1** Authorized users MUST create candidates manually and upload resumes.
- **FR-9.2** The system MUST detect duplicate candidates (global records, permission-controlled access) and offer: link existing, discard draft, or request override.
- **FR-9.3** Candidates MUST be linkable to requisitions and enter the pipeline.

### 5.10 Pipeline — Shipped

- **FR-10.1** Pipeline stages MUST be configurable per workspace (onboarding + Admin settings), with template validation.
- **FR-10.2** Authorized users MUST move candidates between stages; every move MUST record stage history.
- **FR-10.3** Stage history MUST be auditable (who, when, from → to).

### 5.11 Interviews, offers — Shipped (thin)

- **FR-11.1** Authorized users MUST schedule interviews against pipeline applications and record feedback.
- **FR-11.2** Authorized users MUST create offers and record accept/reject decisions.

### 5.12 Daily updates & meetings — Shipped

- **FR-12.1** Users MUST submit daily updates against their assigned requisitions (requisition selector + date + summary as minimum).
- **FR-12.2** Users with review permission MUST review submitted updates.
- **FR-12.3** Users MUST schedule and view meetings.

### 5.13 Approvals — Shipped

- **FR-13.1** Authorized users MUST request approvals; approvers with `approval.decide` MUST see pending requests in an inbox and approve/reject with comments.
- **FR-13.2** Approval permission codes MUST be present in role seeds (Admin decides, operational roles may request/view).

### 5.14 Notifications — Shipped

- **FR-14.1** The system MUST generate in-app notifications on key actions: requisition creation, pipeline stage moves, daily-update submission, approval decisions, assignment changes.
- **FR-14.2** The notifications page MUST show a live unread badge count and support mark-as-read; the backend endpoints MUST be authoritative.

### 5.15 Portal accounts — Shipped

- **FR-15.1** Admin MUST register company job-portal accounts (platform, login, ownership: company-shared or user-owned).
- **FR-15.2** Users MUST book usage slots against portal accounts; overlapping planned slots MUST be rejected.
- **FR-15.3** The analytics dashboard MUST show booked portal hours per platform per week.

### 5.16 Dashboards & reports — Partial

- **FR-16.1** Users MUST see dashboards appropriate to their permissions (my-work, pipeline summary, admin/manager views).
- **FR-16.2** Reports SHOULD cover time-to-fill, source effectiveness, team workload, SLA tracking. *(Several report pages are not fully wired — see §7 gaps.)*

### 5.17 Global UX — Shipped

- **FR-17.1** All pages MUST share global CSS/JS so header, footer, buttons, cards, and dialogs are unified — per-page copies are prohibited for shared concerns.
- **FR-17.2** Empty states MUST be shown when a data source returns zero results (icon, title, action hint).
- **FR-17.3** Keyboard shortcuts MUST work: `Esc` (close overlays), `Alt+←/→` (back/forward), `Ctrl/Cmd+Shift+N` (new candidate), `Shift+G` (dashboard), `/` (focus search), `?` (shortcut help).
- **FR-17.4** One failed API call on a page MUST NOT prevent the rest of the page from rendering (per-endpoint error boundaries).
- **FR-17.5** Buttons that own their behavior (inline dialogs) MUST NOT be hijacked by contextual routing to legacy form pages.

---

## 6. Non-Functional Requirements

- **NFR-1 Security.** All non-public endpoints require a valid session; all sensitive actions require their permission code; passwords are bcrypt; uploads are type/size constrained.
- **NFR-2 RBAC integrity.** Permission checks live in the backend dependency layer (single owner), not scattered per-route. The frontend gate is convenience, not security.
- **NFR-3 Location scoping.** Queries for operational data MUST be scoped to the user's permitted locations.
- **NFR-4 Test coverage.** The backend integration suite (FastAPI + real SQL Server via CI runner script) MUST pass; the RBAC chain (role create → permission assign → user create → RBAC probe) and the daily-update chain (assign → submit → owner notified) MUST have regression tests.
- **NFR-5 Auditability.** Stage moves, approval decisions, and credential changes MUST leave an audit trail.
- **NFR-6 Environment hygiene.** Dev servers MUST run on configurable ports (`API_PORT` for the frontend proxy) so they coexist with other local projects; the DB is SQL Server via the local container.
- **NFR-7 Documentation currency.** Docs describing removed features (Stitch exports, legacy scripts, old credentials) MUST NOT survive in `docs/` — stale docs are defects.

---

## 7. Known Gaps (work in progress — kept honest)

These are the open items between the current state and MVP-complete:

1. **Fresh-tenant E2E playtest** — onboarding → designations → locations → roles → user creation → login as created user → requisition → pipeline move → approval, run in the browser end to end. Chain pieces are individually tested; the full walkthrough is not yet recorded.
2. **Report pages wiring** — several report/dashboard pages still render thin or static content (time-to-fill, source effectiveness, custom report builder).
3. **Report depth** — report endpoints cover time-to-fill, source effectiveness, SLA, and a dataset catalog for the custom builder; deeper cross-filtering and exports are not built.
4. **Email notifications** — in-app only (Deferred for MVP, listed so it is a decision, not an accident).
5. **Careless-path hardening** — empty-form submits, rapid double-clicks on save, reload mid-dialog need a final pass.

---

## 8. Definition of Done (MVP acceptance flow)

The MVP may be declared ready when this flow passes in the browser, on a fresh database, without manual DB edits:

1. Visit landing → **Start free trial** → complete 7 onboarding steps (company, locations, pipeline stages, designations, roles, users, launch).
2. Completing user logs in as Admin; dashboard shows their data.
3. Admin creates an additional role with limited permissions, creates a user with it, sends setup link; the new user sets a password and logs in.
4. The limited user experiences correct read-only/hidden UI for actions their role lacks, and full function for actions granted.
5. Admin creates a client and a requisition (own designation, own pipeline stages); assigns the limited user as contributor.
6. Contributor submits a daily update → Admin gets a notification.
7. Contributor moves a candidate through pipeline stages → stage history records it.
8. An approval is requested and decided in the approvals inbox → both parties see the outcome.
9. Portal usage is booked and appears in the weekly analytics card.
10. Backend test suite passes (including RBAC-chain and daily-update-chain regression tests).

---

## 9. Traceability

- Product philosophy: `WORKING_MODEL.md`, `WORKING_MODEL_FEATURES_AND_ROLE_LIFECYCLE.md`
- Original scope freeze: `BUILD_PACK_MVP_FREEZE.md`
- Use cases & actor matrix: `MVP_USE_CASE_CATALOG.md`, `MVP_USE_CASE_ACTOR_MATRIX.md`
- Permission catalog: `PERMISSION_CODE_LIST.md`, `BUILD_PACK_PERMISSION_ACTION_MATRIX.md`
- API surface: `API_ENDPOINTS.md`, `BUILD_PACK_API_CONTRACT_BASELINE.md`
- Database: `DATABASE_DESIGN.md`, `backend/db/schema.sql` (schema is generated from the live DB)
- Where the docs are silent or stale, this document wins.
