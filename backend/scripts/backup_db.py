"""Nightly portable database backup (Phase 6.6).

    python scripts/backup_db.py              # export, upload, apply retention
    python scripts/backup_db.py --list       # backups in the bucket, newest first

A second line of defence next to the database provider's own point-in-time
restore: a ``.bacpac`` (schema + data) that can be imported into Azure SQL,
AWS RDS or any SQL Server, stored in the object store under
``BACKUP_S3_PREFIX`` (default ``backups/``) of ``BACKUP_S3_BUCKET`` (default:
the file bucket; a separate bucket with its own credentials and object lock
is better, see docs/runbooks/backup-restore.md).

Each backup is two objects:
  <prefix><db>/<YYYY>/<MM>/<db>-<stamp>.bacpac
  <prefix><db>/<YYYY>/<MM>/<db>-<stamp>.json   manifest: sha256, size, row
                                                counts per table, latest
                                                migration, consistency
Consistency: on Azure SQL the export reads a transactionally consistent
``CREATE DATABASE ... AS COPY OF`` copy. Elsewhere it counts every table
before and after the export; the manifest says whether anything changed
while it ran, and the restore drill accepts counts inside that window.

Retention: every backup for BACKUP_RETENTION_DAYS (35), then the first
backup of each month for BACKUP_MONTHLY_KEEP months (12).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

STAMP = "%Y%m%dT%H%M%SZ"


# ---- connections ---------------------------------------------------------------

def credentials() -> tuple[str, str]:
    from app.core.config import settings

    user = os.environ.get("BACKUP_DB_USER") or os.environ.get("MIGRATE_DB_USER") or settings.db_user
    password = os.environ.get("BACKUP_DB_PASSWORD") or os.environ.get("MIGRATE_DB_PASSWORD") or settings.db_password
    return user, password


def ado_connection_string(database: str, host: str | None = None, port: int | None = None,
                          user: str | None = None, password: str | None = None) -> str:
    """The connection string sqlpackage understands."""
    from app.core.config import settings

    default_user, default_password = credentials()
    return (f"Server=tcp:{host or settings.db_host},{port or settings.db_port};Database={database};"
            f"User ID={user or default_user};Password={password or default_password};"
            f"Encrypt={'True' if settings.db_encrypt else 'False'};"
            f"TrustServerCertificate={'True' if settings.db_trust_server_certificate else 'False'};"
            "Connection Timeout=30;")


def odbc_connect(database: str, host: str | None = None, port: int | None = None,
                 user: str | None = None, password: str | None = None):
    import pyodbc

    from app.core.config import settings

    default_user, default_password = credentials()
    return pyodbc.connect(
        f"DRIVER={{{settings.db_driver}}};SERVER={host or settings.db_host},{port or settings.db_port};"
        f"DATABASE={database};UID={user or default_user};PWD={password or default_password};"
        f"Encrypt={'yes' if settings.db_encrypt else 'no'};"
        f"TrustServerCertificate={'yes' if settings.db_trust_server_certificate else 'no'};",
        autocommit=True, timeout=30)


def row_counts(connection) -> dict[str, int]:
    rows = connection.cursor().execute(
        "SELECT s.name + '.' + t.name, SUM(p.rows) FROM sys.tables t "
        "JOIN sys.schemas s ON s.schema_id = t.schema_id "
        "JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1) "
        "WHERE t.is_ms_shipped = 0 GROUP BY s.name, t.name").fetchall()
    return {name: int(count) for name, count in rows}


def latest_migration(connection) -> str | None:
    row = connection.cursor().execute(
        "IF OBJECT_ID(N'dbo.schema_migrations') IS NOT NULL "
        "SELECT TOP 1 version FROM dbo.schema_migrations ORDER BY version DESC").fetchone()
    return row[0] if row else None


def is_azure_sql(connection) -> bool:
    return int(connection.cursor().execute("SELECT CAST(SERVERPROPERTY('EngineEdition') AS INT)").fetchone()[0]) == 5


def sqlpackage(*args: str) -> None:
    started = time.perf_counter()
    result = subprocess.run(["sqlpackage", *args], capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-15:])
        raise RuntimeError(f"sqlpackage {args[0]} failed after {time.perf_counter() - started:.0f}s:\n{tail}")


# ---- object store --------------------------------------------------------------

def s3_client():
    import boto3

    from app.core.config import settings

    kwargs = {"region_name": settings.s3_region or None}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key_id:
        kwargs["aws_access_key_id"] = settings.s3_access_key_id
        kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
    return boto3.client("s3", **kwargs)


def bucket() -> str:
    from app.core.config import settings

    name = os.environ.get("BACKUP_S3_BUCKET") or settings.s3_bucket
    if not name:
        raise SystemExit("✗ set BACKUP_S3_BUCKET (or S3_BUCKET)")
    return name


def prefix() -> str:
    from app.core.config import settings

    return f"{os.environ.get('BACKUP_S3_PREFIX', 'backups/').rstrip('/')}/{settings.db_name}/"


def list_backups(s3=None) -> list[dict]:
    """Manifests in the bucket, newest first."""
    s3 = s3 or s3_client()
    found: list[dict] = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket(), Prefix=prefix()):
        for obj in page.get("Contents", []):
            match = re.search(r"-(\d{8}T\d{6}Z)\.json$", obj["Key"])
            if match:
                found.append({"key": obj["Key"], "stamp": match.group(1),
                              "at": datetime.strptime(match.group(1), STAMP).replace(tzinfo=timezone.utc)})
    return sorted(found, key=lambda item: item["at"], reverse=True)


def to_delete(backups: list[dict], now: datetime, keep_days: int, keep_months: int) -> list[dict]:
    """Everything older than keep_days, except the first backup of each of
    the last keep_months months. Never deletes the newest backup."""
    if not backups:
        return []
    monthly_keep: set[str] = set()
    by_month: dict[str, dict] = {}
    for item in sorted(backups, key=lambda b: b["at"]):
        by_month.setdefault(item["at"].strftime("%Y-%m"), item)
    for month in sorted(by_month, reverse=True)[:keep_months]:
        monthly_keep.add(by_month[month]["key"])
    newest = max(backups, key=lambda b: b["at"])["key"]
    cutoff = now - timedelta(days=keep_days)
    return [b for b in backups if b["at"] < cutoff and b["key"] not in monthly_keep and b["key"] != newest]


# ---- the job --------------------------------------------------------------------

def run_backup() -> dict:
    from app.core.config import settings

    database = settings.db_name
    started = datetime.now(timezone.utc)
    stamp = started.strftime(STAMP)
    timings: dict[str, float] = {}
    source = database
    copy_name = None
    conn = odbc_connect(database)
    try:
        counts_before = row_counts(conn)
        migration = latest_migration(conn)
        azure = is_azure_sql(conn)
    finally:
        conn.close()

    with tempfile.TemporaryDirectory(prefix="recruitops-backup-") as work:
        bacpac = Path(work) / f"{database}-{stamp}.bacpac"
        t0 = time.perf_counter()
        if azure and os.environ.get("BACKUP_FROM_COPY", "1") != "0":
            copy_name = f"{database}_bkp_{stamp.lower()}"
            master = odbc_connect("master")
            try:
                master.cursor().execute(f"CREATE DATABASE [{copy_name}] AS COPY OF [{database}];")
                for _ in range(360):  # up to an hour
                    state = master.cursor().execute(
                        "SELECT state_desc FROM sys.databases WHERE name = ?", copy_name).fetchone()
                    if state and state[0] == "ONLINE":
                        break
                    time.sleep(10)
                else:
                    raise RuntimeError(f"database copy {copy_name} did not come online in an hour")
            finally:
                master.close()
            source = copy_name
        timings["copy_s"] = round(time.perf_counter() - t0, 1)
        try:
            t0 = time.perf_counter()
            sqlpackage("/Action:Export", f"/SourceConnectionString:{ado_connection_string(source)}",
                       f"/TargetFile:{bacpac}", "/p:VerifyFullTextDocumentTypesSupported=false")
            timings["export_s"] = round(time.perf_counter() - t0, 1)
        finally:
            if copy_name:
                master = odbc_connect("master")
                try:
                    master.cursor().execute(f"DROP DATABASE IF EXISTS [{copy_name}];")
                finally:
                    master.close()

        conn = odbc_connect(database)
        try:
            counts_after = counts_before if copy_name else row_counts(conn)
        finally:
            conn.close()

        digest = hashlib.sha256()
        with bacpac.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        changed = sorted(t for t in set(counts_before) | set(counts_after)
                         if counts_before.get(t) != counts_after.get(t))
        manifest = {
            "database": database,
            "created_at": started.isoformat(),
            "stamp": stamp,
            "app_version": settings.app_version,
            "latest_migration": migration,
            "engine": "azure-sql" if azure else "sql-server",
            "consistency": "database-copy" if copy_name else ("quiet" if not changed else "live-export"),
            "tables_changed_during_export": changed,
            "row_counts_before": counts_before,
            "row_counts_after": counts_after,
            "bacpac_sha256": digest.hexdigest(),
            "bacpac_bytes": bacpac.stat().st_size,
            "timings": timings,
        }

        s3 = s3_client()
        base = f"{prefix()}{started:%Y/%m}/{database}-{stamp}"
        extra = {"ServerSideEncryption": "AES256"} if not settings.s3_endpoint_url else {}
        t0 = time.perf_counter()
        s3.upload_file(str(bacpac), bucket(), f"{base}.bacpac", ExtraArgs=extra or None)
        s3.put_object(Bucket=bucket(), Key=f"{base}.json", Body=json.dumps(manifest, indent=2).encode(),
                      ContentType="application/json", **extra)
        timings["upload_s"] = round(time.perf_counter() - t0, 1)

    deleted = apply_retention(s3)
    try:
        versioning = s3.get_bucket_versioning(Bucket=bucket()).get("Status", "Disabled")
    except Exception:
        versioning = "unknown"
    return {"key": f"{base}.bacpac", "bytes": manifest["bacpac_bytes"], "tables": len(counts_before),
            "rows": sum(counts_before.values()), "consistency": manifest["consistency"],
            "timings": timings, "deleted_old": deleted, "bucket_versioning": versioning}


def apply_retention(s3) -> int:
    keep_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "35"))
    keep_months = int(os.environ.get("BACKUP_MONTHLY_KEEP", "12"))
    doomed = to_delete(list_backups(s3), datetime.now(timezone.utc), keep_days, keep_months)
    for item in doomed:
        stem = item["key"][: -len(".json")]
        s3.delete_objects(Bucket=bucket(), Delete={"Objects": [{"Key": stem + ".bacpac"}, {"Key": stem + ".json"}]})
    return len(doomed)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    opts = ap.parse_args()
    if opts.list:
        for item in list_backups():
            print(item["at"].isoformat(), item["key"])
        return
    print(json.dumps(run_backup(), indent=2, default=str))


if __name__ == "__main__":
    main()
