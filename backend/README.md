# FastAPI backend

Run and operate the API here. Product requirements: [`../docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`](../docs/PRODUCT_REQUIREMENTS_DOCUMENT.md).

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configure environment (MSSQL connection and secrets) via `.env` / settings as used by `app.core.config`.

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

## Tests

```bash
.venv/bin/python -m pytest
```

## Demo admin (after seed)

- Email: `admin@executiveconnection.com`
- Password: `admin123`
