"""Create a FRESH staging database next to your dev DB (decision D-12).

Drops and recreates the target database, then runs scripts/migrate.py (the
same runner every deploy uses): schema baseline, every numbered migration,
and the reference data.

Uses the DB_HOST / DB_USER / DB_PASSWORD from backend/.env; only the database
name differs. Refuses to touch the dev database named in .env.

    cd backend && .venv/bin/python scripts/create_staging_db.py            # recruitops_staging
    .venv/bin/python scripts/create_staging_db.py --name recruitops_demo
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def dev_db_name() -> str:
    env_file = BACKEND / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("DB_NAME="):
                return line.split("=", 1)[1].strip()
    return "recruitment_system"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="recruitops_staging")
    opts = ap.parse_args()
    name = opts.name
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise SystemExit("database name must be a simple identifier")
    if name.lower() == dev_db_name().lower():
        raise SystemExit(f"refusing to recreate the dev database '{name}' named in backend/.env")

    os.environ["DB_NAME"] = name  # settings read env before .env
    import pyodbc  # noqa: E402

    from app.db.sql_runner import build_pyodbc_connection_string  # noqa: E402

    master = pyodbc.connect(build_pyodbc_connection_string("master"), autocommit=True)
    cursor = master.cursor()
    cursor.execute(
        f"IF DB_ID(N'{name}') IS NOT NULL BEGIN "
        f"ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{name}]; END; "
        f"CREATE DATABASE [{name}];"
    )
    master.close()
    print(f"✓ created empty database {name}")

    # Schema, migrations and reference data through the deploy runner.
    import subprocess  # noqa: PLC0415

    subprocess.run([sys.executable, str(BACKEND / "scripts" / "migrate.py")], check=True,
                   env={**os.environ, "DB_NAME": name, "DEPLOY_ACTOR": "create_staging_db"})
    print(f"\nNext: DB_NAME={name} .venv/bin/python scripts/seed_staging.py")


if __name__ == "__main__":
    main()
