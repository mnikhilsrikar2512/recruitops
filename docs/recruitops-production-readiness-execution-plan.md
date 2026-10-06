# RecruitOps — Production Readiness Execution Plan

**Version:** 1.0 · **Date:** 2026-10-04
**Purpose:** Turn the NO-GO assessment into a sequenced, testable path to production, where every PRD §13 criterion has a named proof.
**Built from:** `PRODUCT_REQUIREMENTS_DOCUMENT.md` (PRD), `production-readiness-assessment.md` (assessment), `pipeline-rbac-architecture-spec.md` (RBAC spec), `readiness-qa-and-decisions.md` (decision log).
**Dates:** none are committed. They need your launch date and team split (input I-1). Effort is given as T-shirt sizes (S ≤ 3 dev-days, M ≤ 2 weeks, L 2–4 weeks, XL > 4 weeks), which are my estimates and should be recalibrated once the team is known.

---

## 1. Corrected baseline

The decision log verified that `apiRequest` is defined nowhere, so no page can load business data from the API. That invalidates two assessment "MET" ratings. The item 4 evidence is also stale, because the old line numbers belong to a 6,250-line file that is now 553 lines.

| §13 | Criterion | Assessment said | Corrected | Launch blocker? |
|---|---|---|---|---|
| 1 | Isolation tests + dual-tenant seed | MET | **MET** (must be re-proven after the tenants migration) | gate |
| 2 | JWT + rotating refresh | FAIL | FAIL | **Yes** |
| 3 | Object storage | FAIL | FAIL | **Yes** |
| 4 | Sidebar/guards match role; Admin = control plane | PARTIAL | PARTIAL (gate exists but has an admin bypass; 5 inert helper references) | **Yes** |
| 5 | Notifications real copy + live metrics + CTAs | MET | **FAIL**: no data loader exists | **Yes** |
| 6 | Core modules end-to-end | MET | **FAIL**: the browser cannot call the API; `app.js:2863` throws `ReferenceError` | **Yes** |
| 7 | §10 security in prod config | FAIL | FAIL | **Yes** |
| 8 | Environments / backups / audit retention | PARTIAL | PARTIAL. *My recommendation:* environments and backups are launch-blocking once real data exists; the retention job can follow in the first post-launch sprint. | Backups/envs: yes |
| 9 | Provisioning both ways | FAIL | **Deferred.** Launch is ops-provisioned. A repeatable ops provisioning procedure is still required (§5.H). | No (ops path: yes) |
| 10 | QA guardrails | PARTIAL | PARTIAL. The slug guardrail becomes testable after tenants ship. | Gate |
| 11 | AI V1 gates | PARTIAL | **Flag-off at launch.** The gates apply only when AI is enabled. | No |
| 12 | Account security | FAIL | FAIL | **Yes** |
| 13 | API contract | PARTIAL | PARTIAL | Gate |
| 14 | Data lifecycle | FAIL | FAIL (scope narrowed, see D-07) | **Yes** |
| 15 | File safety | FAIL | FAIL (control gap only; 0 files stored today) | **Yes** |
| 16 | Legal & privacy | FAIL | FAIL (acceptance gate deferred; docs and privacy endpoints still required) | **Yes** |
| 17 | Ops readiness | FAIL | FAIL | **Yes** |

**Tally:** 1 met · 4 partial · 2 deferred or flag-off · 10 failing. (My earlier rough estimate was 1 / 5 / 11, so this is a closer count.)
**Indicative readiness:** about 3 / 10, down from 3.8. P2 (RBAC and navigation) drops the most, from 6 to about 3. This is a judgment call, not a measurement.

**Data that supports the plan (from the decision log):**
- Users 258, candidates 13, `candidate_files` 0 rows, sessions 1,971. There is no production data to migrate.
- 0 pipeline templates. Live applications already use 5 non-baseline stage labels that vanish from reports today.
- Every offer currently routes to approval, because `create_offer()` has no threshold logic.

---

## 2. Decision register

