# RecruitOps

Multi-tenant recruitment operations system (frontend + FastAPI + MSSQL).

Product behavior, roles, modules, APIs, security, and production-ready criteria:

→ [`docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`](docs/PRODUCT_REQUIREMENTS_DOCUMENT.md)

## Project layout

| Path | Role |
|------|------|
| `frontend/` | Static HTML pages, shared JS/CSS, Node static server + `/api` proxy |
| `backend/` | FastAPI application |
| `docs/` | PRD, RBAC spec, readiness assessment, execution plan, phase status |
| `scripts/` | Idempotent SQL migrations (`00X_*.sql`) and utility scripts |
| `tools/ci/` | CI gates (contract check, undefined-identifier check, asset check, runner) |

## Guided product tour (onboarding)

`frontend/shared/tour.js` is a self-contained, client-side spotlight-ring +
tooltip-card tour engine — no backend or DB involved. It auto-starts the
first time a user who already has access opens one of the 22 registered
modules (Role Dashboard, Requisitions, Candidates, Pipeline Board, Approvals
Inbox, Users, Roles, Permissions Editor, Visibility Rules, Reports, Company
Settings, Clients, Offers, Interviews, Daily Review, Daily Update
Submission, Follow-Ups, Audit Log, Data Export & Delete Requests, Portal
Accounts, Hiring Stages, Work Assignment, My Profile), tracked per user per
module in `localStorage`, with a "Replay tour" button always available.
Because it only ever runs on a page the user already reached, it needs no
RBAC logic of its own — the page's existing permission gate controls who
ever sees a given tour. To add a module, add one entry to `TOUR_REGISTRY` in
`tour.js` and one `<script src="../shared/tour.js">` tag to that page.

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

Or start both with `./start.sh` (API on :8000, UI on :4174).

## Checks (run in CI on every PR — `.github/workflows/ci.yml` (shipped as `tools/ci/github-workflow-ci.yml` — move it there to enable))

```bash
# Backend: throwaway SQL Server container → schema → seed → pytest
cd backend && DB_PORT=1434 ./scripts/run_tests_ci.sh

# Frontend: syntax, undefined globals, API contract, assets,
# browser sweep of every page (admin + recruiter), end-to-end UI flows
tools/ci/run_frontend_checks.sh
```

The frontend checks run against `frontend/tests/mock-api-server.js`, a mock
generated from the backend's OpenAPI schema: any page that calls a path,
method or request body the backend would reject fails the build.

### Demo login (seeded DB)

See `backend/README.md` for credentials after seeding.
