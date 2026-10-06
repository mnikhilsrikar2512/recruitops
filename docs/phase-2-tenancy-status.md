# Phase 2 — Tenancy (companies as the isolation root): status

**Date:** 2026-10-06 · **Plan:** `recruitops-production-readiness-execution-plan.md` §4 Phase 2
**Decisions applied:** `decisions-2026-10-06.md` (I-5, D-02, D-03, D-04, Q5)
**Branch:** `phase-2-tenancy` (on top of `phase-1-foundation`)

## Model

- A **company** (`dbo.tenants`) is the tenant. It owns a head office and branches.
- `tenant_id` lives on offices (`dbo.branches` + its mirror `dbo.locations`),
  `dbo.users` and `dbo.roles`. Everything else (clients, requisitions,
  applications, approvals, meetings, daily updates, workflow items, …) already
  hangs off an office, so its company is derived through the office.
  Candidates are global identity records; a candidate is "in" a company when the
  company created it, it sits on one of its offices, or it has an application
  on one of its requisitions.
- `roles.tenant_id IS NULL` = shared **system role** (the Admin template),
  readable by every company, editable by none. Every other role is private to
  one company; codes are unique per company and never collide with a system code.
- Office codes are unique **per company** (two companies may both have `HYD`).
- A company admin (`role_code = admin`) reaches every office of **their own**
  company and nothing outside it. Everyone else: their own office.
- A company whose status is not `active` cannot sign in, and live sessions stop.

## What changed

| Plan item | Delivered |
|---|---|
| 2.1 schema | `scripts/010_tenants.sql` — tenants table, `tenant_id` + FKs + indexes, per-company office/role code uniqueness, idempotent backfill (everything that exists = one "Default Company"), self-verifying. Applied by `create_staging_db.py` and CI. |
| 2.2 backfill | Same migration; `backend/scripts/apply_migration.py` applies it to the dev DB **with a server-side backup first**. |
| 2.3 scope every route | `app/services/scope.py` is the single place that decides reach. Every list query carries `AND (:tenant_id IS NULL OR <office> IN <company offices>)` (approvals, clients, daily updates, interviews, meetings, offers, pipeline, requisitions, users, workflow actions, candidates, locations, roles, dashboards, reports). Direct-id guards (`require_record_in_location`, pipeline/candidate/workflow access checks) answer **404** outside the company. Every write payload's references (`*_user_id`, `client_id`, `requisition_id`, contacts, offices, matched candidate) are checked to be inside the caller's company (`scope.assert_payload_refs_in_company`). Users/roles/offices are created inside the caller's company. Candidate footprint is limited to the caller's company (D-04). |
| 2.6 (part) | CI gate `tools/ci/admin_bypass_gate.py` (runs in `run_frontend_checks.sh`): no new `role_code == "admin"` checks; the 10 remaining are permission/last-admin checks owned by 2.5. |
| seeds | `seed_ci.py` puts the CI database in one company. `seed_staging.py` builds **two real companies** (Northwind, Contoso), each with its own company admin (`admin@<domain>`) who creates the rest through the API. |
| tests | `tests/test_company_isolation_db.py` (second company + its admin; lists, direct ids, cross-company references, private roles, read-only system roles, suspended company). `live_smoke.py` Stage 2b: 7 company-admin isolation checks. The admin browser sweep now signs in as the Northwind company admin. |

## Remaining in Phase 2

| Item | Notes |
|---|---|
| 2.4 login | Email-only login already finds the company (D-02); signup is Phase 5. |
| 2.5 + 2.6 | **Done (see below).** |
| AI agents | **Done:** every read tool takes the caller's company and answers "not found" outside it; company-wide callers read every office of their own company. |
| Portal accounts, master data, company profile | **Done (migration 012):** see below. |
| `dbo.locations` mirror | New offices are mirrored with the same id via `IDENTITY_INSERT`, which needs ALTER permission on the table. Collapse the two tables before production DB credentials are least-privilege (Phase 6). |
| 2.8 / 2.9 | Footprint is tenant-only now; the parity harness is next. |