### 2.1 Decided
| ID | Decision | Source |
|---|---|---|
| D-01 | Launch is **ops-provisioned**; self-serve signup is post-launch | Confirmed |
| D-02 | Build a physical `tenants` table and `tenant_id`; slug-based login | Confirmed |
| D-09 | MFA is **TOTP**; Admin MFA is enforced **before a tenant can go active** | Recommended in the log |
| D-10 | **AI is OFF at launch**; the flag is asserted off in CI | Confirmed |
| D-11 | Metric-bucket reporting fix is **P0**; overlays and scorecards are post-launch | Verified |
| D-12 | Staging uses a **fresh seeded DB**; never copy the dev DB | Verified |

### 2.2 Adopted on my recommendation (change any of these and I will update the plan)
| ID | Decision | Rationale |
|---|---|---|
| D-03 | **Admin seed = the Admin column of PRD §3.2 only**, not all 184 catalog codes. CI proves admin passes control-plane routes via grants and is **denied** execution routes. | PRD §2, §3.1 and §4.3 forbid giving Admin the execution pack; an all-codes seed makes the sidebar show everything. |
| D-04 | **Footprint becomes a platform-ops capability**, not a Tenant Admin one. It moves to an ops-only surface (`/ops/v1/…`) behind a separate credential held in the secrets manager, plus a network allowlist. It is documented as an explicit PRD exception and fully audited. | PRD §3 says Tenant Admins never see other tenants. |
| D-05 | Permission name is **`pipeline.read.summary`**; amend the PRD. | It is the live code; `pipeline.board.read` exists nowhere in `backend/`. |
| D-06 | **Per-tenant offer-approval threshold** in Settings. The default is **0**, meaning every offer needs approval, which preserves current behavior. A per-requisition override is optional later. Delete `offer_ctc_max` from the RBAC spec. | Neither exists today; the PRD specifies the tenant setting. |
| D-07 | **Soft-delete scope narrowed:** enforce the seeded `<entity>.delete.soft` codes for candidates, clients, users and company; one capability gates archive and restore. Applications keep the rejected/withdrawn/joined lifecycle. Requisitions use close + `requisition.reopen`. Hard delete is ops-only. **PRD §9.0, §11 and §13 item 14 are amended to match.** | Archiving applications would duplicate the status lifecycle. |
| D-08 | **One-release JWT cutover.** All sessions are invalidated and `user_sessions` is purged in the same migration. | No production users yet. |
| D-13 | **Sequence tenancy before JWT.** Phases are ordered Foundation → Tenancy/RBAC → Auth → Files/Data → Legal → Ops → Verify. | JWT claims carry `tenant_id` (PRD §10), so tenants must exist first. The assessment's "security first" order would force rework. |

### 2.3 Pending your input (the plan is written to proceed with the stated fallback)
| ID | Input needed | Fallback used if unanswered |
|---|---|---|
| I-1 | Target launch date; team size by backend / frontend / DevOps / QA | Roadmap stays sequence-only, with no dates |
| I-2 | Cloud, region, existing account or landing zone | Design uses provider-neutral adapters; AWS is the reference implementation |
| I-3 | Staging and production hostnames | Placeholders `staging.<domain>` and `app.<domain>`; CORS and TLS cannot close without real names |
| I-4 | On-call owner, backup-drill owner, expected peak concurrent users | Item 17 cannot close; load-test size is unknown |
| I-5 | **Branch-to-company mapping** for the tenant backfill | The migration **refuses to run** without a mapping file (fail closed). It never defaults to one tenant per branch, which would split a company's locations. |
| I-6 | Is `executiveconnection.com` real or fictional data? | If real, re-run the PII assessment before staging |
| I-7 | Legal counsel for ToS, Privacy Policy and DPA text | I cannot author legal terms; engineering builds the versioning and acceptance mechanism only |

---

## 3. Target architecture (what "done" looks like)

```
Browser (static HTML + shared JS)
  └─ api-client.js  → apiRequest(): Bearer JWT, 401→refresh→retry once, 409 handling, §9.0 error envelope
        │  HTTPS (TLS at LB/ingress, HSTS)
FastAPI /api/v1
  ├─ AuthN: JWT access (sub, tenant_id, sid), refresh opaque+hashed+rotating (family_id)
  ├─ AuthZ: require_permissions(...) from DB grants ONLY (no role_code bypass)
  ├─ Tenant scope: repository-layer tenant filter + assert_row_in_tenant on direct-ID routes
  ├─ Storage adapter → S3-compatible private bucket (signed URLs after authZ) + scan gate
  ├─ Rate limit / session denylist / permission cache → Redis
  └─ /ops/v1 (platform-ops credential): tenant provisioning, footprint, break-glass
MSSQL (tenants, tenant_id on all operational roots, version columns, archived_*)
Secrets manager · CI/CD (build→test→lint→migrate→deploy) · logs/metrics/alerts · backups
```

