# RecruitOps — Multi-Client Pipeline Architecture & RBAC Permission-Parity Specification

**Status:** Draft for implementation · **Author:** Principal HR Tech Systems Architect
**Scope:** Client-specific interview pipelines, stage normalization, RBAC parity, workflow governance
**Grounded against:** live `recruitment_system` schema (SQL Server), `backend/app/*`, `frontend/shared/*`, PRD `docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`

---

## 0. Current-State Audit (what exists vs. what this spec adds)

Verified against the live database and codebase before writing a line of spec:

| Area | Exists today | Gap this spec closes |
|---|---|---|
| Template hierarchy | `pipeline_templates (client_id, location_id, stage_scope)` + `pipeline_template_stages (stage_code, stage_name, stage_order, stage_type, allows_rejection)` | ✅ skeleton present · ❌ no inheritance chain, no versioning, **zero seeded templates** (table empty — apps fall back to ad-hoc stage moves) |
| Stage history | `candidate_stage_history (from_stage, to_stage, change_reason, changed_by_user_id, source_type)` — append-only by convention, written from `candidates.py:933` and `pipeline.py:286` | ❌ no immutable guard (trigger), no required `reason` for backward moves at DB level |
| Interview rounds | `interview_rounds (round_type, status, feedback_status, decision, feedback_notes)` | ❌ `feedback_notes` is free text — PRD §5 requires structured scorecards (`scorecard_json` spec'd, not implemented) |
| Metric buckets | Reports hard-code raw stage labels: `reports.py` matches `current_stage IN (N'joined', N'hired')`, dashboards match `N'submitted', N'submitted_to_client', N'client-review'` | ❌ **any client-custom stage label silently vanishes from Time-to-Fill / SLA / funnel reporting** — the single largest data-integrity risk in the platform |
| Optimistic locking | `updated_at` columns exist on all four tables | ❌ no `version` column, no zero-row conflict detection on writes |
| Terminal/reopen | `application_status` flips on stage moves; `requisition.reopen` permission exists | ❌ no reopen endpoint; terminal guard covers `joined` only — Rejected/Withdrawn paths are unguarded |
| RBAC parity | Sidebar filtered by `navigation.js` (`navPermissionSet()` default-deny from `session.permissions`); deep links gated by `NAV_PAGE_PERMISSIONS`; **page gate implemented** in `api-client.js` (`enforcePagePermission` + `syncUserPermissions`, self-bootstrapped by `startPageGate()`) | ⚠️ `require_permissions` bypasses DB resolution for admins — parity holds for identical *grants*; the gate mirrors that admin bypass via `role_code === "admin"` (see §2.2 deviation note). Only 5 code references remain (`renderers.js:968, 2267, 2268` + the gate's own fallbacks at `api-client.js:223, 354`); all 5 are **inert** because `isAdmin()`/`hasPermission()`/`userPermissions()` are not defined anywhere — see §2.2 Known gaps. *(An earlier draft of this row said "17 sites" — that figure and its cited line numbers belong to the pre-rewrite 6,250-line `api-client.js`, now 553 lines.)* |

**Design stance:** every proposal below either (a) fills a verified gap, (b) generalizes an existing mechanism, or (c) is explicitly marked as a parity-risk remediation.

---

## 1. Multi-Client Candidate Interview Pipeline Architecture

### 1.1 Master Baseline vs. Client Overlays (inheritance chain)

The PRD baseline is `Sourced → Screened → Interview → Offer → Joined` + terminal `Rejected`, `Withdrawn`. Client variety is handled by **overlay inheritance, never by forking the baseline**.

**Resolution chain (most specific wins, first match applies):**

```
Platform Baseline (read-only seed, is_system = 1)
  └── Tenant Master Template       (tenant-wide default; client_id NULL, location_id NULL, stage_scope = 'tenant-master')
        └── Client Overlay          (client_id set; location_id NULL)
              └── Location Overlay  (location_id set; client_id NULL)   -- optional geo/branch variation
                    └── Requisition Pin  (requisitions.pipeline_template_id set explicitly)
```

**Rules:**

1. **Baseline immutability.** The five baseline stages plus two terminal stages are platform seed rows (`stage_scope = 'baseline'`, `is_system = 1`). Tenants may *rename the display label* of baseline stages but cannot delete them, reorder past terminal position, or change their `metric_bucket`.
2. **Overlay = delta, not copy.** A client overlay stores only *additions* (sub-stages like "VP Sync") and *label remaps* ("Screened" → "Client Screen Complete"). The runtime pipeline is **materialized on requisition pin** into `requisition_pipeline_stages` (§1.4), so the board renders a concrete ordered list — no join-time inheritance gymnastics, no UI clutter.
3. **Single active template per requisition.** `requisitions.pipeline_template_id` is pinned at requisition creation (default: client overlay if one exists, else tenant master). `candidate_applications.pipeline_template_id` snapshots it at application creation — mid-flight template edits never rewrite live applications (PRD immutability rule).
4. **Overlay edit = new template version.** `pipeline_templates.version` increments on every edit. Applications keep their pinned template; a `superseded_by_template_id` pointer lets the UI offer "adopt new client flow" as an explicit, audited action.
5. **Stage-move validation reads the application's materialized stage set** (mechanism already exists in `move_pipeline_stage_service` via `find_pipeline_template_stage_for_application`) — extended to read materialized rows rather than live template rows.

### 1.2 Custom Interview Types & Structured Scorecards

| Concept | Storage | Rules |
|---|---|---|
| Interview types | `interview_round_types` tenant picklist: `phone`, `video`, `onsite`, `panel` (PRD §5 baseline) + tenant additions | `is_active` flag; deactivation never deletes history |
| Stage → allowed types | `pipeline_stage_interview_types (template_stage_id, round_type, is_default, max_rounds, requires_scorecard)` | Restricts which interview types may be scheduled *at that stage*; the scheduler UI select is built from this, not hard-coded |
| Scorecard template | `scorecard_templates (tenant_branch_id, stage_type, name, criteria_json, version, is_active)` | `criteria_json`: ordered array of `{ criterion_id, label, weight, rating_min, rating_max, required }`. Seeded defaults per stage type (Screening: communication, role fit; Panel: 5 criteria + recommendation) |
| Scorecard response | `interview_rounds.scorecard_json` (PRD §9 naming) + `scorecard_template_id`, `scorecard_version`, `overall_rating`, `recommendation` | Response JSON validated server-side against the template: all `required` criteria present, ratings in bounds. **A round cannot become `completed` without a valid scorecard** when the stage requires one |

**Transitions:** `interview_rounds.status`: `scheduled → completed | no-show | rescheduled | cancelled`; `feedback_status: pending → submitted`. A `completed` round with `feedback_status = 'pending'` **blocks the stage move** out of that stage when `requires_scorecard = 1` (see §3.1).

### 1.3 Stage Normalization Layer (the reporting-correctness keystone)

**Principle:** analytics never read raw stage labels; they read `metric_bucket`, set once at template-edit time and snapshotted per application thereafter.

**Fixed metric buckets** (platform enum, not tenant-editable):

| `metric_bucket` | Baseline stages mapped | Examples of client labels absorbed | Reporting consumer |
|---|---|---|---|
| `sourced` | Sourced | "Talent Pool", "Identified" | Funnel entry counts |
| `screened` | Screened | "Client Screen Complete", "Recruiter Screen" | Screening SLA |
| `interview` | Interview | "VP Sync", "Technical Assessment", "Panel Loop", "Case Study" | Interview velocity, per-type analytics |
| `offer` | Offer | "Offer Approval", "Comp Review" | Offer-stage SLA |
| `joined` | Joined / Hired | "Onboarding", "Start Date Confirmed" | Time-to-Fill closure |
| `rejected` | Rejected | "Client Decline", "No Fit" | Funnel loss |
| `withdrawn` | Withdrawn | "Candidate Pulled Out" | Funnel loss |

**Mechanics:**

- `pipeline_template_stages.metric_bucket` — NOT NULL, CHECK-constrained enum; tenant overlays choose from the enum only.
- `requisition_pipeline_stages.metric_bucket` — materialized copy at pin time.
- `candidate_stage_history.from_bucket, to_bucket` — written at move time from the materialized row, so **reports join history only** and never re-resolve labels; historic buckets survive template edits forever.
- **Reporting remediation:** every `current_stage IN (N'joined', N'hired')`-style predicate in `reports.py` / `dashboards.py` is replaced by `current_bucket = 'joined'` (or reads `vw_application_metric_state`). Until migrated, custom client stages are invisible to those reports — top-priority fix.
- A **Stage Bucket Map** admin page (tenant → bucket → stages) lets admins audit mis-bucketed client stages from the control plane.

### 1.4 Database Schema Adjustments

Full migration in §4.3. Summary:

```sql
pipeline_templates       + version INT NOT NULL DEFAULT 1
                         + is_system BIT NOT NULL DEFAULT 0
                         + superseded_by_template_id BIGINT NULL (self-FK)
pipeline_template_stages + metric_bucket NVARCHAR(20) NOT NULL  (CHECK enum)
                         + is_terminal BIT NOT NULL DEFAULT 0
                         + requires_scorecard BIT NOT NULL DEFAULT 0
NEW requisition_pipeline_stages     -- materialized, ordered, per-requisition concrete stages
NEW scorecard_templates             -- tenant scorecard definitions (criteria_json, version)
NEW pipeline_stage_interview_types  -- stage ↔ interview-type matrix
candidate_applications   + version INT NOT NULL DEFAULT 1   -- optimistic lock
requisitions             + version INT NOT NULL DEFAULT 1
candidate_stage_history  + from_bucket, to_bucket NVARCHAR(20) NULL
                         + reopened_from_history_id BIGINT NULL (self-FK)
interview_rounds         + scorecard_template_id, scorecard_version, scorecard_json,
                           overall_rating, recommendation
+ append-only trigger on candidate_stage_history (UPDATE/DELETE → ROLLBACK + RAISERROR)
```

**Optimistic-locking convention (all four tables):** every mutation is
`UPDATE ... SET version += 1, updated_at = SYSUTCDATETIME() WHERE id = :id AND version = :client_version;`
— zero rows updated ⇒ concurrent writer won ⇒ service raises `409 Conflict` carrying the fresh row. SQLAlchemy pattern in §4.3.

---

## 2. End-to-End RBAC & Permission Parity Validation

### 2.1 Persona Testing Matrix

Fixture: two branches (HYD01, MUM01), two clients, two requisitions; personas created through the API exactly like `test_tenant_isolation_db.py` does. Expected results for B and C are identical in every row.

| # | Step | A · Tenant Admin | B · Recruiter 1 | C · Recruiter 2 (identical codes) | Parity assert |
|---|---|---|---|---|---|
| 1 | Login → `/permissions/me` | role `admin`; control-plane codes only | `candidate.read`, `pipeline.board.read`, `daily_update.write` | identical set | `set(B.codes) == set(C.codes)` |
| 2 | Sidebar render | Work/Home, Daily Ops, Admin & Control Plane, Reports — **no** execution links | Sourcing/Pipeline + Daily Ops only; no Admin links | byte-identical link set to B | `B.links === C.links` |
| 3 | Deep link `pipeline-board.html` | **Blocked** unless execution grants exist (PRD §3.1: admin default = oversight only) | 200, board renders | 200 | same status, same visible columns |
| 4 | Board dataset | — | own-location rows only | identical row-ID set | `B.ids == C.ids` |
| 5 | Stage-move button | hidden (no `pipeline.stage.move`) | visible | visible | `B.visible == C.visible` |
| 6 | Stage-move API, other-location application | 403 | 403 | 403 | equal status **and** detail |
| 7 | Stage-move API, own location, forward | 403 | 200 | 200 | equal; history rows identical shape |
| 8 | Backward move without reason | 403 | 422 `reason required` | 422 | identical detail string |
| 9 | Move to Offer with branch toggle off | 409 handoff | 409 | 409 | identical |
| 10 | Candidate profiles page | Blocked | 200, location-scoped list | 200 | `B.rows == C.rows` |
| 11 | Daily update submit | 403 (no `daily_update.write`) | 201 | 201 | equal payload shape |
| 12 | UI⇄codes coherence | zero actions visible without a backing code | ✓ | ✓ | automated sweep |
| 13 | Concurrent edit (optimistic lock) | — | stale-version write → 409 + fresh row | same | identical 409 body |

> **Naming drift flag:** the PRD persona grants `pipeline.board.read`, but the live seed ships `pipeline.read.summary`. The parity harness tests what `/permissions/me` actually returns and treats the drift as a remediation item (rename the code or add it to `PERMISSION_ALIASES`).

**Harness:** `backend/tests/test_rbac_parity_db.py` — builds personas B and C via the API (role → permissions → user → setup-link → login chain), then asserts identical `/permissions/me` payload *sets*, identical board/candidate row-ID sets, and for every sidebar-visible page identical `require_permissions` outcomes. Skips when the DB is unreachable (established convention).

### 2.2 UI/Frontend Guard Rules (capability checks only)

**Current parity risk:** 17 `isAdmin()` call-sites (e.g. `api-client.js:360, 367, 482, 1351, 2955`). `isAdmin()` is a role-name check. PRD §3.2: *"There is no 'if admin, show every link' bypass."* The pattern `isAdmin() || hasPermission(x)` breaks parity in the opposite direction: an admin *without* the grant sees more than their codes justify, diverging from a recruiter *with* the grant.

> **Rule RB-1:** UI conditionals assert *capability*, not identity. Replace `isAdmin() || hasPermission(code)` with `hasPermission(code)`; admin convenience must come from **seeded grants on the admin role**, never from a runtime role-name branch. (One documented exception: `get_candidate_footprint_service` — an oversight surface whose value is crossing tenant lines; role-gated server-side and audited.)

**Sidebar renderer (filtering strictly from `/permissions/me`)** — code in §4.1. Rules:

- One source of truth: `session.permissions` refreshed from `/permissions/me` on login, on tab focus, and on a 5-minute interval (kills the stale-permission bug class); re-render sidebar/home after refresh so parity survives a permissions change mid-session.
- `NAV_PAGE_PERMISSIONS` drives sidebar links *and* deep-link gating from the same map (already true in `navigation.config.js`) — a page reachable by deep link must be reachable by link, and vice versa.
- Buttons: rendered only when the exact action code resolves; hidden (not disabled) when default-deny applies — a disabled button still leaks the feature's existence.

**Page routing — implementation as shipped** (`frontend/shared/api-client.js`, 553 lines):

> The previously cited `bootPage()` helper does not exist in the codebase. The gate that
> ships today is the three-function chain below; this is the authoritative description.

1. **`syncUserPermissions()`** — fires `GET /api/v1/auth/me` and
   `GET /api/v1/permissions/me` **in parallel** with `Authorization: Bearer <token>`
   (prefix from `config.api_prefix`; auth is bearer-only — `get_current_auth_context`
   rejects cookie auth). The merged session persists `{…auth/me, …permissions/me}` so
   `role_code`, `permissions`, `scopes` and `allowed_pages` come from the RB-1 source of
   truth. A `401`/`403` clears session **and** token (revoked/deactivated user).
2. **`enforcePagePermission(pageId)`** — evaluated **only after both calls resolve**. In
   order, first match wins:

   - *no synced session* → **allow** (nothing to gate; the backend still enforces every API)
   - *`role_code === "admin"`* → **allow** (mirrors `require_permissions`' admin bypass)
   - *page id ∈ `ADMIN_CONTROL_PLANE`* → **deny**
   - *`NAV_PAGE_PERMISSIONS[page]` satisfied by alias-resolved codes* → **allow**
   - *otherwise* → **deny**

   Denial → `access-denied.html?denied=1&page=<routeId>&redirect=<current URL>`.
3. **`startPageGate()`** — self-bootstraps on `DOMContentLoaded` from `api-client.js`,
   which *every* page loads (one wiring point, no per-page edits). It hides
   `#main-content` while syncing and re-reveals either way, guarded by a 4 s safety
   timeout so a hung sync can never blank a page. `bootRBACGate()` memoizes so
   `login.html`'s inline hook and the shared bootstrap cannot double-sync.

**Gate hooks:** `registerPermissionGate(fn)` / `runPermissionGates()` run registered
callbacks before the deep-link enforcement; everything is exported on
`window.RecruitOpsLive` (16 APIs, incl. `readSession`, `readAuthToken`, `clearSession`).

**Sidebar:** `navShapeEntriesForSidebar()` shapes the admin sidebar to
`ADMIN_SIDEBAR_BASE` (+ `my-work-dashboard` when an execution grant exists) per PRD §3.1;
non-admins pass through `navEntriesFor()`'s default-deny untouched.

**Documented deviations (deliberate, flagged for review):**

- **Role-name bypass retained.** The gate allows `role_code === "admin"` before consulting
  codes, which Rule RB-1 forbids for UI conditionals. Kept because it is byte-parity with
  the backend's own bypass (`deps.py:131`), and dropping it would deny seeded admins.
  *If strict RB-1 compliance is preferred, this is one branch in `enforcePagePermission` —
  but the backend bypass must be removed in the same change or parity breaks the other way.*
- **Fail-closed hard deny.** All `ADMIN_CONTROL_PLANE` ids are denied to non-admins even
  when the backend would allow them via grant (e.g. a non-admin granted `user.read` can
  `GET /users`, asserted by `test_rbac_chain_integration.py`). The frontend is therefore
  **stricter** than the API — acceptable (fail-closed, backend stays authoritative) but not
  identical. Exact parity = reorder the table above so the code check precedes the set check.
- **Refresh cadence not implemented.** §4.1's `refreshPermissions()` (tab-focus + 5-minute
  interval + re-render) is **spec-only**; the shipped gate syncs once per page load.
  Stale-permission windows within a session therefore remain open.

**Known gaps:** `isAdmin()`, `hasPermission()` and `userPermissions()` are referenced but
**never defined**, so their call-sites are permanently inert:

- `renderers.js:968` — `typeof hasPermission === "function" && (isAdmin() || hasPermission("ai.agent.inbox_triage"))`
  short-circuits to `false`: the AI-triage toggle can never enable. Note the pattern itself
  is an RB-1 violation (`isAdmin() || hasPermission(x)`) and must become capability-only.
- `renderers.js:2267-2268` — `renderAgentsWorkbench()` receives `adminUser = false` and
  `perms = []`, so no `ai.agent.*` run buttons ever render.
- `navigation.js:288` — `loadHomeMetrics()` finds no `apiRequest` and returns early, leaving
  home metrics at `—`. No `apiRequest`/HTTP helper is defined anywhere in `frontend/shared/`;
  only `/auth/me` + `/permissions/me` are fetched (by the gate itself).
- `approvals-inbox.html` tab counts are **static markup** (`>0<`) with no loader.

### 2.3 Backend API Authorization

Layered enforcement, each layer independently testable:

1. **Authentication** — `get_current_auth_context` resolves the bearer session token to `AuthContext` (user, role_code, location_id). 401 on missing/expired/revoked.
2. **Permission verification** — `require_permissions(*codes)` / `require_any_permission` resolve codes from DB grants (`role_permissions` + user/branch extras, cached) with `PERMISSION_ALIASES` fallback. The admin bypass inside these deps is acceptable *only* because admin convenience is seeded; the parity harness (matrix step 12) asserts the bypass never substitutes for a missing UI code.
3. **Location scoping** — `require_location_scope` for location-scoped resources; repository queries bind `:location_id` from `auth_context.user.location_id`, **never from client input**. New rule: list endpoints must clamp any query-string `location_id` to the actor's scope — reject, don't silently honor.
4. **Tenant isolation** — there is no physical `tenant_id` column; tenants are realized as `branches` + `client_companies.branch_id` (per the PRD hierarchy Tenant → Locations → Clients → Requisitions). Cross-tenant isolation = requisition branch membership, enforced by service-layer row checks (`_can_access_pipeline_application`, `_can_access_candidate`) and locked by `test_tenant_isolation_db.py`. A physical `tenants` table is deferred until true row-sharing across agencies is required — the hierarchy is representable without a risky column migration today.
5. **Row-level re-check** — services re-verify the specific row's branch against the actor (`assert_row_in_tenant`, §4.2), because list scoping alone never protects direct-ID routes.

---

## 3. Workflow Automation & Governance Controls

### 3.1 Stage Transition Triggers

| Trigger | When | Rule | Enforcement point |
|---|---|---|---|
| Offer threshold approval | move → any stage with `metric_bucket = 'offer'` | If `payload.offered_ctc > requisition.offer_ctc_max` (when set) → auto-create `approval_requests` row (`offer-approval`, priority high) and route through approval instead of an immediate move | `move_pipeline_stage_service` pre-write hook |
| Scorecard completion | leaving any stage with `requires_scorecard = 1` | All interview rounds at that stage must be `completed` with a template-valid `scorecard_json`; else **422** `Scorecard required before leaving <stage>` | service hook + UI disables the Move button |
| Location reassignment | candidate owner relocates | Application stays with the **requisition's** branch (tenant-of-record); reassigning the *candidate* never moves their applications; audit entry written; `candidate_location_transfer_requests` flow already models this | transfer service |
| Template supersession | admin edits a client overlay | `version += 1`; pinned applications untouched; UI surfaces "New client flow available" with an explicit adopt action (audited) | template service |
| Duplicate risk | move → offer with `client_duplicate_flag = 1` | Soft-block requiring explicit confirmation before proceeding | service hook |

### 3.2 Terminal & Reopen Logic

**Entering terminal states** (Rejected / Withdrawn / Joined):

- Rejected: requires `rejection_reason` (+ client/internal side) — existing behavior, keep.
- Withdrawn: requires a reason; sets `application_status = 'withdrawn'` (add to the terminal set in `move_pipeline_stage_service` — currently only `joined` is guarded there).
- Joined: requires `joining_date` (existing validation); locks the application.
- All three: append history with `to_bucket`; `application_status` flips; `version += 1`.

**Reopen (Manager-permissioned):**

- New permission **`pipeline.stage.reopen`** — seeded to Manager; *not* to Recruiter; *not* implicitly to Admin unless seeded (Rule RB-1).
- `POST /api/v1/pipeline/applications/{id}/reopen`, body `{ to_stage, reason }` (reason required, ≥ 16 chars, matching the platform's rationale conventions).
- **No history mutation, ever.** The terminal history row remains untouched; a *new* row is appended with `from_stage = <terminal>`, `to_stage = <target>`, `source_type = 'reopen'`, and `reopened_from_history_id` pointing at the terminal row it reverses (audit traversal without mutating the past).
- Guardrails: reopening a `joined` application with `offer_status = 'accepted'` additionally requires `pipeline.stage.reopen.joined`; denied while an approval request is pending; optimistic-lock version check applies; the target stage must exist in the application's materialized stage set.

---

## 4. Implementation & Code Remediation Deliverables

### 4.1 Frontend — dynamic sidebar renderer filtered strictly by `/permissions/me`

> **Implementation status.** Partially shipped. The sidebar's default-deny filtering and
> admin shaping are live (`navigation.js`: `navPermissionSet()`, `navEntriesFor()`,
> `navShapeEntriesForSidebar()`), and the page gate described in §2.2 is live
> (`api-client.js`). **Not shipped:** the `refreshPermissions()` focus/interval refresh and
> `hasPermission()`/`stageMoveButtonHtml()` below — they are reference code. They also
> depend on an `apiRequest()` helper that **is not defined anywhere** in
> `frontend/shared/`, so adopting them as-is requires introducing that helper first
> (or calling `syncUserPermissions()` directly, which already speaks Bearer auth).

```javascript
/* navigation.js — permission-parity sidebar. Source of truth:
   session.permissions (from /permissions/me), refreshed on focus/interval.
   Capability checks only — no role-name branches (Rule RB-1). */

let permissionRefreshTimer = null;

async function refreshPermissions() {
  try {
    const me = await apiRequest("/permissions/me");
    const session = RecruitOpsLive.session || readSession();
    const codes = Array.isArray(me.permissions) ? me.permissions : [];
    /* Parity means identical SETS, not identical arrays — normalize order. */
    session.permissions = [...new Set(codes)].sort();
    if (me.role_code) session.role_code = me.role_code;
    writeSession(session);
    RecruitOpsLive.session = session;
    /* Re-render code-dependent surfaces so parity survives a mid-session
       permission change (e.g. admin grants a code while B is logged in). */
    buildSidebarNav();
    buildMobileNav();
    if (document.querySelector("[data-home-grid]")) buildHomeGrid();
  } catch { /* offline: keep last-known codes; never widen access on error */ }
}

function startPermissionRefresh() {
  if (permissionRefreshTimer) return;
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshPermissions();
  });
  permissionRefreshTimer = setInterval(refreshPermissions, 5 * 60 * 1000);
}

function hasPermission(code) {
  const session = (typeof readSession === "function" && readSession()) || {};
  return (session.permissions || []).includes(code);
}

/* Sidebar: default-deny. A link renders iff the user holds >= 1 permission
   the page requires; the SAME map (NAV_PAGE_PERMISSIONS) gates deep links,
   so link-visibility and deep-link access can never diverge. */
function navSidebarHtml({ activeFile = "", compact = false } = {}) {
  const config = window.NAV_CONFIG;
  const entries = config.entries.filter((entry) => {
    if (entry.showInSidebar === false) return false;
    const required = entry.permissions || [];
    if (!required.length) return true;               // account chrome only
    return required.some((code) => hasPermission(code));
  });
  const groups = config.categories
    .map((category) => ({ category, items: entries.filter((e) => e.category === category.key) }))
    .filter((g) => g.items.length > 0);

  const link = (entry) => {
    const active = entry.file === activeFile;
    return `<a href="${entry.file}" class="nav-link${active ? " is-active" : ""}"
              ${active ? 'aria-current="page"' : ""}>
      <span class="material-symbols-outlined shrink-0">${entry.icon}</span>
      <span class="sidebar-label">${entry.label}</span></a>`;
  };

  return groups.map(({ category, items }) => `
    <details class="nav-group"${compact ? "" : " open"} data-nav-group="${category.key}">
      <summary class="nav-group-toggle">
        <span class="material-symbols-outlined nav-group-icon">${category.icon}</span>
        <span class="nav-group-label">${category.label}</span>
        <span class="material-symbols-outlined nav-group-chevron">expand_more</span>
      </summary>
      <div class="nav-sub">${items.map(link).join("\n")}</div>
    </details>`).join("\n")
    + `<a href="login.html?loggedOut=true" class="sidebar-logout" data-logout-link="true">
         <span class="material-symbols-outlined">logout</span><span class="sidebar-label">Logout</span></a>`;
}

/* Action buttons: capability checks, never `if (isAdmin())`. */
function stageMoveButtonHtml(application, currentStage) {
  if (!hasPermission("pipeline.stage.move")) return "";   // hidden = default-deny
  if (["rejected", "withdrawn", "joined"].includes(currentStage)) {
    return hasPermission("pipeline.stage.reopen")
      ? `<button data-live-reopen-application="${application.id}">Reopen</button>`
      : "";
  }
  return `<button data-route="stage-move-dialog.html?application_id=${application.id}">Move stage</button>`;
}
```

### 4.2 Backend — FastAPI dependency: permission + tenant boundary

```python
# app/api/deps.py — composed authorization dependency chain.

def require_tenant_scoped(*permission_codes: str):
    """Permission check + location-scope presence. Use for any route that
    touches specific business rows; combine with assert_row_in_tenant()."""
    def dependency(
        auth_context: AuthContext = Depends(get_current_auth_context),
        engine: Engine = Depends(get_engine),
    ) -> AuthContext:
        # 1) Permissions — resolved from DB grants (cached), never from the
        #    JWT body alone; the token only authenticates, it never authorizes.
        if auth_context.user.role_code != "admin":
            resolved = _get_cached_permissions(engine, auth_context.user.id)
            missing = [c for c in permission_codes if not _has_permission(resolved, c)]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {missing[0]}",
                )
        # 2) Location scope must exist for row-level work.
        if auth_context.user.location_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Location scope is not available for this user",
            )
        return auth_context
    return dependency


def assert_row_in_tenant(auth_context: AuthContext, row_branch_id: int | None) -> None:
    """Row-level tenant boundary. Tenants are realized as branches in this
    schema; the admin passes ONLY because cross-tenant oversight is seeded
    on the admin role (explicit, audited) — never as a silent bypass."""
    if auth_context.user.role_code == "admin":
        return
    if row_branch_id is None or row_branch_id != auth_context.user.location_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resource belongs to a different tenant",
        )


class StaleWriteConflict(Exception):
    """Raised when an optimistic-lock UPDATE matches zero rows; the service
    layer maps this to HTTP 409 with the current stored row."""


def execute_versioned_update(connection, sql: str, params: dict) -> int:
    result = connection.execute(text(sql), params)
    if result.rowcount == 0:
        raise StaleWriteConflict()
    return result.rowcount


# Route usage:
@router.patch("/applications/{application_id}/stage", response_model=PipelineStageMoveResponse)
def move_stage_endpoint(
    application_id: int = Path(..., ge=1),
    payload: PipelineStageMove = ...,
    auth_context: AuthContext = Depends(require_tenant_scoped("pipeline.stage.move")),
    engine: Engine = Depends(get_engine),
) -> PipelineStageMoveResponse:
    application = find_pipeline_application_by_id(engine, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Pipeline application was not found")
    assert_row_in_tenant(auth_context, application.location_id)   # tenant boundary
    return move_pipeline_stage_service(engine, application_id, payload, auth_context)
```

### 4.3 Database migration — normalization + history + optimistic locking

```sql
/* =====================================================================
   010_pipeline_normalization.sql
   Metric buckets, overlay versioning, materialized requisition stages,
   scorecards, append-only history guard, optimistic locking.
   Idempotent — every step COL_LENGTH/OBJECT_ID guarded.
   ===================================================================== */

/* 1. Metric buckets + stage semantics on template stages */
IF COL_LENGTH(N'dbo.pipeline_template_stages', N'metric_bucket') IS NULL
  ALTER TABLE dbo.pipeline_template_stages ADD metric_bucket NVARCHAR(20) NOT NULL
    CONSTRAINT DF_pts_metric_bucket DEFAULT (N'interview');
IF COL_LENGTH(N'dbo.pipeline_template_stages', N'is_terminal') IS NULL
  ALTER TABLE dbo.pipeline_template_stages ADD is_terminal BIT NOT NULL DEFAULT 0;
IF COL_LENGTH(N'dbo.pipeline_template_stages', N'requires_scorecard') IS NULL
  ALTER TABLE dbo.pipeline_template_stages ADD requires_scorecard BIT NOT NULL DEFAULT 0;
GO

ALTER TABLE dbo.pipeline_template_stages DROP CONSTRAINT IF EXISTS CK_pts_metric_bucket;
ALTER TABLE dbo.pipeline_template_stages ADD CONSTRAINT CK_pts_metric_bucket
  CHECK (metric_bucket IN (N'sourced', N'screened', N'interview', N'offer',
                           N'joined', N'rejected', N'withdrawn'));
GO

/* 2. Baseline bucket backfill (deterministic from existing columns) */
UPDATE dbo.pipeline_template_stages SET metric_bucket = CASE
    WHEN stage_code LIKE N'%reject%'   THEN N'rejected'
    WHEN stage_code LIKE N'%withdraw%' THEN N'withdrawn'
    WHEN stage_type = N'joining' OR stage_code IN (N'joined', N'hired') THEN N'joined'
    WHEN stage_type = N'offer'   OR stage_code LIKE N'%offer%'  THEN N'offer'
    WHEN stage_code LIKE N'%screen%'   THEN N'screened'
    WHEN stage_code LIKE N'%sourc%'    THEN N'sourced'
    ELSE N'interview' END;
GO

/* 3. Template versioning (overlay edits are explicit, audited events) */
IF COL_LENGTH(N'dbo.pipeline_templates', N'version') IS NULL
  ALTER TABLE dbo.pipeline_templates ADD version INT NOT NULL DEFAULT 1;
IF COL_LENGTH(N'dbo.pipeline_templates', N'is_system') IS NULL
  ALTER TABLE dbo.pipeline_templates ADD is_system BIT NOT NULL DEFAULT 0;
IF COL_LENGTH(N'dbo.pipeline_templates', N'superseded_by_template_id') IS NULL
  ALTER TABLE dbo.pipeline_templates ADD superseded_by_template_id BIGINT NULL
    REFERENCES dbo.pipeline_templates (id);
GO

/* 4. Materialized per-requisition stages — the board/report contract */
IF OBJECT_ID(N'dbo.requisition_pipeline_stages', N'U') IS NULL
CREATE TABLE dbo.requisition_pipeline_stages (
  id BIGINT IDENTITY PRIMARY KEY,
  requisition_id BIGINT NOT NULL REFERENCES dbo.requisitions (id),
  template_stage_id BIGINT NOT NULL REFERENCES dbo.pipeline_template_stages (id),
  stage_code NVARCHAR(100) NOT NULL,
  stage_name NVARCHAR(200) NOT NULL,
  stage_order INT NOT NULL,
  stage_type NVARCHAR(60) NOT NULL,
  metric_bucket NVARCHAR(20) NOT NULL,
  is_terminal BIT NOT NULL DEFAULT 0,
  requires_scorecard BIT NOT NULL DEFAULT 0,
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME2 NOT NULL CONSTRAINT DF_rps_created DEFAULT SYSUTCDATETIME(),
  CONSTRAINT UQ_rps_requisition_stage UNIQUE (requisition_id, stage_code)
);
GO

/* 5. Structured scorecards */
IF OBJECT_ID(N'dbo.scorecard_templates', N'U') IS NULL
CREATE TABLE dbo.scorecard_templates (
  id BIGINT IDENTITY PRIMARY KEY,
  tenant_branch_id BIGINT NULL REFERENCES dbo.branches (id),
  stage_type NVARCHAR(60) NOT NULL,
  name NVARCHAR(200) NOT NULL,
  criteria_json NVARCHAR(MAX) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  is_active BIT NOT NULL DEFAULT 1,
  created_at DATETIME2 NOT NULL CONSTRAINT DF_sct_created DEFAULT SYSUTCDATETIME(),
  updated_at DATETIME2 NOT NULL CONSTRAINT DF_sct_updated DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID(N'dbo.pipeline_stage_interview_types', N'U') IS NULL
CREATE TABLE dbo.pipeline_stage_interview_types (
  id BIGINT IDENTITY PRIMARY KEY,
  template_stage_id BIGINT NOT NULL REFERENCES dbo.pipeline_template_stages (id),
  round_type NVARCHAR(60) NOT NULL,
  is_default BIT NOT NULL DEFAULT 0,
  max_rounds INT NULL,
  requires_scorecard BIT NOT NULL DEFAULT 1,
  CONSTRAINT UQ_psit UNIQUE (template_stage_id, round_type)
);
GO

IF COL_LENGTH(N'dbo.interview_rounds', N'scorecard_template_id') IS NULL
  ALTER TABLE dbo.interview_rounds ADD scorecard_template_id BIGINT NULL
    REFERENCES dbo.scorecard_templates (id);
IF COL_LENGTH(N'dbo.interview_rounds', N'scorecard_version') IS NULL
  ALTER TABLE dbo.interview_rounds ADD scorecard_version INT NULL;
IF COL_LENGTH(N'dbo.interview_rounds', N'scorecard_json') IS NULL
  ALTER TABLE dbo.interview_rounds ADD scorecard_json NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'dbo.interview_rounds', N'overall_rating') IS NULL
  ALTER TABLE dbo.interview_rounds ADD overall_rating DECIMAL(4,2) NULL;
IF COL_LENGTH(N'dbo.interview_rounds', N'recommendation') IS NULL
  ALTER TABLE dbo.interview_rounds ADD recommendation NVARCHAR(40) NULL;
GO

/* 6. History: metric buckets + reopen linkage (append-only in §8) */
IF COL_LENGTH(N'dbo.candidate_stage_history', N'from_bucket') IS NULL
  ALTER TABLE dbo.candidate_stage_history ADD from_bucket NVARCHAR(20) NULL;
IF COL_LENGTH(N'dbo.candidate_stage_history', N'to_bucket') IS NULL
  ALTER TABLE dbo.candidate_stage_history ADD to_bucket NVARCHAR(20) NULL;
IF COL_LENGTH(N'dbo.candidate_stage_history', N'reopened_from_history_id') IS NULL
  ALTER TABLE dbo.candidate_stage_history ADD reopened_from_history_id BIGINT NULL
    REFERENCES dbo.candidate_stage_history (id);
GO

/* 7. Optimistic locking */
IF COL_LENGTH(N'dbo.candidate_applications', N'version') IS NULL
  ALTER TABLE dbo.candidate_applications ADD version INT NOT NULL DEFAULT 1;
IF COL_LENGTH(N'dbo.requisitions', N'version') IS NULL
  ALTER TABLE dbo.requisitions ADD version INT NOT NULL DEFAULT 1;
GO

/* 8. Append-only guard: history is immutable (PRD §5). A governed
   maintenance path (session program_name) is the only exemption. */
IF OBJECT_ID(N'dbo.trg_stage_history_append_only', N'TR') IS NOT NULL
  DROP TRIGGER dbo.trg_stage_history_append_only;
GO
CREATE TRIGGER dbo.trg_stage_history_append_only
ON dbo.candidate_stage_history
AFTER UPDATE, DELETE
AS
BEGIN
  SET NOCOUNT ON;
  IF EXISTS (SELECT 1 FROM sys.dm_exec_sessions
             WHERE session_id = @@SPID AND program_name LIKE N'recruitops-audit%')
    RETURN;  -- governed maintenance path only
  ROLLBACK TRANSACTION;
  RAISERROR (N'candidate_stage_history is append-only; edits are forbidden (PRD section 5).', 16, 1);
END;
GO

/* 9. Reporting safety net while report code migrates to buckets: a view that
   resolves the metric bucket for an application's CURRENT stage. Reports
   switch from current_stage IN (...) predicates to current_bucket = '...'. */
IF OBJECT_ID(N'dbo.vw_application_metric_state', N'V') IS NOT NULL
  DROP VIEW dbo.vw_application_metric_state;
GO
CREATE VIEW dbo.vw_application_metric_state AS
SELECT
  ca.id AS application_id,
  ca.requisition_id,
  r.branch_id,
  r.client_company_id,
  COALESCE(rps.metric_bucket,
    CASE
      WHEN ca.current_stage IN (N'joined', N'hired')        THEN N'joined'
      WHEN ca.current_stage LIKE N'%offer%'                 THEN N'offer'
      WHEN ca.current_stage LIKE N'%reject%'                THEN N'rejected'
      WHEN ca.current_stage LIKE N'%withdraw%'              THEN N'withdrawn'
      WHEN ca.current_stage LIKE N'%screen%'                THEN N'screened'
      WHEN ca.current_stage LIKE N'%sourc%'                 THEN N'sourced'
      ELSE N'interview'
    END) AS current_bucket,
  ca.current_stage,
  ca.application_status,
  ca.stage_updated_at
FROM dbo.candidate_applications ca
JOIN dbo.requisitions r ON r.id = ca.requisition_id
LEFT JOIN dbo.requisition_pipeline_stages rps
  ON rps.requisition_id = ca.requisition_id AND rps.stage_code = ca.current_stage;
GO
```

**SQLAlchemy optimistic-lock pattern (repository layer):**

```python
def update_application_stage(
    engine: Engine, application_id: int, *, client_version: int, **fields: object
) -> int:
    set_clause = ", ".join(f"{name} = :{name}" for name in fields)
    stmt = text(f"""
        UPDATE dbo.candidate_applications
        SET {set_clause},
            version += 1,
            updated_at = SYSUTCDATETIME()
        OUTPUT INSERTED.version AS new_version
        WHERE id = :application_id AND version = :client_version;
    """)
    with engine.begin() as connection:
        row = connection.execute(
            stmt,
            {**fields, "application_id": application_id, "client_version": client_version},
        ).mappings().first()
    if row is None:  # zero rows updated -> a concurrent writer won
        current = read_application_version(engine, application_id)
        raise StaleWriteConflict(current_version=current)  # service -> HTTP 409
    return int(row["new_version"])
```

---

## 5. Delivery Sequencing (risk-ordered)

1. **P0 — metric buckets + history buckets + `vw_application_metric_state`** (reporting correctness; zero behavior change for default tenants).
2. **P0 — append-only trigger** on stage history (data-integrity guarantee precedes feature work).
3. **P1 — optimistic locking** columns + versioned UPDATE conversion + SPA 409 handling.
4. **P1 — parity remediation:** define (or delete) the missing `isAdmin()` / `hasPermission()` / `userPermissions()` helpers — today only 5 code references remain (`renderers.js:968, 2267, 2268` + `api-client.js:223, 354`) and all are inert — then convert the `isAdmin() || hasPermission(x)` pattern at `renderers.js:968` to capability-only; `pipeline.read.summary` naming alignment (PRD §3.2 must be amended — see `readiness-qa-and-decisions.md` Q10); ship the parity harness test. *(The frontend page gate itself — §2.2 — is shipped.)*
5. **P2 — overlay inheritance + materialization, structured scorecards, reopen endpoint + `pipeline.stage.reopen`.**
