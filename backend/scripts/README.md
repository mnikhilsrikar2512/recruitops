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

The dump writes three passes (tables, then foreign keys, then CHECK
constraints, all as `ALTER TABLE ... ADD CONSTRAINT`) so circular FK
dependencies (`locations ↔ roles ↔ users`) replay cleanly into an empty
database. CHECK constraints get their own pass because SQLAlchemy's table
reflection doesn't surface them on SQL Server -- without it, a CHECK
constraint added straight against a live database is invisible here and can
silently drift from what the application code actually writes to that
column. Re-run this after any schema change, including adding or editing a
CHECK constraint, and commit the result.

## CI seed

`scripts/seed_ci.py` populates a fresh database with the minimum the API and
tests need:

- 70-code permission catalog (`dbo.permissions`), including the AI agent codes
  (see below)
- `admin` role granted every permission
- Admin user `ci.admin@recruitops-test.com` / `admin123`
- Primary branch link (`dbo.branches` + `dbo.user_branch_roles`)
- Client id 1 in `dbo.client_companies` (requisition creation requires it)

It is idempotent — safe to run repeatedly. After seeding it runs `verify_seed()`,
which fails with a non-zero exit if any seeded row a test depends on is missing
(requisition/candidate pair, portal account, letterhead entity, AI permission
codes).

## AI agent permissions (`ai.*`)

The agents API (`app/api/v1/agents.py`) is gated by a base permission plus one
per-agent code (PRD §4.16; agents are declared in `app/agents/registry.py`):

| Code | Gates |
|------|-------|
| `ai.use` | Any agent invocation (list catalog, run an agent) |
| `ai.agent.resume_screener` | Resume Screener runs + decisions |
| `ai.agent.daily_brief` | Daily Brief runs + decisions |
| `ai.agent.inbox_triage` | Inbox Triage runs + decisions |

Only the `admin` role bypasses the check (`app/api/deps.py`); every other role
needs these codes granted through `role.permissions.assign` (Admin → Roles),
the CI seed, or the backfill migration below.

### Backfilling existing databases (007)

Databases created before the agents feature have no `ai.*` rows. Apply the
idempotent migration once — it only inserts what is missing:

```bash
sqlcmd -S localhost -U sa -P "$DB_PASSWORD" -C -d recruitment_system \
  -i scripts/007_grant_ai_permissions.sql
```

`scripts/007_grant_ai_permissions.sql`:

1. Inserts the four `ai.*` catalog rows.
2. Grants them to existing roles **derived from the closest operational
   permission they already hold** — `ai.use`, `ai.agent.resume_screener`, and
   `ai.agent.inbox_triage` to every role holding `candidate.read`, and
   `ai.agent.daily_brief` to every role holding `daily_update.read` — so
   one-off/test roles with no real permissions are not widened.
3. Verifies the result (raises on failure) and is safe to re-run.

The `admin` role needs no backfill grant: `scripts/seed_ci.py` grants it every
permission, and its API check bypass covers databases seeded by other means.

## Migrations

Numbered scripts in the repo-root `scripts/` directory, each idempotent and
safe to re-run. Most are SQL, applied with `sqlcmd -i` in order:

- `005_create_approvals_table.sql` — approvals table + demo rows
- `006_create_agent_runs_table.sql` — `agent_runs` table for V1 agents
- `007_grant_ai_permissions.sql` — `ai.*` permission codes + role backfill
  (see above)
- `008_sync_admin_permissions.py` — backfills the system Admin role's
  `role_permissions` to the current `ADMIN_PERMISSION_CODES`
  (`app/core/rbac.py`). Run with `.venv/bin/python scripts/008_sync_admin_permissions.py`
  (Python, not `sqlcmd`, because it reads the permission list directly from
  code instead of duplicating it in SQL). Any database that existed before a
  code was added to `ADMIN_PERMISSION_CODES` needs this re-run, or routes
  gated on the new code 403 for an account that's supposed to have full
  access — `scripts/seed_ci.py` only seeds a brand-new database with the
  *current* list; it does not backfill an existing one.

`backend/db/schema.sql` stays tables-only by design — permission rows are data
and belong to `seed_ci.py` / migrations.
