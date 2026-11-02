"""Bring a database to the current schema, the gated step every deploy runs
before new code starts (Phase 6.2).

    cd backend
    .venv/bin/python scripts/migrate.py --status          # what's applied, what's pending
    .venv/bin/python scripts/migrate.py                   # apply pending, then reference data
    .venv/bin/python scripts/migrate.py --create-db       # also CREATE DATABASE if missing (staging, CI, compose)

What it does, in order:

1. Takes an exclusive application lock (sp_getapplock) so two deploys can
   never migrate the same database at once.
2. Creates ``dbo.schema_migrations`` (version, checksum, applied_at,
   applied_by, duration_ms) if needed.
3. Empty database: applies ``backend/db/schema.sql`` and records it as the
   ``000_schema`` baseline.
4. Applies every ``scripts/NNN_*.sql`` (repo root) that isn't recorded yet,
   in order, and records each with its SHA-256. Every migration is written
   to be idempotent and to verify itself, so a database that was migrated
   by hand before this runner existed is brought under tracking safely:
   already-applied files simply re-run as no-ops.
5. Refuses to continue when an applied file has changed since it ran
   (checksum mismatch) — fix forward with a new numbered file instead.
6. Seeds reference data (``seed_reference_data.py``): the permission
   catalog and the shared Admin role. Never companies, users or demo data.

Exit code is non-zero on any failure, which stops the deploy pipeline
before new code is rolled out.

Credentials: ``MIGRATE_DB_USER`` / ``MIGRATE_DB_PASSWORD`` when set (a login
allowed to change the schema), otherwise ``DB_USER`` / ``DB_PASSWORD``. The
running app can then use a login without DDL rights.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import re
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
MIGRATIONS_DIR = Path(os.environ.get("MIGRATIONS_DIR", REPO / "scripts"))
SCHEMA_FILE = BACKEND / "db" / "schema.sql"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

BASELINE = "000_schema"
LOCK_NAME = "recruitops:migrate"
# 005/006 are folded into db/schema.sql; 007 is superseded by the reference
# data seed (it only granted AI codes to roles that existed at the time).
NOT_RUN = {"005", "006", "007"}
_NAME = re.compile(r"^(\d{3})_[A-Za-z0-9_]+\.sql$")


@dataclass(frozen=True)
class Migration:
    version: str  # file name without .sql, e.g. "032_encrypt_mfa_secrets"
    path: Path

    @property
    def checksum(self) -> str:
        return sha256_text(self.path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    # Line endings don't change meaning; a checkout on Windows must not look "modified".
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    found: list[Migration] = []
    seen: dict[str, str] = {}
    for path in sorted(directory.glob("*.sql")):
        match = _NAME.match(path.name)
        if not match or match.group(1) in NOT_RUN:
            continue
        number = match.group(1)
        if number in seen:
            raise SystemExit(f"✗ two migrations share number {number}: {seen[number]} and {path.name}")
        seen[number] = path.name
        found.append(Migration(path.stem, path))
    return found


def _connection_string(database: str) -> str:
    from app.core.config import settings
    from app.db.sql_runner import build_pyodbc_connection_string

    base = build_pyodbc_connection_string(database)
    user = os.environ.get("MIGRATE_DB_USER")
    password = os.environ.get("MIGRATE_DB_PASSWORD")
    if user:
        base = base.replace(f"UID={settings.db_user};", f"UID={user};", 1)
    if password is not None and user:
        base = base.replace(f"PWD={settings.db_password};", f"PWD={password};", 1)
    return base


def _exec_batches(cursor, sql_text: str) -> None:
    from app.db.sql_runner import split_sql_batches

    for batch in split_sql_batches(sql_text):
        cursor.execute(batch.sql_text)
        while cursor.nextset():
            pass


def _connect(database: str, attempts: int | None = None):
    """The database may still be starting: retry for about a minute
    (MIGRATE_CONNECT_ATTEMPTS x ~7 s), then give up."""
    import pyodbc

    attempts = attempts or int(os.environ.get("MIGRATE_CONNECT_ATTEMPTS", "8"))
    last: Exception | None = None
    for _ in range(attempts):
        try:
            return pyodbc.connect(_connection_string(database), autocommit=True, timeout=5)
        except pyodbc.Error as exc:  # noqa: PERF203
            last = exc
            time.sleep(2)
    raise SystemExit(f"✗ cannot connect to {database}: {last}")


def create_database_if_missing(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise SystemExit("✗ DB_NAME must be a simple identifier")
    master = _connect("master")
    master.cursor().execute(f"IF DB_ID(N'{name}') IS NULL CREATE DATABASE [{name}];")
    master.close()


TRACKING_DDL = """
IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
CREATE TABLE dbo.schema_migrations (
    version      NVARCHAR(200) NOT NULL CONSTRAINT PK_schema_migrations PRIMARY KEY,
    checksum     CHAR(64)      NOT NULL,
    applied_at   DATETIME2(3)  NOT NULL CONSTRAINT DF_schema_migrations_applied_at DEFAULT SYSUTCDATETIME(),
    applied_by   NVARCHAR(200) NOT NULL,
    duration_ms  INT           NOT NULL
);
"""


def _applied(cursor) -> dict[str, str]:
    return {row[0]: row[1] for row in cursor.execute("SELECT version, checksum FROM dbo.schema_migrations").fetchall()}


def _user_table_count(cursor) -> int:
    return cursor.execute(
        "SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped = 0 AND name <> N'schema_migrations'").fetchone()[0]


def _record(cursor, version: str, checksum: str, started: float) -> None:
    who = os.environ.get("DEPLOY_ACTOR") or f"{getpass.getuser()}@{socket.gethostname()}"
    cursor.execute(
        "INSERT INTO dbo.schema_migrations (version, checksum, applied_by, duration_ms) VALUES (?, ?, ?, ?)",
        version, checksum, who[:200], int((time.perf_counter() - started) * 1000))


def plan(applied: dict[str, str], migrations: list[Migration], allow_changed: bool = False) -> list[Migration]:
    """Pending migrations, after checking applied ones haven't been edited."""
    changed = [m.version for m in migrations if m.version in applied and applied[m.version] != m.checksum]
    if changed and not allow_changed:
        raise SystemExit(
            "✗ already-applied migrations were edited since they ran: " + ", ".join(changed)
            + "\n  Put the change in a new numbered migration instead (or --allow-changed after review).")
    return [m for m in migrations if m.version not in applied]


