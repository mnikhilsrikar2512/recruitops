#!/bin/bash
# Start both backend and frontend servers
# Usage: bash serve.sh

cd "$(dirname "$0")"

echo "=== Starting Backend (port 8000) ==="
cd backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "=== Starting Frontend (port 3000) ==="
cd frontend
.venv/bin/python -m http.server 3000 &
FRONTEND_PID=$!
cd ..

sleep 2

echo ""
echo "════════════════════════════════════════════════════"
echo "  RecruitOps is running!"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Login: any @executiveconnection.com email"
echo "  Password: admin123"
echo "════════════════════════════════════════════════════"
echo ""
echo "Press Ctrl+C to stop both servers"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