---

## 4. Phased roadmap

Each phase has an **entry condition**, **work items**, and an **exit gate** that must pass before the next phase starts. Items marked ∥ can run in parallel with others in the same phase.

### Phase 0 — Truth and decisions (documents only) · size S
**Entry:** now.
| # | Work | Output |
|---|---|---|
| 0.1 | Apply the **corrected assessment** (§1) and fix the stale "17 sites" evidence | assessment v2 |
| 0.2 | Apply the **PRD amendment list** (§8) | PRD v2 |
| 0.3 | Fix the RBAC spec: §2.3 item 4 (tenants), remove `offer_ctc_max`, correct the `isAdmin` count to 5, fix the decision-log summary row for Q10b (offers require approval; they do not auto-approve) | spec v2 |
| 0.4 | Collect I-1 to I-7 | inputs filed |
| 0.5 | Reconcile the **permission catalog**: 184 live codes vs the roughly 50 in PRD §3.2. List codes in the DB but not the PRD (add a row or remove) and PRD codes missing in the DB. Note the PRD gap: Business Titles has no permission code. | catalog reconciliation table |

**Exit gate:** PRD v2 approved; no open contradiction between the four documents.

### Phase 1 — Foundation: make the app actually work · size L
**Entry:** Phase 0 exit.
| # | Work | Size |
|---|---|---|
| 1.1 | **CI baseline first.** Add a pipeline running backend pytest, frontend lint and a static-asset check on every PR. Everything below needs it. | S |
| 1.2 | **Define `apiRequest()`** in `frontend/shared/api-client.js`: base prefix, Bearer header, JSON, §9.0 error envelope parsing, `Idempotency-Key` passthrough, 401 hook (a stub until Phase 3), 409 hook. Export it on `RecruitOpsLive`. | M |
| 1.3 | Fix `app.js:2863` (stage-move now works) and `navigation.js:288` (`loadHomeMetrics` loads real data). Add loaders for notification list and badge counts, and approvals tab counts (currently static `0`). | M |
| 1.4 | Remove or properly implement the 5 inert references (`renderers.js:968, 2267, 2268`; `api-client.js:223, 354`) using capability-only `hasPermission(code)`. | S |
| 1.5 | Implement `refreshPermissions()` (focus + 5-minute interval + re-render) from RBAC spec §4.1. | S |
| 1.6 | Config scaffolding: env-based settings for S3, Redis, secrets, JWT keys, CORS list. `cors_origins` stops defaulting to `*`. | S |
| 1.7 | **Fresh seeded staging DB** with a dual-tenant seed (D-12). | S |
| 1.8 ∥ | **Re-baseline the smoke test** against live data (§6.3), since earlier "browser-verified" runs were evidently against static markup. | M |

**Exit gate:**
- A page-level test loads a list through the API for each core module (clients, requisitions, candidates, pipeline, approvals, notifications).
- No `ReferenceError` in the browser console across all 101 pages (automated sweep).
- CI is green and required for merge.

