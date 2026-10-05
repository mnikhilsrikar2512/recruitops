# Staging smoke test — v2 (re-baselined, plan 1.8)

Replaces assessment §3. Applies the §6.3 corrections: bearer tokens (not cookies),
`https://` base URL, the PRD §3.1 admin sidebar, and **no known-gap waivers** on
launch-blocker items (a check that fails because a later phase hasn't shipped is
recorded as FAIL with the phase number — it is not waived).

## Setup

1. **Fresh database** (decision D-12 — never a copy of dev): create an empty DB, apply
   `backend/db/schema.sql` and the `scripts/00X_*.sql` migrations, then seed:
   `cd backend && STAGING_PASSWORD='…' .venv/bin/python scripts/seed_staging.py`
2. Start the stack (`./start.sh` locally; containers in Phase 6).
3. Run the automated half:
   - API: `python tools/ci/live_smoke.py --base <origin> --password "$STAGING_PASSWORD"`
   - Browser: `python frontend/tests/page_sweep.py --base <origin> --live --email <persona> --password …`
     (once per persona below)

## Personas (from `seed_staging.py`)

| Persona | Account | Tenant |
|---|---|---|
| **TA** Admin (control plane) | `ci.admin@recruitops-test.com` | all (today's global admin) |
| **MA** Manager, tenant A | `manager@northwind-staging.test` | Northwind Staffing — Bengaluru |
| **RA** Recruiter, tenant A | `recruiter@northwind-staging.test` | Northwind Staffing — Bengaluru |
| **MB / RB** tenant B | `manager@` / `recruiter@contoso-staging.test` | Contoso Talent — Hyderabad |

Until Phase 2 adds a `tenants` table, a tenant is a branch with everything scoped to it.

## Checklist

`auto` = covered by `live_smoke.py` (step ids match its output) or the browser sweep.

### Stage 0 — Pre-flight
| # | Step | Expected | How |
|---|---|---|---|
| 0.1 | `GET /api/v1/health` | 200 | auto |
| 0.2 | CI green on the deployed commit | backend + frontend jobs pass | CI |
| 0.3 | AI flag | `APP_ENV=staging` → `GET /api/v1/agents/` returns 404 | manual |
| 0.4 | DB is a fresh seed | personas above exist; no dev data | manual |

### Stage 1 — Auth & session
| # | Step | Expected | How |
|---|---|---|---|
| 1.1 | TA logs in | 200, **bearer token** issued, lands on Home | auto + sweep |
| 1.2 | MA / RA / RB log in | 200 | auto |
| 1.3 | Wrong password | 401, clean body, no stack trace; UI shows "Authentication Failed" | auto + flows |
| 1.4 | Logout, replay the old token | 401 | auto |
| 1.5 | Permission sync | `/permissions/me` returns grants; UI re-syncs on focus / 5 min | auto |
| 1.6 | Account lockout after repeated failures | 429 / locked | **FAIL until Phase 3.5** |
| 1.7 | Access + refresh tokens; expired refresh forces re-login | — | **FAIL until Phase 3.2** |
| 1.8 | MFA required for every active Admin | — | **FAIL until Phase 3.6** |
| 1.9 | Session list / revoke | — | **FAIL until Phase 3.3** |

### Stage 2 — Tenant isolation
| # | Step | Expected | How |
|---|---|---|---|
| 2.1 | RA lists requisitions | sees tenant A only; RB sees tenant B only | auto |
| 2.2 | RA requests a tenant-B requisition by id; pipeline board | 403/404, nothing from B | auto |
| 2.3 | Error bodies | no foreign-tenant ids, no SQL, no traceback | auto |
| 2.4 | Wrong tenant slug at login | clean 404/400 | **FAIL until Phase 2.4** |

### Stage 3 — RBAC & navigation
| # | Step | Expected | How |
|---|---|---|---|
| 3.1 | TA sidebar | exactly the PRD §3.1 Admin list: dashboards, Users, Locations, Roles, Business Titles, Visibility Rules, Work Assignment, Portal Accounts, Notifications, Approvals, Reports, Settings, Audit Logs, AI usage/policy, Data Export/Delete | manual (**FAIL until Phase 2.5–2.6**: admin currently sees execution pages) |
| 3.2 | RA sidebar | execution pages per grants; no control plane | sweep (recruiter) |
| 3.3 | RA deep-links to `user-management.html` | Access Denied | sweep |
| 3.4 | RA calls `/users/`, `POST /roles/` | 403 | auto |
| 3.5 | Two non-admins with identical grants | identical UI and API results | manual (automated in Phase 2.9) |

### Stage 4 — Core happy path
| # | Step | Expected | How |
|---|---|---|---|
| 4.1 | Client → requisition → candidate → application | 201s; INR rendering | auto + flows |
| 4.2 | Stage move; approval decided | 200s; approvals list updates | auto + flows |
| 4.3 | Notification action | real copy; CTA opens the record; badge count | auto (list) + manual (CTA) |
| 4.4 | Duplicate candidate (same email) | flagged | manual |
| 4.5 | Every page as TA and RA | no console errors, API rows render | sweep (`--live`) |

### Stage 5 — Guardrails (PRD §13 item 10)
| # | Step | Expected | How |
|---|---|---|---|
| 5.1 | Deactivate the last active admin | 400 with explicit message | manual |
| 5.2 | Password shorter than 12 | rejected | **FAIL until Phase 3.5** (8 today) |
| 5.3 | 409 on concurrent edit | second writer gets 409 + fresh row | **FAIL until Phase 4.3** |
| 5.4 | Archived record hidden | not listed / 404 | **FAIL until Phase 4.4** |

### Stage 6 — Files & AI
| # | Step | Expected | How |
|---|---|---|---|
| 6.1 | Upload a valid PDF résumé | 201; retrievable by the owning tenant only | manual |
| 6.2 | `.exe` renamed `.pdf`; EICAR file | rejected / quarantined | **FAIL until Phase 4.2** |
| 6.3 | AI agents | off (404) on staging | manual (0.3) |

### Stage 7 — Ops & error shape
| # | Step | Expected | How |
|---|---|---|---|
| 7.1 | Invalid payload | 422 `{detail, errors}`, no traceback | auto |
| 7.2 | Large list | `meta {page, page_size, total}` | auto |
| 7.3 | CORS from a disallowed origin | origin not echoed | auto |
| 7.4 | TLS + HSTS + HTTP→HTTPS | enforced | **FAIL until Phase 3.8 / 6** |
| 7.5 | Backups + restore drill | documented, timed | **FAIL until Phase 6.6** |

## Sign-off rule

Stages 0–5 must pass 100%. Rows marked **FAIL until Phase N** are launch blockers owned
by that phase; they are tracked, not waived. The Phase 1 bar is: every `auto` row passes
on a freshly seeded environment.
