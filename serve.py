#!/usr/bin/env python3
"""Start both backend and frontend servers."""
import subprocess
import sys
import time
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

procs = []

try:
    print("Starting backend on port 8000...")
    backend = subprocess.Popen(
        [os.path.join(BACKEND_DIR, ".venv/bin/python"), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    procs.append(backend)

    print("Starting frontend on port 3000...")
    python_bin = sys.executable
    frontend = subprocess.Popen(
        [python_bin, "-m", "http.server", "3000"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    procs.append(frontend)

    time.sleep(3)

    print()
    print("═" * 50)
    print("  RecruitOps is running!")
    print()
    print("  Frontend:  http://localhost:3000")
    print("  Backend:   http://localhost:8000")
    print("  API Docs:  http://localhost:8000/docs")
    print()
    print("  Login: any @executiveconnection.com email")
    print("  Password: admin123")
    print("═" * 50)
    print()
    print("Press Ctrl+C to stop")

    while True:
        time.sleep(1)
        if backend.poll() is not None:
            print(f"Backend exited with code {backend.returncode}")
            break
        if frontend.poll() is not None:
            print(f"Frontend exited with code {frontend.returncode}")
            break

except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    for p in procs:
        p.terminate()
        p.wait()
    print("Servers stopped.")
