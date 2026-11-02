#!/usr/bin/env bash
# Run the RecruitOps load test with k6 in Docker (no local install needed).
#
#   BASE_URL=https://staging.<domain> deploy/loadtest/run.sh            # full run: 300 VUs, 10 min hold
#   BASE_URL=... VUS=20 HOLD=1m THINK_SECONDS=1 deploy/loadtest/run.sh    # quick shakedown
#
# Needs deploy/loadtest/fixture.json from backend/scripts/seed_loadtest.py
# (see README.md). Writes reports/<timestamp>-summary.json and exits non-zero
# when a latency/error target is missed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${BASE_URL:?set BASE_URL, e.g. https://staging.example.com}"
FIXTURE="${FIXTURE:-$HERE/fixture.json}"
[ -f "$FIXTURE" ] || { echo "✗ no fixture at $FIXTURE — run backend/scripts/seed_loadtest.py first" >&2; exit 2; }
case "$BASE_URL" in
  *localhost*|*127.0.0.1*) BASE_URL="${BASE_URL/localhost/host.docker.internal}"; BASE_URL="${BASE_URL/127.0.0.1/host.docker.internal}" ;;
esac
mkdir -p "$HERE/reports"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
K6_IMAGE="${K6_IMAGE:-grafana/k6:0.54.0}"

docker run --rm -i --add-host=host.docker.internal:host-gateway \
  -v "$HERE:/work" -v "$(cd "$(dirname "$FIXTURE")" && pwd)/$(basename "$FIXTURE"):/work/fixture.json:ro" -w /work \
  -e BASE_URL="$BASE_URL" -e FIXTURE=/work/fixture.json \
  -e VUS="${VUS:-300}" -e HOLD="${HOLD:-10m}" -e THINK_SECONDS="${THINK_SECONDS:-5}" \
  -e INSECURE="${INSECURE:-0}" -e DEBUG="${DEBUG:-}" -e SUMMARY="reports/$STAMP-summary.json" \
  "$K6_IMAGE" run recruitops.js