### Phase 2 — Tenancy and RBAC parity · size XL
**Entry:** Phase 1 exit.
| # | Work | Size |
|---|---|---|
| 2.1 | **`tenants` table** (`id, slug UNIQUE, display_name, status, created_at`); `tenant_id NOT NULL` on every operational root (branches, users, custom roles, clients, requisitions, candidates, applications, notifications, approvals, daily updates, meetings, audit rows, files, settings). Tenant-scoped uniqueness: `(tenant_id, email)`, `(tenant_id, branch code)`. Idempotent Alembic migration. | L |
| 2.2 | **Backfill from the mapping file (I-5).** Fail closed if absent. Because staging uses a fresh seed (D-12), the backfill mostly serves the dev DB. | S |
| 2.3 | **Repository-layer tenant scope** (single helper used by all repositories) plus `assert_row_in_tenant` on every direct-ID route. Add a CI test that every table is either tenant-scoped or on an explicit allowlist. | L |
| 2.4 | **Slug login:** `POST /auth/login` takes `slug + email + password`; unknown slug returns a clean 404/400 envelope. This makes the §13 item 10 wrong-slug guardrail testable. | M |
| 2.5 | **Remove the admin bypass in both places in one change:** `api/deps.py:131` and the `roleCode === "admin"` branch in `enforcePagePermission`. | M |
| 2.6 | **Admin seed migration per D-03:** Admin template = exactly the Admin column of PRD §3.2. System templates (Admin, Manager, Recruiter) seed new tenants from the PRD §3.2 defaults. Existing dev roles are reset by the migration. | M |
| 2.7 | **Resolve the exceptions and drift:** align `pipeline.read.summary`; add `pipeline.stage.reopen` and any new code to the PRD §3.2 table first (rule: no code ships without a row). | S |
| 2.8 | **Footprint → platform-ops** per D-04: move to `/ops/v1`, ops credential, allowlist, audit; keep and adapt the 6 existing tests. | M |
| 2.9 | **Parity harness** `test_rbac_parity_db.py` (RBAC spec §2.1 matrix) and rewrite the 21 isolation tests for real tenants. | L |

**Exit gate (all automated):**
- Dual-tenant denial suite green with real `tenant_id` (§13 item 1 re-proven).
- Admin sidebar link set == PRD §3.1 list **exactly**; admin is denied every execution route.
- Two non-admin users with identical grants see identical UI and receive identical API results.
- Wrong-slug login returns a clean error with no stack trace.
- No code path reads `role_code == "admin"` for authorization (grep gate in CI), except the documented ops surface.

### Phase 3 — Account security and perimeter · size XL
**Entry:** Phase 2 exit; Redis available in staging (I-2).
| # | Work | Size |
|---|---|---|
| 3.1 | **JWT access** (short TTL, claims `sub, tenant_id, sid`), signing key in the secrets manager. | M |
| 3.2 | **Refresh tokens:** opaque, hashed at rest, rotation on use, `family_id`, **reuse detection revokes the family**; revoke on logout and password change. | L |
| 3.3 | **Session management:** repurpose `user_sessions` (family, device, IP, last seen). Endpoints `GET/DELETE /auth/sessions`, `DELETE /auth/sessions/{sid}`; admin force-revoke on deactivation or compromise; scheduled cleanup of stale rows. | M |
| 3.4 | **One-release cutover** (D-08): purge `user_sessions`, force re-login, regression test that old opaque tokens return 401. | S |
| 3.5 | **Password policy:** min 12, common/breached blocklist, lockout and backoff on repeated failures. For the breached check, use the HIBP range API if staging has egress; otherwise a bundled offline blocklist (decide with I-2). | M |
| 3.6 | **MFA (TOTP):** `user_mfa` table, `/auth/mfa/enroll|verify|challenge`, DELETE with re-verify, recovery codes (hashed), `mfa-enroll.html`, `mfa-challenge.html`, `active-sessions.html`. **A tenant cannot be set `active` until every active Admin has MFA** (enforced in ops provisioning). Ops break-glass path. | L |
| 3.7 | **Rate limiting (Redis):** login 5/min/IP and 10/min/account, forgot-password, refresh; numeric defaults per PRD §10. | M |
| 3.8 | **Perimeter:** exact-match CORS allowlist, `allow_credentials` without wildcard, security headers, TLS at LB, HSTS, HTTP→HTTPS redirect (needs I-3). | S |
| 3.9 | **Frontend:** wire the 401 hook to refresh-and-retry once; clear session on refresh failure. | S |

**Exit gate:**
- Refresh-theft test: reusing a rotated refresh token kills the whole family.
- Expired refresh requires a full re-login (§13 item 10 guardrail).
- An Admin without MFA blocks a tenant from going active.
- CORS probe from a disallowed origin is rejected.
- Rate-limit test hits 429 at the documented thresholds.
- Password of 8 characters is rejected; a breached password is rejected.

