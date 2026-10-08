"""Apply one numbered migration (repo-root scripts/NNN_*.sql) to a database.

Defaults to the database in backend/.env (your dev DB). Takes a server-side
backup first unless --no-backup is given, so the step can be undone with a
RESTORE. Every migration is idempotent and verifies itself.

    cd backend && .venv/bin/python scripts/apply_migration.py 010_tenants.sql
    .venv/bin/python scripts/apply_migration.py 010_tenants.sql --name recruitops_staging --no-backup
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from create_staging_db import dev_db_name  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("migration", help="file name under <repo>/scripts, e.g. 010_tenants.sql")
    ap.add_argument("--name", default=None, help="database (default: DB_NAME from backend/.env)")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--backup-dir", default="/var/opt/mssql/data",
                    help="directory ON THE SQL SERVER host/container for the .bak file")
    opts = ap.parse_args()

    path = BACKEND.parent / "scripts" / opts.migration
    if not re.fullmatch(r"\d{3}_[A-Za-z0-9_]+\.sql", opts.migration) or not path.exists():
        raise SystemExit(f"no such migration: {path}")
    name = opts.name or dev_db_name()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise SystemExit("database name must be a simple identifier")
    os.environ["DB_NAME"] = name

    import pyodbc  # noqa: PLC0415

    from app.db.sql_runner import build_pyodbc_connection_string, split_sql_batches  # noqa: PLC0415

    connection = pyodbc.connect(build_pyodbc_connection_string(name), autocommit=True)
    cursor = connection.cursor()
    if not opts.no_backup:
        bak = f"{opts.backup_dir.rstrip('/')}/{name}-pre-{opts.migration[:3]}-{time.strftime('%Y%m%d-%H%M%S')}.bak"
        cursor.execute(f"BACKUP DATABASE [{name}] TO DISK = N'{bak}' WITH INIT, COPY_ONLY")
        while cursor.nextset():
            pass
        print(f"✓ backup written on the SQL Server: {bak}")
        print(f"  undo: RESTORE DATABASE [{name}] FROM DISK = N'{bak}' WITH REPLACE")
    for batch in split_sql_batches(path.read_text(encoding="utf-8")):
        cursor.execute(batch.sql_text)
        while cursor.nextset():
            pass
    connection.close()
    print(f"✓ {opts.migration} applied to {name}")


if __name__ == "__main__":
    main()
