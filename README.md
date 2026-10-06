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
