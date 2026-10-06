# RecruitOps — Readiness Q&A & Decision Log

**Date:** 2026-10-04
**Purpose:** Verify the production-readiness assessment's factual claims against the live code and DB, answer the open scoping/architecture questions, and separate **evidence-based answers** from **decisions still owed by the team**.
**Companion docs:** `production-readiness-assessment.md` (Go/No-Go), `pipeline-rbac-architecture-spec.md` (RBAC/pipeline spec), `PRODUCT_REQUIREMENTS_DOCUMENT.md` (PRD §13 exit criteria).

---

## Part 0 — Verification results (run before answering)

### 0.1 `grep -rn "apiRequest\|fetch(" frontend/` — exact output

```
frontend/shared/navigation.js:288:  const api = typeof apiRequest === "function" ? apiRequest : null;
frontend/shared/api-client.js:176:      fetch(`${API_PREFIX}/auth/me`, { headers }),
frontend/shared/api-client.js:177:      fetch(`${API_PREFIX}/permissions/me`, { headers }),
frontend/shared/app.js:2863:        await apiRequest(`/pipeline/applications/${applicationId}/stage`, {
frontend/shared/routing.js:129:    const response = await fetch(fetchHref, { credentials: "same-origin", headers: { Accept: "text/html" } });
```

**Reading of those 5 lines:**

| Line | What it is | Net effect |
|---|---|---|
| `navigation.js:288` | guarded `typeof` probe → `null` | `loadHomeMetrics()` returns early; home metrics stay `—` |
| `api-client.js:176,177` | the RB-1 gate's own fetch | **the only business-data fetch in the app** (session + permissions) |
| `app.js:2863` | **unguarded** `await apiRequest(...)` | throws `ReferenceError` when the pipeline drag-drop handler runs |
| `routing.js:129` | fetch of an **HTML page** for in-page overlays | navigation, not data |

`grep -rn "function apiRequest\|apiRequest =\|apiRequest:"` across the whole repo returns **nothing** — `apiRequest` is **never defined**. The only endpoint strings (`/requisitions`, `/notifications`, `/approvals`, at `navigation.js:292,294,296`) sit behind the guarded, always-`null` `api`. No page carries an inline script that fetches data.

### 0.2 `isAdmin` / `hasPermission` / `userPermissions` — exact output

```
frontend/shared/renderers.js:968:  const canTriage = typeof hasPermission === "function" && (isAdmin() || hasPermission("ai.agent.inbox_triage"));
frontend/shared/renderers.js:2267: const adminUser = typeof isAdmin === "function" && isAdmin();
frontend/shared/renderers.js:2268: const perms = typeof userPermissions === "function" ? userPermissions() : [];
frontend/shared/navigation.js:3,4,11         (prose in a comment header — not call sites)
frontend/shared/api-client.js:220,221        (prose in a comment — not a call site)
frontend/shared/api-client.js:223,354         (the gate's own `typeof isAdmin === "function"` fallbacks)
```

**5 code references, all inert** (`isAdmin`, `hasPermission`, `userPermissions` are defined nowhere): 3 in `renderers.js`, 2 in the gate's fallbacks.

### 0.3 Do `renderers.js` / `navigation.js` actually load in pages?

| File | Pages loading it | of 101 total |
|---|---|---|
| `shared/renderers.js` | **100** | 101 |
| `shared/api-client.js` | **100** | 101 |
| `shared/app.js` | **100** | 101 |
| `shared/navigation.js` | **76** | 101 (app pages; auth/marketing pages omit it) |

Observed script order in `pages/approvals-inbox.html`:
`renderers → api-client → ui-utils → tables → forms → sidebar → pipeline → routing → navigation.config → navigation → app`

**Conclusion: this is live production code, not a refactor in progress.** It executes in users' browsers today, so every inert-code finding below affects users **now**.

### 0.4 Additional DB/code probes run for this document

