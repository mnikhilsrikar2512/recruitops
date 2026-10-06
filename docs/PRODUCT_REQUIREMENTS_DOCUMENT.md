# RecruitOps — Product Requirements Document

**Status:** Source of truth for the end product  
**Audience:** Product, engineering, QA  
**Tenancy:** Multi-tenant SaaS (each recruiting company is an isolated tenant)

This is the only product document in the repository. How to run the stack lives in the root and `backend/` READMEs.

---

## 1. Vision

RecruitOps is a multi-tenant recruitment operations platform. Each **tenant** is a recruiting company (agency or internal TA team). Tenants do not share users, clients, requisitions, candidates, or notifications.

Within a tenant, teams work across **locations** (offices/branches). Location names and codes may repeat across tenants; they must be unique inside one tenant.

The product supports:

- Hiring for **client companies** (external clients)
- Optional internal hiring for the tenant’s own roles
- Location-scoped teams with **role-based access**
- End-to-end flow: client → requisition → candidate → pipeline → interview → offer → join
- Daily operational updates, approvals, meetings, portal sourcing accounts, and reports
- **Agentic AI assistants (V1):** Resume Screener, Daily Brief, Inbox Triage — with human approval before durable writes; more agents in later versions

**Production-ready** means the checklist in §13 is fully met — not merely that screens exist.

---

## 2. How the product works (narrative)

1. A company becomes a **tenant** (ops creates it, or self-serve signup creates tenant + first Admin).
2. Tenant Admin configures **locations**, **roles & permissions**, and **users**.
3. Recruiters / Managers manage **clients** and open **requisitions**.
4. Recruiters add **candidates**, upload resumes to **object storage**, run duplicate checks, and link candidates to requisitions.
5. Work moves on the **pipeline board** (stages, history, ownership).
6. **Interviews**, **offers**, and **join tracking** close the hire.
7. **Daily updates**, **approvals**, **meetings**, and **notifications** keep the team aligned.
8. **Reports** show time-to-fill, source effectiveness, workload, and placements — always scoped to the signed-in tenant.
9. **Agentic AIs (V1):** Resume Screener, Daily Brief, and Inbox Triage assist inside those flows. Agents propose; humans confirm before data is saved—except explicitly allowed auto-actions configured by Tenant Admin. More agents ship in later versions (§4.16).

Sidebar navigation shows **only pages that give value for that role** — driven by the role’s permission codes. Tenant Admin configures those permissions on the role editor for every role, including Admin.

**Critical rule — Admin does not see all pages.** Tenant Admin is an oversight and control-plane role. The Admin sidebar lists only admin-valuable pages (setup, people, governance, health of the business). Day-to-day execution pages (sourcing, pipeline moves, interview booking, daily-update submission, etc.) stay off the Admin nav unless the Admin role is explicitly granted those page permissions. There is **no** “if admin, show every link” bypass in the UI or API.

---

## 3. Actors and roles

| Role | Who | What they do |
|------|-----|----------------|
| **Tenant Admin** | Company administrator | Configures the tenant: users, locations, roles/permissions, settings, portal accounts, work assignment; monitors company/location health, approvals, notifications, and reports. Does **not** use the product as a full recruiter workspace by default. Cannot see other tenants. |
| **Manager** | Location / delivery lead | Oversight of clients, requisitions, pipeline, daily-update review, team workload within assigned location(s). |
| **Recruiter / HR** | Execution | Candidates, pipeline moves, daily updates, interviews/offers as permitted. |
| **Future: Reviewer** | Approver-only | Approvals inbox and related reads without full hiring create rights. |
| **Future: External / Portal user** | Limited | Client portal or sourcing-tool operator views (out of V1 depth). |
| **Platform ops** (not in-app V1 UI) | RecruitOps operator | Creates tenants manually when needed; not a cross-tenant “super Admin” inside the product UI for V1. |

**System vs. custom roles:** Tenant Admin, Manager, and Recruiter/HR ship as **system role templates** (fixed name, tenant-editable permission set). A tenant may also create **custom roles** (tenant-owned, deletable, no fixed permission set) via Role Management. System role templates seed with the default permission sets in §3.2; a tenant is free to change them per-tenant afterward — the defaults only govern what a brand-new tenant starts with.

Permissions are codes (e.g. `user.read`, `dashboard.view_admin`, `pipeline.stage.move`). Pages and actions require matching codes. **Default-deny sidebar:** a link appears only if the signed-in role has at least one required permission for that page. See §3.2 for the full permission-code catalog and default grants per system role.

### 3.1 Default Admin navigation (value pages only)

Seeded Tenant Admin permissions unlock **only** these sidebar destinations (plus always-available account chrome: My Profile, Logout):

| Nav area | Pages |
|----------|--------|
| Work / home | Role Dashboard (admin), Company Dashboard, Location Dashboard, My Work (shown only if the signed-in Admin also holds at least one execution-page grant — otherwise hidden, since there is no personal work queue to summarize) |
| Inbox | Notifications, Approvals |
| Admin | Users, Locations, Roles (+ permissions editor), Business Titles, Visibility Rules, Work Assignment, Portal Accounts, **AI usage & policy**, **Audit Log**, **Data Export/Delete Requests** |
| Reports | Analytics / Reports library, User Performance, Team Workload, SLA / company performance views that serve oversight |
| Account | My Profile (incl. MFA enrollment, active sessions); tenant Settings (company profile / logo, timezone/locale/working days) |

**Not on default Admin sidebar** (Manager / Recruiter value instead): Client Directory, Requisition List/Intake, Candidate Profiles, Pipeline Board, Interview Scheduler, Offer Management, Join Tracker, Daily Updates workspace/submission, Meetings, Follow-ups, and similar execution surfaces.

Admins who must also operate as recruiters get those pages only after an explicit permission grant on the Admin role (or by using a second user account with Recruiter role). Backend may still allow Admin to open a deep link if a permission exists; the **sidebar never dumps the full catalog**.

### 3.2 Permission-code catalog (default grants)

Every code follows `module.action` (or `module.subaction`). This is the source of truth every module in §4 and every page in §6 implicitly references. **A** = Tenant Admin, **M** = Manager, **R** = Recruiter/HR default grants (● granted, ○ not granted; tenants may change any of these after onboarding).

