#!/usr/bin/env bash
# Frontend gates, runnable locally and in CI (Phase 1 exit criteria):
#   1. JS syntax            node --check on frontend/shared/*.js
#   2. Undefined globals    tools/ci/undef_check.js (no ReferenceErrors waiting to happen)
#   3. API contract         tools/ci/api_contract_check.py (every apiRequest path exists)
#   4. Static assets        tools/ci/static_assets_check.py
#   5. Browser sweep        all pages × {admin, recruiter} against the contract mock
#   6. UI flows             login, create client/requisition, approve, stage move, read, logout
#
# Needs: node 18+, python 3.12 with `playwright` (+ `playwright install chromium`),
# typescript (npm), and either OPENAPI=path/to/openapi.json or the backend's
# Python deps installed so the schema can be exported.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PORT="${MOCK_PORT:-4180}"

echo "→ 1/6 JS syntax"
for f in frontend/shared/*.js frontend/server.js frontend/tests/*.js; do node --check "$f"; done

echo "→ 2/6 undefined identifiers"
node tools/ci/undef_check.js frontend/shared

echo "→ 3/6 API contract (frontend calls ⊆ backend routes)"
python3 tools/ci/api_contract_check.py "$ROOT"

echo "→ 4/6 static assets"
python3 tools/ci/static_assets_check.py

OPENAPI="${OPENAPI:-$ROOT/frontend/tests/openapi.json}"
if [ "${EXPORT_OPENAPI:-1}" = "1" ] && python3 -c "import fastapi" 2>/dev/null; then
  echo "→ exporting OpenAPI from the backend"
  (cd backend && python3 scripts/export_openapi.py "$OPENAPI")
fi
[ -f "$OPENAPI" ] || { echo "✗ no OpenAPI document at $OPENAPI" >&2; exit 1; }

echo "→ starting contract mock on :$PORT"
node frontend/tests/mock-api-server.js --openapi "$OPENAPI" --port "$PORT" >/tmp/recruitops-mock.log 2>&1 &
MOCK_PID=$!
trap 'kill $MOCK_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/__mock/log" >/dev/null && break; sleep 0.3; done

echo "→ 5/6 browser sweep (admin)"
python3 frontend/tests/page_sweep.py --base "http://127.0.0.1:$PORT" --persona admin
echo "→ 5/6 browser sweep (recruiter)"
python3 frontend/tests/page_sweep.py --base "http://127.0.0.1:$PORT" --persona recruiter
echo "→ 6/6 UI flows"
python3 frontend/tests/flows.py --base "http://127.0.0.1:$PORT"
echo "✓ frontend checks passed"
