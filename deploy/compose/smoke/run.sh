#!/usr/bin/env bash
# Run both smoke suites against the local stack (docker compose up first).
set -euo pipefail
cd "$(dirname "$0")"
export NO_PROXY="localhost,127.0.0.1,${NO_PROXY:-}"
python3 journey.py
python3 platform.py