| Code | Gates | A | M | R |
|------|-------|---|---|---|
| `dashboard.view_admin` | Company/Location/Admin dashboards | ● | ○ | ○ |
| `dashboard.view_execution` | Role dashboard, My Work, daily review | ○ | ● | ● |
| `user.read` / `user.write` | Admin → Users | ●/● | ○/○ | ○/○ |
| `location.read` / `location.write` | Admin → Locations | ●/● | ○/○ | ○/○ |
| `role.read` / `role.write` | Admin → Roles + permissions editor | ●/● | ○/○ | ○/○ |
| `visibility_rules.write` | Admin → Visibility Rules | ● | ○ | ○ |
| `work_assignment.write` | Admin → Work Assignment | ● | ○ | ○ |
| `portal_accounts.write` | Admin → Portal Accounts | ● | ○ | ○ |
| `ai.use` | Any agent invocation | ○ | ● | ● |
| `ai.agent.resume_screener` / `.daily_brief` / `.inbox_triage` | Per-agent access | ○ | ●/●/● | ●/○/● |
| `ai.policy.write` | Admin → AI usage & policy | ● | ○ | ○ |
| `audit_log.read` | Admin → Audit Log | ● | ○ | ○ |
| `privacy_request.write` | Admin → Data Export/Delete Requests | ● | ○ | ○ |
| `client.read` / `client.write` | Client Directory, detail, create/edit | ○/○ | ●/● | ●/○ |
| `requisition.read` / `.write` | Requisition list/intake/detail | ○/○ | ●/● | ●/○ |
| `requisition.status.write` | Requisition status change | ○ | ● | ○ |
| `requisition.reassign_owner` | Owner reassignment | ○ | ● | ○ |
| `candidate.read` / `.write` | Candidate profiles, detail, upload | ○/○ | ●/● | ●/● |
| `candidate.duplicate.decide` | Duplicate-check decision | ○ | ● | ● |
| `pipeline.read.summary` | Pipeline board view (was `pipeline.board.read`) | ○ | ● | ● |
| `pipeline.stage.reopen` | Reopen a rejected/withdrawn application (planned; not yet granted by any route) | ○ | ● | ○ |
| `pipeline.stage.move` | Stage-move action | ○ | ● | ● |
| `interview.write` / `offer.write` | Schedule interview / create offer | ○/○ | ●/● | ●/○ |
| `interview.feedback.write` | Submit interview feedback | ○ | ● | ● |
| `offer.decision.write` | Record offer accept/decline | ○ | ● | ○ |
| `daily_update.write` | Submit a daily update | ○ | ○ | ● |
| `daily_update.review` | Review/approve daily updates | ○ | ● | ○ |
| `approval.decide` | Decide an approval | ● | ● | ○ |
| `approval.request` | Raise an approval/exception | ○ | ● | ● |
| `meeting.write` / `followup.write` | Meetings, follow-ups | ○/○ | ●/● | ●/● |
| `notification.read` | Notifications center | ● | ● | ● |
| `report.read` | Reports library, analytics | ● | ● | ○ (own metrics only) |
| `settings.write` | Tenant Settings (branding, timezone), Business Titles and other pick-lists | ● | ○ | ○ |
| `scope.company` | Reach every office of the user's own company (lists, dashboards, reports); without it a user reaches their own office only | ● | ○ | ○ |

New codes introduced by a future module (§5) must be added to this table before that module ships — no page or action ships without a row here.

### 3.3 Implementation codes (finer-grained codes the API checks)

The API checks finer codes than the product rows above; each one implements exactly one §3.2 row. A role template grants a §3.2 row by granting all of that row's implementation codes. `tests/test_permission_catalog_prd.py` fails the build when a route, page gate or role template uses a code that has no row in §3.2 or here.

| Implementation code | §3.2 row |
|---|---|
| `approval.create` | `approval.request` |
| `approval.read` | `approval.decide` |
| `assignment.create` | `work_assignment.write` |
| `assignment.read` | `work_assignment.write` |
| `assignment.update` | `work_assignment.write` |
| `candidate.create` | `candidate.write` |
| `candidate.duplicate.check` | `candidate.duplicate.decide` |
| `candidate.duplicate.discard_draft` | `candidate.duplicate.decide` |
| `candidate.duplicate.link_existing` | `candidate.duplicate.decide` |
| `candidate.duplicate.request_override` | `candidate.duplicate.decide` |
| `candidate.link_requisition` | `candidate.write` |
| `candidate.resume.upload` | `candidate.write` |
| `candidate.update` | `candidate.write` |
| `client.contact.create` | `client.write` |
| `client.contact.read` | `client.read` |
| `client.contact.update` | `client.write` |
| `client.create` | `client.write` |
| `client.update` | `client.write` |
| `daily_update.create_main` | `daily_update.write` |
| `daily_update.read` | `daily_update.review` |
| `dashboard.read_my_work` | `dashboard.view_execution` |
| `dashboard.read_pipeline_summary` | `dashboard.view_execution` |
| `dashboard.view_hr` | `dashboard.view_execution` |
| `dashboard.view_manager` | `dashboard.view_execution` |
| `dashboard.view_recruiter` | `dashboard.view_execution` |
| `interview.create` | `interview.write` |
| `interview.feedback.submit` | `interview.feedback.write` |
| `interview.read` | `interview.write` |
| `location.create` | `location.write` |
| `location.update` | `location.write` |
| `meeting.create` | `meeting.write` |
| `meeting.read` | `meeting.write` |
| `meeting.update` | `meeting.write` |
| `notification.mark_read` | `notification.read` |
| `offer.create` | `offer.write` |
| `offer.decide` | `offer.decision.write` |
| `offer.read` | `offer.write` |
| `pipeline.board.read` | `pipeline.read.summary` |
| `pipeline.read.detail` | `pipeline.read.summary` |
| `pipeline.stage.history.read` | `pipeline.read.summary` |
| `portal.assign_slot` | `portal_accounts.write` |
| `portal.create` | `portal_accounts.write` |
| `portal.read` | `portal_accounts.write` |
| `portal.update` | `portal_accounts.write` |
| `requisition.create` | `requisition.write` |
| `requisition.status.update` | `requisition.status.write` |
| `requisition.update` | `requisition.write` |
| `role.create` | `role.write` |
| `role.permissions.assign` | `role.write` |
| `role.update` | `role.write` |
| `settings.create` | `settings.write` |
| `settings.read` | `settings.write` |
| `settings.update` | `settings.write` |
| `user.create` | `user.write` |
| `user.credentials.manage` | `user.write` |
| `user.update` | `user.write` |
| `workflow_action.nudge` | `dashboard.view_execution` |
| `workflow_action.read` | `dashboard.view_execution` |
| `workflow_action.resolve` | `dashboard.view_execution` |
| `workflow_action.run` | `dashboard.view_execution` |
| `workflow_overlay.submit` | `dashboard.view_execution` |

---

## 4. Modules — current (V1)

### 4.1 Tenancy & onboarding

**Purpose:** Create and configure a recruiting company.  
**Flows:** Self-serve signup (tenant slug, company name, first Admin) **or** ops-provisioned tenant; then welcome → company profile → locations → roles → hiring teams → launch.  
**Rules:** Slug unique globally; first Admin cannot be deleted while sole admin; all subsequent data stamped with `tenant_id`.

### 4.2 Auth & account

**Purpose:** Sign in, recover access, manage profile.  
**Flows:** Login with **tenant slug + email + password** → JWT access + refresh → `/permissions/me` → home. Profile: name/phone; password change. Forgot/reset/setup with tokens.  
**Rules:** Credentials valid only inside the tenant; refresh rotation; logout revokes refresh family.

### 4.3 Admin control plane

**Purpose:** Users, locations, roles, business titles, visibility, work assignment, portal accounts.  
**Flows:** CRUD users; assign primary location + role; deactivate with work transfer; edit role permissions (drives each role’s sidebar, including Admin’s curated set); manage branches; assign requisition contributors; book portal slots.  
**Rules:** Last active Tenant Admin cannot lose admin / be deactivated without another admin; users cannot be assigned branches/roles from another tenant; Admin role seed must **not** include the full execution-page permission pack.

### 4.4 Clients

**Purpose:** Hiring clients the tenant recruits for.  
**Flows:** Directory → detail → contacts; create/edit client.  
**Rules:** Tenant + location scoped; contacts belong to client.

