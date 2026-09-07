#!/bin/bash
# Persistent server launcher - run this in Terminal.app
cd "$(dirname "$0")"

cleanup() { kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit; }
trap cleanup INT TERM

echo "Starting RecruitOps..."
cd backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../frontend && python3 -m http.server 3000 &
FRONTEND_PID=$!
cd ..

sleep 3
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  RecruitOps is running!                      ║"
echo "║                                              ║"
echo "║  Frontend: http://localhost:3000             ║"
echo "║  Backend:  http://localhost:8000             ║"
echo "║  API Docs: http://localhost:8000/docs        ║"
echo "║                                              ║"
echo "║  Login: admin@executiveconnection.com        ║"
echo "║  Password: admin123                          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop"

wait
