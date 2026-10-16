#!/usr/bin/env bash
# CI-friendly test runner: throwaway SQL Server container → schema → seed → pytest → teardown.
#
# Usage:
#   ./scripts/run_tests_ci.sh                    # full run with throwaway container
#   KEEP_CONTAINER=1 ./scripts/run_tests_ci.sh   # keep the container for debugging
#   SKIP_DOCKER=1 ./scripts/run_tests_ci.sh      # use the already-running DB (localhost:1433)
#
# The integration tests skip gracefully when the database is unreachable, so this
# script still exits green on hosts without Docker.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CONTAINER_NAME="recruitops-test-db"
SA_PASSWORD="RecruitOps-CI-Strong!42"
DB_NAME="recruitops_ci"
DB_PORT="${DB_PORT:-1433}"
KEEP_CONTAINER="${KEEP_CONTAINER:-0}"
SKIP_DOCKER="${SKIP_DOCKER:-0}"

cd "$BACKEND_DIR"

if [ ! -x .venv/bin/python ]; then
  echo "✗ backend/.venv not found — create it and install requirements first" >&2
  exit 1
fi

cleanup() {
  if [ "$SKIP_DOCKER" = "1" ] || [ "$KEEP_CONTAINER" = "1" ]; then
    echo "ℹ container $CONTAINER_NAME left running (KEEP_CONTAINER=${KEEP_CONTAINER})"
    return
  fi
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  echo "✓ threw away $CONTAINER_NAME"
}
trap cleanup EXIT

# sqlcmd lives at a versioned path (/opt/mssql-tools18/…) inside the container —
# resolve it there and forward arguments.
run_sqlcmd() {
  docker exec -i "$CONTAINER_NAME" bash -c \
    'exec "$(ls /opt/mssql-tools*/bin/sqlcmd | head -1)" "$@"' sqlcmd "$@"
}

if [ "$SKIP_DOCKER" != "1" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "✗ docker not available — integration tests will skip" >&2
  else
    # Reuse a leftover container only when KEEP_CONTAINER=1, otherwise always fresh
    if [ "$KEEP_CONTAINER" != "1" ]; then
      docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
      echo "→ starting throwaway SQL Server container ($CONTAINER_NAME)…"
      docker run -d --name "$CONTAINER_NAME" \
        -e "ACCEPT_EULA=Y" \
        -e "MSSQL_SA_PASSWORD=$SA_PASSWORD" \
        -e "MSSQL_PID=Developer" \
        -p "${DB_PORT}:1433" \
        mcr.microsoft.com/mssql/server:2022-latest >/dev/null \
        || { echo "✗ failed to start container" >&2; exit 1; }
    fi

    echo "→ waiting for SQL Server to accept connections…"
    ready=0
    for _ in $(seq 1 60); do
      if run_sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C -Q "SELECT 1" >/dev/null 2>&1; then
        ready=1
        break
      fi
      sleep 1
    done
    if [ "$ready" != "1" ]; then
      echo "✗ SQL Server did not become ready in 60s" >&2
      docker logs "$CONTAINER_NAME" 2>&1 | tail -20 >&2
      exit 1
    fi
    echo "✓ SQL Server is ready"

    echo "→ creating fresh database $DB_NAME…"
    run_sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C \
      -Q "IF DB_ID('$DB_NAME') IS NOT NULL DROP DATABASE [$DB_NAME]; CREATE DATABASE [$DB_NAME];" >/dev/null

    echo "→ applying schema (backend/db/schema.sql)…"
    if ! run_sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C -d "$DB_NAME" -b \
      -i /dev/stdin < "$BACKEND_DIR/db/schema.sql" >/tmp/schema_apply.log 2>&1; then
      echo "✗ schema apply failed — first errors:" >&2
      grep -iE "error|already|invalid|cannot" /tmp/schema_apply.log | head -8 >&2
      exit 1
    fi

    echo "→ verifying table count…"
    table_count=$(run_sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C -d "$DB_NAME" -h -1 -W \
      -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA='dbo';" 2>/dev/null | tr -d '[:space:]')
    if [ -z "$table_count" ] || [ "$table_count" -lt 50 ]; then
      echo "✗ schema incomplete: expected ≥50 tables, got '${table_count:-none}'" >&2
      exit 1
    fi
    echo "✓ $table_count tables present"

    # Migrations newer than the schema dump (005/006 are in schema.sql;
    # 007 is covered by seed_ci.py). Same list as scripts/create_staging_db.py.
    for migration in 008_display_ids.sql 009_branch_offer_toggle.sql 010_tenants.sql 011_admin_seed.sql 012_tenant_settings.sql 013_jwt_sessions.sql 014_login_lockout.sql 015_mfa.sql 016_metric_buckets.sql 017_pipeline_reopen.sql 018_row_versions.sql 019_soft_delete.sql 020_offer_threshold.sql 021_file_pipeline.sql 022_signing_bonus_policy.sql 023_withdraw_reasons.sql 024_requisition_holds.sql 025_client_stage_lists.sql 026_legal.sql 027_privacy.sql 028_signup.sql 029_setup_checklist.sql 030_cross_tenant_duplicate_flags.sql 031_visibility_rules.sql; do
      echo "→ applying migration $migration…"
      if ! run_sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C -d "$DB_NAME" -b \
        -i /dev/stdin < "$BACKEND_DIR/../scripts/$migration" >/tmp/migration_apply.log 2>&1; then
        echo "✗ migration $migration failed:" >&2
        head -8 /tmp/migration_apply.log >&2
        exit 1
      fi
    done
  fi
else
  echo "→ SKIP_DOCKER=1 — using already-running database at localhost:${DB_PORT}"
fi

# Point the app/tests at the throwaway container (DB_* beats .env in app config)
export DB_HOST="localhost"
export DB_PORT="$DB_PORT"
export DB_NAME="$DB_NAME"
export DB_USER="sa"
export DB_PASSWORD="$SA_PASSWORD"
export DB_ENCRYPT="false"
export DB_TRUST_SERVER_CERTIFICATE="true"

if [ "$SKIP_DOCKER" != "1" ] && command -v docker >/dev/null 2>&1; then
  echo "→ seeding minimal data (permissions, admin role/user, location)…"
  .venv/bin/python scripts/seed_ci.py
fi

echo "→ running pytest…"
.venv/bin/python -m pytest tests/ -q "$@"
status=$?

if [ "$status" = "0" ]; then
  echo "✓ all tests passed"
else
  echo "✗ tests failed with exit $status" >&2
fi
exit $status