### 4.5 Requisitions

**Purpose:** Open roles / job demands.  
**Flows:** List → intake create/edit → detail → status → assignments → owner reassignment.  
**Rules:** Must link to a client in the same tenant; **location consistency** means the requisition’s location must match one of the linked client’s active locations, and any assigned recruiter/owner must belong to that same location (or hold a cross-location grant).

### 4.6 Candidates & documents

**Purpose:** Talent records and resumes.  
**Flows:** Profiles → detail → upload/review resume (object storage) → duplicate check/decision → finalize → link to requisition.  
**Rules:** Files in object storage; metadata in DB; duplicate decisions audited using the match rule in §11 (exact email/phone auto-flag, fuzzy name+location suggest-only).

### 4.7 Pipeline

**Purpose:** Application stage tracking.  
**Flows:** Board → stage move → application detail/history.  
**Default stages (tenant-editable via `onboarding-pipeline-stage-builder.html`):** Sourced → Screened → Interview → Offer → Joined, plus two always-present terminal stages **Rejected** and **Withdrawn** that a tenant cannot delete or reorder out of terminal position.  
**Rules:** Stage moves permissioned (`pipeline.stage.move`); history immutable (append-only, never edited/deleted); backward moves are allowed and logged with a required reason (`stage-move-dialog.html`); once an application reaches **Rejected**, **Withdrawn**, or **Joined** it is terminal — no further stage moves, only a Manager-permissioned "reopen" action that creates a new stage-history entry rather than mutating the old one; scoped via requisition/branch tenant.

### 4.8 Interviews, offers, join

**Purpose:** Late-stage hiring.  
**Flows:** Schedule interview → feedback; create offer → decision; join tracker.  
**Interview types:** Phone, Video, Onsite, Panel (tenant-editable picklist via master data). Feedback capture is a structured **scorecard** (per-round rating scale + free-text notes), not free text alone.  
**No-show / reschedule:** an interview round has a status of Scheduled / Completed / No-show / Rescheduled / Cancelled; No-show and Cancelled rounds do not block moving the application, but are visible in application history.  
**Offer approval:** an offer above a tenant-configured threshold (set in Settings) routes through the standard Approvals module (§4.10) before it can be marked "sent"; offers below the threshold can be sent directly by anyone with `offer.write`.  
**Rules:** Tied to applications; tenant-scoped.

### 4.9 Daily updates

**Purpose:** Recruiter operational reporting.  
**Flows:** Workspace draft/submit → review → detail.  
**Fields:** date, location, free-text summary, structured counters (calls made, resumes sourced, candidates screened, interviews scheduled), blockers (free text), linked requisitions (optional).  
**Cadence:** one update per user per working day; a missed update is surfaced to the user's Manager on `daily-updates-review.html` as an "overdue" flag after the tenant-configured cutoff time (default 10:00 next business day) — no hard block on other work, this is visibility only for V1.  
**Rules:** Submitter vs reviewer permissions (`daily_update.write` vs `daily_update.review`); tenant + location filters.

### 4.10 Approvals & workflow actions

**Purpose:** Governance exceptions and queues.  
**Flows:** Approvals inbox decide; workflow queue run/resolve/nudge.  
**What triggers an approval (V1 catalog — tenant can add more via Visibility Rules):** offer above threshold (§4.8), user deactivation with active work transfer, role-permission change affecting another Admin, requisition reassignment across locations, tenant data export/delete request. Each type carries its own required-fields/notes shape but shares the same inbox and decision record.  
**Rules:** Decision recorded (`approval.decide`); notifications to stakeholders.

### 4.11 Meetings & follow-ups

**Purpose:** External/business conversations and follow-ups.  
**Flows:** Meetings list/form; follow-ups (filtered views).  
**Rules:** Tenant-scoped; attendees recorded.

### 4.12 Notifications (in-app V1)

**Purpose:** Actionable inbox — no email digests required for V1.  
**Flows:** Center list → detail → mark read → open related record.  
**Rules:** Clear human copy; priority; deep-link `action_url`; recipient + tenant scoped. Prototype/static copy must not appear in production UI.

### 4.13 Dashboards & reports

**Purpose:** Role home, my work, analytics.  
**Flows:** Role / my-work / location / company dashboards; reports library; time-to-fill; source effectiveness; placements; custom builder.  
**KPIs shown per dashboard (V1):**
- *Role dashboard (Recruiter/Manager):* open requisitions owned, applications by stage, interviews this week, overdue daily updates.
- *My Work:* personal queue — assigned tasks, upcoming interviews, pending approvals awaiting my input.
- *Location dashboard:* time-to-fill (location avg), active requisitions, team workload, SLA breaches.
- *Company dashboard (Admin):* tenant-wide time-to-fill, placements this month, location comparison, AI usage summary.  
**Rules:** Metrics never cross tenants.

### 4.14 Settings

**Purpose:** Tenant branding and company profile.  
**Flows:** Profile + logo (object storage); tenant defaults — timezone, locale (date/number format), working days/hours (used for daily-update cadence §4.9 and SLA calculations), offer-approval threshold (§4.8).  
**Rules:** Settings belong to current tenant only; timezone/locale defaults apply to any user who hasn’t set a personal override.

### 4.15 Support (V1)

**Purpose:** In-product help shell.  
**Rules:** Static help is acceptable for V1; no ticket backend required for production bar unless listed in §12. AI help copilot may sit beside this later (§4.16).

### 4.16 Agentic AI (product capability)

**Purpose:** A small set of **named agents** that run bounded tasks inside RecruitOps. Each agent has a job, allowed tools, tenant-scoped data access, and a UI surface (panel, wizard step, or inbox suggestion). Agents do not replace roles; they accelerate work under RBAC.

**Principles**
- **Tenant isolation:** prompts, retrieval, and tool calls use only the signed-in tenant’s data.
- **Human-in-the-loop (default):** agent output is a draft/suggestion until the user accepts (or Admin enables a narrow auto-apply rule).
- **Audit:** every agent run logs actor, agent id, inputs refs, outputs summary, accept/reject.
- **Permissions:** `ai.use`, plus per-agent codes (e.g. `ai.agent.resume_screener`).
- **No silent cross-module writes** without an allowed tool + user/admin policy.
- **Input sanitization / prompt-injection defense:** resume text and other user- or candidate-supplied content is treated as untrusted. It is passed to the LLM only inside a fenced "data" role/section, never concatenated into system instructions; tool-invocation instructions embedded in that content are ignored by the orchestration layer.
- **Confidence signaling:** structured outputs (e.g. Resume Screener extraction, match notes) include a confidence indicator; low-confidence fields are visually flagged for the reviewer instead of presented as fact.
- **Provider fallback:** the AI orchestration service supports a secondary LLM provider/model; if the primary provider errors or times out, the run either retries against the fallback or fails visibly with a retryable error — it never silently returns a stale/empty draft as if it succeeded.
- **Cost governance:** `ai_tenant_policies` includes a per-tenant monthly token/spend cap and a per-run token ceiling. When a tenant hits its cap, new runs are blocked with a clear message (not silently degraded) until Admin raises the limit or the next cycle starts.
- **Fairness review (hiring-adjacent scoring):** Resume Screener match scores are advisory only, are never the sole basis for a reject action inside the product, and are logged with enough context (inputs + score + rationale) to support a bias audit. Score-driving logic is reviewed before GA and after any material prompt/model change.
- **Eval/regression gate:** each V1 agent has a fixed evaluation set (sample resumes / updates / notifications with expected outputs). A prompt or model change may not ship until it passes the eval set at or above the previous baseline.

