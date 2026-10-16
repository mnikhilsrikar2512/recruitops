"""Create a FRESH staging database next to your dev DB (decision D-12).

Drops and recreates the target database, applies backend/db/schema.sql and the
migrations newer than the schema dump (008, 009). 005/006 are already in
schema.sql and 007 is a backfill that seed_ci.py covers.

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

# 005/006 tables are already in db/schema.sql (005 also inserts demo approvals
# that need existing locations); 007 is covered by seed_ci.py. Only the
# migrations newer than the schema dump are applied.
MIGRATIONS = ["008_display_ids.sql", "009_branch_offer_toggle.sql", "010_tenants.sql", "011_admin_seed.sql", "012_tenant_settings.sql", "013_jwt_sessions.sql", "014_login_lockout.sql", "015_mfa.sql", "016_metric_buckets.sql", "017_pipeline_reopen.sql", "018_row_versions.sql", "019_soft_delete.sql", "020_offer_threshold.sql", "021_file_pipeline.sql", "022_signing_bonus_policy.sql", "023_withdraw_reasons.sql", "024_requisition_holds.sql", "025_client_stage_lists.sql", "026_legal.sql", "027_privacy.sql", "028_signup.sql", "029_setup_checklist.sql", "030_cross_tenant_duplicate_flags.sql", "031_visibility_rules.sql"]


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

    from app.db.sql_runner import build_pyodbc_connection_string, split_sql_batches  # noqa: E402

    master = pyodbc.connect(build_pyodbc_connection_string("master"), autocommit=True)
    cursor = master.cursor()
    cursor.execute(
        f"IF DB_ID(N'{name}') IS NOT NULL BEGIN "
        f"ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{name}]; END; "
        f"CREATE DATABASE [{name}];"
    )
    master.close()
    print(f"✓ created empty database {name}")

    connection = pyodbc.connect(build_pyodbc_connection_string(name), autocommit=True)
    cursor = connection.cursor()
    cursor.execute((BACKEND / "db" / "schema.sql").read_text(encoding="utf-8"))
    while cursor.nextset():
        pass
    tables = cursor.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA='dbo'"
    ).fetchone()[0]
    if tables < 50:
        raise SystemExit(f"schema incomplete: {tables} tables")
    print(f"✓ schema applied ({tables} tables)")

    for migration in MIGRATIONS:
        sql_text = (BACKEND.parent / "scripts" / migration).read_text(encoding="utf-8")
        for batch in split_sql_batches(sql_text):
            cursor.execute(batch.sql_text)
            while cursor.nextset():
                pass
        print(f"✓ migration {migration}")
    connection.close()
    print(f"\nNext: DB_NAME={name} .venv/bin/python scripts/seed_staging.py")


if __name__ == "__main__":
    main()