def run(create_db: bool, status_only: bool, allow_changed: bool, seed: bool) -> int:
    from app.core.config import settings

    database = settings.db_name
    if create_db:
        create_database_if_missing(database)
    connection = _connect(database)
    cursor = connection.cursor()
    got = cursor.execute(
        "DECLARE @r INT; EXEC @r = sp_getapplock @Resource = ?, @LockMode = 'Exclusive', "
        "@LockOwner = 'Session', @LockTimeout = 600000; SELECT @r;", LOCK_NAME).fetchone()[0]
    if got < 0:
        raise SystemExit("✗ another migration holds the lock (waited 10 minutes)")
    try:
        _exec_batches(cursor, TRACKING_DDL)
        applied = _applied(cursor)
        migrations = discover()
        fresh = _user_table_count(cursor) == 0 and BASELINE not in applied
        pending = plan(applied, migrations, allow_changed)

        print(f"database {database} on {settings.db_host}: {len(applied)} recorded, "
              f"{len(pending)} pending{' (empty: schema baseline first)' if fresh else ''}")
        for migration in pending:
            print(f"  pending  {migration.version}")
        if status_only:
            return 1 if (pending or fresh) and os.environ.get("MIGRATE_STATUS_FAIL_ON_PENDING") else 0

        if fresh:
            started = time.perf_counter()
            schema = SCHEMA_FILE.read_text(encoding="utf-8")
            cursor.execute(schema)
            while cursor.nextset():
                pass
            if _user_table_count(cursor) < 50:
                raise SystemExit("✗ schema baseline incomplete")
            _record(cursor, BASELINE, sha256_text(schema), started)
            print(f"✓ {BASELINE} ({_user_table_count(cursor)} tables)")

        for migration in pending:
            started = time.perf_counter()
            try:
                _exec_batches(cursor, migration.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise SystemExit(f"✗ {migration.version} failed: {exc}") from None
            _record(cursor, migration.version, migration.checksum, started)
            print(f"✓ {migration.version} ({int((time.perf_counter() - started) * 1000)} ms)")

        if seed:
            from seed_reference_data import seed_reference_data

            counts = seed_reference_data(cursor)
            print(f"✓ reference data: {counts['permissions_added']} permissions added "
                  f"({counts['permissions_total']} in catalog), Admin role holds {counts['admin_grants']} grants")
        print("✓ database is current")
        return 0
    finally:
        try:
            cursor.execute("EXEC sp_releaseapplock @Resource = ?, @LockOwner = 'Session';", LOCK_NAME)
        finally:
            connection.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", action="store_true", help="show applied/pending and exit without changes")
    ap.add_argument("--create-db", action="store_true", help="CREATE DATABASE first if it doesn't exist")
    ap.add_argument("--allow-changed", action="store_true", help="don't stop on edited, already-applied files")
    ap.add_argument("--no-seed", action="store_true", help="skip the reference data step")
    opts = ap.parse_args()
    raise SystemExit(run(opts.create_db, opts.status, opts.allow_changed, seed=not opts.no_seed))


if __name__ == "__main__":
    main()