#### Named agents (V1)

| Agent ID | Name | Job | Where used | Output |
|----------|------|-----|------------|--------|
| `resume_screener` | Resume Screener | Parse resume from object storage; extract skills/experience; score vs a requisition when one is selected | Resume upload/review, candidate detail | Structured profile draft + match notes (user confirms before save) |
| `daily_brief` | Daily Brief | Summarize a user’s or team’s daily updates / my-work queue | Role dashboard, daily review, manager review | Short brief + suggested focus items |
| `inbox_triage` | Inbox Triage (Inbox Brief) | Prioritize notifications; rewrite unclear copy into What / Why / Next | Notifications center | Sorted queue + clearer headlines (apply on view; mark-read still user-driven) |

#### Named agents (later versions)

| Agent ID | Name | Job |
|----------|------|-----|
| `requisition_drafter` | Requisition Drafter | Draft JD / intake fields from short brief or client notes |
| `match_advisor` | Match Advisor | Rank candidates for a requisition (or reqs for a candidate) |
| `interview_coach` | Interview Coach | Suggest interview questions and scorecards from requisition + stage |
| `offer_assistant` | Offer Assistant | Draft offer letter / package summary from policy templates |
| `client_insight` | Client Insight | Summarize client hiring health and risks for Admin/Manager |
| `exception_analyst` | Exception Analyst | Explain approval/exception context and recommend decide path |
| `help_copilot` | Help Copilot | Answer “how do I…?” from product docs inside Support |

**Runtime (tech):** Backend **AI orchestration service** (FastAPI module) calling an LLM provider with tool adapters (read candidate/requisition, fetch resume text from object storage, write draft-only entities). Optional vector index **per tenant** for resume/JD retrieval. UI: shared `ai-agent-panel` overlay + inline “Ask agent” CTAs on host pages.

**Admin value page:** optional **AI usage & policy** under Admin nav (enable agents, spend/limits, auto-apply toggles) — fits §3.1 oversight, not execution clutter.

### 4.17 Compliance & legal (V1)

**Purpose:** Make the platform legally operable for paying tenants who hold candidate PII and use AI in a hiring context.  
**Flows:** Terms of Service + Privacy Policy + Data Processing Addendum (DPA) accepted at tenant signup (self-serve) and on file for ops-provisioned tenants; tenant-facing "Data export/delete request" page under Settings that calls the §9.7 privacy endpoints; cookie/consent banner on marketing pages.  
**Rules:** ToS/Privacy/DPA versions are tracked with acceptance timestamp + user id; a tenant cannot be marked `active` via self-serve signup without acceptance; AI-specific disclosures (candidates may be scored by an automated tool) are included in the Privacy Policy and, where legally required by the tenant’s jurisdiction, surfaced to candidates.  
**Non-goals for V1:** full multi-region data residency (document the current storage region only), SOC 2 report (target for a later version, see §12).

---

## 5. Modules — future

| Module | Intent |
|--------|--------|
| Email notification digests | Optional outbound email for invites/resets already; digests later |
| Calendar sync | Google/Outlook for interviews/meetings |
| Client portal | External client self-service |
| Additional AI agents | Requisition Drafter, Match Advisor, Interview Coach, Offer Assistant, Client Insight, Exception Analyst, Help Copilot (§4.16 later versions) |
| Billing / subscription | Per-tenant plans (may meter AI usage) |
| Platform super-admin console | Cross-tenant ops UI |
| Mobile native apps | Beyond responsive web |
| Multi-currency offers | Localized offer packages |
| Slack / Teams bots | Push critical approvals |
| Enterprise SSO (SAML/OIDC) | "Sign in with Google/Microsoft/Okta" per tenant, alongside slug+password |
| SOC 2 Type II | Formal audit once tenant volume/ACV justifies it |
| Multi-region data residency | Store a tenant’s data in a chosen region |

---

## 6. Page inventory and wireframes

**Status legend:** `Existing` = prototype page ships as-is into production once hardened per §13. `Existing → update` / `Existing → harden` = prototype page needs specific rework named in its Wireframe-focus cell before it meets the production bar. `Overlay` = modal/drawer/dialog, not a routable page. `New (V1)` = not in the current prototype; must be built for this PRD’s V1 scope. `Future` / `Future overlay` = out of V1 scope, tracked for a later version (§5). `Marketing` = public/unauthenticated page, not gated by permission codes.

Every non-overlay, non-marketing page is gated by at least one code from §3.2; pages aren’t re-annotated with their code here to avoid the table drifting out of sync with §3.2 — §3.2 is the source of truth for what gates what.

Wireframe legend (every page):

```
┌─ Topbar: section · page title · search · notifications · avatar(profile)
├─ Sidebar: only role-valuable permitted nav links (Admin = control plane, not all pages; collapsed = flyout)
└─ Canvas
   ├─ Header: title + primary CTA(s)
   ├─ Filters / tabs (if any)
   ├─ Main content
   └─ Empty | Loading | Error | Access denied states
```

### 6.1 Marketing & auth

| Page | Status | Wireframe focus |
|------|--------|-----------------|
| `index.html` / landing | Existing | Brand hero, CTA Login / Learn |
| `login.html` | Existing → update | Tenant slug, email, password, links forgot/signup |
| `forgot-password.html` | Existing | Email + tenant context |
| `reset-password.html` | Existing | Token + new password |
| `password-setup.html` | Existing | Invite token + new password |
| `access-denied.html` | Existing | Message + back to home |
| `not-found.html` | Existing | 404 + home |
| **Tenant signup** | Future page | Company name, slug, admin email/password |
| `tenant-setup.html` | Existing shell | Ops/self-serve completion |

### 6.2 Onboarding

| Page | Status | Wireframe |
|------|--------|-----------|
| `onboarding-welcome.html` | Existing | Progress, Start |
| `onboarding-company-profile.html` | Existing | Company fields, logo upload |
| `onboarding-locations.html` | Existing | Add locations table |
| `onboarding-role-setup.html` | Existing | Role templates toggles |
| `onboarding-hiring-teams.html` | Existing | Invite users |
| `onboarding-pipeline-stage-builder.html` | Existing | Stage list reorder |
| `onboarding-integrations.html` | Existing / future depth | Portal/calendar stubs |
| `onboarding-success-launch.html` | Existing | Launch to dashboard |
| Overlay: `onboarding-add-custom-stage-overlay.html` | Existing | Stage name form |

### 6.3 Work home

| Page | Status | Wireframe |
|------|--------|-----------|
| `role-dashboard.html` | Existing | KPI cards, queues, shortcuts |
| `my-work-dashboard.html` | Existing | Personal tasks, overdue |
| `daily-review.html` | Existing | Day plan list |
| `company-dashboard.html` | Existing | Tenant-wide KPIs (admin) |
| `location-dashboard.html` | Existing | Location KPIs |
| `delivery-work-queue.html` | Existing | Prioritized work list |
| `dashboard-actions-overlay.html` | Overlay | Quick actions |

### 6.4 Admin

