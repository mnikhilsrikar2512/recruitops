"""Restore-to-verify drill (Phase 6.6). Proves the newest backup can actually
be restored, and how long it takes.

    python scripts/restore_drill.py                 # newest backup
    python scripts/restore_drill.py --key <...json> # a specific one
    python scripts/restore_drill.py --keep          # leave the restored database for inspection

Steps, each timed:
  1. download the newest .bacpac and its manifest
  2. check the SHA-256 against the manifest
  3. import it into a new scratch database (recruitops_drill_<stamp>)
  4. verify: every table's row count is what the manifest recorded (inside
     the before/after window for live exports), the latest migration
     matches, and the app's own queries work against it
  5. drop the scratch database

The evidence report (JSON + Markdown) is uploaded next to the backups
under drills/ and printed. Exit code is non-zero if any check fails, so the
scheduler's heartbeat alerts the on-call owner.

The drill restores onto the server in DRILL_DB_HOST/PORT/USER/PASSWORD
(default: the app's server with the backup credentials), which must allow
CREATE DATABASE. Never point it at a name that exists: it refuses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import backup_db  # noqa: E402


def target() -> dict:
    from app.core.config import settings

    user, password = backup_db.credentials()
    return {"host": os.environ.get("DRILL_DB_HOST", settings.db_host),
            "port": int(os.environ.get("DRILL_DB_PORT", settings.db_port)),
            "user": os.environ.get("DRILL_DB_USER", user),
            "password": os.environ.get("DRILL_DB_PASSWORD", password)}


def compare_counts(manifest: dict, restored: dict[str, int]) -> list[str]:
    """Problems found; empty means every table matches."""
    before, after = manifest["row_counts_before"], manifest["row_counts_after"]
    problems: list[str] = []
    for table in sorted(set(before) | set(after) | set(restored)):
        if table not in restored:
            problems.append(f"{table}: missing after restore")
            continue
        low = min(before.get(table, 0), after.get(table, 0))
        high = max(before.get(table, 0), after.get(table, 0))
        if table not in before and table not in after:
            problems.append(f"{table}: not in the backup's manifest")
        elif not low <= restored[table] <= high:
            problems.append(f"{table}: {restored[table]} rows, expected {low}" + (f"..{high}" if high != low else ""))
    return problems


def app_checks(connection) -> dict:
    """A few of the queries the product depends on, against the restored copy."""
    cursor = connection.cursor()
    checks = {
        "companies": "SELECT COUNT(*) FROM dbo.tenants",
        "users": "SELECT COUNT(*) FROM dbo.users",
        "admin_role_grants": ("SELECT COUNT(*) FROM dbo.role_permissions rp JOIN dbo.roles r ON r.id = rp.role_id "
                              "WHERE r.code = N'admin' AND r.tenant_id IS NULL"),
        "legal_documents_in_force": "SELECT COUNT(*) FROM dbo.legal_documents WHERE status = N'active'",
        "metric_bucket_view": "SELECT COUNT(*) FROM dbo.vw_application_metric_state",
    }
    results = {}
    for name, sql in checks.items():
        try:
            results[name] = int(cursor.execute(sql).fetchone()[0])
        except Exception as exc:  # report, don't stop the drill
            results[name] = f"error: {exc.__class__.__name__}: {str(exc)[:120]}"
    return results


def run_drill(key: str | None = None, keep: bool = False) -> dict:
    s3 = backup_db.s3_client()
    backups = backup_db.list_backups(s3)
    if not backups:
        raise SystemExit("✗ no backups found to drill")
    chosen = next((b for b in backups if b["key"] == key), None) if key else backups[0]
    if not chosen:
        raise SystemExit(f"✗ no backup {key}")
    started = datetime.now(timezone.utc)
    drill_db = f"recruitops_drill_{started.strftime('%Y%m%d%H%M%S')}"
    where = target()
    timings: dict[str, float] = {}
    report: dict = {"backup": chosen["key"], "backup_taken_at": chosen["at"].isoformat(),
                    "backup_age_hours": round((started - chosen["at"]).total_seconds() / 3600, 1),
                    "drill_started_at": started.isoformat(), "restored_as": drill_db,
                    "target_server": f"{where['host']},{where['port']}"}
    ok = True
    with tempfile.TemporaryDirectory(prefix="recruitops-drill-") as work:
        t0 = time.perf_counter()
        manifest = json.loads(s3.get_object(Bucket=backup_db.bucket(), Key=chosen["key"])["Body"].read())
        bacpac = Path(work) / "restore.bacpac"
        s3.download_file(backup_db.bucket(), chosen["key"][: -len(".json")] + ".bacpac", str(bacpac))
        timings["download_s"] = round(time.perf_counter() - t0, 1)
        report["bacpac_bytes"] = bacpac.stat().st_size
        report["consistency"] = manifest.get("consistency")

        t0 = time.perf_counter()
        digest = hashlib.sha256()
        with bacpac.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        report["checksum_ok"] = digest.hexdigest() == manifest["bacpac_sha256"]
        ok &= report["checksum_ok"]
        timings["checksum_s"] = round(time.perf_counter() - t0, 1)

        master = backup_db.odbc_connect("master", **where)
        try:
            if master.cursor().execute("SELECT DB_ID(?)", drill_db).fetchone()[0] is not None:
                raise SystemExit(f"✗ {drill_db} already exists; refusing to touch it")
        finally:
            master.close()

        t0 = time.perf_counter()
        try:
            backup_db.sqlpackage("/Action:Import", f"/SourceFile:{bacpac}",
                                 f"/TargetConnectionString:{backup_db.ado_connection_string(drill_db, **where)}")
            report["import_ok"] = True
        except RuntimeError as exc:
            report["import_ok"] = False
            report["import_error"] = str(exc)[-2000:]
            ok = False
        timings["import_s"] = round(time.perf_counter() - t0, 1)

    try:
        if report.get("import_ok"):
            t0 = time.perf_counter()
            conn = backup_db.odbc_connect(drill_db, **where)
            try:
                restored = backup_db.row_counts(conn)
                problems = compare_counts(manifest, restored)
                report["tables"] = len(restored)
                report["rows"] = sum(restored.values())
                report["row_count_problems"] = problems
                report["latest_migration"] = backup_db.latest_migration(conn)
                report["migration_matches"] = report["latest_migration"] == manifest.get("latest_migration")
                report["app_checks"] = app_checks(conn)
            finally:
                conn.close()
            app_ok = all(isinstance(v, int) for v in report["app_checks"].values()) \
                and report["app_checks"].get("admin_role_grants", 0) > 0
            ok &= not problems and report["migration_matches"] and app_ok
            timings["verify_s"] = round(time.perf_counter() - t0, 1)
    finally:
        if not keep:
            t0 = time.perf_counter()
            master = backup_db.odbc_connect("master", **where)
            try:
                master.cursor().execute(f"DROP DATABASE IF EXISTS [{drill_db}];")
            finally:
                master.close()
            timings["drop_s"] = round(time.perf_counter() - t0, 1)

    report["timings"] = timings
    report["restore_time_minutes"] = round(
        (timings.get("download_s", 0) + timings.get("checksum_s", 0) + timings.get("import_s", 0)
         + timings.get("verify_s", 0)) / 60, 2)
    report["result"] = "PASS" if ok else "FAIL"
    upload_report(s3, report)
    return report


def markdown(report: dict) -> str:
    lines = [f"# Restore drill {report['drill_started_at'][:10]}: **{report['result']}**", "",
             f"- Backup: `{report['backup']}` (taken {report['backup_taken_at']}, {report['backup_age_hours']} h old)",
             f"- Consistency of the backup: {report.get('consistency')}",
             f"- Restored as `{report['restored_as']}` on {report['target_server']}",
             f"- Checksum: {'ok' if report.get('checksum_ok') else 'MISMATCH'}",
             f"- Import: {'ok' if report.get('import_ok') else 'FAILED'}",
             f"- Tables / rows: {report.get('tables')} / {report.get('rows')}",
             f"- Row-count problems: {len(report.get('row_count_problems', [])) or 'none'}",
             f"- Latest migration: {report.get('latest_migration')} "
             f"({'matches' if report.get('migration_matches') else 'DIFFERS'})",
             f"- App checks: {json.dumps(report.get('app_checks'))}",
             f"- **Time to restore: {report['restore_time_minutes']} minutes** "
             f"(download {report['timings'].get('download_s')} s, import {report['timings'].get('import_s')} s, "
             f"verify {report['timings'].get('verify_s')} s)"]
    for problem in report.get("row_count_problems", [])[:20]:
        lines.append(f"  - {problem}")
    if report.get("import_error"):
        lines += ["", "```", report["import_error"][-1500:], "```"]
    return "\n".join(lines) + "\n"


def upload_report(s3, report: dict) -> None:
    from app.core.config import settings

    base = f"{os.environ.get('BACKUP_S3_PREFIX', 'backups/').rstrip('/')}/drills/{settings.db_name}/" \
           f"{report['drill_started_at'][:19].replace(':', '')}"
    try:
        s3.put_object(Bucket=backup_db.bucket(), Key=f"{base}.json", Body=json.dumps(report, indent=2).encode(),
                      ContentType="application/json")
        s3.put_object(Bucket=backup_db.bucket(), Key=f"{base}.md", Body=markdown(report).encode(),
                      ContentType="text/markdown")
        report["report_key"] = f"{base}.md"
    except Exception as exc:
        report["report_upload_error"] = str(exc)[:200]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", help="manifest key (…json) to restore instead of the newest")
    ap.add_argument("--keep", action="store_true", help="don't drop the restored database")
    opts = ap.parse_args()
    report = run_drill(opts.key, opts.keep)
    print(markdown(report))
    raise SystemExit(0 if report["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
