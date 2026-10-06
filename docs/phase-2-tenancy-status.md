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
| 2.5 + 2.6 | Replace the role-code admin bypass in `require_permissions` with a seeded Admin permission set + `scope.company` permission; frontend admin bypass. The gate's allow-list must reach 0 (except `scope.py`). |
| AI agents | Agent read tools are office-scoped for everyone (company admins included) until the tools are tenant-aware. AI is off outside dev (D-10). |
| Portal accounts, master data | Still global catalogues; decide per-company vs shared before launch. |
| `/auth/me` scope labels | Still say `global` for admins (cosmetic; 2.5). |
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
