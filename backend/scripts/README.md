# Backend Scripts

## Test runner (CI-friendly)

```bash
cd backend

# Full run: throwaway SQL Server container → fresh DB → schema → seed → pytest → teardown
DB_PORT=1434 ./scripts/run_tests_ci.sh

# Keep the container for debugging a failure
KEEP_CONTAINER=1 DB_PORT=1434 ./scripts/run_tests_ci.sh

# Skip Docker and test against an already-running database
SKIP_DOCKER=1 ./scripts/run_tests_ci.sh

# Extra args are forwarded to pytest
DB_PORT=1434 ./scripts/run_tests_ci.sh -k rbac
```

The runner:

1. Starts a throwaway `mssql/server:2022` container (`recruitops-test-db`).
2. Drops and recreates the `recruitops_ci` database.
3. Applies `backend/db/schema.sql` (60 tables, 150 FKs, fail-fast `-b`).
4. Verifies the table count (≥ 50).
5. Seeds the permission catalog, admin role/user, branch, and one client via `scripts/seed_ci.py`.
6. Runs `pytest` with `DB_*` environment variables pointing at the container.
7. Removes the container (unless `KEEP_CONTAINER=1`).

Integration tests skip gracefully when no database is reachable, so the suite
still exits green in environments without Docker.

## Schema dump

`backend/db/schema.sql` is generated from the live database — regenerate it
after schema changes and commit the result:

```bash
cd backend && .venv/bin/python scripts/dump_schema.py
```

The dump writes two passes (tables first, then foreign keys as
`ALTER TABLE ... ADD CONSTRAINT`) so circular FK dependencies
(`locations ↔ roles ↔ users`) replay cleanly into an empty database.

## CI seed

`scripts/seed_ci.py` populates a fresh database with the minimum the API and
tests need:

- 33-code permission catalog (`dbo.permissions`)
- `admin` role granted every permission
- Admin user `ci.admin@recruitops-test.com` / `admin123`
- Primary branch link (`dbo.branches` + `dbo.user_branch_roles`)
- Client id 1 in `dbo.client_companies` (requisition creation requires it)

It is idempotent — safe to run repeatedly.
