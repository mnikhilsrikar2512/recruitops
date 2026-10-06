#!/usr/bin/env bash
# Phase 1 closing run on a developer machine — one command, run from anywhere:
#
#   bash "/path/to/recrutment system/tools/ci/phase1_verify.sh"
#
# 1. installs backend deps into backend/.venv (+ playwright for the browser checks)
# 2. creates a FRESH database "recruitops_staging" on the SQL Server from backend/.env
#    (your dev database is never touched)
# 3. seeds the CI baseline and runs the backend test suite against it
# 4. seeds the two staging tenants
# 5. starts the API and UI on free ports (from 18010 / 14184) on that database
# 6. runs the live API smoke test and the browser sweep (admin + tenant-A recruiter)
# Logs: <repo>/.phase1-logs/*.log (gitignored)   Summary at the end.
# Uses its own free ports (never 8000/4174) so an already-running dev backend on
# :8000 (e.g. the launchd com.recruitops.backend job) is not hit by mistake.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAGING_DB="${STAGING_DB:-recruitops_staging}"
STAGING_PASSWORD="${STAGING_PASSWORD:-Staging#2026-Recruit}"
LOGS="$ROOT/.phase1-logs"   # inside the repo (gitignored) so the logs can be shared
mkdir -p "$LOGS"
cd "$ROOT/backend"
PY=.venv/bin/python
declare -a SUMMARY=()
record() { SUMMARY+=("$1  $2"); }

if [ ! -x "$PY" ]; then
  echo "→ creating backend/.venv"
  python3 -m venv .venv || { echo "✗ could not create backend/.venv"; exit 1; }
fi
[ -f .env ] || { echo "✗ backend/.env missing — copy .env.example and set DB_* first"; exit 1; }

echo "→ 1/6 installing dependencies"
$PY -m pip install -q -r requirements-dev.txt playwright >"$LOGS/pip.log" 2>&1 \
  && $PY -m playwright install chromium >>"$LOGS/pip.log" 2>&1 \
  && record PASS "dependencies installed" || { record FAIL "dependency install (see $LOGS/pip.log)"; }

echo "→ 2/6 fresh database $STAGING_DB"
if $PY scripts/create_staging_db.py --name "$STAGING_DB" 2>&1 | tee "$LOGS/create_db.log"; then
  record PASS "fresh database $STAGING_DB"
else
  record FAIL "create database (see $LOGS/create_db.log)"
  printf '\n%s\n' "${SUMMARY[@]}"; exit 1
fi
export DB_NAME="$STAGING_DB"

echo "→ 3/6 baseline seed + backend tests"
$PY scripts/seed_ci.py >"$LOGS/seed_ci.log" 2>&1 || record FAIL "seed_ci (see $LOGS/seed_ci.log)"
if $PY -m pytest tests/ -q -p no:cacheprovider 2>&1 | tee "$LOGS/pytest.log" | grep -E "^(FAILED|ERROR)| passed| failed"; [ "${PIPESTATUS[0]}" = "0" ]; then
  record PASS "backend tests ($(tail -1 "$LOGS/pytest.log"))"
else
  record FAIL "backend tests ($(tail -1 "$LOGS/pytest.log")) — see $LOGS/pytest.log"
fi

echo "→ 4/6 staging tenants"
if STAGING_PASSWORD="$STAGING_PASSWORD" $PY scripts/seed_staging.py 2>&1 | tee "$LOGS/seed_staging.log"; then
  record PASS "staging seed (2 tenants)"
else
  record FAIL "staging seed (see $LOGS/seed_staging.log)"
fi

free_port() {  # first free TCP port at or above $1
  "$PY" - "$1" <<'PYEOF'
import socket, sys
port = int(sys.argv[1])
while True:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port)); print(port); break
        except OSError:
            port += 1
PYEOF
}
API_PORT_V="${API_PORT_V:-$(free_port 18010)}"
WEB_PORT_V="${WEB_PORT_V:-$(free_port 14184)}"
BASE="http://127.0.0.1:$WEB_PORT_V"
echo "→ 5/6 starting API :$API_PORT_V and UI :$WEB_PORT_V on $STAGING_DB"
$PY -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT_V" >"$LOGS/api.log" 2>&1 &
API_PID=$!
(cd "$ROOT/frontend" && API_PORT="$API_PORT_V" PORT="$WEB_PORT_V" exec node server.js) >"$LOGS/web.log" 2>&1 &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -sf "$BASE/api/v1/health" >/dev/null && break; sleep 0.5; done
if curl -sf "$BASE/api/v1/health" >/dev/null && kill -0 "$API_PID" 2>/dev/null; then
  record PASS "stack up ($BASE → API :$API_PORT_V, DB $STAGING_DB)"
else
  record FAIL "stack did not start (see $LOGS/api.log, $LOGS/web.log)"
fi

echo "→ 6/6 live smoke + browser sweep"
cd "$ROOT"
backend/.venv/bin/python tools/ci/live_smoke.py --base "$BASE" --password "$STAGING_PASSWORD" \
  2>&1 | tee "$LOGS/live_smoke.log" | grep -E "FAIL|checks passed"
[ "${PIPESTATUS[0]}" = "0" ] && record PASS "live smoke ($(tail -1 "$LOGS/live_smoke.log"))" \
  || record FAIL "live smoke ($(tail -1 "$LOGS/live_smoke.log")) — see $LOGS/live_smoke.log"
backend/.venv/bin/python frontend/tests/page_sweep.py --base "$BASE" --live \
  --email ci.admin@recruitops-test.com --password admin123 --persona admin \
  >"$LOGS/sweep_admin.log" 2>&1 \
  && record PASS "browser sweep admin ($(tail -1 "$LOGS/sweep_admin.log"))" \
  || record FAIL "browser sweep admin ($(tail -1 "$LOGS/sweep_admin.log")) — see $LOGS/sweep_admin.log"
backend/.venv/bin/python frontend/tests/page_sweep.py --base "$BASE" --live \
  --email recruiter@northwind-staging.example.com --password "$STAGING_PASSWORD" --persona recruiter \
  >"$LOGS/sweep_recruiter.log" 2>&1 \
  && record PASS "browser sweep recruiter ($(tail -1 "$LOGS/sweep_recruiter.log"))" \
  || record FAIL "browser sweep recruiter ($(tail -1 "$LOGS/sweep_recruiter.log")) — see $LOGS/sweep_recruiter.log"

echo; echo "════════ Phase 1 verification ════════"
printf '%s\n' "${SUMMARY[@]}"
echo "Logs: $LOGS   (paste this summary + any FAIL log back to Claude)"
printf '%s\n' "${SUMMARY[@]}" | grep -q '^FAIL' && exit 1 || exit 0
