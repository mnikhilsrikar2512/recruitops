# RecruitOps

**Multi-tenant recruitment operations platform** — requisitions, candidate
pipelines, interviews, offers, and reporting for recruiting teams, with
role-based access control fine-grained enough that one company's admin can
configure exactly who on their team sees and does what.

Built as a FastAPI backend over Microsoft SQL Server, with a static,
dependency-light HTML/JS frontend. No framework lock-in, no build step
required to run it locally.

For full product behavior, roles, modules, APIs, security posture, and
production-readiness criteria, see:

→ [`docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`](docs/PRODUCT_REQUIREMENTS_DOCUMENT.md)

## What's in here

- **Multi-tenant by design** — every company's data is isolated at the data
  layer, not just the UI.
- **Granular, role-based permissions** — access is controlled per action
  (e.g. creating a requisition vs. reading one are separate grants), assigned
  per role, and fully admin-configurable. See
  [`docs/pipeline-rbac-architecture-spec.md`](docs/pipeline-rbac-architecture-spec.md).
  Visibility Rules layer on top to mask specific sensitive fields (like
  margin or bill rate) from roles that shouldn't see them, independent of
  page-level access.
- **Full recruiting lifecycle** — clients, requisitions, candidates, pipeline
  stages, interviews, offers, approvals, daily activity tracking, and
  reporting.
- **Guided onboarding** — a built-in product tour walks new users through
  each module the first time they open it. See
  [Guided product tour](#guided-product-tour-onboarding) below.
- **CI-gated** — every pull request runs backend tests against a real,
  throwaway SQL Server instance and a full frontend contract/browser suite
  before it can merge. See [Checks](#checks-ci) below.

## Project layout

| Path | Role |
|------|------|
| `frontend/` | Static HTML pages, shared JS/CSS, Node static server + `/api` proxy |
| `backend/` | FastAPI application |
| `docs/` | PRD, RBAC spec, readiness assessment, execution plan, phase status |
| `scripts/` | Idempotent SQL migrations (`00X_*.sql`) and utility scripts |
| `tools/ci/` | CI gates (contract check, undefined-identifier check, asset check, runner) |

## Company Overview permissions (read-only oversight) + extra permission grants

The built-in **Admin** role is deliberately control-plane only (users,
offices, roles, settings, approvals, reports) — it does not include
day-to-day read access to individual requisitions, candidates, clients,
offers, interviews, etc. **Company Overview** is a read-only bundle that
fills that gap:

`candidate.read`, `client.read`, `client.contact.read`,
`requisition.read`, `offer.read`, `interview.read`, `meeting.read`,
`pipeline.read.summary`, `pipeline.read.detail`,
`pipeline.stage.history.read`, `daily_update.read`,
`workflow_action.read`, `assignment.read`, `portal.read`.

No create/update/decide/assign code is included — this bundle can see
everything, change nothing. It's defined once as
`COMPANY_OVERVIEW_PERMISSION_CODES` in `backend/app/core/rbac.py`.

**A user still holds exactly one role** — the data model doesn't support
stacking two concurrent roles, and that's intentional. What changed is
that **extra permissions can now be granted directly to a user, on top of
their one role**, via `PUT /users/{user_id}/extra-permissions` (and read
back with the matching `GET`), backed by `dbo.user_extra_permissions` (a
table that already existed in the schema but was unused until now — see
`backend/app/repositories/auth.py`'s `list_resolved_permissions`, which
unions it in alongside the user's role permissions). This is a strict
replace-all set, same semantics as `PUT /roles/{role_id}/permissions`: it
only adds permission reach, and never changes the user's displayed role,
title, or hierarchy level.

So an admin who wants both control-plane access and full read-only
day-to-day visibility doesn't need a second role or a second login — grant
them the Company Overview codes as extra permissions on their one Admin
account. In the UI, this is on the **User Detail** page (reachable from
**Users**): a signed-in Admin sees an "Additional permissions" card there
with a toggle for Company Overview. Via the API it's the same
`PUT /users/{user_id}/extra-permissions` call the toggle makes.
`backend/scripts/seed_staging.py` demonstrates both paths for each seeded
tenant: a standalone "Company Overview" role with its own demo login
(`overview@<domain>`), and the bundle granted directly to the tenant's
admin as extra permissions.

## Guided product tour (onboarding)

`frontend/shared/tour.js` is a self-contained, client-side spotlight-ring +
tooltip-card tour engine — no backend or database involved. It auto-starts
the first time a user who already has access opens one of the 22 registered
modules:

Role Dashboard, Requisitions, Candidates, Pipeline Board, Approvals Inbox,
Users, Roles, Permissions Editor, Visibility Rules, Reports, Company
Settings, Clients, Offers, Interviews, Daily Review, Daily Update
Submission, Follow-Ups, Audit Log, Data Export & Delete Requests, Portal
Accounts, Hiring Stages, Work Assignment, My Profile.

Each module's tour is tracked per user in `localStorage`, and a "Replay
tour" control is always available in the top bar. Because the tour only
ever runs on a page the user already reached, it carries no RBAC logic of
its own — the page's existing permission gate already decides who ever
sees it.

To add a module: add one entry to `TOUR_REGISTRY` in `tour.js` (a short list
of `{selector, title, body}` steps) and one `<script src="../shared/tour.js">`
tag to that page. Nothing else needs to change.

## Run locally

### Backend (port 8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # then set DB_* for your SQL Server
# Configure MSSQL / env per backend/README.md
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (port 4174)

```bash
cd frontend
API_PORT=8000 PORT=4174 node server.js
```

Open: [http://127.0.0.1:4174/pages/login.html](http://127.0.0.1:4174/pages/login.html)

Use the Node server (not `python -m http.server`) so `/api/` proxies to FastAPI.

Or start both at once with `./start.sh` (API on :8000, UI on :4174).

### Demo login (seeded DB)

See [`backend/README.md`](backend/README.md) for credentials after seeding.

## Checks (CI)

Every pull request runs the same checks defined in
[`.github/workflows/ci.yml`](.github/workflows/ci.yml), which you can also
run locally:

```bash
# Backend: throwaway SQL Server container → schema → seed → pytest
cd backend && DB_PORT=1434 ./scripts/run_tests_ci.sh

# Frontend: syntax, undefined globals, API contract, static assets,
# browser sweep of every page across personas, end-to-end UI flows
tools/ci/run_frontend_checks.sh
```

The frontend checks run against `frontend/tests/mock-api-server.js`, a mock
generated from the backend's OpenAPI schema: any page that calls a path,
method, or request body the backend would reject fails the build.

## Documentation

| Doc | Covers |
|-----|--------|
| [`docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`](docs/PRODUCT_REQUIREMENTS_DOCUMENT.md) | Product behavior, roles, modules, APIs, security, production-readiness criteria |
| [`docs/pipeline-rbac-architecture-spec.md`](docs/pipeline-rbac-architecture-spec.md) | RBAC and pipeline architecture |
| [`docs/production-readiness-assessment.md`](docs/production-readiness-assessment.md) | Production-readiness assessment |
| [`docs/recruitops-production-readiness-execution-plan.md`](docs/recruitops-production-readiness-execution-plan.md) | Execution plan and phase tracking |
| [`docs/runbooks/`](docs/runbooks) | Operational runbooks |
| [`backend/README.md`](backend/README.md) | Backend setup, configuration, and demo credentials |
