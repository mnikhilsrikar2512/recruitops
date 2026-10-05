#!/bin/bash
# Backend only (used by com.recruitops.backend.plist). Runs from this repo's location.
cd "$(dirname "$0")/backend"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT:-8000}"
