# FastAPI Backend

This folder is the active Python/FastAPI backend for the recruitment system.

## Scope

- Active FastAPI backend for the current live prototype
- Integrated with the lightweight frontend runtime in `frontend/`
- MSSQL-first database workflow
- Module-wise API routing for the MVP domains

## What Exists

- FastAPI application bootstrap
- permissive CORS setup for the live prototype
- settings and environment management
- MSSQL connection URL builder
- DB health check service
- SQL bootstrap manifest and runner foundation
- module-wise API router structure for:
  - locations
  - users
  - roles
  - clients
  - requisitions
  - candidates
  - pipeline
  - daily updates
  - dashboards
  - notifications
  - auth
  - permissions

## Implemented Modules

- `auth`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
- `permissions`
  - `GET /api/v1/permissions/me`
- `locations`
  - list, create, update
- `roles`
  - list, create, update, permission assignment
- `users`
  - list, create, update, credential reset
- `clients`
  - list, create, detail, update, contacts
- `requisitions`
  - list, create, detail, update, status, assignments
- `candidates`
  - list, create, detail, update, documents, duplicate decision, finalize
- `pipeline`
  - board, application detail, stage move, history
- `daily-updates`
  - list, create, detail
- `dashboards`
  - role summary, my-work summary
- `notifications`
  - list, mark-read

## Current Frontend Integration

The active frontend runtime in `frontend/` now calls this backend directly.

Current live pages using FastAPI endpoints:

- `frontend/pages/login.html`
  - `POST /api/v1/auth/login`
  - `GET /api/v1/permissions/me`
- `frontend/pages/dashboard.html`
  - `GET /api/v1/auth/me`
  - `GET /api/v1/permissions/me`
  - `GET /api/v1/dashboards/role`
  - `GET /api/v1/dashboards/my-work`
- `frontend/pages/users.html`
  - `GET /api/v1/users`
  - `GET /api/v1/roles`
  - `GET /api/v1/locations`
- `frontend/pages/locations.html`
  - `GET /api/v1/locations`
- `frontend/pages/clients.html`
  - `GET /api/v1/clients`
  - `GET /api/v1/locations`
- `frontend/pages/requisitions.html`
  - `GET /api/v1/requisitions`
  - `GET /api/v1/locations`
- `frontend/pages/candidates.html`
  - `GET /api/v1/candidates`
- `frontend/pages/pipeline.html`
  - `GET /api/v1/pipeline/board`
  - `GET /api/v1/locations`
- `frontend/pages/daily-updates.html`
  - `GET /api/v1/daily-updates`
  - `POST /api/v1/daily-updates`
  - `GET /api/v1/requisitions`
- `frontend/pages/notifications.html`
  - `GET /api/v1/notifications`
  - `PATCH /api/v1/notifications/{notification_id}/read`

## Planned Build Direction

1. Validate full live frontend flows against a running seeded database
2. Port any remaining DB bootstrap commands from the current backend flow
3. Tighten permission enforcement around create, update, and exception actions
4. Add broader endpoint and integration tests where feasible
5. Validate the live prototype against the MSSQL schema and seed scripts

## Run Shape

Example commands once dependencies are installed:

```bash
uvicorn app.main:app --reload --port 8000
python -m app.scripts.bootstrap_db
python -m app.scripts.db_status
```

## Current Source SQL

The canonical schema is `backend/db/schema.sql` (60 tables; regenerate from the live database with `backend/scripts/dump_schema.py`). CI replay uses `backend/scripts/run_tests_ci.sh` with seeding from `backend/scripts/seed_ci.py`. The original planning scripts (`scripts/001_*`–`004_*`) were superseded and removed.
