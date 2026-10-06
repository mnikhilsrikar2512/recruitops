# FastAPI backend

Run and operate the API here. Product requirements: [`../docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`](../docs/PRODUCT_REQUIREMENTS_DOCUMENT.md).

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # runtime only: requirements.txt
cp .env.example .env                  # then fill in DB_* (see comments inside)
```

Configure environment (MSSQL connection and secrets) via `.env` / settings as used by `app.core.config`.
`APP_ENV=staging|production` refuses to boot with a wildcard or `http://` `CORS_ORIGINS`,
an empty `DB_PASSWORD`, or `AI_ENABLED=true` (`validate_settings()`); in those
environments the agents API answers 404 (AI is off at launch, decision D-10).

## Run API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health: `GET http://127.0.0.1:8000/api/v1/health`

## Frontend proxy

From `frontend/`:

```bash
API_PORT=8000 PORT=4174 node server.js
```

Do not use `python -m http.server` for the UI (no `/api` proxy).

## Database

- Canonical schema: `db/schema.sql`
- Status: `python -m app.scripts.db_status`
- Do not re-run `python -m app.scripts.bootstrap_db` against a live database unless you intend to recreate schema
- CI seed: `scripts/seed_ci.py` (see `scripts/run_tests_ci.sh`)
- Staging/demo seed: `scripts/seed_staging.py` — two isolated tenants with manager and
  recruiter personas (password `$STAGING_PASSWORD`, default in the script); run on a
  fresh database only, then `../tools/ci/live_smoke.py` (see `../docs/staging-smoke-test.md`)
- Idempotent migrations: repo-root `scripts/00X_*.sql` — run
  `scripts/007_grant_ai_permissions.sql` once against databases created before
  the agents feature so non-admin roles can be granted AI agent access (see
  `scripts/README.md`)

### AI agent permissions

Non-admin roles need `ai.use` plus the per-agent `ai.agent.*` codes (granted via
Admin → Roles, the CI seed, or migration `007`); details in
[`scripts/README.md`](scripts/README.md#ai-agent-permissions-ai).

## Tests

```bash
.venv/bin/python -m pytest
```

## Demo admin (after seed)

- Email: `admin@executiveconnection.com`
- Password: `admin123`