| Page | Status | Wireframe |
|------|--------|-----------|
| `user-management.html` | Existing | User table, Add User |
| `user-detail.html` | Existing | Profile, role, location, actions |
| `deactivate-user-dialog.html` | Overlay | Reason + transfer target |
| `location-management.html` | Existing | Location table CRUD |
| `role-management.html` | Existing | Roles table |
| `role-permissions-editor.html` | Existing | Permission toggles → Save |
| `business-titles.html` | Existing | Title master list |
| `visibility-rules.html` | Existing | Scope rules by role |
| `work-assignment.html` | Existing | Assign contributors |
| `portal-accounts.html` | Existing | Accounts + slots |
| `my-profile.html` | Existing | Details + password forms |

### 6.5 Clients & requisitions

| Page | Status | Wireframe |
|------|--------|-----------|
| `client-directory.html` | Existing | Searchable table, kebab View/Edit |
| `client-detail.html` | Existing | Summary, contacts, reqs |
| `contact-form-dialog.html` | Overlay | Contact fields |
| `requisition-list.html` | Existing | Filters, Create |
| `requisition-intake.html` / `-edit` | Existing | Multi-section form |
| `requisition-detail.html` | Existing | Status, owners, assignments |
| `assignment-history-drawer.html` | Overlay | History list |
| `reassign-owner-dialog.html` | Overlay | New owner |
| `reassignment-review-drawer.html` | Overlay | Review impact |
| `status-update-dialog.html` | Overlay | New status + note |

### 6.6 Candidates & pipeline

| Page | Status | Wireframe |
|------|--------|-----------|
| `candidate-profiles.html` | Existing | Table/cards, Add |
| `candidate-detail.html` | Existing | Profile, docs, apps |
| `candidate-screening.html` | Existing | Screening checklist |
| `candidate-review-drawer.html` | Overlay | Review fields |
| `candidate-duplicate-review.html` | Existing | Match list + decision |
| `duplicate-warning-modal.html` | Overlay | Warning + continue |
| `resume-upload-and-review.html` | Existing | Upload → preview → save |
| `link-to-requisition-dialog.html` | Overlay | Pick req |
| `review-matches-workspace.html` | Existing | Match review |
| `pipeline-board.html` | Existing | Columns by stage, cards |
| `application-detail-drawer.html` | Overlay | App summary |
| `application-history.html` / `pipeline-history-drawer` | Existing | Timeline |
| `stage-move-dialog.html` | Overlay | To-stage + reason |
| `stage-history-audit-log.html` | Existing | Audit table |

### 6.7 Interviews, offers, join

| Page | Status | Wireframe |
|------|--------|-----------|
| `interview-scheduler.html` | Existing | List/calendar shell + Schedule |
| `interview-detail.html` | Existing | Round details |
| `interview-feedback-dialog.html` | Overlay | Score + notes |
| `offer-management.html` | Existing | Offers table |
| `offer-create-dialog.html` | Overlay | Offer fields |
| `join-tracker.html` | Existing | Join statuses |

### 6.8 Daily ops, inbox, meetings

| Page | Status | Wireframe |
|------|--------|-----------|
| `daily-updates-workspace.html` | Existing | List + compose |
| `daily-updates-submission.html` | Existing | Submit form |
| `daily-updates-review.html` | Existing | Review queue |
| `daily-update-detail-panel.html` | Overlay/panel | Full update |
| `approvals-inbox.html` | Existing | Tabs + decide |
| `approval-review-drawer.html` | Overlay | Approve/reject + notes |
| `exception-request-dialog.html` | Overlay | Exception form |
| `clarification-request-dialog.html` | Overlay | Clarification form |
| `notifications-center.html` | Existing → harden | Live queue only; What/Why/Next + Open |
| `notification-detail-panel.html` | Overlay | Full story + CTA |
| `meetings.html` | Existing | Meeting list |
| `meeting-form-dialog.html` | Overlay | Schedule meeting |
| `follow-ups.html` | Existing | Follow-up list |
| `follow-up-form-dialog.html` | Overlay | Follow-up fields |

### 6.9 Reports & misc

| Page | Status | Wireframe |
|------|--------|-----------|
| `analytics-dashboard.html` | Existing | Charts + filters |
| `reports.html` / report viewer / custom builder | Existing | Dataset pick → view |
| `pipeline-analytics.html` | Existing | Funnel |
| `time-to-fill-report.html` | Existing | Report table |
| `source-effectiveness.html` | Existing | Source metrics |
| `sla-tracker.html` | Existing | SLA list |
| `user-performance-reports.html` | Existing | Per-user metrics |
| `team-workload.html` | Existing | Load balance |
| `support-workspace.html` | Existing | Help content |
| `use-cases.html` / product-tour* | Marketing | Tour only |
| `ai-agent-panel.html` | Future overlay | Agent name, goal, streaming/status, draft result, Accept / Edit / Discard |
| `ai-usage-policy.html` | Future (Admin) | Enable agents, limits, auto-apply toggles, usage summary |
| `mfa-enroll.html` | New (V1) | QR/secret, confirm code, recovery codes display |
| `mfa-challenge.html` | New (V1) | Code entry during login |
| `active-sessions.html` | New (V1, in My Profile) | Device list, last seen, Revoke / Revoke all |
| `audit-log-viewer.html` | New (V1, Admin) | Filterable event table, event detail drawer |
| `data-export-delete-request.html` | New (V1, Admin Settings) | Request export/delete, status of prior requests |
| `legal-acceptance.html` | New (V1, signup step) | ToS / Privacy / DPA summary + accept checkbox |

**Future pages to build (add wireframes same pattern):** Tenant signup; Interview calendar (full); Company settings hub; Email preference center; Billing (post-V1); AI usage & policy; shared AI agent panel wired on host pages; SSO configuration (Admin).

---

## 7. Tech stack (target production)

| Layer | Choice |
|-------|--------|
| Frontend | Static HTML pages + shared JS/CSS (`frontend/`), Node ≥ 20 LTS static server with `/api` proxy; no bundler required for V1 (vanilla JS modules) |
| Backend | Python 3.11+, FastAPI (`backend/`), `/api/v1`; SQLAlchemy 2.x ORM + Alembic migrations |
| Database | Microsoft SQL Server 2019+ |
| Auth | **JWT access token** (short-lived) + **refresh token** (rotating, stored hashed server-side) |
| Files | **S3-compatible object storage** for resumes/logos/documents |
| AI | LLM provider via backend **agents** module; optional per-tenant vector index for resume/JD retrieval; tool adapters enforce RBAC + tenant scope |
| Cache / shared state | **Redis (required, not optional)** — backs rate limiting (§10), session tracking (§10), idempotency keys (§9.0), refresh-token denylist, and agent job queues; these features need cross-instance shared state and cannot run on in-process memory once there’s more than one API instance |
| API docs | FastAPI auto-published OpenAPI schema at `/api/v1/openapi.json`; served as human-readable docs in non-prod environments |
| Deploy | Containerized API + static frontend + managed MSSQL + object storage + managed Redis |

Current prototype may still use opaque session tokens; production architecture standardizes on JWT access + refresh as above.

---

## 8. Database (target model)

### 8.1 Tenancy

- `tenants` — id, slug (unique), display_name, status, created_at  
- Every operational root row carries `tenant_id NOT NULL`  
- Evolve/replace single-primary `company_entities` with tenant-scoped branding (`tenant_settings` / logo object key)