### Phase 4 — Files, data integrity, lifecycle · size XL
**Entry:** Phase 2 exit (can overlap Phase 3 once storage infra exists). ∥
| # | Work | Size |
|---|---|---|
| 4.1 | **Storage adapter** interface; S3-compatible implementation, private bucket, keys prefixed `tenant_id/`, **signed URLs issued only after authZ**; `core/storage.py` local-disk path retained for dev only. | M |
| 4.2 | **Upload pipeline:** magic-byte MIME sniff, allowlist (PDF/DOC/DOCX, logos PNG/JPG), size caps (resume ≤ 10 MB, logo ≤ 5 MB), then **quarantine → malware scan → available**. A failed scan is quarantined and never linked. Apply `Idempotency-Key` on upload. | L |
| 4.3 | **Optimistic locking:** `version` on candidates, requisitions, applications; versioned UPDATE; 409 with the fresh row; frontend 409 dialog ("this record changed, reload"). | L |
| 4.4 | **Soft-delete (D-07):** enforce `candidate.delete.soft` and `client.delete.soft` (and the user and company codes); archived rows are excluded by default with `?include_archived=true`, enforced in the repository layer; archive and restore audited; hard delete is not reachable from the app. | L |
| 4.5 | **Metric buckets (P0):** `metric_bucket` column + CHECK enum, `from_bucket`/`to_bucket` on history, `vw_application_metric_state`; replace every literal stage predicate in `reports.py` and `dashboards.py`; the append-only trigger on `candidate_stage_history`. | L |
| 4.6 | **Terminal-state guard:** extend `move_pipeline_stage_service` to Rejected and Withdrawn; backward moves require a reason; `POST …/reopen` + `pipeline.stage.reopen` with append-only history. | M |
| 4.7 | **Duplicate matching:** keep exact email/phone auto-flag; add a fuzzy name+location tier as suggest-only; audit decisions. | M |
| 4.8 | **Offer threshold (D-06):** tenant Settings field (default 0); `create_offer()` routes to approval only above the threshold. | M |
| 4.9 | **API contract sweep:** pagination, `sort`, filters (unsupported filter → 400), §9.0 error envelope on every list and mutate endpoint; response sweep for foreign-tenant IDs. | L |

**Exit gate:**
- An `.exe` renamed `.pdf` is rejected; an EICAR test file is quarantined and never linkable.
- Two concurrent edits: the second gets 409 with the fresh row.
- A report over the 5 live custom stage labels counts them in the right buckets.
- Archived candidates are hidden from lists and from direct-ID reads for non-authorized users, and restore works for authorized users.
- An offer below the threshold sends directly; above it creates an approval; the default threshold of 0 approves everything.

### Phase 5 — Legal, privacy, provisioning · size L
**Entry:** Phase 2 exit; I-7 (counsel) engaged.
| # | Work | Size |
|---|---|---|
| 5.1 | **Legal versioning:** `legal_acceptances` table; `GET/POST /legal/acceptances`; published ToS, Privacy Policy and DPA pages with version numbers; AI-scoring disclosure copy in the Privacy Policy. Text comes from counsel (I-7). | M |
| 5.2 | **Ops provisioning** (`POST /tenants` or an ops CLI under `/ops/v1`): creates tenant, first Admin, seeds system roles, records legal acceptance on the tenant's behalf, enforces the MFA gate before `active`. Repeatable and idempotent, with a runbook. | L |
| 5.3 | **Privacy endpoints:** `POST /privacy/export-request`, `POST /privacy/delete-request`, `GET /privacy/requests`; `privacy_requests` table; routed through Approvals (PRD §4.10); delete purges tenant operational data while audit rows are held 90 days (PRD §12); `data-export-delete-request.html`. | L |
| 5.4 | **Audit log viewer** (`/audit-logs`, `audit-log-viewer.html`) and audit events for session revocation, MFA changes, privacy requests. | M |

**Exit gate:**
- Provision a fresh tenant from nothing to an active, MFA-protected Admin using only the runbook.
- Export request produces a complete tenant archive; delete request purges data and keeps audit rows for the hold period.
- Legal versions are recorded with timestamp and user id.

