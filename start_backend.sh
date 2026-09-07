#!/bin/bash
cd "/Users/bhargavnikhil/Desktop/recrutment system/backend"
exec ../backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