- `pipeline.board.read` vs `pipeline.read.summary`: `pipeline.board.read` appears **nowhere** in `backend/`; `pipeline.read.summary` is live at `api/v1/pipeline.py:26`, `api/deps.py:32`, `services/auth.py:71`.
- `requisitions.offer_ctc_max`: **does not exist** anywhere in `backend/` or `frontend/` (spec §3.1 claim is aspirational).
- Offer approval: `create_offer()` (`repositories/offers.py:142`) sets `offer_status = 'pending-approval'` and **unconditionally** inserts an `offer-approval` row — no threshold condition exists.
- `core/config.py`: **zero** S3/Redis/secret-manager configuration; `core/storage.py` is local-disk only.
- Pipeline templates: `pipeline_templates` = **0 rows**, `pipeline_template_stages` = **0 rows**, `requisition_pipeline_stages` = **table does not exist**.
- `candidate_applications.current_stage` distinct values: `Executive Review`, `internal-screening`, `interview`, `joined`, `shortlisted`, `some-untemplated-stage`, `Technical Interview`.
- PII aggregates (values not printed): users **258**, non-seed domains **1** (domain `recruitops.com`); candidates **13**, emails all synthetic (`example.com` 9, `test.com` 1, `test.local` 2 — **0 real domains**); `candidate_files` **0 rows**; `user_sessions` **1971**.

---

## Part 1 — Verification questions

> **Correction (2026-10-05, `phase-1-foundation-status.md`):** the grep below ran against an
> uncommitted working tree in which `api-client.js` had been cut from 5,978 to ~550 lines.
> The committed client (`0b2aeaa`) defines `apiRequest` and ~70 page loaders; the data layer
> has been restored. Items 5 and 6 are re-evaluated in the Phase 1 status doc.

### Q1. Does the frontend load data through another mechanism, or is `apiRequest` really missing?

**`apiRequest` is genuinely missing.** No other file, module, or inline script fetches business data — the only two `fetch()` calls in the data path are the RB-1 gate's `/auth/me` + `/permissions/me`.

**Therefore assessment items 5 and 6 are FAIL, not MET, and the ~3.8 weighted score is too generous.**

- **Item 6 — "Core modules end-to-end": FAIL.** End-to-end cannot be true if no page can retrieve a list from the API. The backend endpoints exist and pass tests, but the browser has no way to call them. The "browser-verified happy paths (tasks A–G)" must have been verified against **static prototype markup** (the HTML ships hardcoded rows/templates), not live API integration.
- **Item 5 — "Notifications real copy + working CTAs": FAIL (was ✅ MET).** CTA *navigation* works (`routing.js`), but with no data loader the notification list and badge count cannot be populated from `/notifications`. Static copy rendering is not a working notification.
- **Also overstated:** P2's claim that navigation "renders strictly from `/permissions/me`" — that endpoint is only fetched by the RB-1 gate, and only when a token exists.
- **Also broken:** `app.js:2863` will throw at runtime on pipeline drag-drop.

