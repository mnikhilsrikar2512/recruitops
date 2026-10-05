#!/bin/bash
# (alias of start.sh) Start RecruitOps locally: FastAPI on :8000 + the frontend server on :4174.
# The frontend server proxies /api → :8000, so the browser stays same-origin.
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-4174}"

if [ ! -x backend/.venv/bin/python ]; then
  echo "backend/.venv is missing. Create it first:"
  echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt"
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required for the frontend server (frontend/server.js)."
  exit 1
fi

cleanup() { kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit; }
trap cleanup INT TERM

echo "Starting RecruitOps..."
(cd backend && exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT") &
BACKEND_PID=$!
(cd frontend && API_PORT="$API_PORT" PORT="$WEB_PORT" exec node server.js) &
FRONTEND_PID=$!

sleep 3
echo ""
echo "  App:      http://localhost:${WEB_PORT}/pages/login.html"
echo "  API:      http://localhost:${API_PORT}/api/v1/health"
echo "  API docs: http://localhost:${API_PORT}/docs"
echo ""
echo "  Demo login (after seeding): see backend/README.md"
echo "Press Ctrl+C to stop"
wait