## Verify

```bash
bash tools/ci/phase1_verify.sh          # fresh staging DB, applies 008–010, seeds 2 companies
```

Dev database (once, deliberately — your launchd backend needs it after pulling this branch):

```bash
cd backend && .venv/bin/python scripts/apply_migration.py 010_tenants.sql
```

## Result of the verification run (2026-10-06, fresh `recruitops_staging`, commit `d84586c`)

| Check | Result |
|---|---|
| Backend suite | **417 passed**, 3 skipped (incl. `test_company_isolation_db.py`) |
| Staging seed | 2 real companies (Northwind, Contoso), each: company admin + manager + recruiter, 2 clients, 2 requisitions, 3 applications, 2 approvals |
| Live API smoke | **38/38** (incl. 7 company-admin isolation checks) |
| Browser sweep, Northwind company admin | 101 pages, 0 failing |
| Browser sweep, Northwind recruiter | 101 pages, 0 failing |

Fixed on the way: `UQ_users_employee_code` treats NULL as a value (SQL-inserted admins now get codes);
login tolerates records without a tenant status; the Admin role answers 403 "System roles are read-only"
to company admins (stricter than the old 409).

## 2.5 + 2.6 — Admin is the control plane, by grant (D-03)

| Item | Delivered |
|---|---|
| No role-code bypass | `require_permissions` / `require_any_permission`, the agents guards and the frontend (`hasPermission`, sidebar, page gate, action/form gates) no longer treat `role_code == "admin"` as "allow everything". Every user, admins included, passes routes by grant. |
| Company-wide reach is a grant | New code `scope.company`. `api/deps.get_current_auth_context` resolves it per request; `services/scope.is_company_wide` reads that flag. |
| Admin template | `app/core/rbac.py` `ADMIN_PERMISSION_CODES` (39 codes: users, offices, roles, settings, approvals, dashboards/reports, notifications, portal accounts, work assignment, governance, `scope.company`) = PRD §3.2 Admin column. `scripts/011_admin_seed.sql` adds missing catalog rows and **resets** the Admin role to exactly that set; the API refuses to change it (409) and companies can't edit system roles (403). |
| Seeds | CI admin = Admin template **plus** a CI-only "CI Full Access" role so DB tests can drive recruiting routes. Staging: the company admin creates roles and users only; the manager creates clients, requisitions, approvals; the recruiter adds candidates. |
| Tests | `test_admin_seed.py` (SQL ↔ code template, no execution codes, no bypass with a real engine, company-wide follows the grant). `test_company_isolation_db.py`: a pure company admin passes control-plane routes and is **403** on candidates/requisitions/clients/pipeline. Live smoke Stage 2c: same checks against staging. Mock sweep adds a `full` persona (every page with data) and the admin persona must reach the control-plane pages. Unit-test stub admins keep full access through a conftest shim that only applies to MagicMock engines. |
| CI gate | `admin_bypass_gate.py` allow-list is down to identity checks only (last-admin protection, the hand-built-context fallback in `scope.py`). |

**Dev database:** apply `011_admin_seed.sql` (`apply_migration.py`). After it, the dev Admin
login can no longer open recruiting pages — by design (D-03). To keep recruiting as that
user, give them an execution role as a second office role (like the CI admin).

Known leftover: `services/daily_updates.py` still lets a submitter whose primary role is
`admin` skip the same-office/linked-requisition checks; admins no longer hold
`daily_update.create_main`, so it is unreachable, and it goes with the Phase 4 cleanup.

### Result of the 2.5/2.6 verification run (2026-10-06, commit `b738580`)