### Phase 6 — Operations hardening · size XL
**Entry:** Phases 3 and 4 largely complete; I-2, I-3 and I-4 answered.
| # | Work | Size |
|---|---|---|
| 6.1 | **Containerize** the API and frontend server; separate `dev` / `staging` / `production` with separate DB, storage and secrets. | M |
| 6.2 | **CD pipeline:** build → test → lint → deploy per environment; **migrations as a gated step**; no manual prod deploys. | L |
| 6.3 | **Managed secrets** migration; remove prod reliance on `.env`; rotation schedule documented. | M |
| 6.4 | **Observability:** structured logs with request ids, error tracking, health check, metrics. | M |
| 6.5 | **SLOs and alerts:** 99.5% uptime target; on-call alerts for error-rate spike, latency breach, failed backup (AI provider alert deferred with AI). Escalation path documented. | M |
| 6.6 | **Backups and DR:** daily DB backups, documented RPO/RTO, **monthly restore-to-verify drill**; object-store versioning; audit-retention enforcement job. | L |
| 6.7 | **Load test:** 3× expected peak (needs I-4); p95 targets < 400 ms read, < 800 ms write, < 2 s reports. | L |

**Exit gate:** one full deploy to staging via the pipeline with no manual steps; a restore drill completed and timed; load-test report meets p95 targets; a test alert reaches the on-call owner.

### Phase 7 — Staging verification and go/no-go · size M
**Entry:** Phases 1 to 6 exit gates passed.
1. Run the **updated smoke test** (§6.3) end to end against staging.
2. Run the full automated proof suite (§6.1) and attach the evidence pack.
3. UAT with two real-shape personas (Tenant Admin, Recruiter) across the happy path and every guardrail.
4. Security review: dependency scan, secrets scan, a focused manual check of auth, tenant isolation and file handling.
5. Fill in the go/no-go checklist (§7).

**Exit gate:** every launch-blocker item in §7 is checked with linked evidence. Anything still open is explicitly accepted in writing by the product owner.

### Dependency summary
```
P0 ─▶ P1 (API client, CI) ─▶ P2 (tenants, RBAC) ─┬▶ P3 (JWT, MFA, Redis) ─┐
                                                  ├▶ P4 (files, lifecycle) ─┼▶ P6 (ops) ─▶ P7 (go/no-go)
                                                  └▶ P5 (legal, provisioning)┘
```
Critical path: P1 → P2 → P3 → P6 → P7. Phases 4 and 5 are parallelizable once P2 exits and infra (I-2) exists.

---

## 5. Key design notes (where the existing documents are silent or wrong)

