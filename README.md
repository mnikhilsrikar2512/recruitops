# RecruitOps

Multi-tenant recruitment operations system (frontend + FastAPI + MSSQL).

Product behavior, roles, modules, APIs, security, and production-ready criteria:

→ [`docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`](docs/PRODUCT_REQUIREMENTS_DOCUMENT.md)

## Project layout

| Path | Role |
|------|------|
| `frontend/` | Static HTML pages, shared JS/CSS, Node static server + `/api` proxy |
| `backend/` | FastAPI application |
| `docs/` | Product Requirements Document only |
| `scripts/` | Utility scripts |

## Run locally

### Backend (port 8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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

### Demo login (seeded DB)

See `backend/README.md` for credentials after seeding.