| Check | Result |
|---|---|
| Backend suite | **423 passed**, 3 skipped (incl. `test_admin_seed.py`, pure-admin control-plane/denied checks) |
| Staging seed | built by company admin (roles, users) → manager (clients, requisitions, approvals) → recruiter (candidates) |
| Live API smoke | **48/48** (incl. Stage 2c: admin holds `scope.company`, 200 on control-plane routes, 403 on execution routes) |
| Browser sweep, Northwind company admin | 101 pages, 0 failing (execution pages show Access Denied, control-plane pages load) |
| Browser sweep, Northwind recruiter | 101 pages, 0 failing |

## 2.3 completion — settings, portal accounts, agents, coverage gate, parity harness

| Item | Delivered |
|---|---|
| Company profile | `company_entities.tenant_id`: one profile/letterhead/logo **per company** (before: one shared row every company edited). Created from the company name on first use. Logo URL carries the profile id (`/settings/logo?v=<id>`). |
| Pick-lists (master data) | `master_data_values.tenant_id`: NULL rows are shared templates; a company gets its own editable copy of a list the first time it opens it; codes unique per company. Editing a template or another company's value is "not found". |
| Portal accounts | Lists, availability and usage summary filtered to the caller's company; every `/{portal_account_id}` route 404s outside it; payload users/offices checked. |
| AI agent tools | Tenant-aware (see table above). |
| Coverage gate | `app/core/tenancy.py` classifies all 64 tables (company root, via office, via parent, via user, or shared with a reason); `tests/test_tenancy_coverage.py` fails when a table is added without a line or a named column is missing. |
| Parity harness | `tests/test_rbac_parity_db.py`: two users with identical grants in the same office get identical results on 11 shared lists and identical permissions/pages/scopes. |

Remaining Phase 2 items are closed below.

### Result of the 2.3-completion run (2026-10-06, commit `fda0003`)

Backend **438 passed**, 3 skipped (incl. tenancy coverage, parity harness, per-company profile) · live smoke **48/48** · browser sweeps admin and recruiter 101/101 clean · migrations 008–012 on a fresh staging database.

## 2.7, 2.8 and the exit gate

| Item | Delivered |
|---|---|
| 2.7 catalog drift | PRD §3.2: `pipeline.board.read` → `pipeline.read.summary`; rows added for `pipeline.stage.reopen` (planned), `scope.company`; Business Titles named under `settings.write`. New PRD §3.3 maps all 61 finer implementation codes to their §3.2 row. `tests/test_permission_catalog_prd.py` fails when a route, page gate or role template uses a code with no row. |
| 2.8 footprint | Resolved by D-04: the candidate footprint is limited to the caller's own company (company admins only). A cross-company view, if ever needed, is a platform-ops surface (Phase 6 ops tooling), not part of the product API. |
| Admin sidebar == PRD §3.1 | `tests/test_admin_sidebar_prd.py`. Changes: Company Settings (`tenant-setup`) added to the sidebar (PRD "tenant Settings"); Pipeline Analytics removed from the admin base (execution data). Not built yet, and listed in the test for when they ship: AI usage & policy, Audit Log, Data Export/Delete Requests. |

### Phase 2 exit gate

| Gate | Status |
|---|---|
| Dual-company denial suite green with real `tenant_id` | `test_company_isolation_db.py`, live smoke 2b/2c |
| Admin sidebar == PRD §3.1 exactly; admin denied every execution route | `test_admin_sidebar_prd.py`; `test_company_isolation_db.py` + live smoke 2c (403s) |
| Identical grants → identical UI and API results | `test_rbac_parity_db.py` |
| Wrong login returns a clean error (email-only login, D-02) | live smoke 1.3 (401, no stack trace) |
| No `role_code == "admin"` authorization (CI grep gate) | `admin_bypass_gate.py` (identity checks only) |

Rest of the shared-table enforcement (pipeline templates, report locks, transfer/access requests) is tracked in `app/core/tenancy.py` and applied when those routes are built.
