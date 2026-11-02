#!/bin/sh
# One image, several roles:
#   api        (default) the HTTP API
#   migrate    apply migrations + reference data, then exit (deploy gate)
#   scheduler  run the recurring jobs (privacy, sessions, upload cleanup)
#   job NAME   run one scheduled job once and exit
#   <anything else> is executed as given (e.g. "python scripts/provision_company.py ...")
set -eu
cd /app/backend

case "${1:-api}" in
  api)
    # Metrics from every worker process are summed from files here; start clean.
    if [ -n "${PROMETHEUS_MULTIPROC_DIR:-}" ]; then
      rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/* 2>/dev/null || true
      mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
    fi
    exec uvicorn app.main:app \
      --host 0.0.0.0 --port "${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-2}" \
      --no-proxy-headers --no-server-header --no-access-log \
      --timeout-keep-alive "${KEEPALIVE_SECONDS:-15}" \
      --timeout-graceful-shutdown "${GRACEFUL_SECONDS:-20}"
    ;;
  migrate)
    shift
    exec python scripts/migrate.py "$@"
    ;;
  scheduler)
    shift
    exec python scripts/scheduler.py "$@"
    ;;
  job)
    shift
    exec python scripts/scheduler.py --run-once "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