**Recommended correction:** item 6 ✅→❌, item 5 ✅→❌, item 4 evidence line-numbers → stale (§Part 1 Q2). Recompute the weighted score; it should land **below 3.8** (P2's 6/10 is the most inflated pillar).

### Q2. Treat the assessment's "17 sites" as stale and the spec's "3 inert sites" as current?

**Yes on "17" being stale; the spec's count needs a small correction.**

- The assessment cites `api-client.js` lines `182, 360, 367, 482, 683, 1351, 2144, 2519, 2955, 3736` — those belong to the **old 6,250-line `api-client.js`**. The file is now **553 lines** and contains no `isAdmin` at any of those lines. **Stale.**
- The spec's "3" counted `renderers.js:968`, `2267` and "the gate's own fallback". The precise figure is **5 code references** — `renderers.js:968, 2267, 2268` + `api-client.js:223, 354` — **all inert**. Two other grep hits (`navigation.js:3,4,11`, `api-client.js:220,221`) are comment prose.

**Action:** spec §0/§5 wording corrected to "5 references (3 in `renderers.js` + 2 gate fallbacks), all inert". The *substantive* point — the helpers are undefined and therefore dead — is unchanged.

### Q3. Is `renderers.js` / `navigation.js` code that loads in pages, or a refactor in progress?

**It loads — 100/101 and 76/101 pages respectively, in normal script order (§0.3).** Not a refactor; this executes today. Consequences users experience now:

| Finding | Line | User-visible effect today |
|---|---|---|
| AI triage toggle inert | `renderers.js:968` | the toggle can never enable (`typeof hasPermission` short-circuits `false`) |
| Agent run buttons inert | `renderers.js:2267-2268` | `renderAgentsWorkbench()` gets `adminUser=false`, `perms=[]` → no `ai.agent.*` buttons render |
| Home metrics inert | `navigation.js:288` | metric values stay `—` forever |
| Approvals counts static | `approvals-inbox.html` | tab counts are literal `0` markup, no loader |
| Stage-move call broken | `app.js:2863` | `ReferenceError` on pipeline drag-drop |

---

## Part 2 — Scope and goal

### Q4. What should the finished model be: remediation roadmap, technical design, revised PRD + test plan — or all three?

**All three, in this order, because the documents currently contradict each other.**

1. **Revised PRD (first — it is the source of truth).** It must absorb: the physical-tenants decision (Q7), `pipeline.read.summary` naming (Q10), the admin-bypass removal (Q9), the offer-threshold model (Q10), and the ops-provisioned launch (Q5). Until this lands, every design document drifts.
2. **Technical design** for the blocks that have no design today: JWT + rotating refresh, MFA/TOTP, object storage + upload validation, the `tenants` table migration, metric buckets, soft-delete + optimistic locking.
3. **Remediation roadmap** mapped to PRD §13 items 1–17 with owners and dates, plus the corrected assessment (Q1) as the baseline.

The existing `pipeline-rbac-architecture-spec.md` covers only RBAC + pipeline; it should be demoted to a component design under (2), not treated as the program plan.

### Q5. Is launch strictly ops-provisioned with a few known tenants?

**Yes (confirmed by the team).** Effects on the assessment:

- **Item 9** (tenant provisioning both ways) → reclassify **FAIL → Non-Blocker**, exactly as the assessment's own footnote permits ("*Reclassify to Non-Blocker only if launch is strictly ops-provisioned*").
- **Signup gate** leaves the launch path — but **item 16 does not fully clear**: ToS/DPA/privacy pages and the `/privacy/export-request` + `/privacy/delete-request` endpoints are still required for B2B tenants, even with zero self-serve signup. Only the *acceptance-gate* sub-item goes away.

### Q6. Target date and team size?

**Not known from the repository — this is an input you must supply.** No date, sprint plan, or team roster exists in the codebase, and I won't invent one. It is a hard prerequisite for Q4's roadmap: without a date and headcount the roadmap can sequence risk but cannot commit to dates. **Needed from you: target launch date, and team size split by backend/frontend/DevOps/QA.**

---

## Part 3 — Architecture decisions that block the rest

### Q7. Physical `tenants` table + `tenant_id` now, or amend the PRD to branch-based?

**Build it (confirmed).** Evidence supporting the decision, beyond your reasoning:

- No slug resolution exists anywhere in the backend, so assessment **item 10's wrong-tenant-slug guardrail is untestable** — a physical tenant with `slug` is what makes that guardrail implementable.
- Per-tenant uniqueness (email/employee_code/tenant-scoped codes) and the tenant **delete flow** both need a real parent row to cascade or cascade-soft from.
- The spec's §2.3 item 4 "*physical `tenants` table is deferred*" **contradicts the PRD and this decision — amend the spec.**

**Scope implied:** new `tenants` table (`id, slug, name, status, created_at…`) → `branches.tenant_id` FK; slug-based login resolution; tenant-scoped uniqueness constraints; tenant delete = staged soft-deactivate with an ops break-glass; migration backfilling one tenant per existing branch. This also closes item 10.

### Q8. Footprint feature: remove, move ops-only outside the app, or keep as a PRD exception?

**Recommendation: keep it as an explicit, documented PRD exception** (your call).

- It already ships tested (6 passing footprint tests) and role-gated server-side with audit.
- "Ops-only outside the app" means deleting working, tested code and re-implementing it as an internal tool — pure cost, no security gain, since it is already admin-role-gated.
- The only real objection is PRD §3.2's *"no `if admin, show every link` bypass"* — which is satisfied by writing the exception into the PRD rather than by removing the feature.

### Q9. Remove the admin bypass in frontend **and** backend together, seeding admin grants?

**Yes — remove both in one change (confirmed).** The spec explicitly warns that removing one side breaks parity the other way, and the reasoning holds: the backend bypass is at `api/deps.py:131` (`if auth_context.user.role_code == "admin": return auth_context`), and the frontend gate's bypass is the `roleCode === "admin"` branch in `enforcePagePermission`.

**Required companion work (otherwise removing it bricks admin access):**
1. Seed migration granting the admin role the **full resolved permission catalog** (184 codes today).
2. CI assertion that admin passes every route *via grants*, not identity — i.e. delete the `role_code == "admin"` short-circuit and prove `test_rbac_chain_integration.py` still passes.
3. Frontend: drop the `roleCode === "admin"` branch; gate evaluates purely on `NAV_PAGE_PERMISSIONS`.
4. Keep the one documented server-side exception (`get_candidate_footprint_service`) if Q8 selects "keep".

### Q10. Which permission name wins? And is the offer threshold per-tenant or per-requisition?

**(a) Permission name: `pipeline.read.summary` wins.** Verified: it is the live code at `api/v1/pipeline.py:26` (the actual `require_permissions` guard), `api/deps.py:32` (`PERMISSION_ALIASES`), and `services/auth.py:71` (`allowed_pages`). `pipeline.board.read` exists **nowhere** in `backend/`. The frontend already aliases `pipeline.board.read → pipeline.read.summary`, so nothing breaks at runtime.
→ **Amend PRD §3.2 to `pipeline.read.summary`.** (Alternative — rename to the PRD's `pipeline.board.read` — means a coordinated change across backend guard, aliases, seed, and DB catalog in one migration for zero functional gain. Not worth it.)

**(b) Offer threshold: neither exists — and today every offer needs approval.**
- `requisitions.offer_ctc_max` (spec §3.1): **does not exist** in any schema, migration, or code.
- PRD's per-tenant Settings threshold: **does not exist** either.
- Actual behavior: `create_offer()` unconditionally sets `offer_status='pending-approval'` and inserts an `offer-approval` row — **100% of offers route to approval.**

→ **Recommendation: implement the PRD's per-tenant Settings threshold** (tenant-level fits the multi-tenant model and is what the PRD specifies), with an optional per-requisition override column later. **Delete the spec's `offer_ctc_max` reference** — it describes code that was never written.

---

## Part 4 — Security and platform

### Q11. Which cloud and services for object storage, managed Redis, secrets, malware scanning?

**Cannot be answered from the repository — `core/config.py` contains zero S3/Redis/secret configuration and `core/storage.py` is local-disk only. This is your decision (account, region, cost, compliance).**

**Recommendation (AWS-first; say the word and I'll write the design either way):**

| Need | Recommended | Notes |
|---|---|---|
| Object storage | **S3 + SSE-KMS**, bucket private, presigned GET/PUT | replaces `core/storage.py`; closes assessment items 3 + 15 |
| Managed Redis | **ElastiCache (Valkey/Redis OSS)** | sessions after Q12 cutover + permission cache (`_get_cached_permissions`) |
| Secrets | **AWS Secrets Manager** (or SSM Parameter Store) | replaces gitignored `.env`; closes item 17's secret-store gap |
| Malware scan | **ClamAV in Lambda** on `ObjectCreated`, or **Sophos/ScanImage** gateway | must block linking until clean (item 15) |

**Alternative to name if you're on Azure:** Blob + CMK, Azure Cache for Redis, Key Vault, Defender for Storage. **Needed from you: cloud, region, and whether an existing account/landing zone applies.**

### Q12. One-release cutover to JWT + rotating refresh, invalidating all sessions including the 1,964 stale?

**Yes — recommended.** Rationale:

- Sessions are opaque with no refresh flow today (item 2 FAIL), so there is nothing valuable to preserve — no user experience depends on the current tokens.
- The session table is already polluted: **1,971 rows ≈ 12.7 per active user**, almost all stale (the count has grown since the assessment's 1,964).
- **No production users exist yet** (launch is future work), so "invalidating all sessions" costs at most a one-time re-login for staged/demo accounts.
- A rolling dual-format migration is strictly *more* work and *more* risk than one cutover.

**Cutover checklist:** JWT signing key in the secrets manager; refresh-token rotation with reuse detection; revocation/denylist; **purge `user_sessions` in the same migration**; forced re-login; and a regression test asserting old opaque tokens now 401.

### Q13. TOTP-only MFA? Admin MFA at login or before the tenant goes active?

**TOTP-only is acceptable for launch** (WebAuthn/passkeys post-launch), provided recovery codes + an ops break-glass path ship with it.

**Enforce Admin MFA *before the tenant goes active*, not merely at login.** Because launch is ops-provisioned (Q5), provisioning-time enforcement is the only way to guarantee no active tenant ever runs without admin MFA; login-enforcement alone leaves a window where an admin exists and can act before their first MFA challenge. Practically: the tenant `status` cannot flip to `active` until every admin role has MFA enrolled, verified during ops provisioning.

### Q14. Exact CORS origins and TLS termination point for staging and production?

**Cannot be answered from the repository — `cors_origins` defaults to `*` and there is no TLS config at all (assessment item 7). Needed from you: the real hostnames.**

**Recommended shape (fill in your domains):**
- Staging: `https://staging.<your-domain>` — API behind the same origin or an explicit allowlist entry.
- Production: `https://app.<your-domain>` (+ any tenant-specific subdomains you will actually serve).
- **TLS terminates at the load balancer / ingress**, not in the app; app serves plain HTTP on the internal port; HSTS with a long max-age at the edge; redirect all HTTP→HTTPS; `cors_origins` becomes an exact-match list with `allow_credentials` and no wildcard.

---

## Part 5 — Data and pipeline

### Q15. Is there real candidate PII in the current DB (256 users)? Scrub plan needed before staging?

**No material real PII — measured, not assumed:**

| Probe | Result |
|---|---|
| User emails on non-seed domains | **1 of 258** (domain `recruitops.com` — own-domain, not a third party) |
| Candidate email domains | `example.com` 9, `test.com` 1, `test.local` 2 → **0 real-world domains** |
| Candidates total | **13** |
| `candidate_files` (stored resumes) | **0 rows** — nothing is on disk |

**Implication:** the assessment's headline risk — *"plaintext PII resumes on local disk"* — currently has **zero files at risk**, because no uploads exist. That is a *control* gap (item 15 stands: an `.exe` renamed `.pdf` would be accepted), not a *data-exposure* incident.

**Recommendation:** a scrub plan is **hygiene, not a staging blocker**. Do it the cheap way: **do not copy this DB** — provision a fresh seeded staging database (the assessment's own Stage 0.4), and keep a documented masking/scrub script as a standing guardrail for any future copy. Note the counts have drifted since the assessment (users 256→258, sessions 1964→1971).

### Q16. Is the client-specific pipeline (metric buckets, materialized stages, scorecards) in scope for launch?

**The reporting-bucket fix is P0 for launch — and the evidence is stronger than the spec stated:**

- `pipeline_templates` = 0 rows, `pipeline_template_stages` = 0 rows, `requisition_pipeline_stages` **table doesn't exist** → template overlays/materialization are unimplemented (spec P2).
- **But live data already contains non-baseline stage labels:** `Executive Review`, `Technical Interview`, `shortlisted`, `internal-screening`, `some-untemplated-stage` alongside baseline `interview`/`joined`.
- Reports match literal predicates (`current_stage IN ('joined','hired')` etc.), so **those 5 labels already vanish from funnel / Time-to-Fill / SLA reporting today.** The spec called this "P0 because custom stages *would* vanish" — in fact they **already do**.

**Scope split:**
- **Launch (P0):** `metric_bucket` column + CHECK enum, `candidate_stage_history.from_bucket/to_bucket`, `vw_application_metric_state`, and swap every literal stage predicate in `reports.py`/`dashboards.py`.
- **Post-launch (P2):** overlay inheritance, `requisition_pipeline_stages` materialization, `scorecard_templates` + structured scorecards — justified by 0 templates existing and no tenant requesting overlays yet.

### Q17. Soft-delete: hidden by default, restore role-limited?

**Yes — and it is assessment item 14 (currently FAIL/BLOCKER).** Recommended model:

- Archived candidates excluded from all list endpoints by default (`?include_archived=true`
  to see them), enforced in the repository layer so direct-ID routes stay consistent.
- **Use the catalog's existing convention — do not invent a `restore` code.**

The 184-code catalog already contains:

| Code | Entity | Enforced in code today? |
|---|---|---|
| `candidate.delete.soft` / `candidate.delete.hard` | candidates | **no** (0 refs) |
| `client.delete.soft`, `client.contact.delete.soft` | clients / contacts | **no** (0 refs) |
| `user.delete`, `user.delete.soft`, `user.delete.hard` | users | **no** (0 refs) |
| `company.delete` | company | **no** (0 refs) |
| `requisition.reopen` | requisitions (reopen only) | **no** (0 refs) |

These are **seeded but unenforced** — zero references in `backend/app/`. Missing entirely:
`requisition.delete.soft`, any application-archive code, and `pipeline.stage.reopen`
(spec §3.2 proposes it; it does not exist).

**Scope recommendation:**

- **One capability governs both directions:** `<entity>.delete.soft` gates *archive and
  restore* — same trust level, both operations audited. A separate `<entity>.restore` would
  double the catalog for no security gain.
- **Applications should not get an archive at all.** They already have a terminal lifecycle
  (`rejected` / `withdrawn` / `joined`) plus `application_status`; stacking "archive" on top
  would duplicate that model. Same reasoning for requisitions: use close + the existing
  `requisition.reopen` rather than a new soft-delete.
- So the concrete scope is: **enforce the codes that already exist** (candidates, clients,
  users, company), **add `requisition.delete.soft`** if true archive is wanted beyond reopen,
  and **leave applications to the status lifecycle**.
- Hard delete (`*.delete.hard`) stays ops-only (aligns with Q7's tenant delete flow).
- Ship it **with** the `version`/409 optimistic-locking work from the same item — soft-delete
  without write-conflict detection leaves the classic "restore over a concurrent edit" race.
- **Correction:** an earlier draft of this answer named a `candidate.restore` permission.
  That code does not exist anywhere in the repo or the DB catalog — it appears only in this
  document. The table above is the verified state.

---

## Part 6 — AI and operations

### Q18. Is AI off at launch?

**Yes (confirmed).** This removes item 11's four gates from the launch path: prompt-injection isolation, eval-set regression gate, provider fallback, and per-tenant cost caps.

**Notes:** keep the flag **default-off** and asserted off in CI (assessment Stage 0.3 already probes this); the draft-only/human-in-the-loop code and its 6 passing tests stay as-is. Separately, the inert AI-triage UI (`renderers.js:968`) means the toggle cannot enable AI anyway — **delete or fix it post-launch**, and do not count its presence as AI readiness.

### Q19. Who owns on-call, backups and restore drills, and what is the expected peak concurrent user count?

**Neither value exists in the repository — both must come from you.** Confirmed there is no CI/CD, no alerting, and no load-test harness (assessment item 17), so **the 3× load test cannot even be sized until you supply peak concurrent users.**

**Needed from you:**
1. **Named on-call owner** (and escalation path) for launch + first sprint.
2. **Backup/restore drill owner and cadence** — recommend monthly restore-to-verify, not just backup-success checks (assessment item 8).
3. **Expected peak concurrent users** (e.g. 50 / 200 / 1,000) — this sets p95 budgets (`<400ms` read, `<800ms` write, `<2s` report) and the 3× load-test target.

---

## Summary — status of every question

| # | Question | Status | Answer in one line |
|---|---|---|---|
| 1 | Data layer: other mechanism or missing `apiRequest`? | **VERIFIED** | `apiRequest` is missing; items 5 & 6 = FAIL; 3.8 too generous |
| 2 | "17 sites" stale vs "3 inert" current? | **VERIFIED** | 17 stale; precise figure = **5 references, all inert** |
| 3 | Do renderers/nav load in pages? | **VERIFIED** | Yes (100/101, 76/101) → findings hit users today |
| 4 | Roadmap / design / PRD+test plan? | **RECOMMENDED** | All three, PRD first (docs currently contradict) |
| 5 | Ops-provisioned launch? | **CONFIRMED** | Item 9 → Non-Blocker; item 16 narrowed, not cleared |
| 6 | Target date + team size? | **⏳ INPUT NEEDED** | No date/team in repo; required before any dated roadmap |
| 7 | Physical tenants table now? | **CONFIRMED: build** | Enables slug login, uniqueness, delete flow; amend spec §2.3 |
| 8 | Footprint: remove / ops-only / exception? | **⏳ YOUR CALL** | Recommend keep as documented PRD exception |
| 9 | Remove admin bypass both sides? | **CONFIRMED** | Yes, together + seed admin grants + CI proof |
| 10a | `pipeline.board.read` or `pipeline.read.summary`? | **VERIFIED** | `pipeline.read.summary` wins; amend PRD §3.2 |
| 10b | Offer threshold: tenant setting or `offer_ctc_max`? | **VERIFIED** | **Neither exists**; every offer auto-approves today → build PRD's tenant setting |
| 11 | Cloud: storage, Redis, secrets, scanning? | **⏳ INPUT NEEDED** | No infra config exists; AWS/Azure recommendation table provided |
| 12 | One-release JWT+refresh cutover? | **RECOMMENDED** | Yes — no production users, 1,971 stale sessions to purge |
| 13 | TOTP-only MFA; when enforced? | **RECOMMENDED** | TOTP yes; enforce **before tenant goes active** |
| 14 | CORS origins + TLS termination? | **⏳ INPUT NEEDED** | Currently `*`; need your hostnames; terminate at LB/ingress |
| 15 | Real PII in DB? | **VERIFIED** | No material PII (0 real domains, 0 files); fresh staging seed, not a blocker |
| 16 | Pipeline buckets in scope for launch? | **VERIFIED** | Bucket fix **P0** — 5 custom labels already vanish from reports |
| 17 | Soft-delete hidden by default? | **RECOMMENDED** | Yes — reuse existing `<entity>.delete.soft` codes (seeded, unenforced) for archive **and** restore; applications keep their status lifecycle; ship with 409 locking |
| 18 | AI off at launch? | **CONFIRMED** | Removes 4 gates from the launch path |
| 19 | On-call owner, backups, peak users? | **⏳ INPUT NEEDED** | 3 values you must supply; blocks item 17 sizing |

**Open inputs required from the team (5):** target date + team size (Q6) · cloud/region/account (Q11) · staging + production hostnames (Q14) · on-call owner, drill cadence, peak concurrent users (Q19) · Q8 footprint preference.