**A. API client contract.** `apiRequest(path, { method, body, headers, signal })` returns parsed JSON. On non-2xx it throws an `ApiError { status, code, message, fieldErrors }` parsed from the PRD §9.0 envelope. On 401 it calls the refresh hook once, then retries once. On 409 it surfaces `currentRow` for the conflict dialog. It must never widen access on failure (matches the RBAC spec's "never widen access on error").

**B. Admin permission seed (D-03).** Admin-column codes in PRD §3.2: `dashboard.view_admin`, `user.read/write`, `location.read/write`, `role.read/write`, `visibility_rules.write`, `work_assignment.write`, `portal_accounts.write`, `ai.policy.write`, `audit_log.read`, `privacy_request.write`, `approval.decide`, `notification.read`, `report.read`, `settings.write`. Plus the codes needed for Business Titles, which the PRD omits (Phase 0.5 resolves). My Work stays hidden unless the Admin also holds an execution grant.

**C. Tenancy.** Every operational root carries `tenant_id NOT NULL` (PRD §8.1). Branch-derived tenancy (the current model) is replaced, not supplemented, so there is one source of truth. JWT carries `tenant_id` but **authorization still resolves from DB grants**. The token authenticates, it does not authorize.

**D. Refresh-token store.** `refresh_tokens(user_id, token_hash, family_id, expires_at, revoked_at, replaced_by)`. Presenting an already-rotated token revokes the entire family and records an audit event. The Redis denylist holds revoked `sid` values until access-token expiry.

**E. Upload state machine.** `received → quarantined → scanning → available | rejected`. Only `available` files can be linked to a record or served. Serving always goes through the authZ check, then a short-lived signed URL.

**F. Offer threshold semantics.** `offer_approval_threshold` in tenant settings (currency: tenant default, INR today). An offer with `offered_ctc > threshold` creates an approval; otherwise it is sent directly. Threshold 0 means everything needs approval. Multi-currency stays future (PRD §5).

**G. Soft-delete.** Add `archived_at`, `archived_by` to candidates and clients. `GET` of an archived row by id returns it only to holders of the matching `.delete.soft` code, otherwise a clean 404. Linked requisitions and applications are **not** cascaded (PRD §8.3 lifecycle rule).

**H. Ops provisioning runbook (outline).** (1) create tenant with unique non-reserved slug; (2) create first Admin with invite; (3) seed system roles from templates; (4) record ToS/Privacy/DPA acceptance and version; (5) Admin completes MFA enrollment; (6) ops verifies and flips status to `active`; (7) smoke login with the slug. Break-glass: ops can reset MFA with a dual-control approval, audited.

---

## 6. Proof strategy

### 6.1 Evidence matrix: one proof per §13 item
| §13 | Proof (automated unless noted) | Where it runs |
|---|---|---|
| 1 | `test_tenant_isolation_db.py` (rewritten for real tenants) plus "every table is tenant-scoped or allowlisted" test | CI |
| 2 | Refresh rotation, reuse-detection and old-opaque-token-401 tests | CI |
| 3 | Integration test against an S3-compatible service (e.g. MinIO) plus a check that signed URLs expire and need authZ | CI |
| 4 | Admin sidebar link set equals PRD §3.1 exactly; admin denied execution routes; two-persona parity harness; grep gate for `role_code == "admin"` | CI |
| 5 | Notification list/badge loaded from the API in a browser test; CTA opens the right record | CI (browser) |
| 6 | Browser happy-path suite: client → requisition → candidate → application → pipeline → daily update → approval, with zero console errors | CI (browser) + staging |
| 7 | CORS reject test, 429 test, TLS and HSTS check against staging | Staging script |
| 8 | Restore drill report with timings; backup job alert test | Manual + evidence file |
| 9 | Provisioning runbook executed from scratch by someone who did not write it | Manual + evidence file |
| 10 | Last-admin, wrong-slug and expired-refresh tests | CI |
| 11 | Flag asserted OFF in CI and in the staging pre-flight; routes disabled | CI |
| 12 | Password policy, lockout, MFA gate, session list/revoke, admin force-revoke tests | CI |
| 13 | Contract tests per list endpoint (pagination, sort, filter 400, envelope); response-leak sweep | CI |
| 14 | Concurrent-write 409 test; soft-delete visibility test; hard-delete unreachable test; bucket-report test | CI |
| 15 | `.exe`-as-`.pdf` rejection; EICAR quarantine; oversize rejection | CI |
| 16 | Legal acceptance recorded; export and delete requests end to end; audit rows held 90 days | CI + staging |
| 17 | Pipeline run log showing gated migration; load-test report; alert fire drill; secrets-store inspection | Evidence pack |

### 6.2 Cross-cutting automated gates (added to CI in Phase 1 and tightened later)
- No `ReferenceError` or console error on any of the 101 pages.
- No raw stack trace, SQL text or foreign-tenant id in any error body.
- Migration up and down (or forward-fix) runs on a clean DB.
- Secret scan and dependency scan clean.
- Coverage must not drop on authorization and tenancy modules.

### 6.3 Smoke-test (assessment §3) corrections
The existing checklist needs these fixes before it is used as the acceptance baseline:
1. **Step 1.1** expects a "session cookie". Auth is bearer-only (`get_current_auth_context` rejects cookies). Change to "access + refresh tokens issued".
2. **Stage 3.1** lists the Admin sidebar as "Users, Locations, Roles, Settings, Audit Logs, Reports only". PRD §3.1 also includes dashboards, Notifications, Approvals, Business Titles, Visibility Rules, Work Assignment, Portal Accounts, AI usage and policy, Data Export/Delete. Compare against the PRD list.
3. **Base URL** must be `https://`, not `http://`.
4. **Steps 5.2 and 5.3** stop being "capture the gap" and become real pass/fail checks once Phases 2 and 3 ship.
5. **Add:** an MFA gate check; session revoke; an archived-record visibility check; a bucket-report check; a 409 conflict check.
6. **Rule:** Stages 0–5 must pass 100% with **no** known-gap waivers for the launch-blocker items.

---

## 7. Go/no-go checklist (Phase 7)

All launch-blocker rows must be checked, with a link to evidence.

- [ ] §13 #1 isolation re-proven on real tenants
- [ ] #2 JWT and rotating refresh live; opaque sessions retired and purged
- [ ] #3 object storage private, signed URLs, tenant-prefixed keys
- [ ] #4 Admin sidebar matches PRD §3.1; no role-name authorization anywhere
- [ ] #5 notifications live from the API with working CTAs
- [ ] #6 core modules pass the browser happy-path suite against live data
- [ ] #7 TLS, HSTS, CORS allowlist, rate limits verified on staging
- [ ] #8 environments separated; backups running; restore drill passed (audit-retention job scheduled)
- [ ] #10 last-admin, wrong-slug, expired-refresh guardrails pass
- [ ] #11 AI flag confirmed OFF in staging and production
- [ ] #12 password policy, MFA required for every active Admin, session list/revoke and force-revoke
- [ ] #13 API contract sweep complete
- [ ] #14 soft-delete (narrowed scope), optimistic locking and bucket reporting live
- [ ] #15 MIME/size validation and malware scan gate live
- [ ] #16 legal pages versioned and recorded; privacy export and delete work
- [ ] #17 gated CD pipeline, load test at 3× peak, SLOs and alerts, managed secrets
- [ ] Ops provisioning runbook executed successfully by a second person
- [ ] Residual risks signed off by the product owner (list attached)

---

## 8. Document amendments (Phase 0)

### 8.1 PRD
| Section | Change |
|---|---|
| §3.2 | `pipeline.board.read` → `pipeline.read.summary`; add rows for `pipeline.stage.reopen` and the Business Titles code; state that the Admin seed equals the Admin column exactly |
| §3 / §11 | Add the explicit **platform-ops exception** for cross-tenant footprint (D-04); Platform ops gets a defined, audited credential |
| §4.8 / §4.14 | Offer threshold: default 0 (all offers need approval); explicit currency note |
| §9.0, §11, §13 #14 | Soft-delete scope narrowed per D-07 (candidates, clients, users, company); requisitions and applications use status lifecycle, close and reopen; hard delete ops-only |
| §13 #9 | "Ops provisioning at launch; self-serve before any public signup" |
| §13 #16 | Acceptance gate applies to self-serve; ops-provisioned tenants have acceptance recorded at provisioning; privacy endpoints and legal docs remain required |
| §4.7 / §4.13 | Reports and dashboards read **metric buckets**, never raw stage labels |
| §7 | Replace "current prototype may still use opaque sessions" with the cutover plan |
| §8.1 | State `tenant_id` on all operational roots; branch-derived tenancy retired |

### 8.2 RBAC spec
- §2.3 item 4: physical `tenants` is no longer deferred.
- §3.1: delete the `offer_ctc_max` reference.
- §0 and §5: "5 inert references", not 17 or 3.
- §2.2: Admin-bypass deviation note resolved by D-03 and Phase 2.5.

### 8.3 Assessment
Apply §1 of this plan; fix the arithmetic (it lists 10 blocker items but says 9); remove the stale line numbers.

---

## 9. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Removing the admin bypass locks admins out | High | Ship the seed migration and the CI "admin passes control-plane routes via grants" test **in the same change** (2.5 + 2.6); rehearse on staging |
| Tenant backfill splits a company | High | Fail-closed on missing mapping (I-5); staging uses a fresh seed |
| JWT cutover disrupts staged users | Low | No production users; one-time re-login |
| Frontend foundation uncovers more missing pieces | Medium | Phase 1 sweep of all 101 pages; budget 20% slack in Phase 1 |
| Malware scanner choice delays Phase 4 | Medium | Adapter interface lets scanning be added behind the gate; use a test scanner in CI |
| Legal text arrives late | Medium | Engineering builds the mechanism; legal pages are placeholders until counsel signs off, and launch is blocked until then |
| No peak-user number | Medium | Load test cannot be sized; closing I-4 early |
| Reports change counts after the bucket fix | Medium | Communicate before and after; the 5 live labels currently go missing, so the fix raises numbers |
| Footprint exposure during the transition | Medium | Disable the Tenant Admin route in Phase 2.8 before any staging exposure |

---

## 10. Immediate next actions

1. **You:** answer I-1 to I-7 (§2.3). I-5 (branch mapping) and I-2 (cloud) unblock the most.
2. **You:** confirm or override D-03, D-04, D-07 and D-13 in §2.2.
3. **Me, once confirmed:** produce PRD v2, assessment v2 and spec v2 (Phase 0), then detailed tickets for Phase 1 with acceptance criteria.
