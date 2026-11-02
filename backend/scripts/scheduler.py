"""Recurring jobs (Phase 6.6). One long-running process:

    python scripts/scheduler.py                 # run forever (the "scheduler" container)
    python scripts/scheduler.py --run-once privacy_jobs
    python scripts/scheduler.py --list

Any number of copies may run: each job takes a database application lock
(sp_getapplock) before it starts, so a job never runs twice at once and a
second replica simply skips it.

Every run logs one JSON line (job, outcome, duration, result) and, when
``JOB_HEARTBEAT_URL`` is set, pings ``<url>/<job>`` on success and
``<url>/<job>/fail`` on failure. That is the healthchecks.io / Cronitor /
Better Uptime convention: the service alerts the on-call owner when a ping
says "fail" *or* when an expected ping never arrives (a dead scheduler).

The process also touches ``/tmp/recruitops/scheduler-heartbeat`` every loop;
the container health check reads its age.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import signal
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("recruitops.scheduler")
HEARTBEAT_FILE = Path(os.environ.get("SCHEDULER_HEARTBEAT_FILE", "/tmp/recruitops/scheduler-heartbeat"))


# ---- jobs ----------------------------------------------------------------------

def _engine():
    from app.db.session import create_db_engine

    return create_db_engine()


def job_privacy(engine) -> dict:
    """Company purges past their 7-day wait, audit-hold releases, expired export zips."""
    from app.services.privacy import run_due_jobs

    return run_due_jobs(engine)


def job_sessions(engine) -> dict:
    from app.repositories.auth import purge_stale_sessions

    days = int(os.environ.get("SESSION_RETENTION_DAYS", "30"))
    return {"sessions_removed": purge_stale_sessions(engine, days), "older_than_days": days}


def job_housekeeping(engine) -> dict:
    """Rows that only matter for a short while."""
    from sqlalchemy import text

    removed: dict[str, int] = {}
    with engine.begin() as connection:
        removed["upload_idempotency"] = connection.execute(text(
            "DELETE FROM dbo.upload_idempotency WHERE created_at < DATEADD(day, -2, SYSUTCDATETIME())")).rowcount or 0
        removed["password_reset_tokens"] = connection.execute(text(
            "DELETE FROM dbo.password_reset_tokens WHERE expires_at < DATEADD(day, -30, SYSUTCDATETIME())")).rowcount or 0
    return removed


def job_db_backup(engine) -> dict:
    """Nightly portable .bacpac to the object store (needs the ops image)."""
    from backup_db import run_backup

    return run_backup()


def job_restore_drill(engine) -> dict:
    """Monthly: restore the newest backup into a scratch DB and verify it."""
    from restore_drill import run_drill

    report = run_drill()
    if report["result"] != "PASS":
        raise RuntimeError(f"restore drill failed: {report.get('report_key') or report}")
    return {k: report.get(k) for k in ("result", "backup", "restore_time_minutes", "tables", "rows", "report_key")}


def job_audit_retention(engine) -> dict:
    """Off unless AUDIT_RETENTION_DAYS is set (an owner decision: how long the
    audit trail is kept). Deletes in batches; rows on the privacy hold are
    already outside dbo.audit_logs."""
    from sqlalchemy import text

    days = int(os.environ.get("AUDIT_RETENTION_DAYS", "0"))
    if days <= 0:
        return {"skipped": "AUDIT_RETENTION_DAYS not set: audit logs are kept indefinitely"}
    if days < 365:
        raise RuntimeError("AUDIT_RETENTION_DAYS below 365 is refused; keep at least a year of audit history")
    removed = 0
    while True:
        with engine.begin() as connection:
            batch = connection.execute(text(
                "DELETE TOP (5000) FROM dbo.audit_logs WHERE created_at < DATEADD(day, -:d, SYSUTCDATETIME())"),
                {"d": days}).rowcount or 0
        removed += batch
        if batch < 5000:
            return {"audit_rows_removed": removed, "older_than_days": days}


def job_mfa_rewrap(engine) -> dict:
    """After a key rotation, re-encrypts seeds still under an older key."""
    from encrypt_mfa_secrets import rewrap_all

    return rewrap_all(engine)


@dataclass(frozen=True)
class Job:
    name: str
    run: Callable[[object], dict]
    every: timedelta | None = None   # fixed interval ...
    daily_at: tuple[int, int] | None = None  # ... or once a day at (hour, minute) UTC
    monthly_on: int | None = None    # with daily_at: only on this day of the month
    description: str = ""
    needs_ops_image: bool = False    # sqlpackage

    def next_after(self, moment: datetime) -> datetime:
        if self.every is not None:
            return moment + self.every
        hour, minute = self.daily_at or (0, 0)
        candidate = moment.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= moment:
            candidate += timedelta(days=1)
        if self.monthly_on is not None:
            while candidate.day != self.monthly_on:
                candidate += timedelta(days=1)
        return candidate


JOBS: dict[str, Job] = {job.name: job for job in (
    Job("privacy_jobs", job_privacy, every=timedelta(hours=1),
        description="company purges, audit-hold releases, expired exports (hourly)"),
    Job("cleanup_sessions", job_sessions, daily_at=(21, 0),
        description="delete sign-ins ended > SESSION_RETENTION_DAYS ago (daily 02:30 IST)"),
    Job("housekeeping", job_housekeeping, daily_at=(21, 15),
        description="old upload idempotency keys and long-expired reset links (daily)"),
    Job("mfa_rewrap", job_mfa_rewrap, daily_at=(21, 30),
        description="re-wrap two-step seeds after a key rotation (daily; no-op otherwise)"),
    Job("audit_retention", job_audit_retention, daily_at=(21, 45),
        description="delete audit rows older than AUDIT_RETENTION_DAYS (off unless set)"),
    Job("db_backup", job_db_backup, daily_at=(20, 30), needs_ops_image=True,
        description="portable .bacpac backup to the object store (daily 02:00 IST)"),
    Job("restore_drill", job_restore_drill, daily_at=(22, 30), monthly_on=1, needs_ops_image=True,
        description="restore the newest backup into a scratch DB and verify it (monthly, 1st, 04:00 IST)"),
)}


# ---- running -------------------------------------------------------------------

def _ping(job: str, ok: bool) -> None:
    base = os.environ.get("JOB_HEARTBEAT_URL", "").rstrip("/")
    if not base:
        return
    try:
        urllib.request.urlopen(f"{base}/{job}{'' if ok else '/fail'}", timeout=10).read()
    except Exception:
        logger.warning("heartbeat ping failed for %s", job, exc_info=True)


class _AppLock:
    """Session-level SQL Server application lock; skips (not waits) when held."""

    def __init__(self, engine, name: str) -> None:
        self.engine, self.name, self.connection, self.acquired = engine, f"recruitops:job:{name}", None, False

    def __enter__(self) -> "_AppLock":
        from sqlalchemy import text

        self.connection = self.engine.connect()
        result = self.connection.execute(text(
            "SET NOCOUNT ON; DECLARE @r INT; EXEC @r = sp_getapplock @Resource = :n, @LockMode = 'Exclusive', "
            "@LockOwner = 'Session', @LockTimeout = 0; SELECT @r;"), {"n": self.name}).scalar()
        self.connection.commit()
        self.acquired = result is not None and result >= 0
        return self

    def __exit__(self, *exc) -> None:
        from sqlalchemy import text

        try:
            if self.acquired:
                self.connection.execute(text("EXEC sp_releaseapplock @Resource = :n, @LockOwner = 'Session';"),
                                        {"n": self.name})
                self.connection.commit()
        finally:
            self.connection.close()


def run_job(job: Job, engine=None) -> bool:
    engine = engine or _engine()
    started = time.perf_counter()
    try:
        with _AppLock(engine, job.name) as lock:
            if not lock.acquired:
                logger.info("job skipped (running elsewhere)", extra={"job": job.name, "outcome": "skipped"})
                return True
            result = job.run(engine)
        logger.info("job finished", extra={"job": job.name, "outcome": "ok",
                                           "duration_ms": round((time.perf_counter() - started) * 1000),
                                           "result": json.loads(json.dumps(result, default=str))})
        _ping(job.name, True)
        return True
    except Exception:
        logger.exception("job failed", extra={"job": job.name, "outcome": "failed",
                                              "duration_ms": round((time.perf_counter() - started) * 1000)})
        _ping(job.name, False)
        return False


_stopping = False


def _stop(*_args) -> None:
    global _stopping
    _stopping = True


def loop(jobs: list[Job], tick_seconds: float = 30.0) -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    now = datetime.now(timezone.utc)
    # Interval jobs run once at start (catch up after a deploy); daily ones wait for their time.
    due = {job.name: (now if job.every else job.next_after(now)) for job in jobs}
    logger.info("scheduler started", extra={"jobs": {name: when.isoformat() for name, when in due.items()}})
    engine = _engine()
    while not _stopping:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.touch()
        now = datetime.now(timezone.utc)
        for job in jobs:
            if now >= due[job.name] and not _stopping:
                run_job(job, engine)
                due[job.name] = job.next_after(datetime.now(timezone.utc))
        time.sleep(tick_seconds)
    logger.info("scheduler stopped")


def main() -> None:
    from app.core.observability import configure_logging

    configure_logging()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-once", metavar="JOB", choices=sorted(JOBS), help="run one job now and exit")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", nargs="*", choices=sorted(JOBS), help="schedule only these jobs")
    opts = ap.parse_args()
    if opts.list:
        for job in JOBS.values():
            print(f"{job.name:18} {job.description}")
        return
    if opts.run_once:
        raise SystemExit(0 if run_job(JOBS[opts.run_once]) else 1)
    names = opts.only or [name for name, job in JOBS.items()
                          if not job.needs_ops_image or shutil.which("sqlpackage")]
    skipped = sorted(set(JOBS) - set(names))
    if skipped and not opts.only:
        logger.warning("sqlpackage not found (not the ops image): not scheduling %s", ", ".join(skipped))
    loop([JOBS[name] for name in names])


if __name__ == "__main__":
    main()