### 8.2 Identity & access

- `users` — tenant_id, email (unique per tenant), password_hash, status, …  
- `roles`, `permissions`, `role_permissions` — system codes; custom roles tenant-owned  
- `branches` (API: locations) — tenant_id, code unique per tenant  
- `user_branch_roles` — user ↔ branch ↔ role  
- `refresh_tokens` — user_id, token_hash, expires_at, revoked_at, family_id  
- `password_reset_tokens`, `user_invitations`, `audit_logs`  
- `user_mfa` — user_id, secret (encrypted), enabled_at, recovery_codes (hashed)  
- `user_sessions` — user_id, refresh family_id, device/user-agent, ip, created_at, last_seen_at, revoked_at  
- `legal_acceptances` — tenant_id, user_id, document_type (tos/privacy/dpa), version, accepted_at  
- `privacy_requests` — tenant_id, requested_by, type (export/delete), status, requested_at, completed_at

### 8.3 Hiring domain (all tenant-scoped)

- `client_companies`, `client_contacts`  
- `requisitions`, `requisition_assignments`, screening/skill/end-client helpers  
- `candidates`, `candidate_documents` (object_key), `candidate_applications`, stage history, duplicate tables  
- `interview_rounds` — application_id, type, status (Scheduled/Completed/No-show/Rescheduled/Cancelled), scheduled_at, scorecard_json  
- `offers` — application_id, package fields, status, approval_id (nullable, set when routed through Approvals per §4.8), decision, decided_at  
- `join_records` — application_id, expected_join_date, actual_join_date, status  
- `daily_updates` / `recruiter_daily_updates` — see §4.9 field schema  
- `meetings`, `meeting_attendees`  
- `notifications`, `notification_templates` — templates hold the "What/Why/Next" copy structure per notification type; a notification row references a template + interpolation values rather than storing raw copy, so template edits (Admin) update future notifications consistently  
- `approvals` / `approval_requests`, `workflow_action_items`, `workflow_action_events`  
- `portal_accounts`, `portal_account_slots`  
- `reports` / `report_rows` as needed  
- `master_data_*` for picklists (incl. interview types, offer-approval threshold)  
- `ai_agents` — catalog of agent ids, status, default config  
- `ai_tenant_policies` — per-tenant enablement, limits, auto-apply flags  
- `ai_runs` — tenant_id, agent_id, actor_user_id, status, input_refs, output_json, accepted_at, error  
- Optional `ai_embeddings` / external vector store keyed by tenant_id + entity_type/id  

**Lifecycle rule:** archiving a `client` or `candidate` (soft-delete, §9.0) does **not** cascade-archive its linked `requisitions`/`candidate_applications` — those keep their own status and remain visible in history/reports; the parent record simply shows as "Archived" wherever it's referenced.

**Search:** `candidates` and `requisitions` carry a computed full-text/search column (skills, title, summary) with a database full-text index (or an external search index, e.g. OpenSearch, if p95 search latency targets in §12 aren't met by DB full-text alone) — candidate/requisition list search is not a simple `LIKE` scan in production.

### 8.4 Key uniqueness

- `(tenant_id, email)` on users  
- `(tenant_id, code)` on branches  
- Global unique `tenants.slug`  
- Object storage keys prefixed by `tenant_id/`

---

## 9. APIs and endpoints

Base: `/api/v1`. All authenticated routes require valid **access JWT** whose `tenant_id` matches the row scope. Unless noted, list/create are tenant-filtered automatically.

### 9.0 Conventions

- **Pagination:** all list endpoints accept `page` (1-based) and `page_size` (default 25, max 100), or `cursor` for high-volume feeds (`notifications`, `audit-logs`); responses include `total`, `page`, `page_size`.
- **Sorting/filtering:** list endpoints accept `sort` (field, `-field` for descending) and entity-appropriate filter query params (e.g. `status`, `location_id`, `date_from/date_to`); unsupported filters return `400`, not a silent no-op.
- **Error contract:** all error responses use `{ "error": { "code": "STRING_CODE", "message": "human copy", "field_errors": [{ "field": "...", "message": "..." }] } }`; `code` is stable and documented per endpoint family (e.g. `TENANT_MISMATCH`, `LAST_ADMIN_PROTECTED`, `VALIDATION_ERROR`).
- **Delete/archive semantics:** entities with business history (clients, requisitions, candidates, applications) are **soft-deleted** (`status = archived`, excluded from default list views, retained for audit/reports); only entities with no downstream history (e.g. a draft contact never linked to anything) may hard-delete. Each entity’s delete behavior is documented in its endpoint row below.
- **Idempotency:** state-changing POSTs that a client may retry (e.g. `/auth/login`, `/candidates/{id}/upload`) accept an `Idempotency-Key` header.

### 9.1 System

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |

### 9.2 Auth & tenancy

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/login` | slug + email + password → access + refresh |
| POST | `/auth/refresh` | rotate refresh → new access (+ refresh) |
| POST | `/auth/logout` | revoke refresh |
| GET | `/auth/me` | current user session summary |
| PATCH | `/auth/profile` | self name/phone |
| POST | `/auth/password/change` | change password |
| POST | `/auth/password/forgot` | start reset |
| POST | `/auth/password/reset` | complete reset |
| POST | `/auth/password/setup` | invite setup |
| POST | `/auth/mfa/enroll` | start MFA enrollment (TOTP), returns QR/secret |
| POST | `/auth/mfa/verify` | confirm MFA code, activates MFA on account |
| POST | `/auth/mfa/challenge` | submit MFA code during login |
| DELETE | `/auth/mfa` | disable MFA (Admin-forced re-verify or password re-entry required) |
| GET | `/auth/sessions` | list active sessions/devices for current user |
| DELETE | `/auth/sessions/{sid}` | revoke a specific session (“log out this device”) |
| DELETE | `/auth/sessions` | revoke all sessions except current (“log out everywhere”) |
| POST | `/tenants/signup` | self-serve tenant + first admin |
| POST | `/tenants` | ops-provision tenant (ops credential / future) |
| GET | `/permissions/me` | effective permission codes + scopes |

### 9.3 Admin modules

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/locations/` | list/create |
| GET/PATCH | `/locations/{id}` | read/update |
| GET/POST | `/users/` | list/create |
| GET/PATCH | `/users/{id}` | read/update |
| POST | `/users/{id}/credentials/reset` | reset credentials |
| POST | `/users/{id}/deactivate` | deactivate + transfer |
| POST | `/users/{id}/move` | move location |
| GET/POST | `/roles/` | list/create |
| GET/PATCH | `/roles/{id}` | read/update |
| GET/PUT | `/roles/{id}/permissions` | read/replace permissions |
| GET/PATCH | `/settings/profile` | tenant company profile |
| PUT/DELETE/GET | `/settings/logo` | logo object |

### 9.4 Clients & requisitions

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/clients/` | list/create |
| GET/PATCH | `/clients/{id}` | read/update |
| GET/POST | `/clients/{id}/contacts` | contacts |
| PATCH | `/clients/contacts/{id}` | update contact |
| GET/POST | `/requisitions/` | list/create |
| GET/PATCH | `/requisitions/{id}` | read/update |
| PATCH | `/requisitions/{id}/status` | status |
| GET/POST | `/requisitions/{id}/assignments` | assignments |
| DELETE | `/requisitions/assignments/{id}` | remove assignment |
| POST | `/requisitions/{id}/reassign-owners` | reassign |

### 9.5 Candidates & pipeline

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/candidates/` | list/create |
| GET/PATCH | `/candidates/{id}` | read/update |
| POST | `/candidates/{id}/documents` | metadata |
| POST | `/candidates/{id}/upload` | upload → object storage |
| GET | `/candidates/{id}/duplicate-check` | check |
| POST | `/candidates/{id}/duplicate-check/decision` | decide |
| POST | `/candidates/{id}/finalize-profile` | finalize |
| POST | `/candidates/{id}/applications` | link req |
| POST | `/candidates/{id}/reassign-owner` | reassign |
| GET | `/pipeline/board` | board |
| GET | `/pipeline/applications/{id}` | detail |
| PATCH | `/pipeline/applications/{id}/stage` | move |
| GET | `/pipeline/applications/{id}/history` | history |

### 9.6 Interviews, offers, daily, meetings, portal

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/interviews/` | list/create |
| GET | `/interviews/{id}` | detail |
| PATCH | `/interviews/{id}/feedback` | feedback |
| GET/POST | `/offers/` | list/create |
| GET | `/offers/{application_id}` | detail |
| PATCH | `/offers/{application_id}/decision` | decide |
| GET/POST | `/daily-updates/` | list/create |
| GET | `/daily-updates/{id}` | detail |
| GET/POST | `/meetings/` | list/create |
| GET/PATCH | `/meetings/{id}` | read/update |
| CRUD | `/portal-accounts/` (+ slots) | sourcing accounts |

### 9.7 Inbox, workflow, files, reports, dashboards

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/notifications/` | list |
| PATCH | `/notifications/{id}/read` | mark read |
| GET/POST | `/approvals/` | list/create |
| GET | `/approvals/{id}` | detail |
| PATCH | `/approvals/{id}/decide` | decide |
| GET | `/workflow-actions/queue` | queue |
| POST | `/workflow-actions/overlay-submissions` | overlay |
| POST | `/workflow-actions/{id}/run\|resolve\|nudge` | actions |
| GET | `/files/{path}` | authorized file redirect/stream |
| GET | `/dashboards/role\|my-work\|location-summary\|company-summary` | dashboards |
| GET | `/reports/*` | time-to-fill, source-effectiveness, placements, client-summary, datasets |
| GET | `/reports/*/export` | export a report as CSV/XLSX/PDF (`?format=`) |
| GET/POST/PATCH | `/master-data/...` | picklists |
| GET | `/audit-logs` | list audit events (Admin; filter by actor, entity, date range) |
| GET | `/audit-logs/{id}` | audit event detail |
| POST | `/privacy/export-request` | tenant Admin requests full tenant data export (incl. AI run logs) |
| POST | `/privacy/delete-request` | tenant Admin requests tenant data deletion; queued + confirmed out-of-band |
| GET | `/privacy/requests` | status of export/delete requests |
| GET/POST | `/legal/acceptances` | record/read ToS · Privacy · DPA version acceptance for the tenant |

### 9.8 Agentic AI

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/ai/agents` | list agents available to tenant + user permissions |
| GET | `/ai/policies` | tenant AI policy (Admin) |
| PATCH | `/ai/policies` | update enablement / limits / auto-apply (Admin) |
| POST | `/ai/runs` | start agent run `{ agent_id, context }` |
| GET | `/ai/runs/{run_id}` | poll status + draft output |
| POST | `/ai/runs/{run_id}/accept` | apply accepted draft via allowed tools |
| POST | `/ai/runs/{run_id}/reject` | discard draft |
| GET | `/ai/usage` | tenant usage summary (Admin) |

---

## 10. Security

- **TLS 1.2+** everywhere in production, HSTS enabled on all public endpoints  
- **JWT access** (short TTL, claims: `sub`, `tenant_id`, `sid`) in `Authorization: Bearer`  
- **Refresh tokens** opaque, hashed at rest, rotated on use, revocable on logout/password change  
- **Password hashing** (bcrypt/argon2); force change flags honored  
- **Password policy:** minimum length 12, blocklist of common/breached passwords (e.g. HaveIBeenPwned range check), no forced periodic rotation (NIST-aligned), account lockout/backoff after repeated failed logins  
- **MFA (V1, TOTP):** available to every user, **required for Tenant Admin** before the tenant can be marked production-active; recovery codes issued at enrollment  
- **SSO (Future, not V1-blocking):** SAML/OIDC per tenant as an alternative to slug+email+password — tracked in §5  
- **RBAC** on every mutating and sensitive read endpoint  
- **Tenant isolation** enforced in service/repository layer (not only UI)  
- **Rate limits** on login (5/min/IP + 10/min/account), signup, forgot-password, refresh — explicit numeric defaults, tenant-configurable within a floor/ceiling  
- **Session/device management:** users can list and revoke their own active sessions (`/auth/sessions`); Admin can force-revoke a user’s sessions on deactivation or suspected compromise  
- **CORS** restricted to known frontend origins  
- **Object storage** private buckets; short-lived signed URLs; keys never guessable across tenants  
- **File upload validation:** resumes/logos restricted to an allow-list of MIME types (PDF/DOC/DOCX/PNG/JPG), size-capped (resumes ≤ 10 MB, logos ≤ 5 MB), and scanned for malware before being marked available; failed scans are quarantined, never linked to a candidate record  
- **AI:** prompts/tools scoped to `tenant_id`; no training on other tenants’ data; PII minimized in logs; provider keys server-side only; untrusted content (resume text, notes) never concatenated into system-level instructions (see §4.16 prompt-injection defense)  
- **Audit logs** for admin, stage moves, deactivations, permission changes, session revocations, MFA changes, **AI accept/reject**, and privacy export/delete requests  
- **Input validation** (Pydantic) and parameterized SQL only  
- **API error contract** (see §9.0) never leaks stack traces, internal ids from other tenants, or DB error text to the client  
- **Secrets management:** DB credentials, object-storage keys, and LLM provider keys are stored in a managed secret store (e.g. AWS Secrets Manager / Vault), never in source control or plain environment files checked into the repo; rotated on a documented schedule  

---

## 11. Guardrails

| Guardrail | Rule |
|-----------|------|
| Cross-tenant access | Always 404/403; never leak existence |
| Tenant Admin power | Full **control-plane** power within tenant; sidebar limited to admin-value pages (§3.1); execution pages only if explicitly granted |
| Last admin | Cannot demote/deactivate last active admin in tenant |
| Location codes | Unique per tenant; may collide across tenants |
| Sidebar | Default-deny; show only permitted pages; Admin never auto-sees every page — only admin-value set (§3.1) |
| Profile phone | Name-only save must not clear phone |
| File access | AuthZ check before signed URL |
| Refresh theft | Rotation + reuse detection revokes family |
| Self-serve signup | Reserved slugs blocked; email verification path documented |
| Data export/delete | Tenant Admin can request export/delete of tenant data (privacy) |
| Backups | Point-in-time DB + object-store versioning |
| AI writes | Default human accept; auto-apply only if Admin policy allows a specific agent action |
| AI tenant bleed | Agent tools refuse foreign tenant ids; retrieval filtered by tenant_id |
| AI prompt injection | Candidate/resume content is data, never treated as instructions by the orchestration layer or tool adapters |
| AI scoring fairness | Resume Screener score is advisory only; never the sole basis for an automated reject; run inputs/rationale retained for audit |
| Duplicate candidates | Match rule: exact email OR exact phone = auto-flag; fuzzy name+location similarity above threshold = suggest-only (human decides) |
| Record deletion | Business-history entities (clients, requisitions, candidates, applications) soft-delete/archive only; hard delete limited to never-linked draft records |
| Timezone | All timestamps stored UTC; displayed in the location’s configured timezone (or user’s browser timezone if unset) — interview/meeting times must show timezone explicitly on every surface |
| Concurrent edits | Optimistic locking (`updated_at`/version check) on requisition, candidate, and pipeline-stage writes; conflicting write returns `409` with latest version, not silent overwrite |
| MFA for Admin | Tenant cannot go production-active until every active Tenant Admin has MFA enrolled |
| Legal acceptance | Self-serve signup cannot complete without ToS/Privacy/DPA acceptance recorded |

---

## 12. Non-functionals (included)

| Area | Requirement |
|------|-------------|
| Environments | `dev` / `staging` / `production` with separate DB, storage, secrets |
| Backup / DR | Daily DB backups; RPO/RTO documented; restore drill |
| Audit retention | Configurable per tenant in Settings (default ≥ 1 year, no enforced max). **Precedence over delete requests:** a `/privacy/delete-request` purges tenant operational data, but audit-log rows referencing that tenant are retained for a fixed legal-hold period (default 90 days post-purge, tenant-configurable down to the regulatory minimum, never to zero) before they too are purged — this is disclosed in the Privacy Policy (§4.17) so "delete my data" and "we keep audit trails briefly for security/legal reasons" don't silently contradict each other. |
| API versioning | `/api/v1` is the only version for V1; a breaking change ships as `/api/v2` running alongside `v1` for a documented deprecation window (minimum 90 days) rather than mutating `v1` in place |
| Accessibility | Keyboard nav, focus, labels, contrast on primary flows |
| Mobile | Responsive shell; critical flows usable on phone |
| Rate limits | Auth endpoints protected |
| Integrations | Portal accounts V1; calendar sync Future; LinkedIn/Naukri as portal tooling; LLM provider for agents |
| Privacy | Export/delete request flow for tenant data (include AI run logs) |
| Observability | Structured logs, health check, error tracking, AI run metrics/cost |
| CI/CD | Automated build → test → lint → deploy pipeline per environment; no manual prod deploys; migrations run as a gated pipeline step |
| Performance | p95 API latency < 400ms for reads / < 800ms for writes at target load; dashboard/report queries < 2s p95; load-tested to 3x expected concurrent-user peak before GA |
| SLOs / alerting | 99.5% API uptime target (V1); on-call alert on error-rate spike, latency breach, failed backup, AI provider outage; documented escalation path |
| API conventions | Pagination, sorting/filtering, and error-contract standards per §9.0 apply to every list/mutate endpoint |
| Report exports | CSV/XLSX/PDF export available on all standard reports (§9.7) |
| Legal / compliance | ToS, Privacy Policy, DPA published and versioned; AI-scoring disclosure included; SOC 2 and multi-region residency are Future (§5) |
| Secrets management | Managed secret store per environment; no plaintext secrets in repo or unmanaged `.env` files in prod |
| Browser support | Latest 2 versions of Chrome, Edge, Safari, Firefox; graceful degradation elsewhere |

---

## 13. Production-ready definition

The product may be called **production ready** only when all of the following are true:

1. **Multi-tenant isolation** proven by automated cross-tenant denial tests and dual-tenant seed.  
2. **JWT access + refresh** live; opaque-only sessions retired.  
3. **Object storage** used for resumes/logos; no reliance on local-only disk in prod.  
4. **Sidebar and page guards** match role permissions; Tenant Admin sidebar matches §3.1 value pages only (no “show all because admin”).  
5. **Notifications** show real human copy, live metrics, and working Open-record CTAs (no prototype filler).  
6. Core modules work end-to-end: auth → admin setup → clients → requisitions → candidates → pipeline → daily updates → approvals.  
7. Security items in §10 enabled in prod config (TLS, CORS, rate limits, private buckets).  
8. Environments, backups, and audit retention from §12 in place.  
9. Tenant provisioning works both ways: **ops create** and **self-serve signup**.  
10. QA sign-off on happy paths + guardrail cases (last admin, wrong tenant slug, expired refresh).  
11. **Agentic AI (when enabled for a tenant):** V1 agents only — Resume Screener, Daily Brief, Inbox Triage — with tenant isolation, audited accept/reject, and no durable write without accept (unless Admin auto-apply policy). Core hiring can ship production-ready with AI **feature-flagged off**; turning AI on requires this item. Later agents are not required for V1 production-ready. Enabling AI additionally requires: eval-set pass (§4.16), prompt-injection input handling live, provider fallback configured, and per-tenant cost caps enforced.
12. **Account security:** password policy enforced, MFA available to all users and **required for every active Tenant Admin**, session list/revoke available to users, Admin can force-revoke a user’s sessions.
13. **API contract:** standard pagination, filtering/sorting, and error-response shape (§9.0) implemented across list/mutate endpoints; no endpoint returns raw stack traces or cross-tenant ids on error.
14. **Data lifecycle:** soft-delete/archive implemented for clients, requisitions, candidates, and applications (no silent hard deletes of business history); duplicate-candidate matching rule (§11) implemented and audited; optimistic-locking conflict handling live on requisition/candidate/pipeline writes.
15. **File safety:** upload MIME/size validation and malware scanning enforced before a resume/logo is linked to a record.
16. **Legal & compliance baseline:** ToS, Privacy Policy, and DPA published and versioned; self-serve signup blocks completion without acceptance; AI-scoring disclosure present in the Privacy Policy; `/privacy/export-request` and `/privacy/delete-request` implemented end-to-end (not just documented).
17. **Ops readiness:** CI/CD pipeline gating deploys (incl. DB migrations), load test completed at 3x expected peak, SLO/alerting configured per §12, secrets stored in a managed secret store (not repo/plaintext env files).

---

## 14. Implementation priority (engineering)

1. Document freeze (this PRD) — **done when approved**  
2. Sidebar RBAC default-deny + Admin value-nav seed (§3.1)  
3. Notifications clarity  
4. Tenants + `tenant_id` + login slug + JWT access/refresh  
5. Object storage for files + upload validation/malware scanning (§10)  
6. Full API tenant filtering + dual-tenant tests + API conventions: pagination, error contract, soft-delete (§9.0)  
7. Self-serve signup + ops provisioning APIs + legal acceptance gate (§4.17)  
8. Account security: password policy, MFA enrollment/challenge, session list/revoke (§10)  
9. Agentic AI module: orchestration + prompt-injection handling + provider fallback + V1 agents (Resume Screener, Daily Brief, Inbox Triage) + eval sets + Admin policy page (incl. cost caps)  
10. Privacy export/delete, audit-log viewer, and remaining NFRs (§12)  
11. CI/CD pipeline, load testing, SLO/alerting, secrets-manager migration (§12)  
12. Later-version AI agents (§4.16) after V1 agents are stable  

---

*End of Product Requirements Document.*
